/*
 * Timing program of a bf16 timing run of gemm (ADR-0181 decision 2).
 *
 * Built with the source files of one kernel of ADR-0156 into one timing
 * executable, it draws the inputs once, calls the kernel once untimed and then
 * times one call per repeat until the stopping rule of ADR-0007 decision 4
 * ends the measurement, as timing_driver.c does for fp32 (ADR-0009). It does
 * no floating-point arithmetic on the operands and needs the C library and
 * POSIX.1-2008 only (no -lm).
 *
 * Command line, exactly eight arguments:
 *
 *     <m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>
 *
 * with the spelling, bounds and refusals of timing_driver.c.
 *
 * Inputs: a (m*k) and b (k*n), one malloc each, filled once before the
 * untimed call by the generator of bf16_verification.h with the seed of the
 * command line, draw 0 and bits = 8 for both operands, exactly as
 * bf16_verification_gemm.c draws its draw 0. c (m*n) is not initialised.
 *
 * Report and exit statuses: those of bf16_timing.h, which are those of
 * timing_driver.c.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_timing_gemm"

#include "bf16_timing.h"

void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);

typedef void kernel_function(size_t, size_t, size_t, const uint16_t *restrict, const uint16_t *restrict,
                             uint16_t *restrict);

/* Read through volatile, so that no build knows the callee and drops a call with unread output. */
static kernel_function *volatile kernel = hilclaw_gemm_bf16;

int main(int argc, char **argv)
{
    size_t m, k, n, a_bytes, b_bytes, c_bytes;
    uint64_t base;
    uint16_t *a, *b, *c;
    kernel_function *call;
    struct timing t;

    if (argc != 9)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <k> <n> " TIMING_USAGE);
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    k = (size_t)digits("k", argv[2], 1, SIZE_MAX);
    n = (size_t)digits("n", argv[3], 1, SIZE_MAX);
    timing_arguments(&t, argv + 4);

    if (!byte_size(m, k, sizeof(uint16_t), &a_bytes) || !byte_size(k, n, sizeof(uint16_t), &b_bytes) ||
        !byte_size(m, n, sizeof(uint16_t), &c_bytes))
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    a = malloc(a_bytes);
    b = malloc(b_bytes);
    c = malloc(c_bytes);
    if (a == NULL || b == NULL || c == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");
    base = draw_base(t.seed, 0);
    draw_patterns(a, m * k, base, 0, 8);
    draw_patterns(b, k * n, base, (uint64_t)(m * k), 8);

    call = kernel;
    for (timing_open(&t); timing_begin(&t); timing_end(&t))
        call(m, k, n, a, b, c);
    timing_close(&t);
    free(c);
    free(b);
    free(a);
    return 0;
}
