/*
 * Verification program of a bf16 verification run of swiglu (ADR-0163).
 *
 * Built with the source files of one kernel of ADR-0160 into one verification
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
 * Inputs: the generator of bf16_verification.h with bits = 10 for gate and
 * bits = 8 for up. Elements 0 .. m*n - 1 of a draw are gate and elements m*n ..
 * 2*m*n - 1 are up, in the row_major layout of ADR-0160 (gate[i*n + j],
 * up[i*n + j]).
 *
 * Check value of a draw: that of bf16_verification.h over gate, then up.
 *
 * Report, on the standard output the process was started with, and nothing
 * else there. For each draw in order: the check value as the 4 bytes a uint32_t
 * has in memory, written before the kernel is called; then, after the one call
 * hilclaw_swiglu_bf16(m, n, gate, up, out) has returned, the m*n elements of
 * out (out[i*n + j]) as the 2*m*n bytes they have in memory. After the last
 * draw the end mark, the 4 bytes "end\n". A complete report has
 * draws * (4 + 2*m*n) + 4 bytes. Before each call every element of out is set
 * to the bit pattern 0x7FC0 (a bf16 NaN). Descriptor 1 is pointed at standard
 * error before the first call, so what a kernel prints is not part of the
 * report.
 *
 * Exit statuses: those of bf16_verification.h.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_verification_swiglu"

#include "bf16_verification.h"

void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out);

int main(int argc, char **argv)
{
    size_t m, n, bytes;
    uint64_t draws, seed, d, base;
    uint32_t check;
    uint16_t *gate, *up, *out;
    int report;

    if (argc != 5)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <n> <draws> <seed>");
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    n = (size_t)digits("n", argv[2], 1, SIZE_MAX);
    draws = digits("draws", argv[3], 1, UINT64_MAX);
    seed = digits("seed", argv[4], 0, UINT64_MAX);

    if (!byte_size(m, n, sizeof(uint16_t), &bytes) || bytes > SIZE_MAX - bytes)
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    gate = malloc(bytes);
    up = malloc(bytes);
    out = malloc(bytes);
    if (gate == NULL || up == NULL || out == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");

    report = report_open();
    for (d = 0; d < draws; d++) {
        base = draw_base(seed, d);
        draw_patterns(gate, m * n, base, 0, 10);
        draw_patterns(up, m * n, base, (uint64_t)(m * n), 8);
        check = check_value(gate, bytes, up, bytes);
        emit(report, &check, sizeof check);
        fill_output(out, m * n);
        hilclaw_swiglu_bf16(m, n, gate, up, out);
        emit(report, out, bytes);
    }
    emit(report, "end\n", 4);
    free(out);
    free(up);
    free(gate);
    return 0;
}
