/*
 * Driver program of a timing run (ADR-0009).
 *
 * Built with the source files of one kernel of ADR-0008 into one timing
 * executable, it prepares the operands, calls the kernel once untimed and then
 * times one call per repeat until the stopping rule of ADR-0007 decision 4 ends
 * the measurement. It needs the C library and POSIX.1-2008 only (no -lm).
 *
 * Command line, exactly eight arguments (hilclaw/harness/timing.py):
 *
 *     <m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>
 *
 * m, k, n, n_min, n_max and seed are decimal digits with no sign, no space and
 * no leading zero: m, k, n >= 1, n_min >= 2, n_max >= n_min, seed < 2^64.
 * cv_max is a positive finite number that strtod reads wholly, and sample_form
 * is the word "interval" or "reciprocal". No argument has a default, and no
 * standard input, file or environment variable is read.
 *
 * Report, on the standard output the process was started with: one
 * "resolution_ns <i>" line before the first call, one "interval_ns <i>" line
 * per repeat when it is taken, and a last line "stop converged" or
 * "stop not_converged". Descriptor 1 is pointed at standard error before the
 * first call, so what a kernel prints is not part of the report.
 *
 * Exit status:
 *   0  the stopping rule ended the run; follows a "stop" line and nothing else
 *   2  the command line
 *   3  an array whose size cannot be held or that cannot be allocated
 *   4  the clock, a descriptor or a write of the report
 *   5  a timed interval of 0 ns (its "interval_ns 0" line is written)
 * A status other than 0 comes with one line on standard error and without a
 * "stop" line.
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <float.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);

typedef void gemm_function(size_t, size_t, size_t, const float *restrict,
                           const float *restrict, float *restrict);

enum {
    STATUS_COMMAND_LINE = 2,
    STATUS_MEMORY = 3,
    STATUS_SYSTEM = 4,
    STATUS_ZERO_INTERVAL = 5
};

/* Read through volatile, so that no build knows the callee and drops a call with unread output. */
static gemm_function *volatile kernel = hilclaw_gemm;
static int report_fd = -1;

static int fail(int status, const char *subject, const char *message)
{
    fprintf(stderr, "timing_driver: %s: %s\n", subject, message);
    return status;
}

static uint64_t digits(const char *name, const char *text, uint64_t minimum, uint64_t maximum)
{
    const char *rule = "must be decimal digits (no sign, space or leading zero) within its range";
    uint64_t value = 0;
    const char *p = text;
    int valid = *p != '\0' && (p[0] != '0' || p[1] == '\0');

    for (; valid && *p != '\0'; p++) {
        uint64_t digit = (uint64_t)(*p - '0');

        valid = *p >= '0' && *p <= '9' && digit <= maximum && value <= (maximum - digit) / 10;
        if (valid)
            value = value * 10 + digit;
    }
    if (!valid || value < minimum)
        exit(fail(STATUS_COMMAND_LINE, name, rule));
    return value;
}

static int byte_size(size_t rows, size_t columns, size_t element, size_t *bytes)
{
    if (rows > SIZE_MAX / element / columns)
        return 0;
    *bytes = rows * columns * element;
    return 1;
}

static uint64_t splitmix64(uint64_t *state)
{
    uint64_t z = (*state += UINT64_C(0x9E3779B97F4A7C15));

    z = (z ^ (z >> 30)) * UINT64_C(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94D049BB133111EB);
    return z ^ (z >> 31);
}

/* Each element is +-(0.5 + u * 2^-24) with u of 23 bits: exact in float, magnitude in [0.5, 1). */
static void fill(float *array, size_t count, uint64_t *state)
{
    size_t i;

    for (i = 0; i < count; i++) {
        uint64_t bits = splitmix64(state);
        float magnitude = 0.5f + (float)(bits >> 41) / 16777216.0f;

        array[i] = (bits & 1) != 0 ? -magnitude : magnitude;
    }
}

static void emit(const char *text)
{
    size_t left = strlen(text);

    while (left > 0) {
        ssize_t written = write(report_fd, text, left);

        if (written < 0 && errno == EINTR)
            continue;
        if (written <= 0)
            exit(fail(STATUS_SYSTEM, "report", "cannot write to the standard output"));
        text += written;
        left -= (size_t)written;
    }
}

static void emit_value(const char *keyword, uint64_t value)
{
    char line[64];

    snprintf(line, sizeof line, "%s %" PRIu64 "\n", keyword, value);
    emit(line);
}

static int elapsed_ns(const struct timespec *from, const struct timespec *to, uint64_t *ns)
{
    uint64_t seconds;
    long nanoseconds = to->tv_nsec - from->tv_nsec;

    if (from->tv_sec < 0 || to->tv_sec < from->tv_sec)
        return 0;
    seconds = (uint64_t)to->tv_sec - (uint64_t)from->tv_sec;
    if (nanoseconds < 0) {
        if (seconds == 0)
            return 0;
        seconds -= 1;
        nanoseconds += 1000000000L;
    }
    if (seconds > (UINT64_MAX - 999999999) / 1000000000)
        return 0;
    *ns = seconds * 1000000000 + (uint64_t)nanoseconds;
    return 1;
}

/* ADR-0007 decision 4 as CV^2 < cv_max^2, so that no square root is needed. */
static int converged(const double *samples, size_t count, double cv_max)
{
    double sum = 0.0, squares = 0.0, mean;
    size_t i;

    for (i = 0; i < count; i++)
        sum += samples[i];
    mean = sum / (double)count;
    for (i = 0; i < count; i++) {
        double deviation = (samples[i] - mean) / mean;

        squares += deviation * deviation;
    }
    return squares < cv_max * cv_max * (double)(count - 1);
}

int main(int argc, char **argv)
{
    size_t m, k, n, n_min, n_max, a_bytes, b_bytes, c_bytes, sample_bytes, count = 0;
    uint64_t seed, ns = 0;
    double cv_max, *samples;
    float *a, *b, *c;
    char *end;
    int reciprocal, started, stopped, state = 0;
    struct timespec origin, resolution, before, after;
    gemm_function *call;

    if (argc != 9)
        return fail(STATUS_COMMAND_LINE, "usage",
                    "<m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>");
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    k = (size_t)digits("k", argv[2], 1, SIZE_MAX);
    n = (size_t)digits("n", argv[3], 1, SIZE_MAX);
    n_min = (size_t)digits("n_min", argv[4], 2, SIZE_MAX);
    n_max = (size_t)digits("n_max", argv[5], n_min, SIZE_MAX);
    cv_max = strtod(argv[6], &end);
    if (end == argv[6] || *end != '\0' || !(cv_max > 0.0) || cv_max > DBL_MAX)
        return fail(STATUS_COMMAND_LINE, "cv_max", "must be a positive finite number");
    reciprocal = strcmp(argv[7], "reciprocal") == 0;
    if (!reciprocal && strcmp(argv[7], "interval") != 0)
        return fail(STATUS_COMMAND_LINE, "sample_form", "must be interval or reciprocal");
    seed = digits("seed", argv[8], 0, UINT64_MAX);

    if (!byte_size(m, k, sizeof(float), &a_bytes) || !byte_size(k, n, sizeof(float), &b_bytes) ||
        !byte_size(m, n, sizeof(float), &c_bytes) ||
        !byte_size(n_max, 1, sizeof(double), &sample_bytes))
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    a = malloc(a_bytes);
    b = malloc(b_bytes);
    c = malloc(c_bytes);
    samples = malloc(sample_bytes);
    if (a == NULL || b == NULL || c == NULL || samples == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands and the samples");
    fill(a, m * k, &seed);
    fill(b, k * n, &seed);

    report_fd = dup(STDOUT_FILENO);
    if (report_fd < 0 || dup2(STDERR_FILENO, STDOUT_FILENO) < 0)
        return fail(STATUS_SYSTEM, "descriptors", "cannot keep the standard output apart");
    origin.tv_sec = 0;
    origin.tv_nsec = 0;
    if (clock_getres(CLOCK_MONOTONIC, &resolution) != 0 || !elapsed_ns(&origin, &resolution, &ns))
        return fail(STATUS_SYSTEM, "clock_getres", "cannot read the resolution of CLOCK_MONOTONIC");
    emit_value("resolution_ns", ns);

    call = kernel;
    call(m, k, n, a, b, c);
    while (state == 0) {
        started = clock_gettime(CLOCK_MONOTONIC, &before);
        call(m, k, n, a, b, c);
        stopped = clock_gettime(CLOCK_MONOTONIC, &after);
        if (started != 0 || stopped != 0 || !elapsed_ns(&before, &after, &ns))
            return fail(STATUS_SYSTEM, "clock_gettime", "cannot read an interval of the clock");
        emit_value("interval_ns", ns);
        if (ns == 0)
            return fail(STATUS_ZERO_INTERVAL, "interval", "an interval of 0 ns is not a sample");
        samples[count++] = reciprocal ? 1.0 / (double)ns : (double)ns;
        if (count >= n_min && converged(samples, count, cv_max))
            state = 1;
        else if (count == n_max)
            state = 2;
    }
    emit(state == 1 ? "stop converged\n" : "stop not_converged\n");
    free(samples);
    free(c);
    free(b);
    free(a);
    return 0;
}
