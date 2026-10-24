/*
 * Verification program of a bf16 verification run of rmsnorm (ADR-0163).
 *
 * Built with the source files of one kernel of ADR-0158 into one verification
 * executable, it draws the inputs of each draw from a seed, reports a check
 * value of them, calls the kernel once and writes the kernel's output to the
 * report. It holds no reference, comparison, tolerance or verdict, reads no
 * clock and does no floating-point arithmetic. It needs the C library and
 * POSIX.1-2008 only (no -lm).
 *
 * Command line, exactly four arguments:
 *
 *     <m> <n> <draws> <seed>
 *
 * Each is decimal digits with no sign, no space and no leading zero: m, n >= 1
 * within size_t, 1 <= draws < 2^64, 0 <= seed < 2^64. No argument has a
 * default, and no standard input, file or environment variable is read.
 *
 * eps: a constant, not an argument. It is the binary32 value of the bit
 * pattern 0x3727C5AC, the value nearest to 1e-05 (ADR-0163 decision 3;
 * rmsnorm_bf16_contract.EPS), formed from that pattern by memcpy.
 *
 * Inputs: the generator of bf16_verification.h with bits = 8 for both
 * operands. Elements 0 .. m*n - 1 of a draw are x and elements m*n ..
 * m*n + n - 1 are w, in the row_major layout of ADR-0158 (x[i*n + j], w[j]).
 *
 * Check value of a draw: that of bf16_verification.h over x, then w.
 *
 * Report, on the standard output the process was started with, and nothing
 * else there. For each draw in order: the check value as the 4 bytes a uint32_t
 * has in memory, written before the kernel is called; then, after the one call
 * hilclaw_rmsnorm_bf16(m, n, eps, x, w, y) has returned, the m*n elements of y
 * (y[i*n + j]) as the 2*m*n bytes they have in memory. After the last draw the
 * end mark, the 4 bytes "end\n". A complete report has
 * draws * (4 + 2*m*n) + 4 bytes. Before each call every element of y is set to
 * the bit pattern 0x7FC0 (a bf16 NaN). Descriptor 1 is pointed at standard
 * error before the first call, so what a kernel prints is not part of the
 * report.
 *
 * Exit statuses: those of bf16_verification.h.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_verification_rmsnorm"

#include "bf16_verification.h"

#include <string.h>

typedef char float_has_32_bits[sizeof(float) == sizeof(uint32_t) ? 1 : -1];

void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x, const uint16_t *restrict w, uint16_t *restrict y);

int main(int argc, char **argv)
{
    const uint32_t eps_bits = UINT32_C(0x3727C5AC);
    size_t m, n, x_bytes, w_bytes;
    uint64_t draws, seed, d, base;
    uint32_t check;
    uint16_t *x, *w, *y;
    float eps;
    int report;

    if (argc != 5)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <n> <draws> <seed>");
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    n = (size_t)digits("n", argv[2], 1, SIZE_MAX);
    draws = digits("draws", argv[3], 1, UINT64_MAX);
    seed = digits("seed", argv[4], 0, UINT64_MAX);
    memcpy(&eps, &eps_bits, sizeof eps);

    if (!byte_size(m, n, sizeof(uint16_t), &x_bytes) || !byte_size(1, n, sizeof(uint16_t), &w_bytes) ||
        x_bytes > SIZE_MAX - w_bytes)
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    x = malloc(x_bytes);
    w = malloc(w_bytes);
    y = malloc(x_bytes);
    if (x == NULL || w == NULL || y == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");

    report = report_open();
    for (d = 0; d < draws; d++) {
        base = draw_base(seed, d);
        draw_patterns(x, m * n, base, 0, 8);
        draw_patterns(w, n, base, (uint64_t)(m * n), 8);
        check = check_value(x, x_bytes, w, w_bytes);
        emit(report, &check, sizeof check);
        fill_output(y, m * n);
        hilclaw_rmsnorm_bf16(m, n, eps, x, w, y);
        emit(report, y, x_bytes);
    }
    emit(report, "end\n", 4);
    free(y);
    free(w);
    free(x);
    return 0;
}
