/*
 * Timing program of a bf16 timing run of sdpa_kv_cache (ADR-0181 decision 2),
 * built with one kernel of ADR-0162; loop, report and exit statuses:
 * bf16_timing.h.
 *
 *     <m> <l> <h> <h_kv> <d> <n_min> <n_max> <cv_max> <sample_form> <seed>
 *
 * l >= m and h a multiple of h_kv (status 2 otherwise). P = l - m is derived.
 *
 * Each cache is one allocation of exactly l rows of h_kv*d elements, with no
 * guard rows.
 *
 * Inputs, drawn once by the generator of bf16_verification.h as draw 0 of
 * bf16_verification_sdpa_kv_cache.c with the timing seed, bits = 8, in one
 * sequence: q (m*h*d), k_new and v_new (m*h_kv*d each), rows 0 .. P - 1 of
 * cache_k and of cache_v (P*h_kv*d each). Rows P .. l - 1 and out are not
 * initialised, and nothing is reset between repeats: every call after the
 * first finds in rows P .. l - 1 what the call before it wrote there.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_timing_sdpa_kv_cache"

#include "bf16_timing.h"

void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);

typedef void kernel_function(size_t, size_t, size_t, size_t, size_t, const uint16_t *restrict,
                             const uint16_t *restrict, const uint16_t *restrict, uint16_t *restrict,
                             uint16_t *restrict, uint16_t *restrict);

/* Read through volatile, so that no build knows the callee and drops a call with unread output. */
static kernel_function *volatile kernel = hilclaw_sdpa_kv_cache_bf16;

int main(int argc, char **argv)
{
    size_t m, l, h, h_kv, d, heads, row, q_bytes, new_bytes, cache_bytes, q_count, new_count, drawn;
    uint64_t base, first;
    uint16_t *q, *k_new, *v_new, *cache_k, *cache_v, *out;
    kernel_function *call;
    struct timing t;

    if (argc != 11)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <l> <h> <h_kv> <d> " TIMING_USAGE);
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    l = (size_t)digits("l", argv[2], 1, SIZE_MAX);
    h = (size_t)digits("h", argv[3], 1, SIZE_MAX);
    h_kv = (size_t)digits("h_kv", argv[4], 1, SIZE_MAX);
    d = (size_t)digits("d", argv[5], 1, SIZE_MAX);
    timing_arguments(&t, argv + 6);
    if (l < m)
        return fail(STATUS_COMMAND_LINE, "l", "must not be less than m");
    if (h % h_kv != 0)
        return fail(STATUS_COMMAND_LINE, "h", "must be a multiple of h_kv");

    if (!byte_size(h, d, 1, &heads) || !byte_size(m, heads, sizeof(uint16_t), &q_bytes) ||
        !byte_size(h_kv, d, 1, &row) || !byte_size(m, row, sizeof(uint16_t), &new_bytes) ||
        !byte_size(l, row, sizeof(uint16_t), &cache_bytes))
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    q_count = q_bytes / sizeof(uint16_t);
    new_count = new_bytes / sizeof(uint16_t);
    drawn = (l - m) * row;
    if (new_count > (SIZE_MAX - q_count) / 2 || drawn > (SIZE_MAX - q_count - 2 * new_count) / 2)
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    q = malloc(q_bytes);
    k_new = malloc(new_bytes);
    v_new = malloc(new_bytes);
    cache_k = malloc(cache_bytes);
    cache_v = malloc(cache_bytes);
    out = malloc(q_bytes);
    if (q == NULL || k_new == NULL || v_new == NULL || cache_k == NULL || cache_v == NULL || out == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");

    base = draw_base(t.seed, 0);
    draw_patterns(q, q_count, base, 0, 8);
    first = (uint64_t)q_count;
    draw_patterns(k_new, new_count, base, first, 8);
    first += (uint64_t)new_count;
    draw_patterns(v_new, new_count, base, first, 8);
    first += (uint64_t)new_count;
    draw_patterns(cache_k, drawn, base, first, 8);
    first += (uint64_t)drawn;
    draw_patterns(cache_v, drawn, base, first, 8);

    call = kernel;
    for (timing_open(&t); timing_begin(&t); timing_end(&t))
        call(m, l, h, h_kv, d, q, k_new, v_new, cache_k, cache_v, out);
    timing_close(&t);
    free(out);
    free(cache_v);
    free(cache_k);
    free(v_new);
    free(k_new);
    free(q);
    return 0;
}
