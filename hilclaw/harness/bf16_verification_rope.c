/*
 * Verification program of a bf16 verification run of rope (ADR-0164).
 *
 * Built with the source files of one kernel of ADR-0161 into one verification
 * executable, it reads the freqs_cis rows of the run on standard input, draws
 * x of each draw from a seed, reports a check value of the inputs, calls the
 * kernel once and writes the kernel's output to the report. It holds no
 * reference, comparison, tolerance or verdict, reads no clock and does no
 * floating-point arithmetic: the rows are bytes it receives and copies. It
 * needs the C library and POSIX.1-2008 only (no -lm).
 *
 * Command line, exactly five arguments:
 *
 *     <m> <h> <d> <draws> <seed>
 *
 * Each is decimal digits with no sign, no space and no leading zero: m, h,
 * d >= 1 within size_t, d even, 1 <= draws < 2^64, 0 <= seed < 2^64. No
 * argument has a default, and no file or environment variable is read.
 *
 * Standard input: exactly 4*m*d bytes, the m*d binary32 patterns of the rows
 * in memory order and the byte order of the host, then end of input. They are
 * read once, after the command line and the sizes are checked and the arrays
 * allocated, and before the first draw, into a buffer of the program's own.
 *
 * Inputs: x is drawn by the generator of bf16_verification.h with bits = 8,
 * elements 0 .. m*h*d - 1 of a draw in memory order, x[(i*h + j)*d + k]. Before
 * every call the rows are copied from the program's buffer into the kernel's
 * freqs_cis array, freqs_cis[i*d + c], so every draw passes the same rows
 * whatever a kernel did to its inputs.
 *
 * Check value of a draw: that of bf16_verification.h over the 2*m*h*d bytes
 * of x, then the 4*m*d bytes of the kernel's freqs_cis array.
 *
 * Report, on the standard output the process was started with, and nothing
 * else there. For each draw in order: the check value as the 4 bytes a uint32_t
 * has in memory, written before the kernel is called; then, after the one call
 * hilclaw_rope_bf16(m, h, d, x, freqs_cis, out) has returned, the m*h*d
 * elements of out as the 2*m*h*d bytes they have in memory. After the last draw
 * the end mark, the 4 bytes "end\n". A complete report has
 * draws * (4 + 2*m*h*d) + 4 bytes. Before each call every element of out is set
 * to the bit pattern 0x7FC0 (a bf16 NaN). Descriptor 1 is pointed at standard
 * error before the first call, so what a kernel prints is not part of the
 * report.
 *
 * Exit statuses: those of bf16_verification.h (an odd d is a command line
 * status), and
 *   5  standard input that ends before 4*m*d bytes, holds more, or cannot be
 *      read; nothing is written to the report and the kernel is not called.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_verification_rope"

#include "bf16_verification.h"

#include <limits.h>
#include <string.h>

enum { STATUS_INPUT = 5 };

typedef char float_has_32_bits[sizeof(float) == sizeof(uint32_t) ? 1 : -1];

void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out);

static const char *read_rows(unsigned char *rows, size_t left)
{
    unsigned char extra;
    ssize_t got;

    while (left > 0) {
        got = read(STDIN_FILENO, rows, left < (size_t)SSIZE_MAX ? left : (size_t)SSIZE_MAX);
        if (got < 0 && errno == EINTR)
            continue;
        if (got < 0)
            return "cannot be read";
        if (got == 0)
            return "ends before the 4*m*d bytes of the rows";
        rows += got;
        left -= (size_t)got;
    }
    do
        got = read(STDIN_FILENO, &extra, 1);
    while (got < 0 && errno == EINTR);
    if (got < 0)
        return "cannot be read";
    return got == 0 ? NULL : "holds more than the 4*m*d bytes of the rows";
}

int main(int argc, char **argv)
{
    size_t m, h, d, tokens_heads, count, x_bytes, rows_bytes;
    uint64_t draws, seed, draw;
    uint32_t check;
    uint16_t *x, *out;
    unsigned char *rows;
    float *freqs_cis;
    const char *problem;
    int report;

    if (argc != 6)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <h> <d> <draws> <seed>");
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    h = (size_t)digits("h", argv[2], 1, SIZE_MAX);
    d = (size_t)digits("d", argv[3], 1, SIZE_MAX);
    draws = digits("draws", argv[4], 1, UINT64_MAX);
    seed = digits("seed", argv[5], 0, UINT64_MAX);
    if (d % 2 != 0)
        return fail(STATUS_COMMAND_LINE, "d", "must be even");

    if (!byte_size(m, h, 1, &tokens_heads) || !byte_size(tokens_heads, d, sizeof(uint16_t), &x_bytes) ||
        !byte_size(m, d, sizeof(float), &rows_bytes))
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    count = x_bytes / sizeof(uint16_t);
    x = malloc(x_bytes);
    out = malloc(x_bytes);
    rows = malloc(rows_bytes);
    freqs_cis = malloc(rows_bytes);
    if (x == NULL || out == NULL || rows == NULL || freqs_cis == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");

    problem = read_rows(rows, rows_bytes);
    if (problem != NULL)
        return fail(STATUS_INPUT, "standard input", problem);

    report = report_open();
    for (draw = 0; draw < draws; draw++) {
        draw_patterns(x, count, draw_base(seed, draw), 0, 8);
        memcpy(freqs_cis, rows, rows_bytes);
        check = check_value(x, x_bytes, freqs_cis, rows_bytes);
        emit(report, &check, sizeof check);
        fill_output(out, count);
        hilclaw_rope_bf16(m, h, d, x, freqs_cis, out);
        emit(report, out, x_bytes);
    }
    emit(report, "end\n", 4);
    free(freqs_cis);
    free(rows);
    free(out);
    free(x);
    return 0;
}
