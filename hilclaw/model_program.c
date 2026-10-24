/*
 * Model program of the model executor (ADR-0153), first code slice.
 *
 * It loads each gemm kernel from a shared library of its own and calls the
 * kernels' entry points for a list of calls read from an input file, and
 * writes each call's output to the report. It compares nothing and holds no
 * reference, tolerance or verdict. It reads no clock, no environment variable
 * and no standard input. It is not yet a forward pass (ADR-0153 code slice 2).
 * It needs the C library and POSIX.1-2008 only, <dlfcn.h> included.
 *
 * One source, two programs, one dtype each (ADR-0157 decision 3). The macro
 * HILCLAW_MODEL_BF16 at compile time is the only way the program learns its
 * dtype:
 *
 *     build                        entry point        element   NaN pattern
 *     without HILCLAW_MODEL_BF16   hilclaw_gemm       float     0x7FC00000
 *     -DHILCLAW_MODEL_BF16         hilclaw_gemm_bf16  uint16_t  0x7FC0
 *
 * The fp32 program calls the prototype of ADR-0008 decision 4 with fp32
 * kernels of ADR-0008; the bf16 program calls that of ADR-0156 decision 5
 * with bf16 kernels of ADR-0156, each element a bf16 bit pattern. Below, "the
 * entry point" and "an element" are those of the build, and E is the size of
 * an element in bytes: 4 for float, 2 for uint16_t.
 *
 * Command line, at least two arguments:
 *
 *     <input file> <library> [<library> ...]
 *
 * Library i (0-based, in command-line order) is the kernel of index i. Each is
 * opened with dlopen(path, RTLD_NOW | RTLD_LOCAL), so two kernels that define
 * the same symbol stay apart, and its entry point is found with dlsym; all
 * libraries are loaded before the input file is read. The path is handed to
 * dlopen as given: one without a slash is searched for by the dynamic loader
 * under its own rules.
 *
 * Input file, binary, every integer a uint64_t and every element of E bytes,
 * all as they are in memory on the host (host byte order):
 *
 *     N                                         the number of calls, >= 1
 *     then N times: index m k n a[m*k] b[k*n]   index < number of libraries,
 *                                               m, k, n >= 1, a and b in the
 *                                               row_major layout of ADR-0008
 *                                               decision 2
 *
 * The file ends exactly after the last call. The whole file is read and its
 * form is checked before the first call, so an input error never follows a
 * call that ran: a short file, trailing bytes, an index out of range, a zero
 * dimension or an input array whose size cannot be held in the file are all
 * errors of the input file (status 5); an output array whose size does not fit
 * in size_t is found by the same check (status 3).
 *
 * Execution and report. The calls run in file order, one at a time. Each call
 * gets its own a, b and c from malloc, which are distinct and aligned for an
 * element; every element of c is set to the NaN pattern of the build before
 * the call of the entry point (m, k, n, a, b, c). After it returns, the m*n
 * elements of c (c[i*n + j]) are written to the report as the E*m*n bytes they
 * have in memory, on the standard output the process was started with, and
 * nothing else goes there. After the last call comes the end mark, the 4 bytes
 * "end\n": a complete report has the sum of E*m*n over the calls plus 4 bytes.
 * Descriptor 1 is pointed at standard error before the first library is
 * loaded, so what a kernel prints, also while it is loaded, is not part of the
 * report.
 *
 * Exit status:
 *   0  the end mark was written; in no other case
 *   2  the command line
 *   3  an array that cannot be held or allocated
 *   4  a descriptor or a write of the report
 *   5  the input file: open, read or form
 *   6  a library that cannot be loaded or has no entry point; the line names
 *      the library's index and, for a missing entry point, its symbol, and
 *      the text of dlerror() may follow
 * A status other than 0 comes with one line on standard error and without the
 * end mark.
 */
#define _POSIX_C_SOURCE 200809L

#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#ifdef HILCLAW_MODEL_BF16
typedef uint16_t element;
typedef uint16_t element_bits;
#define ENTRY_SYMBOL "hilclaw_gemm_bf16"
#define NAN_BITS UINT16_C(0x7FC0)
#else
typedef float element;
typedef uint32_t element_bits;
#define ENTRY_SYMBOL "hilclaw_gemm"
#define NAN_BITS UINT32_C(0x7FC00000)
#endif

typedef void (*gemm_entry)(size_t m, size_t k, size_t n, const element *restrict a, const element *restrict b,
                           element *restrict c);

typedef char float_is_32_bits[sizeof(float) == sizeof(uint32_t) ? 1 : -1];
typedef char uint16_is_2_bytes[sizeof(uint16_t) == 2 ? 1 : -1];
typedef char element_is_its_bits[sizeof(element) == sizeof(element_bits) ? 1 : -1];
typedef char entry_fits_a_pointer[sizeof(gemm_entry) == sizeof(void *) ? 1 : -1];

enum {
    STATUS_COMMAND_LINE = 2,
    STATUS_MEMORY = 3,
    STATUS_SYSTEM = 4,
    STATUS_INPUT = 5,
    STATUS_LIBRARY = 6
};

enum { CALL_HEADER_WORDS = 4 };

static int report_fd = -1;

static int fail(int status, const char *subject, const char *message)
{
    fprintf(stderr, "model_program: %s: %s\n", subject, message);
    return status;
}

static gemm_entry load(const char *path, size_t index)
{
    void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    void *symbol = NULL;
    const char *problem = "cannot be loaded";
    const char *detail;
    gemm_entry entry;

    if (handle != NULL) {
        dlerror();
        symbol = dlsym(handle, ENTRY_SYMBOL);
        problem = "has no " ENTRY_SYMBOL;
    }
    if (symbol == NULL) {
        detail = dlerror();
        fprintf(stderr, "model_program: library %lu: %s%s%s\n", (unsigned long)index, problem,
                detail != NULL ? ": " : "", detail != NULL ? detail : "");
        exit(STATUS_LIBRARY);
    }
    memcpy(&entry, &symbol, sizeof entry);
    return entry;
}

static unsigned char *read_file(const char *path, size_t *length)
{
    FILE *file = fopen(path, "rb");
    unsigned char *data = NULL;
    size_t used = 0, capacity = 0;

    if (file == NULL)
        exit(fail(STATUS_INPUT, "input file", "cannot be opened"));
    for (;;) {
        size_t got;

        if (used == capacity) {
            unsigned char *grown;

            if (capacity > SIZE_MAX / 2 - 4096)
                exit(fail(STATUS_MEMORY, "input file", "too large to be held"));
            capacity = capacity * 2 + 4096;
            grown = realloc(data, capacity);
            if (grown == NULL)
                exit(fail(STATUS_MEMORY, "input file", "cannot allocate a buffer for it"));
            data = grown;
        }
        got = fread(data + used, 1, capacity - used, file);
        used += got;
        if (got == 0)
            break;
    }
    if (ferror(file))
        exit(fail(STATUS_INPUT, "input file", "cannot be read"));
    fclose(file);
    *length = used;
    return data;
}

static uint64_t word_at(const unsigned char *data, size_t offset)
{
    uint64_t value;

    memcpy(&value, data + offset, sizeof value);
    return value;
}

static int element_bytes(uint64_t rows, uint64_t columns, uint64_t *bytes)
{
    if (rows > UINT64_MAX / sizeof(element) / columns)
        return 0;
    *bytes = rows * columns * sizeof(element);
    return 1;
}

static void check_form(const unsigned char *data, size_t length, size_t libraries)
{
    const size_t header = CALL_HEADER_WORDS * sizeof(uint64_t);
    size_t offset = sizeof(uint64_t);
    uint64_t calls, call;

    if (length < sizeof(uint64_t))
        exit(fail(STATUS_INPUT, "input file", "too short for the number of calls"));
    calls = word_at(data, 0);
    if (calls == 0)
        exit(fail(STATUS_INPUT, "input file", "the number of calls is 0"));
    for (call = 0; call < calls; call++) {
        uint64_t index, m, k, n, a_bytes, b_bytes;

        if (length - offset < header)
            exit(fail(STATUS_INPUT, "input file", "too short for a call"));
        index = word_at(data, offset);
        m = word_at(data, offset + 8);
        k = word_at(data, offset + 16);
        n = word_at(data, offset + 24);
        offset += header;
        if (index >= libraries)
            exit(fail(STATUS_INPUT, "input file", "a kernel index is out of range"));
        if (m == 0 || k == 0 || n == 0)
            exit(fail(STATUS_INPUT, "input file", "a dimension is 0"));
        if (!element_bytes(m, k, &a_bytes) || !element_bytes(k, n, &b_bytes) || a_bytes > length - offset ||
            b_bytes > length - offset - a_bytes)
            exit(fail(STATUS_INPUT, "input file", "too short for the matrices of a call"));
        if (m > SIZE_MAX / sizeof(element) / n)
            exit(fail(STATUS_MEMORY, "input file", "the output of a call cannot be held"));
        offset += (size_t)(a_bytes + b_bytes);
    }
    if (offset != length)
        exit(fail(STATUS_INPUT, "input file", "bytes follow the last call"));
}

static void fill_nan(element *array, size_t count)
{
    const element_bits bits = NAN_BITS;
    size_t i;

    for (i = 0; i < count; i++)
        memcpy(&array[i], &bits, sizeof bits);
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

static size_t run_call(const unsigned char *data, size_t offset, gemm_entry *entries)
{
    size_t index = (size_t)word_at(data, offset);
    size_t m = (size_t)word_at(data, offset + 8);
    size_t k = (size_t)word_at(data, offset + 16);
    size_t n = (size_t)word_at(data, offset + 24);
    size_t a_bytes = m * k * sizeof(element), b_bytes = k * n * sizeof(element), c_bytes = m * n * sizeof(element);
    element *a, *b, *c;

    offset += CALL_HEADER_WORDS * sizeof(uint64_t);
    a = malloc(a_bytes);
    b = malloc(b_bytes);
    c = malloc(c_bytes);
    if (a == NULL || b == NULL || c == NULL)
        exit(fail(STATUS_MEMORY, "malloc", "cannot allocate the operands"));
    memcpy(a, data + offset, a_bytes);
    memcpy(b, data + offset + a_bytes, b_bytes);
    fill_nan(c, m * n);
    entries[index](m, k, n, a, b, c);
    emit(c, c_bytes);
    free(c);
    free(b);
    free(a);
    return offset + a_bytes + b_bytes;
}

int main(int argc, char **argv)
{
    size_t libraries, i, length, offset;
    uint64_t calls, call;
    gemm_entry *entries;
    unsigned char *data;

    if (argc < 3)
        return fail(STATUS_COMMAND_LINE, "usage", "<input file> <library> [<library> ...]");
    libraries = (size_t)(argc - 2);
    entries = malloc(libraries * sizeof *entries);
    if (entries == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the table of entry points");
    report_fd = dup(STDOUT_FILENO);
    if (report_fd < 0 || dup2(STDERR_FILENO, STDOUT_FILENO) < 0)
        return fail(STATUS_SYSTEM, "descriptors", "cannot keep the standard output apart");
    for (i = 0; i < libraries; i++)
        entries[i] = load(argv[i + 2], i);

    data = read_file(argv[1], &length);
    check_form(data, length, libraries);

    calls = word_at(data, 0);
    offset = sizeof(uint64_t);
    for (call = 0; call < calls; call++)
        offset = run_call(data, offset, entries);
    emit("end\n", 4);
    free(data);
    free(entries);
    return 0;
}
