/*
 * Graph program of the model executor: runs a resolved call plan of a model
 * graph file (ADR-0193 decision 5), encoded by hilclaw.model_graph.encode.
 *
 * It loads kernels of the six bf16 kinds from shared libraries, reads the
 * scalars, the arrays, the passes and their steps, the token ids and the
 * contents of the weights and tables from an input file, runs the steps of
 * each pass in order and writes the token ids and the output rows to the
 * report, in the given-sequence mode of ADR-0166 decision 7 or the greedy
 * generation mode of ADR-0176 decision 5. Its loading, report, end mark,
 * token selection and statuses are those of model_forward.c, whose header
 * comment states them; what differs is that the calls come from the input
 * rather than from fixed source. It does no floating-point arithmetic: the
 * scalars and float tables are passed through to kernels, every other element
 * is a uint16_t bf16 pattern that is only copied, and the selection orders
 * patterns by an integer key. It reads no clock, no environment variable and
 * no standard input; it needs the C library and POSIX.1-2008 only, <dlfcn.h>
 * included.
 *
 * Command line, at least two arguments:
 *
 *     <input file> <library> [<library> ...]
 *
 * Library i (0-based) has index i; each is opened with
 * dlopen(path, RTLD_NOW | RTLD_LOCAL), all before the input file is read.
 *
 * Input file, binary, host byte order, no padding; every integer a uint64_t,
 * every float binary32:
 *
 *     A K G S V mode O Q   8 integers: arrays, scalars, passes, the prompt
 *                          length, the vocabulary, mode 0 given-sequence or
 *                          1 generation, the output array and its row width
 *     scalars              K floats
 *     arrays               A records (elements, element size 2 or 4,
 *                          role 0 read from the file or 1 filled)
 *     passes               G records (output rows, steps)
 *     steps                for every pass in order, its steps of 20 integers:
 *                          op, library, 5 shape words, 6 (array, offset)
 *                          operand pairs, scalar
 *     token ids            S + G for the given-sequence mode, S for the other
 *     contents             the elements of every role-0 array, in array order
 *
 * The ops: 0 embed (shape rows, columns, first token; operands the weight
 * and the output: row i of the output gets row token[first + i] of the
 * weight); 1 copy (shape rows, columns, source stride, target stride;
 * operands the source from its offset and the target: row i copies columns
 * elements from offset + i * source stride to offset + i * target stride);
 * 2 gemm (m, k, n; a, b, c), 3 rmsnorm (m, n; x, w, y; the scalar is eps),
 * 4 elementwise_add (m, n; a, b, c), 5 swiglu (m, n; gate, up, out), 6 rope
 * (m, h, d; x, freqs_cis, out) and 7 sdpa_kv_cache (m, l, h, h_kv, d; q,
 * k_new, v_new, cache_k, cache_v, out), each called through the library's
 * hilclaw_<kind>_bf16 with its operands at their offsets. Unused words are 0.
 *
 * Checks, all before the first call. Errors of the input file (status 5): a
 * file shorter than the header, that is not a regular file or whose length
 * is not the one its tables give; A, G, S, V or Q of 0; a mode above 1;
 * an output array that is not a filled 2-byte array; Q above V in the
 * generation mode; an array of 0 elements, an element size other than 2 or
 * 4, a role above 1 or a filled array of 4-byte elements; a scalar that is
 * not finite or not above 0; a pass of 0 steps or 0 output rows, or whose
 * output rows run past the output array; an unknown op; a library index not
 * below the number of libraries; a shape word of 0 but embed's first token;
 * a rope d that is odd, an sdpa h not a multiple of h_kv or l below m; an operand
 * array index not below A, a range past its array, an element size other
 * than the operand's (4 for freqs_cis, 2 otherwise), two operands of a step
 * whose ranges in one array overlap; a scalar index not below K; an embed
 * whose tokens are not below S + the pass index; a token id not below V.
 * The byte size of any table, array or the file that does not fit in size_t
 * or uint64_t is found before anything is allocated from it (status 3), as is
 * a failed allocation. A library lacking the entry point of a step's kind at
 * any pass is status 6, found before the first call.
 *
 * Every filled array element is set to 0x7FC0 once, at allocation. Report,
 * on the standard output the process was started with: the token ids as read,
 * then for each pass its output rows (the first rows * Q elements of the
 * output array after the pass), then in the generation mode the G selected
 * token ids, then the end mark "end\n". In the generation mode the selection
 * row of a pass is its last output row; the selected token is the smallest
 * index of a greatest element by the key of model_forward.c and becomes token
 * S + pass; a NaN in it is status 7. Descriptor 1 is pointed at standard
 * error before the first library is loaded.
 *
 * Exit status: 0 the end mark was written; 2 the command line; 3 a size or an
 * allocation; 4 a descriptor or a write of the report; 5 the input file;
 * 6 a library or an entry point; 7 a NaN in a selection row. A status other
 * than 0 comes with one line on standard error and without the end mark.
 */
#define _POSIX_C_SOURCE 200809L

#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

typedef void (*gemm_entry)(size_t, size_t, size_t, const uint16_t *, const uint16_t *, uint16_t *);
typedef void (*rmsnorm_entry)(size_t, size_t, float, const uint16_t *, const uint16_t *, uint16_t *);
typedef void (*row_entry)(size_t, size_t, const uint16_t *, const uint16_t *, uint16_t *);
typedef void (*rope_entry)(size_t, size_t, size_t, const uint16_t *, const float *, uint16_t *);
typedef void (*sdpa_entry)(size_t, size_t, size_t, size_t, size_t, const uint16_t *, const uint16_t *,
                           const uint16_t *, uint16_t *, uint16_t *, uint16_t *);

typedef char float_is_32_bits[sizeof(float) == sizeof(uint32_t) ? 1 : -1];
typedef char entries_fit_a_pointer[sizeof(gemm_entry) == sizeof(void *) ? 1 : -1];

enum { STATUS_COMMAND_LINE = 2, STATUS_MEMORY, STATUS_SYSTEM, STATUS_INPUT, STATUS_LIBRARY, STATUS_SELECTION };
enum { HEADER_WORDS = 8, ARRAY_WORDS = 3, PASS_WORDS = 2, STEP_WORDS = 20, OPERANDS = 6, NAN_BITS = 0x7FC0 };
enum { EMBED, COPY, GEMM, RMSNORM, ADD, SWIGLU, ROPE, SDPA, OPS };

static const char *const symbol_of[OPS] = {
    NULL, NULL, "hilclaw_gemm_bf16", "hilclaw_rmsnorm_bf16", "hilclaw_elementwise_add_bf16",
    "hilclaw_swiglu_bf16", "hilclaw_rope_bf16", "hilclaw_sdpa_kv_cache_bf16"};
static const unsigned operands_of[OPS] = {2, 2, 3, 3, 3, 3, 3, 6};
static const unsigned shape_of[OPS] = {2, 4, 3, 2, 2, 2, 3, 5};

struct array {
    uint64_t elements, size, role;
    void *data;
};

union entry {
    gemm_entry gemm;
    rmsnorm_entry rmsnorm;
    row_entry row;
    rope_entry rope;
    sdpa_entry sdpa;
};

struct step {
    uint64_t op, library, shape[5], operand[OPERANDS][2], scalar;
    union entry entry;
};

struct graph {
    uint64_t A, K, G, S, V, generate, O, Q, steps;
    float *scalars;
    struct array *arrays;
    uint64_t *passes, *tokens;
    struct step *step;
};

static int report_fd = -1;

static int fail(int status, const char *subject, const char *message)
{
    fprintf(stderr, "model_graph: %s: %s\n", subject, message);
    return status;
}

static void input_error(const char *message)
{
    exit(fail(STATUS_INPUT, "input file", message));
}

static uint64_t times(uint64_t a, uint64_t b)
{
    if (a != 0 && b > UINT64_MAX / a)
        exit(fail(STATUS_MEMORY, "input file", "a size cannot be held"));
    return a * b;
}

static uint64_t plus(uint64_t a, uint64_t b)
{
    if (b > UINT64_MAX - a)
        exit(fail(STATUS_MEMORY, "input file", "a size cannot be held"));
    return a + b;
}

static uint64_t bytes(uint64_t count, uint64_t element)
{
    uint64_t total = times(count, element);

    if (total > SIZE_MAX)
        exit(fail(STATUS_MEMORY, "input file", "a size cannot be held"));
    return total;
}

static uint64_t span(uint64_t a, uint64_t b)
{
    return a != 0 && b > UINT64_MAX / a ? UINT64_MAX : a * b;
}

static uint64_t reach(uint64_t a, uint64_t b)
{
    return b > UINT64_MAX - a ? UINT64_MAX : a + b;
}

static void *allocate(uint64_t size)
{
    void *memory = malloc(size != 0 ? (size_t)size : 1);

    if (memory == NULL)
        exit(fail(STATUS_MEMORY, "malloc", "cannot allocate a buffer"));
    return memory;
}

static void *read_array(FILE *file, uint64_t size)
{
    void *array = allocate(size);

    if (fread(array, 1, (size_t)size, file) != (size_t)size)
        input_error("cannot be read");
    return array;
}

static void library_failure(size_t index, const char *problem, const char *symbol)
{
    const char *detail = dlerror();

    fprintf(stderr, "model_graph: library %lu: %s%s%s%s\n", (unsigned long)index, problem, symbol,
            detail != NULL ? ": " : "", detail != NULL ? detail : "");
    exit(STATUS_LIBRARY);
}

static void counts(const struct step *s, uint64_t V, uint64_t *count)
{
    const uint64_t *x = s->shape;

    switch (s->op) {
    case EMBED:
        count[0] = span(V, x[1]);
        count[1] = span(x[0], x[1]);
        break;
    case COPY:
        count[0] = reach(span(x[0] - 1, x[2]), x[1]);
        count[1] = reach(span(x[0] - 1, x[3]), x[1]);
        break;
    case GEMM:
        count[0] = span(x[0], x[1]);
        count[1] = span(x[1], x[2]);
        count[2] = span(x[0], x[2]);
        break;
    case RMSNORM:
        count[0] = count[2] = span(x[0], x[1]);
        count[1] = x[1];
        break;
    case ROPE:
        count[0] = count[2] = span(span(x[0], x[1]), x[2]);
        count[1] = span(x[0], x[2]);
        break;
    case SDPA:
        count[0] = count[5] = span(span(x[0], x[2]), x[4]);
        count[1] = count[2] = span(span(x[0], x[3]), x[4]);
        count[3] = count[4] = span(span(x[1], x[3]), x[4]);
        break;
    default:
        count[0] = count[1] = count[2] = span(x[0], x[1]);
    }
}

static void check_step(const struct graph *g, const struct step *s, size_t libraries, uint64_t pass)
{
    uint64_t count[OPERANDS], end[OPERANDS];
    unsigned i, j;

    if (s->op >= OPS)
        input_error("a step has an unknown op");
    if (s->op >= GEMM && s->library >= libraries)
        input_error("a library index is out of range");
    for (i = 0; i < shape_of[s->op]; i++)
        if (s->shape[i] == 0)
            input_error("a shape word is 0");
    if ((s->op == ROPE && s->shape[2] % 2 != 0) ||
        (s->op == SDPA && (s->shape[2] % s->shape[3] != 0 || s->shape[1] < s->shape[0])))
        input_error("a shape is outside its kind's range");
    if (s->op == RMSNORM && s->scalar >= g->K)
        input_error("a scalar index is out of range");
    if (s->op == EMBED && plus(s->shape[2], s->shape[0]) > g->S + pass)
        input_error("an embed reads a token not yet known");
    counts(s, g->V, count);
    for (i = 0; i < operands_of[s->op]; i++) {
        const uint64_t index = s->operand[i][0], offset = s->operand[i][1];
        const struct array *a;

        if (index >= g->A)
            input_error("an operand array is out of range");
        a = &g->arrays[index];
        if (a->size != (s->op == ROPE && i == 1 ? 4u : 2u))
            input_error("an operand array has the wrong element size");
        if (s->op == EMBED && i == 0 && (offset != 0 || span(g->V, s->shape[1]) > a->elements))
            input_error("an embed weight has fewer than V rows");
        end[i] = reach(offset, count[i]);
        if (end[i] > a->elements)
            input_error("an operand range runs past its array");
        for (j = 0; j < i; j++)
            if (s->operand[j][0] == index && s->operand[j][1] < end[i] && offset < end[j])
                input_error("two operands of a step overlap");
    }
}

static FILE *read_tables(const char *path, struct graph *g, size_t libraries)
{
    FILE *file = fopen(path, "rb");
    uint64_t header[HEADER_WORDS], length, need, i, p, at = 0, tokens, known;
    struct stat status;

    if (file == NULL)
        input_error("cannot be opened");
    if (fstat(fileno(file), &status) != 0 || !S_ISREG(status.st_mode))
        input_error("is not a regular file");
    length = (uint64_t)status.st_size;
    if (fread(header, 1, sizeof header, file) != sizeof header)
        input_error("too short for the header");
    g->A = header[0], g->K = header[1], g->G = header[2], g->S = header[3], g->V = header[4];
    g->generate = header[5], g->O = header[6], g->Q = header[7];
    if (g->A == 0 || g->G == 0 || g->S == 0 || g->V == 0 || g->Q == 0)
        input_error("a header count is 0");
    if (g->generate > 1 || g->O >= g->A || (g->generate && g->Q > g->V))
        input_error("the mode, the output array or its row width is out of range");
    known = bytes(plus(g->S, g->G), 8);
    need = plus(plus(sizeof header, bytes(g->K, 4)), plus(bytes(g->A, 8 * ARRAY_WORDS), bytes(g->G, 8 * PASS_WORDS)));
    if (need > length)
        input_error("too short for the length its header gives");
    g->scalars = read_array(file, 4 * g->K);
    for (i = 0; i < g->K; i++) {
        uint32_t bits;

        memcpy(&bits, &g->scalars[i], sizeof bits);
        if ((bits & UINT32_C(0x80000000)) != 0 || (bits & UINT32_C(0x7F800000)) == UINT32_C(0x7F800000) || bits == 0)
            input_error("a scalar is not finite or not above 0");
    }
    g->arrays = allocate(bytes(g->A, sizeof *g->arrays));
    for (i = 0; i < g->A; i++) {
        struct array *a = &g->arrays[i];

        if (fread(a, 1, 8 * ARRAY_WORDS, file) != 8 * ARRAY_WORDS)
            input_error("cannot be read");
        a->data = NULL;
        if (a->elements == 0 || (a->size != 2 && a->size != 4) || a->role > 1 || (a->role == 1 && a->size != 2))
            input_error("an array record is out of range");
        bytes(a->elements, a->size);
        if (a->role == 0)
            need = plus(need, a->elements * a->size);
    }
    if (g->arrays[g->O].role != 1 || g->arrays[g->O].size != 2)
        input_error("the output array is not a filled bf16 array");
    g->passes = read_array(file, 8 * PASS_WORDS * g->G);
    g->steps = 0;
    for (p = 0; p < g->G; p++) {
        if (g->passes[2 * p] == 0 || g->passes[2 * p + 1] == 0 ||
            span(g->passes[2 * p], g->Q) > g->arrays[g->O].elements)
            input_error("a pass has no steps or its output rows run past the output array");
        g->steps = plus(g->steps, g->passes[2 * p + 1]);
    }
    tokens = g->generate ? g->S : plus(g->S, g->G);
    need = plus(need, plus(bytes(g->steps, 8 * STEP_WORDS), 8 * tokens));
    if (length < need)
        input_error("too short for the length its header gives");
    if (length > need)
        input_error("bytes follow the last array");
    g->step = allocate(bytes(g->steps, sizeof *g->step));
    for (p = 0; p < g->G; p++)
        for (i = 0; i < g->passes[2 * p + 1]; i++, at++) {
            struct step *s = &g->step[at];

            if (fread(s, 1, 8 * STEP_WORDS, file) != 8 * STEP_WORDS)
                input_error("cannot be read");
            check_step(g, s, libraries, p);
        }
    g->tokens = allocate(known);
    if (fread(g->tokens, 8, (size_t)tokens, file) != (size_t)tokens)
        input_error("cannot be read");
    for (i = 0; i < tokens; i++)
        if (g->tokens[i] >= g->V)
            input_error("a token id is not below V");
    return file;
}

static void bind(void *const *handles, struct graph *g)
{
    uint64_t i;

    for (i = 0; i < g->steps; i++) {
        struct step *s = &g->step[i];
        void *found;

        if (s->op < GEMM)
            continue;
        dlerror();
        found = dlsym(handles[s->library], symbol_of[s->op]);
        if (found == NULL)
            library_failure((size_t)s->library, "has no ", symbol_of[s->op]);
        memcpy(&s->entry, &found, sizeof found);
    }
}

static void read_contents(FILE *file, struct graph *g)
{
    const uint16_t bits = NAN_BITS;
    uint64_t i, e;

    for (i = 0; i < g->A; i++) {
        struct array *a = &g->arrays[i];

        if (a->role == 0) {
            a->data = read_array(file, a->elements * a->size);
            continue;
        }
        a->data = allocate(a->elements * 2);
        for (e = 0; e < a->elements; e++)
            memcpy((uint16_t *)a->data + e, &bits, sizeof bits);
    }
    fclose(file);
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

static void run_step(const struct graph *g, const struct step *s)
{
    uint16_t *o[OPERANDS];
    size_t x[5], i;
    unsigned j;

    for (j = 0; j < 5; j++)
        x[j] = (size_t)s->shape[j];
    for (j = 0; j < operands_of[s->op]; j++)
        o[j] = (uint16_t *)((char *)g->arrays[s->operand[j][0]].data +
                            (size_t)s->operand[j][1] * (size_t)g->arrays[s->operand[j][0]].size);
    switch (s->op) {
    case EMBED:
        for (i = 0; i < x[0]; i++)
            memcpy(o[1] + i * x[1], o[0] + (size_t)g->tokens[x[2] + i] * x[1], x[1] * 2);
        break;
    case COPY:
        for (i = 0; i < x[0]; i++)
            memcpy(o[1] + i * x[3], o[0] + i * x[2], x[1] * 2);
        break;
    case GEMM:
        s->entry.gemm(x[0], x[1], x[2], o[0], o[1], o[2]);
        break;
    case RMSNORM:
        s->entry.rmsnorm(x[0], x[1], g->scalars[s->scalar], o[0], o[1], o[2]);
        break;
    case ROPE:
        s->entry.rope(x[0], x[1], x[2], o[0], (const float *)(void *)o[1], o[2]);
        break;
    case SDPA:
        s->entry.sdpa(x[0], x[1], x[2], x[3], x[4], o[0], o[1], o[2], o[3], o[4], o[5]);
        break;
    default:
        s->entry.row(x[0], x[1], o[0], o[1], o[2]);
    }
}

static long key(uint16_t bits)
{
    long magnitude = bits & 0x7FFF;

    return (bits & 0x8000) != 0 ? -magnitude : magnitude;
}

static void select_token(struct graph *g, uint64_t pass, uint64_t rows)
{
    const uint16_t *row = (const uint16_t *)g->arrays[g->O].data + (size_t)((rows - 1) * g->Q);
    size_t best = 0, i;

    for (i = 0; i < g->Q; i++) {
        if ((row[i] & 0x7F80) == 0x7F80 && (row[i] & 0x7F) != 0) {
            fprintf(stderr, "model_graph: pass %lu: the selection row holds a NaN\n", (unsigned long)pass);
            exit(STATUS_SELECTION);
        }
        if (key(row[i]) > key(row[best]))
            best = i;
    }
    g->tokens[g->S + pass] = best;
}

int main(int argc, char **argv)
{
    struct graph g;
    size_t libraries, i;
    uint64_t p, at = 0, s;
    void **handles;
    FILE *file;

    if (argc < 3)
        return fail(STATUS_COMMAND_LINE, "usage", "<input file> <library> [<library> ...]");
    libraries = (size_t)(argc - 2);
    handles = malloc(libraries * sizeof *handles);
    if (handles == NULL)
        return fail(STATUS_MEMORY, "malloc", "cannot allocate the table of libraries");
    report_fd = dup(STDOUT_FILENO);
    if (report_fd < 0 || dup2(STDERR_FILENO, STDOUT_FILENO) < 0)
        return fail(STATUS_SYSTEM, "descriptors", "cannot keep the standard output apart");
    for (i = 0; i < libraries; i++) {
        handles[i] = dlopen(argv[i + 2], RTLD_NOW | RTLD_LOCAL);
        if (handles[i] == NULL)
            library_failure(i, "cannot be loaded", "");
    }

    memset(&g, 0, sizeof g);
    file = read_tables(argv[1], &g, libraries);
    bind(handles, &g);
    read_contents(file, &g);

    emit(g.tokens, (size_t)(g.generate ? g.S : g.S + g.G) * 8);
    for (p = 0; p < g.G; p++) {
        for (s = 0; s < g.passes[2 * p + 1]; s++, at++)
            run_step(&g, &g.step[at]);
        emit(g.arrays[g.O].data, (size_t)(g.passes[2 * p] * g.Q) * 2);
        if (g.generate)
            select_token(&g, p, g.passes[2 * p]);
    }
    if (g.generate)
        emit(g.tokens + g.S, (size_t)g.G * 8);
    emit("end\n", 4);
    for (p = 0; p < g.A; p++)
        free(g.arrays[p].data);
    free(g.arrays);
    free(g.step);
    free(g.passes);
    free(g.tokens);
    free(g.scalars);
    free(handles);
    return 0;
}
