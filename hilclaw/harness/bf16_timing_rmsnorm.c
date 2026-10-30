/*
 * Timing program of a bf16 timing run of rmsnorm (ADR-0181 decision 2), built
 * with one kernel of ADR-0158; loop, report and exit statuses: bf16_timing.h.
 *
 *     <m> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>
 *
 * eps is a constant, as in bf16_verification_rmsnorm.c: the binary32 value of
 * the bit pattern 0x3727C5AC (rmsnorm_bf16_contract.EPS), formed by memcpy.
 *
 * Inputs, drawn once by the generator of bf16_verification.h as draw 0 of
 * bf16_verification_rmsnorm.c with the timing seed:
 * x (m*n) then w (n), bits = 8 for both; y is not
 * initialised.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_timing_rmsnorm"

#include "bf16_timing.h"

typedef char float_has_32_bits[sizeof(float) == sizeof(uint32_t) ? 1 : -1];

void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x, const uint16_t *restrict w, uint16_t *restrict y);

typedef void kernel_function(size_t, size_t, float, const uint16_t *restrict, const uint16_t *restrict,
                             uint16_t *restrict);

/* Read through volatile, so that no build knows the callee and drops a call with unread output. */
static kernel_function *volatile kernel = hilclaw_rmsnorm_bf16;

int main(int argc, char **argv)
{
    const uint32_t eps_bits = UINT32_C(0x3727C5AC);
    size_t m, n, x_bytes, w_bytes;
    uint64_t base;
    uint16_t *x, *w, *y;
    float eps;
    kernel_function *call;
    struct timing t;

    if (argc != 8)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <n> " TIMING_USAGE);
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    n = (size_t)digits("n", argv[2], 1, SIZE_MAX);
    timing_arguments(&t, argv + 3);
    memcpy(&eps, &eps_bits, sizeof eps);

    if (!byte_size(m, n, sizeof(uint16_t), &x_bytes) || !byte_size(1, n, sizeof(uint16_t), &w_bytes) ||
        x_bytes > SIZE_MAX - w_bytes)
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    x = malloc(x_bytes);
    w = malloc(w_bytes);
    y = malloc(x_bytes);
    if (x == NULL || w == NULL || y == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");
    base = draw_base(t.seed, 0);
    draw_patterns(x, m * n, base, 0, 8);
    draw_patterns(w, n, base, (uint64_t)(m * n), 8);

    call = kernel;
    for (timing_open(&t); timing_begin(&t); timing_end(&t))
        call(m, n, eps, x, w, y);
    timing_close(&t);
    free(y);
    free(w);
    free(x);
    return 0;
}
