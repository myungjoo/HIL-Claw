/*
 * Timing program of a bf16 timing run of swiglu (ADR-0181 decision 2).
 *
 * Built with the source files of one kernel of ADR-0160 into one timing
 * executable, it draws the inputs once, calls the kernel once untimed and then
 * times one call per repeat until the stopping rule of ADR-0007 decision 4
 * ends the measurement, as timing_driver.c does for fp32 (ADR-0009). It does
 * no floating-point arithmetic on the operands and needs the C library and
 * POSIX.1-2008 only (no -lm); a kernel that calls expf needs the caller's -lm.
 *
 * Command line, exactly seven arguments:
 *
 *     <m> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>
 *
 * with the spelling, bounds and refusals of timing_driver.c.
 *
 * Inputs: gate (m*n) and up (m*n), one malloc each, filled once before the
 * untimed call by the generator of bf16_verification.h with the seed of the
 * command line, draw 0, bits = 10 for gate and bits = 8 for up, exactly as
 * bf16_verification_swiglu.c draws its draw 0. out (m*n) is not initialised.
 *
 * Report and exit statuses: those of bf16_timing.h, which are those of
 * timing_driver.c.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_timing_swiglu"

#include "bf16_timing.h"

void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out);

typedef void kernel_function(size_t, size_t, const uint16_t *restrict, const uint16_t *restrict, uint16_t *restrict);

/* Read through volatile, so that no build knows the callee and drops a call with unread output. */
static kernel_function *volatile kernel = hilclaw_swiglu_bf16;

int main(int argc, char **argv)
{
    size_t m, n, bytes;
    uint64_t base;
    uint16_t *gate, *up, *out;
    kernel_function *call;
    struct timing t;

    if (argc != 8)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <n> " TIMING_USAGE);
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    n = (size_t)digits("n", argv[2], 1, SIZE_MAX);
    timing_arguments(&t, argv + 3);

    if (!byte_size(m, n, sizeof(uint16_t), &bytes) || bytes > SIZE_MAX - bytes)
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    gate = malloc(bytes);
    up = malloc(bytes);
    out = malloc(bytes);
    if (gate == NULL || up == NULL || out == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");
    base = draw_base(t.seed, 0);
    draw_patterns(gate, m * n, base, 0, 10);
    draw_patterns(up, m * n, base, (uint64_t)(m * n), 8);

    call = kernel;
    for (timing_open(&t); timing_begin(&t); timing_end(&t))
        call(m, n, gate, up, out);
    timing_close(&t);
    free(out);
    free(up);
    free(gate);
    return 0;
}
