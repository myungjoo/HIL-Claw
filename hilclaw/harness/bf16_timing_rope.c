/*
 * Timing program of a bf16 timing run of rope (ADR-0181 decision 2), built
 * with one kernel of ADR-0161; loop, report and exit statuses: bf16_timing.h.
 *
 *     <m> <h> <d> <n_min> <n_max> <cv_max> <sample_form> <seed>
 *
 * d must be even (status 2 otherwise).
 *
 * Standard input: exactly 4*m*d bytes, the m*d binary32 patterns of the rows
 * as bf16_verification_rope.c takes them, then end of input. They are read
 * once, before the untimed call, straight into the kernel's freqs_cis array.
 *
 * Inputs, drawn once by the generator of bf16_verification.h as draw 0 of
 * bf16_verification_rope.c with the timing seed: x (m*h*d), bits = 8; out is
 * not initialised.
 *
 * One exit status more than the header's:
 *   6  standard input that ends before 4*m*d bytes, holds more, or cannot be
 *      read; nothing is written to the report and the kernel is not called.
 */
#define _POSIX_C_SOURCE 200809L
#define PROGRAM "bf16_timing_rope"

#include "bf16_timing.h"

#include <limits.h>

enum { STATUS_INPUT = 6 };

typedef char float_has_32_bits[sizeof(float) == sizeof(uint32_t) ? 1 : -1];

void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out);

typedef void kernel_function(size_t, size_t, size_t, const uint16_t *restrict, const float *restrict,
                             uint16_t *restrict);

/* Read through volatile, so that no build knows the callee and drops a call with unread output. */
static kernel_function *volatile kernel = hilclaw_rope_bf16;

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
    size_t m, h, d, tokens_heads, x_bytes, rows_bytes;
    uint16_t *x, *out;
    float *freqs_cis;
    const char *problem;
    kernel_function *call;
    struct timing t;

    if (argc != 9)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <h> <d> " TIMING_USAGE);
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    h = (size_t)digits("h", argv[2], 1, SIZE_MAX);
    d = (size_t)digits("d", argv[3], 1, SIZE_MAX);
    timing_arguments(&t, argv + 4);
    if (d % 2 != 0)
        return fail(STATUS_COMMAND_LINE, "d", "must be even");

    if (!byte_size(m, h, 1, &tokens_heads) || !byte_size(tokens_heads, d, sizeof(uint16_t), &x_bytes) ||
        !byte_size(m, d, sizeof(float), &rows_bytes))
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    x = malloc(x_bytes);
    out = malloc(x_bytes);
    freqs_cis = malloc(rows_bytes);
    if (x == NULL || out == NULL || freqs_cis == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");

    problem = read_rows((unsigned char *)freqs_cis, rows_bytes);
    if (problem != NULL)
        return fail(STATUS_INPUT, "standard input", problem);
    draw_patterns(x, x_bytes / sizeof(uint16_t), draw_base(t.seed, 0), 0, 8);

    call = kernel;
    for (timing_open(&t); timing_begin(&t); timing_end(&t))
        call(m, h, d, x, freqs_cis, out);
    timing_close(&t);
    free(freqs_cis);
    free(out);
    free(x);
    return 0;
}
