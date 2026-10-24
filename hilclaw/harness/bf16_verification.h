/*
 * Shared code of the bf16 verification programs (ADR-0163 decision 2).
 *
 * Included by each bf16 verification program under hilclaw/harness/, one per
 * kind, after that program has defined PROGRAM to the name its error lines
 * start with. It holds what the programs share and nothing of one kind: the
 * argument rules, the size check, the error line and the exit statuses of
 * verification_program.c; the generator of the inputs; the fill of an
 * output; the check value; and the report descriptor with its write loop.
 * Every identifier is static (internal linkage), and every function is static
 * inline so that a program which calls only some of them compiles without an
 * unused-function warning. It needs the C library and POSIX.1-2008 only and
 * does no floating-point arithmetic (no <math.h>).
 *
 * Generator, as stated in the docstring of bf16_verification_arrays.py. All
 * arithmetic is on unsigned 64-bit integers modulo 2^64:
 *
 *     G          = 0x9E3779B97F4A7C15
 *     mix(x)     : x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9
 *                  x = (x ^ (x >> 27)) * 0x94D049BB133111EB
 *                  the result is x ^ (x >> 31)
 *     base(d)    = mix(seed + (d + 1) * G)       draw d = 0 .. draws - 1
 *     word(d, e) = mix(base(d) + (e + 1) * G)    element e of the draw
 *     r(d, e)    = word(d, e) >> (64 - bits)
 *     bits = 8:  pattern = 0x3F00 | (r & 0x7F) | ((r >> 7) << 15)
 *     bits = 10: pattern = (0x3F00 + (r & 0x1FF)) | ((r >> 9) << 15)
 *
 * The elements of a draw form one sequence: the first operand in its memory
 * order, then the second. pattern is the uint16_t bf16 bit pattern of the
 * element, in the byte order of the host.
 *
 * Check value of a draw: the CRC-32 that zlib.crc32 computes (reflected
 * polynomial 0xEDB88320, initial value and final XOR 0xFFFFFFFF) of the bytes
 * of the first operand as they are in memory followed by those of the second.
 *
 * Exit statuses:
 *   0  the end mark was written; in no other case
 *   2  the command line
 *   3  an array whose size cannot be held or that cannot be allocated
 *   4  a descriptor or a write of the report
 * A status other than 0 comes with one line on standard error, starting with
 * PROGRAM and ": ", and without the end mark.
 */
#ifndef BF16_VERIFICATION_H
#define BF16_VERIFICATION_H

#if !defined(_POSIX_C_SOURCE) || _POSIX_C_SOURCE < 200809L
#error "define _POSIX_C_SOURCE as 200809L before any include"
#endif
#ifndef PROGRAM
#error "define PROGRAM as the name of the program before this include"
#endif

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#if SIZE_MAX > UINT64_MAX
#error "an element index must fit in 64 bits"
#endif

enum { STATUS_COMMAND_LINE = 2, STATUS_MEMORY = 3, STATUS_SYSTEM = 4 };

#define GOLDEN UINT64_C(0x9E3779B97F4A7C15)
#define OUTPUT_FILL UINT16_C(0x7FC0)

static inline int fail(int status, const char *subject, const char *message)
{
    fprintf(stderr, "%s: %s: %s\n", PROGRAM, subject, message);
    return status;
}

static inline uint64_t digits(const char *name, const char *text, uint64_t minimum, uint64_t maximum)
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

static inline int byte_size(size_t rows, size_t columns, size_t element, size_t *bytes)
{
    if (rows > SIZE_MAX / element / columns)
        return 0;
    *bytes = rows * columns * element;
    return 1;
}

static inline uint64_t mix(uint64_t z)
{
    z = (z ^ (z >> 30)) * UINT64_C(0xBF58476D1CE4E5B9);
    z = (z ^ (z >> 27)) * UINT64_C(0x94D049BB133111EB);
    return z ^ (z >> 31);
}

static inline uint64_t draw_base(uint64_t seed, uint64_t draw)
{
    return mix(seed + (draw + 1) * GOLDEN);
}

static inline void draw_patterns(uint16_t *array, size_t count, uint64_t base, uint64_t first, int bits)
{
    size_t i;

    for (i = 0; i < count; i++) {
        uint64_t r = mix(base + (first + (uint64_t)i + 1) * GOLDEN) >> (64 - bits);

        if (bits == 8)
            array[i] = (uint16_t)(0x3F00 | (r & 0x7F) | ((r >> 7) << 15));
        else
            array[i] = (uint16_t)((0x3F00 + (r & 0x1FF)) | ((r >> 9) << 15));
    }
}

static inline void fill_output(uint16_t *array, size_t count)
{
    size_t i;

    for (i = 0; i < count; i++)
        array[i] = OUTPUT_FILL;
}

static inline uint32_t check_value(const void *first, size_t first_bytes, const void *second, size_t second_bytes)
{
    const unsigned char *parts[2];
    size_t sizes[2], left;
    uint32_t table[256], value, crc = UINT32_C(0xFFFFFFFF);
    int i, bit;

    for (i = 0; i < 256; i++) {
        value = (uint32_t)i;
        for (bit = 0; bit < 8; bit++)
            value = (value >> 1) ^ ((value & 1) != 0 ? UINT32_C(0xEDB88320) : 0);
        table[i] = value;
    }
    parts[0] = first;
    parts[1] = second;
    sizes[0] = first_bytes;
    sizes[1] = second_bytes;
    for (i = 0; i < 2; i++)
        for (left = sizes[i]; left > 0; left--)
            crc = table[(crc ^ *parts[i]++) & 0xFF] ^ (crc >> 8);
    return crc ^ UINT32_C(0xFFFFFFFF);
}

static inline int report_open(void)
{
    int fd = dup(STDOUT_FILENO);

    if (fd < 0 || dup2(STDERR_FILENO, STDOUT_FILENO) < 0)
        exit(fail(STATUS_SYSTEM, "descriptors", "cannot keep the standard output apart"));
    return fd;
}

static inline void emit(int fd, const void *data, size_t left)
{
    const char *p = data;

    while (left > 0) {
        ssize_t written = write(fd, p, left);

        if (written < 0 && errno == EINTR)
            continue;
        if (written <= 0)
            exit(fail(STATUS_SYSTEM, "report", "cannot write to the standard output"));
        p += written;
        left -= (size_t)written;
    }
}

#endif
