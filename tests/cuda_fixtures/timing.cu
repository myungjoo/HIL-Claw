/*
 * Test fixture: a timing run of ADR-0009 on the machine's GPU (ADR-0194 decision 4).
 *
 *     <program> <m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>
 *
 * The eight arguments are those of hilclaw/harness/timing.py (driver_arguments),
 * with the same rules as hilclaw/harness/timing_driver.c. The work is one launch
 * per repeat of a naive fp32 product C = A B (A m x k, B k x n, one thread per
 * element of C, 256 threads a block); the operands are integers 0 to 7 drawn
 * from seed by splitmix64, so every element of C is exact and is checked.
 *
 * Outside the interval: creating the device context (cudaFree(0)), host and
 * device allocation, input generation, the copies to the device, one untimed
 * launch and wait, the copy back and the check. Before each start reading,
 * cudaDeviceSynchronize waits for all earlier work. Inside: the launch, its
 * cudaGetLastError and the cudaDeviceSynchronize that waits for its completion,
 * between two readings of CLOCK_MONOTONIC, whose resolution is resolution_ns.
 * No device event timer is used.
 *
 * Build-time modes, set by -D in the test target's flags (nothing else is read):
 *   TIMING_HOLD_NS=<ns>  thread 0 also spins until %globaltimer advanced <ns>
 *   TIMING_FAULT=1       one cudaMalloc of 1024 times the device's total memory
 *   TIMING_FAULT=2       thread 0 writes through a null pointer
 *   TIMING_FAULT=3       thread 0 spins and never ends
 *
 * The report of ADR-0009 decision 8 goes to the standard output the process
 * was started with; descriptor 1 is pointed at standard error first, as in
 * timing_driver.c. Exit status: 1 a CUDA call or a wrong product; 2 the command
 * line; 3 the sizes or a host allocation; 4 the clock, a descriptor or a write;
 * 5 an interval of 0 ns. A non-zero status comes with one line on standard
 * error and without a "stop" line.
 */
#define _POSIX_C_SOURCE 200809L

#ifdef _WIN32
#error "this fixture reads CLOCK_MONOTONIC and builds on POSIX hosts only"
#endif

#include <errno.h>
#include <float.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

#include <cuda_runtime.h>

#ifndef TIMING_HOLD_NS
#define TIMING_HOLD_NS 0
#endif
#ifndef TIMING_FAULT
#define TIMING_FAULT 0
#endif

#define THREADS 256
#define K_EXACT 342391u
#define OVER 1024

enum {
    STATUS_CUDA = 1,
    STATUS_COMMAND_LINE = 2,
    STATUS_MEMORY = 3,
    STATUS_SYSTEM = 4,
    STATUS_ZERO_INTERVAL = 5
};

static int report_fd = -1;

__device__ static unsigned long long global_ns(void)
{
    unsigned long long t;

    asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(t));
    return t;
}

__global__ static void product(size_t m, size_t k, size_t n, const float *a, const float *b, float *c,
                               unsigned long long hold_ns)
{
    size_t i = (size_t)blockIdx.x * THREADS + threadIdx.x;
    float sum = 0.0f;
    size_t j;

    if (i == 0) {
        unsigned long long start = global_ns();

        if (TIMING_FAULT == 2)
            *(volatile float *)0 = 1.0f;
        while (global_ns() - start < hold_ns)
            ;
    }
    if (i >= m * n)
        return;
    for (j = 0; j < k; j++)
        sum += a[i / n * k + j] * b[j * n + i % n];
    c[i] = sum;
}

static int fail(int status, const char *subject, const char *message)
{
    fprintf(stderr, "timing: %s: %s\n", subject, message);
    return status;
}

static void check(cudaError_t error, const char *call)
{
    if (error != cudaSuccess) {
        fprintf(stderr, "timing: %s: %s: %s\n", call, cudaGetErrorName(error), cudaGetErrorString(error));
        exit(STATUS_CUDA);
    }
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

static uint64_t splitmix64(uint64_t *state)
{
    uint64_t z = (*state += UINT64_C(0x9E3779B97F4A7C15));

    z = (z ^ (z >> 30)) * UINT64_C(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94D049BB133111EB);
    return z ^ (z >> 31);
}

static void fill(float *array, size_t count, uint64_t *state)
{
    size_t i;

    for (i = 0; i < count; i++)
        array[i] = (float)(splitmix64(state) >> 61);
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

static int clock_now(uint64_t *ns)
{
    struct timespec t;

    if (clock_gettime(CLOCK_MONOTONIC, &t) != 0 || t.tv_sec < 0)
        return 0;
    *ns = (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
    return 1;
}

/* ADR-0007 decision 4 as CV^2 < cv_max^2, as in timing_driver.c. */
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

static int product_wrong(size_t m, size_t k, size_t n, const float *a, const float *b, const float *c)
{
    size_t i, j, l;

    for (i = 0; i < m; i++)
        for (j = 0; j < n; j++) {
            uint64_t sum = 0;

            for (l = 0; l < k; l++)
                sum += (uint64_t)a[i * k + l] * (uint64_t)b[l * n + j];
            if (c[i * n + j] != (float)sum)
                return 1;
        }
    return 0;
}

static void launch(size_t m, size_t k, size_t n, const float *a, const float *b, float *c)
{
    unsigned long long hold_ns = TIMING_FAULT == 3 ? ~0ull : (unsigned long long)TIMING_HOLD_NS;

    product<<<(unsigned)((m * n + THREADS - 1) / THREADS), THREADS>>>(m, k, n, a, b, c, hold_ns);
    check(cudaGetLastError(), "product launch");
    check(cudaDeviceSynchronize(), "cudaDeviceSynchronize");
}

int main(int argc, char **argv)
{
    size_t m, k, n, n_min, n_max, done = 0;
    uint64_t seed, ns, before, after;
    double cv_max, *samples;
    float *a, *b, *c, *da, *db, *dc;
    char *end;
    int reciprocal, state = 0;
    struct timespec resolution;

    if (argc != 9)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>");
    m = (size_t)digits("m", argv[1], 1, UINT32_MAX);
    k = (size_t)digits("k", argv[2], 1, UINT32_MAX);
    n = (size_t)digits("n", argv[3], 1, UINT32_MAX);
    n_min = (size_t)digits("n_min", argv[4], 2, SIZE_MAX);
    n_max = (size_t)digits("n_max", argv[5], n_min, SIZE_MAX);
    cv_max = strtod(argv[6], &end);
    if (end == argv[6] || *end != '\0' || !(cv_max > 0.0) || cv_max > DBL_MAX)
        return fail(STATUS_COMMAND_LINE, "cv_max", "must be a positive finite number");
    reciprocal = strcmp(argv[7], "reciprocal") == 0;
    if (!reciprocal && strcmp(argv[7], "interval") != 0)
        return fail(STATUS_COMMAND_LINE, "sample_form", "must be interval or reciprocal");
    seed = digits("seed", argv[8], 0, UINT64_MAX);

    if (k > K_EXACT || m > (size_t)INT32_MAX * THREADS / n || m > SIZE_MAX / sizeof(float) / k ||
        n > SIZE_MAX / sizeof(float) / k || n_max > SIZE_MAX / sizeof(double))
        return fail(STATUS_MEMORY, "sizes", "the matrices or the samples are too large");
    a = (float *)malloc(m * k * sizeof(float));
    b = (float *)malloc(k * n * sizeof(float));
    c = (float *)malloc(m * n * sizeof(float));
    samples = (double *)malloc(n_max * sizeof(double));
    if (a == NULL || b == NULL || c == NULL || samples == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the matrices and the samples");
    fill(a, m * k, &seed);
    fill(b, k * n, &seed);

    report_fd = dup(STDOUT_FILENO);
    if (report_fd < 0 || dup2(STDERR_FILENO, STDOUT_FILENO) < 0)
        return fail(STATUS_SYSTEM, "descriptors", "cannot keep the standard output apart");

    check(cudaFree(0), "cudaFree");
    if (TIMING_FAULT == 1) {
        size_t free_bytes, total_bytes;
        void *all;

        check(cudaMemGetInfo(&free_bytes, &total_bytes), "cudaMemGetInfo");
        check(cudaMalloc(&all, OVER * total_bytes), "cudaMalloc");
    }
    check(cudaMalloc((void **)&da, m * k * sizeof(float)), "cudaMalloc");
    check(cudaMalloc((void **)&db, k * n * sizeof(float)), "cudaMalloc");
    check(cudaMalloc((void **)&dc, m * n * sizeof(float)), "cudaMalloc");
    check(cudaMemcpy(da, a, m * k * sizeof(float), cudaMemcpyHostToDevice), "cudaMemcpy");
    check(cudaMemcpy(db, b, k * n * sizeof(float), cudaMemcpyHostToDevice), "cudaMemcpy");

    if (clock_getres(CLOCK_MONOTONIC, &resolution) != 0 || resolution.tv_sec < 0)
        return fail(STATUS_SYSTEM, "clock", "cannot read the resolution of the monotonic clock");
    emit_value("resolution_ns", (uint64_t)resolution.tv_sec * UINT64_C(1000000000) + (uint64_t)resolution.tv_nsec);

    launch(m, k, n, da, db, dc);
    while (state == 0) {
        int started;

        check(cudaDeviceSynchronize(), "cudaDeviceSynchronize");
        started = clock_now(&before);
        launch(m, k, n, da, db, dc);
        if (!clock_now(&after) || !started || after < before)
            return fail(STATUS_SYSTEM, "clock", "cannot read an interval of the monotonic clock");
        ns = after - before;
        emit_value("interval_ns", ns);
        if (ns == 0)
            return fail(STATUS_ZERO_INTERVAL, "interval", "an interval of 0 ns is not a sample");
        samples[done++] = reciprocal ? 1.0 / (double)ns : (double)ns;
        if (done >= n_min && converged(samples, done, cv_max))
            state = 1;
        else if (done == n_max)
            state = 2;
    }
    check(cudaMemcpy(c, dc, m * n * sizeof(float), cudaMemcpyDeviceToHost), "cudaMemcpy");
    if (product_wrong(m, k, n, a, b, c))
        return fail(STATUS_CUDA, "product", "wrong product");
    check(cudaFree(dc), "cudaFree");
    check(cudaFree(db), "cudaFree");
    check(cudaFree(da), "cudaFree");
    emit(state == 1 ? "stop converged\n" : "stop not_converged\n");
    free(samples);
    free(c);
    free(b);
    free(a);
    return 0;
}
