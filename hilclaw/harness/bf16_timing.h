/*
 * Shared code of the bf16 timing programs (ADR-0181 decision 2), included after
 * _POSIX_C_SOURCE and PROGRAM are defined. It takes the generator, the argument
 * rules, the error line and the report descriptor from bf16_verification.h, and
 * keeps the arguments, clock, loop, stopping rule, report and exit statuses of
 * timing_driver.c (ADR-0009), status 5 being a timed interval of 0 ns. A program
 * runs its one kernel call as
 *
 *     for (timing_open(&t); timing_begin(&t); timing_end(&t))
 *         <kernel call>;
 *     timing_close(&t);
 *
 * The first pass is the untimed call: no reading precedes it and the one that
 * follows it is dropped. On later passes only the call lies between the last
 * action of timing_begin and the first of timing_end, the two clock readings.
 */
#ifndef BF16_TIMING_H
#define BF16_TIMING_H

#include "bf16_verification.h"

#include <float.h>
#include <inttypes.h>
#include <string.h>
#include <time.h>

enum { STATUS_ZERO_INTERVAL = 5 };

#define TIMING_USAGE "<n_min> <n_max> <cv_max> <sample_form> <seed>"

struct timing {
    size_t n_min, n_max, count, calls;
    double cv_max, *samples;
    uint64_t seed;
    int reciprocal, report, started, stopped, state;
    struct timespec before, after;
};

static inline void timing_arguments(struct timing *t, char **argv)
{
    char *end;

    t->n_min = (size_t)digits("n_min", argv[0], 2, SIZE_MAX);
    t->n_max = (size_t)digits("n_max", argv[1], t->n_min, SIZE_MAX);
    t->cv_max = strtod(argv[2], &end);
    if (end == argv[2] || *end != '\0' || !(t->cv_max > 0.0) || t->cv_max > DBL_MAX)
        exit(fail(STATUS_COMMAND_LINE, "cv_max", "must be a positive finite number"));
    t->reciprocal = strcmp(argv[3], "reciprocal") == 0;
    if (!t->reciprocal && strcmp(argv[3], "interval") != 0)
        exit(fail(STATUS_COMMAND_LINE, "sample_form", "must be interval or reciprocal"));
    t->seed = digits("seed", argv[4], 0, UINT64_MAX);
}

static inline void timing_emit_value(const struct timing *t, const char *keyword, uint64_t value)
{
    char line[64];
    int length = snprintf(line, sizeof line, "%s %" PRIu64 "\n", keyword, value);

    emit(t->report, line, (size_t)length);
}

static inline int timing_elapsed_ns(const struct timespec *from, const struct timespec *to, uint64_t *ns)
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
static inline int timing_converged(const double *samples, size_t count, double cv_max)
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

static inline void timing_open(struct timing *t)
{
    struct timespec origin, resolution;
    size_t bytes;
    uint64_t ns = 0;

    t->count = 0;
    t->calls = 0;
    t->state = 0;
    if (!byte_size(t->n_max, 1, sizeof(double), &bytes))
        exit(fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t"));
    t->samples = malloc(bytes);
    if (t->samples == NULL)
        exit(fail(STATUS_MEMORY, "malloc", "cannot allocate the samples"));
    t->report = report_open();
    origin.tv_sec = 0;
    origin.tv_nsec = 0;
    if (clock_getres(CLOCK_MONOTONIC, &resolution) != 0 || !timing_elapsed_ns(&origin, &resolution, &ns))
        exit(fail(STATUS_SYSTEM, "clock_getres", "cannot read the resolution of CLOCK_MONOTONIC"));
    timing_emit_value(t, "resolution_ns", ns);
}

static inline int timing_begin(struct timing *t)
{
    if (t->state != 0)
        return 0;
    if (t->calls++ > 0)
        t->started = clock_gettime(CLOCK_MONOTONIC, &t->before);
    return 1;
}

static inline void timing_end(struct timing *t)
{
    uint64_t ns = 0;

    t->stopped = clock_gettime(CLOCK_MONOTONIC, &t->after);
    if (t->calls == 1)
        return;
    if (t->started != 0 || t->stopped != 0 || !timing_elapsed_ns(&t->before, &t->after, &ns))
        exit(fail(STATUS_SYSTEM, "clock_gettime", "cannot read an interval of the clock"));
    timing_emit_value(t, "interval_ns", ns);
    if (ns == 0)
        exit(fail(STATUS_ZERO_INTERVAL, "interval", "an interval of 0 ns is not a sample"));
    t->samples[t->count++] = t->reciprocal ? 1.0 / (double)ns : (double)ns;
    if (t->count >= t->n_min && timing_converged(t->samples, t->count, t->cv_max))
        t->state = 1;
    else if (t->count == t->n_max)
        t->state = 2;
}

static inline void timing_close(struct timing *t)
{
    const char *line = t->state == 1 ? "stop converged\n" : "stop not_converged\n";

    emit(t->report, line, strlen(line));
    free(t->samples);
}

#endif
