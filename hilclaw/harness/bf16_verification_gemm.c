/*
 * Verification program of a bf16 verification run of gemm (ADR-0163).
 *
 * Built with the source files of one kernel of ADR-0156 into one verification
 * executable, it draws the inputs of each draw from a seed, reports a check
 * value of them, calls the kernel once and writes the kernel's output to the
 * report. It holds no reference, comparison, tolerance or verdict, reads no
 * clock and does no floating-point arithmetic. It needs the C library and
 * POSIX.1-2008 only (no -lm).
 *
 * Command line, exactly five arguments:
 *
 *     <m> <k> <n> <draws> <seed>
 *
 * Each is decimal digits with no sign, no space and no leading zero: m, k, n
 * >= 1 within size_t, 1 <= draws < 2^64, 0 <= seed < 2^64. No argument has a
 * default, and no standard input, file or environment variable is read.
 *
 * Inputs: the generator of bf16_verification.h with bits = 8 for both
 * operands. Elements 0 .. m*k - 1 of a draw are a and elements m*k ..
 * m*k + k*n - 1 are b, in the row_major layout of ADR-0156 (a[i*k + p],
 * b[p*n + j]).
 *
 * Check value of a draw: that of bf16_verification.h over a, then b.
 *
 * Report, on the standard output the process was started with, and nothing
 * else there. For each draw in order: the check value as the 4 bytes a uint32_t
 * has in memory, written before the kernel is called; then, after the one call
 * hilclaw_gemm_bf16(m, k, n, a, b, c) has returned, the m*n elements of c
 * (c[i*n + j]) as the 2*m*n bytes they have in memory. After the last draw the
 * end mark, the 4 bytes "end\n". A complete report has
 * draws * (4 + 2*m*n) + 4 bytes. Before each call every element of c is set to
 * the bit pattern 0x7FC0 (a bf16 NaN). Descriptor 1 is pointed at standard
 * error before the first call, so what a kernel prints is not part of the
 * report.
 *
 * Exit statuses: those of bf16_verification.h.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_verification_gemm"

#include "bf16_verification.h"

void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);

int main(int argc, char **argv)
{
    size_t m, k, n, a_bytes, b_bytes, c_bytes;
    uint64_t draws, seed, d, base;
    uint32_t check;
    uint16_t *a, *b, *c;
    int report;

    if (argc != 6)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <k> <n> <draws> <seed>");
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    k = (size_t)digits("k", argv[2], 1, SIZE_MAX);
    n = (size_t)digits("n", argv[3], 1, SIZE_MAX);
    draws = digits("draws", argv[4], 1, UINT64_MAX);
    seed = digits("seed", argv[5], 0, UINT64_MAX);

    if (!byte_size(m, k, sizeof(uint16_t), &a_bytes) || !byte_size(k, n, sizeof(uint16_t), &b_bytes) ||
        !byte_size(m, n, sizeof(uint16_t), &c_bytes))
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    a = malloc(a_bytes);
    b = malloc(b_bytes);
    c = malloc(c_bytes);
    if (a == NULL || b == NULL || c == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");

    report = report_open();
    for (d = 0; d < draws; d++) {
        base = draw_base(seed, d);
        draw_patterns(a, m * k, base, 0, 8);
        draw_patterns(b, k * n, base, (uint64_t)(m * k), 8);
        check = check_value(a, a_bytes, b, b_bytes);
        emit(report, &check, sizeof check);
        fill_output(c, m * n);
        hilclaw_gemm_bf16(m, k, n, a, b, c);
        emit(report, c, c_bytes);
    }
    emit(report, "end\n", 4);
    free(c);
    free(b);
    free(a);
    return 0;
}
