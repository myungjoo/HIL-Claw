/*
 * Verification program of a bf16 verification run of sdpa_kv_cache (ADR-0165).
 *
 * Built with the source files of one kernel of ADR-0162 into one verification
 * executable, it draws the inputs of each draw from a seed, sets the fills,
 * reports a check value of them, calls the kernel once and writes the
 * kernel's output and both cache allocations to the report. It holds no
 * reference, comparison, tolerance or verdict, reads no clock and does no
 * floating-point arithmetic. It needs the C library and POSIX.1-2008 only.
 *
 * Command line, exactly seven arguments:
 *
 *     <m> <l> <h> <h_kv> <d> <draws> <seed>
 *
 * Each is decimal digits with no sign, no space and no leading zero: m, l, h,
 * h_kv, d >= 1 within size_t, 1 <= draws < 2^64, 0 <= seed < 2^64; l >= m and
 * h a multiple of h_kv (ADR-0165 decision 3). P = l - m, the number of cached
 * rows, is derived and is not an argument. No argument has a default, and no
 * standard input, file or environment variable is read.
 *
 * Inputs: the generator of bf16_verification.h with bits = 8 for every
 * element. The elements of a draw form one sequence, in this order: q
 * (m*h*d), k_new and v_new (m*h_kv*d each), then rows 0 .. P - 1 of the
 * cache_k operand and rows 0 .. P - 1 of the cache_v operand (P*h_kv*d each).
 * Element (i, j, e) of q and out is at q[(i*h + j)*d + e], element (i, g, e)
 * of k_new and v_new at (i*h_kv + g)*d + e, and element (t, g, e) of a cache
 * operand at (t*h_kv + g)*d + e (ADR-0162 decisions 4 and 5).
 *
 * Allocations: each cache is one allocation of l + 2m rows of h_kv*d
 * elements: m leading guard rows, the l rows of the operand, m trailing guard
 * rows. The kernel receives the address of the first operand row, the
 * allocation's address plus m*h_kv*d elements.
 *
 * Fills, before each call: in both allocations, the guard rows and rows
 * P .. l - 1 of the operand hold the bit pattern 0x7FC0 (a bf16 NaN), set anew
 * every draw together with the drawn rows; every element of out holds 0x7FC0.
 *
 * Check value of a draw: the CRC-32 that zlib.crc32 computes (as in
 * bf16_verification.h) over five byte ranges in memory order: q, k_new, v_new,
 * the whole cache_k allocation, then the whole cache_v allocation, guard rows
 * included. out is not covered.
 *
 * Report, on the standard output the process was started with, and nothing
 * else there. For each draw in order: the check value as the 4 bytes a
 * uint32_t has in memory, written before the kernel is called; then, after the
 * one call hilclaw_sdpa_kv_cache_bf16(m, l, h, h_kv, d, q, k_new, v_new,
 * cache_k, cache_v, out) has returned, the 2*m*h*d bytes of out, then the
 * whole cache_k allocation, then the whole cache_v allocation, as their bytes
 * in memory. After the last draw the end mark, the 4 bytes "end\n". A complete
 * report has draws * (4 + 2*m*h*d + 4*(l + 2m)*h_kv*d) + 4 bytes. Descriptor 1
 * is pointed at standard error before the first call, so what a kernel prints
 * is not part of the report.
 *
 * Exit statuses: those of bf16_verification.h; status 2 also for l < m and
 * for an h that is not a multiple of h_kv.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_verification_sdpa_kv_cache"

#include "bf16_verification.h"

struct byte_range {
    const void *data;
    size_t bytes;
};

void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);

static uint32_t check_ranges(const struct byte_range *ranges, size_t count)
{
    uint32_t table[256], value, crc = UINT32_C(0xFFFFFFFF);
    const unsigned char *p;
    size_t i, left;
    int bit;

    for (i = 0; i < 256; i++) {
        value = (uint32_t)i;
        for (bit = 0; bit < 8; bit++)
            value = (value >> 1) ^ ((value & 1) != 0 ? UINT32_C(0xEDB88320) : 0);
        table[i] = value;
    }
    for (i = 0; i < count; i++)
        for (p = ranges[i].data, left = ranges[i].bytes; left > 0; left--)
            crc = table[(crc ^ *p++) & 0xFF] ^ (crc >> 8);
    return crc ^ UINT32_C(0xFFFFFFFF);
}

static int multiplied(size_t a, size_t b, size_t *product)
{
    if (a > SIZE_MAX / b)
        return 0;
    *product = a * b;
    return 1;
}

int main(int argc, char **argv)
{
    size_t m, l, h, h_kv, d, cached, row, q_count, new_count, cache_count, drawn;
    size_t q_bytes, new_bytes, cache_bytes;
    uint64_t draws, seed, draw, base, first;
    uint32_t check;
    uint16_t *q, *k_new, *v_new, *cache_k, *cache_v, *out, *k_operand, *v_operand;
    struct byte_range ranges[5];
    int report;

    if (argc != 8)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <l> <h> <h_kv> <d> <draws> <seed>");
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    l = (size_t)digits("l", argv[2], 1, SIZE_MAX);
    h = (size_t)digits("h", argv[3], 1, SIZE_MAX);
    h_kv = (size_t)digits("h_kv", argv[4], 1, SIZE_MAX);
    d = (size_t)digits("d", argv[5], 1, SIZE_MAX);
    draws = digits("draws", argv[6], 1, UINT64_MAX);
    seed = digits("seed", argv[7], 0, UINT64_MAX);
    if (l < m)
        return fail(STATUS_COMMAND_LINE, "l", "must not be less than m");
    if (h % h_kv != 0)
        return fail(STATUS_COMMAND_LINE, "h", "must be a multiple of h_kv");
    cached = l - m;

    if (!multiplied(h, d, &q_count) || !multiplied(m, q_count, &q_count) ||
        !byte_size(q_count, 1, sizeof(uint16_t), &q_bytes) || !multiplied(h_kv, d, &row) ||
        !multiplied(m, row, &new_count) || !byte_size(new_count, 1, sizeof(uint16_t), &new_bytes) ||
        m > (SIZE_MAX - l) / 2 || !multiplied(l + 2 * m, row, &cache_count) ||
        !byte_size(cache_count, 1, sizeof(uint16_t), &cache_bytes) || !multiplied(cached, row, &drawn) ||
        new_count > (SIZE_MAX - q_count) / 2 || drawn > (SIZE_MAX - q_count - 2 * new_count) / 2)
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    q = malloc(q_bytes);
    k_new = malloc(new_bytes);
    v_new = malloc(new_bytes);
    cache_k = malloc(cache_bytes);
    cache_v = malloc(cache_bytes);
    out = malloc(q_bytes);
    if (q == NULL || k_new == NULL || v_new == NULL || cache_k == NULL || cache_v == NULL || out == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");
    k_operand = cache_k + new_count;
    v_operand = cache_v + new_count;
    ranges[0].data = q;
    ranges[0].bytes = q_bytes;
    ranges[1].data = k_new;
    ranges[1].bytes = new_bytes;
    ranges[2].data = v_new;
    ranges[2].bytes = new_bytes;
    ranges[3].data = cache_k;
    ranges[3].bytes = cache_bytes;
    ranges[4].data = cache_v;
    ranges[4].bytes = cache_bytes;

    report = report_open();
    for (draw = 0; draw < draws; draw++) {
        base = draw_base(seed, draw);
        draw_patterns(q, q_count, base, 0, 8);
        first = (uint64_t)q_count;
        draw_patterns(k_new, new_count, base, first, 8);
        first += (uint64_t)new_count;
        draw_patterns(v_new, new_count, base, first, 8);
        first += (uint64_t)new_count;
        fill_output(cache_k, cache_count);
        fill_output(cache_v, cache_count);
        draw_patterns(k_operand, drawn, base, first, 8);
        first += (uint64_t)drawn;
        draw_patterns(v_operand, drawn, base, first, 8);
        check = check_ranges(ranges, 5);
        emit(report, &check, sizeof check);
        fill_output(out, q_count);
        hilclaw_sdpa_kv_cache_bf16(m, l, h, h_kv, d, q, k_new, v_new, k_operand, v_operand, out);
        emit(report, out, q_bytes);
        emit(report, cache_k, cache_bytes);
        emit(report, cache_v, cache_bytes);
    }
    emit(report, "end\n", 4);
    free(out);
    free(cache_v);
    free(cache_k);
    free(v_new);
    free(k_new);
    free(q);
    return 0;
}
