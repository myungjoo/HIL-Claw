/*
 * Verification program of a verification run (ADR-0017).
 *
 * Built with the source files of one kernel of ADR-0008 into one verification
 * executable, it draws the inputs of each draw from a seed, reports a check
 * value of them, calls the kernel once and writes the kernel's output to the
 * report. It holds no reference, comparison, tolerance or verdict and reads no
 * clock. It needs the C library and POSIX.1-2008 only (no -lm).
 *
 * Command line, exactly five arguments:
 *
 *     <m> <k> <n> <draws> <seed>
 *
 * Each is decimal digits with no sign, no space and no leading zero: m, k, n
 * >= 1 within size_t, 1 <= draws < 2^64, 0 <= seed < 2^64. No argument has a
 * default, and no standard input, file or environment variable is read.
 *
 * Inputs. All arithmetic is on unsigned 64-bit integers modulo 2^64:
 *
 *     G          = 0x9E3779B97F4A7C15
 *     mix(x)     : x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9
 *                  x = (x ^ (x >> 27)) * 0x94D049BB133111EB
 *                  the result is x ^ (x >> 31)
 *     base(d)    = mix(seed + (d + 1) * G)       draw d = 0 .. draws - 1
 *     word(d, e) = mix(base(d) + (e + 1) * G)    element e = 0 .. m*k + k*n - 1
 *     bits(d, e) = (word & 1) << 31 | 126 << 23 | word >> 41
 *
 * Element e < m*k is a[e] and element e >= m*k is b[e - m*k], in the row_major
 * layout of ADR-0008 decision 2 (a[i*k + p], b[p*n + j]). bits(d, e) is the
 * binary32 bit pattern of the element, held as a uint32_t in the byte order of
 * the host: +-(0.5 + u * 2^-24) with u = word >> 41 (23 bits), negative when
 * bit 0 of word is set, so every magnitude is in [0.5, 1).
 *
 * Check value of a draw: the CRC-32 that zlib.crc32 computes (reflected
 * polynomial 0xEDB88320, initial value and final XOR 0xFFFFFFFF) of the bytes
 * of a as they are in memory followed by the bytes of b.
 *
 * Report, on the standard output the process was started with, and nothing
 * else there. For each draw in order: the check value as the 4 bytes a uint32_t
 * has in memory, written before the kernel is called; then, after the one call
 * hilclaw_gemm(m, k, n, a, b, c) has returned, the m*n elements of c
 * (c[i*n + j]) as the 4*m*n bytes they have in memory. After the last draw the
 * end mark, the 4 bytes "end\n". A complete report has
 * draws * (4 + 4*m*n) + 4 bytes. Before each call every element of c is set to
 * the bit pattern 0x7FC00000 (a NaN). Descriptor 1 is pointed at standard error
 * before the first call, so what a kernel prints is not part of the report.
 *
 * Exit status:
 *   0  the end mark was written; in no other case
 *   2  the command line
 *   3  an array whose size cannot be held or that cannot be allocated
 *   4  a descriptor or a write of the report
 * A status other than 0 comes with one line on standard error and without the
 * end mark.
 */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);

#if SIZE_MAX > UINT64_MAX
#error "an element index must fit in 64 bits"
#endif

typedef char float_is_32_bits[sizeof(float) == sizeof(uint32_t) ? 1 : -1];

enum { STATUS_COMMAND_LINE = 2, STATUS_MEMORY = 3, STATUS_SYSTEM = 4 };

#define GOLDEN UINT64_C(0x9E3779B97F4A7C15)

static int report_fd = -1;
static uint32_t crc_table[256];

static int fail(int status, const char *subject, const char *message)
{
    fprintf(stderr, "verification_program: %s: %s\n", subject, message);
    return status;
}

static uint64_t digits(const char *name, const char *text, uint64_t minimum, uint64_t maximum)
{
    const char *rule = "must be decimal digits (no sign, space or leading zero) within its range";
    uint64_t value = 0;
    const char *p = text;
    int valid = *p != '\0' && (p[0] != '0' || p[1] == '\0');

    for (; valid && *p != '\0'; p++) {
        uint64_t digit = (uint64_t)(*p - '0');

        valid = *p >= '0' && *p <= '9' && digit <= maximum && value <= (maximum - digit) / 10;
        if (valid)
            value = value * 10 + digit;
    }
    if (!valid || value < minimum)
        exit(fail(STATUS_COMMAND_LINE, name, rule));
    return value;
}

static int byte_size(size_t rows, size_t columns, size_t element, size_t *bytes)
{
    if (rows > SIZE_MAX / element / columns)
        return 0;
    *bytes = rows * columns * element;
    return 1;
}

static uint64_t mix(uint64_t z)
{
    z = (z ^ (z >> 30)) * UINT64_C(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94D049BB133111EB);
    return z ^ (z >> 31);
}

static void draw(float *array, size_t count, uint64_t base, uint64_t first)
{
    size_t i;

    for (i = 0; i < count; i++) {
        uint64_t word = mix(base + (first + (uint64_t)i + 1) * GOLDEN);
        uint32_t bits = (uint32_t)((word & 1) << 31) | UINT32_C(126) << 23 | (uint32_t)(word >> 41);

        memcpy(&array[i], &bits, sizeof bits);
    }
}

static void fill_nan(float *array, size_t count)
{
    const uint32_t bits = UINT32_C(0x7FC00000);
    size_t i;

    for (i = 0; i < count; i++)
        memcpy(&array[i], &bits, sizeof bits);
}

static void crc_prepare(void)
{
    uint32_t i, value;
    int bit;

    for (i = 0; i < 256; i++) {
        value = i;
        for (bit = 0; bit < 8; bit++)
            value = (value >> 1) ^ ((value & 1) != 0 ? UINT32_C(0xEDB88320) : 0);
        crc_table[i] = value;
    }
}

static uint32_t crc_update(uint32_t crc, const void *data, size_t count)
{
    const unsigned char *p = data;

    for (; count > 0; count--)
        crc = crc_table[(crc ^ *p++) & 0xFF] ^ (crc >> 8);
    return crc;
}

static void emit(const void *data, size_t left)
{
    const char *p = data;

    while (left > 0) {
        ssize_t written = write(report_fd, p, left);

        if (written < 0 && errno == EINTR)
            continue;
        if (written <= 0)
            exit(fail(STATUS_SYSTEM, "report", "cannot write to the standard output"));
        p += written;
        left -= (size_t)written;
    }
}

int main(int argc, char **argv)
{
    size_t m, k, n, a_bytes, b_bytes, c_bytes;
    uint64_t draws, seed, d, base;
    uint32_t check;
    float *a, *b, *c;

    if (argc != 6)
        return fail(STATUS_COMMAND_LINE, "usage", "<m> <k> <n> <draws> <seed>");
    m = (size_t)digits("m", argv[1], 1, SIZE_MAX);
    k = (size_t)digits("k", argv[2], 1, SIZE_MAX);
    n = (size_t)digits("n", argv[3], 1, SIZE_MAX);
    draws = digits("draws", argv[4], 1, UINT64_MAX);
    seed = digits("seed", argv[5], 0, UINT64_MAX);

    if (!byte_size(m, k, sizeof(float), &a_bytes) || !byte_size(k, n, sizeof(float), &b_bytes) ||
        !byte_size(m, n, sizeof(float), &c_bytes))
        return fail(STATUS_MEMORY, "sizes", "an array of these dimensions does not fit in size_t");
    a = malloc(a_bytes);
    b = malloc(b_bytes);
    c = malloc(c_bytes);
    if (a == NULL || b == NULL || c == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the operands");

    report_fd = dup(STDOUT_FILENO);
    if (report_fd < 0 || dup2(STDERR_FILENO, STDOUT_FILENO) < 0)
        return fail(STATUS_SYSTEM, "descriptors", "cannot keep the standard output apart");
    crc_prepare();

    for (d = 0; d < draws; d++) {
        base = mix(seed + (d + 1) * GOLDEN);
        draw(a, m * k, base, 0);
        draw(b, k * n, base, (uint64_t)(m * k));
        check = crc_update(crc_update(UINT32_C(0xFFFFFFFF), a, a_bytes), b, b_bytes);
        check ^= UINT32_C(0xFFFFFFFF);
        emit(&check, sizeof check);
        fill_nan(c, m * n);
        hilclaw_gemm(m, k, n, a, b, c);
        emit(c, c_bytes);
    }
    emit("end\n", 4);
    free(c);
    free(b);
    free(a);
    return 0;
}
