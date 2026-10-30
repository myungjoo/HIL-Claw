/*
 * Timing program of a bf16 timing run of elementwise_add (ADR-0181 decision 2), built
 * with one kernel of ADR-0159; loop, report and exit statuses: bf16_timing.h.
 *
 *     <m> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>
 *
 * Inputs, drawn once by the generator of bf16_verification.h as draw 0 of
 * bf16_verification_elementwise_add.c with the timing seed:
 * a (m*n) then b (m*n), bits = 8 for both; c is not
 * initialised.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_timing_elementwise_add"

#include "bf16_timing.h"

void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);

typedef void kernel_function(size_t, size_t, const uint16_t *restrict, const uint16_t *restrict, uint16_t *restrict);

/* Read through volatile, so that no build knows the callee and drops a call with unread output. */
static kernel_function *volatile kernel = hilclaw_elementwise_add_bf16;

int main(int argc, char **argv)
{
    size_t m, n, bytes;
    uint64_t base;
    uint16_t *a, *b, *c;
    kernel_function *call;
    struct timing t;

    if (argc != 8)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <n> " TIMING_USAGE);
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    n = (size_t)digits("n", argv[2], 1, SIZE_MAX);
    timing_arguments(&t, argv + 3);

    if (!byte_size(m, n, sizeof(uint16_t), &bytes) || bytes > SIZE_MAX - bytes)
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    a = malloc(bytes);
    b = malloc(bytes);
    c = malloc(bytes);
    if (a == NULL || b == NULL || c == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");
    base = draw_base(t.seed, 0);
    draw_patterns(a, m * n, base, 0, 8);
    draw_patterns(b, m * n, base, (uint64_t)(m * n), 8);

    call = kernel;
    for (timing_open(&t); timing_begin(&t); timing_end(&t))
        call(m, n, a, b, c);
    timing_close(&t);
    free(c);
    free(b);
    free(a);
    return 0;
}
