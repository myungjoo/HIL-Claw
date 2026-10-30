/*
 * Forward program of the model executor: the bf16 forward pass of ADR-0166.
 *
 * It loads kernels of the six bf16 kinds from shared libraries, reads the
 * weights, the RoPE table, eps, the token ids and the library table from an
 * input file, runs the calls of a generation in the order of ADR-0166
 * decisions 1 and 3 and writes the token ids and the logits to the report:
 * the prefill, then the G - 1 decode passes, in the given-sequence mode of
 * ADR-0166 decision 7 or in the greedy generation mode of ADR-0176 decision 5.
 * Its one rule over values is that mode's token selection; it holds no
 * reference, tolerance or verdict and builds no RoPE table. It does no
 * floating-point arithmetic: eps and the RoPE table are passed through to the
 * kernels, every other element is a uint16_t bf16 pattern that is only
 * copied, never cast, and the selection orders patterns by an integer key. It
 * reads no clock, no environment variable and no standard input. It needs the
 * C library and POSIX.1-2008 only, <dlfcn.h> included. The rules behind the
 * buffers, the operands of each call, the copies and the cache are ADR-0166's
 * and are not restated here.
 *
 * Command line, at least two arguments:
 *
 *     <input file> <library> [<library> ...]
 *
 * Library i (0-based, in command-line order) has index i. Each is opened with
 * dlopen(path, RTLD_NOW | RTLD_LOCAL), all of them before the input file is
 * read; the path is handed to dlopen as given.
 *
 * Notation of ADR-0166: D hidden, F intermediate, V vocabulary, N layers,
 * H heads, H_kv KV heads, d head_dim, W = (H + 2*H_kv)*d, S the prompt length,
 * G the generation length, C = S + G - 1. Call sites, in this order (the order
 * of hilclaw.model_binding's call-site tuples), with their kinds:
 *
 *     0 qkv  1 o  2 gate  3 up  4 down  5 lm_head            gemm
 *     6 attention_norm  7 ffn_norm  8 norm                   rmsnorm
 *     9 attention_residual  10 ffn_residual                  elementwise_add
 *     11 ffn_activation                                      swiglu
 *     12 rope_q  13 rope_k                                   rope
 *     14 sdpa                                                sdpa_kv_cache
 *
 * Input file, binary, host byte order, with no padding: every integer a
 * uint64_t, every bf16 element a uint16_t pattern, every float binary32.
 *
 *     D F V N H H_kv d S G form            10 integers; form is
 *                                          lm_head_rows + 2*mode, with
 *                                          lm_head_rows 0 "all" and 1
 *                                          "last", mode 0 the given-sequence
 *                                          mode and 1 the generation mode
 *     eps                                  1 float
 *     library table                        15*G integers: for call site s and
 *                                          pass p (pass 0 is the prefill),
 *                                          entry s*G + p is the index of the
 *                                          library that call site uses at
 *                                          pass p
 *     RoPE table                           C*d floats, row-major
 *                                          [positions, d], row t position t
 *     token ids                            the given-sequence mode: S + G
 *                                          integers, the prompt, then the
 *                                          given tokens; the generation
 *                                          mode: the S integers of the prompt
 *     embedding                            V*D bf16, row t token t
 *     N times, for layer 0 ... N - 1:
 *       w_attention_norm                   D bf16
 *       w_qkv                              D*W bf16, [D, W], columns the Q,
 *                                          K and V ranges, head by head
 *       w_o                                H*d*D bf16, [H*d, D]
 *       w_ffn_norm                         D bf16
 *       w_gate, w_up                       D*F bf16 each, [D, F]
 *       w_down                             F*D bf16, [F, D]
 *     w_norm                               D bf16
 *     w_lm_head                            D*V bf16, [D, V]
 *
 * The file ends exactly after w_lm_head. Checks, all before the first call: a
 * file shorter than the header and eps, a dimension, S or G of 0, H not a
 * multiple of H_kv, an odd d, a form above 3, an eps that is
 * not finite or not above 0 (checked on its bit pattern), an input file that
 * is not a regular file or whose length is not the one the header gives, a
 * library index not below the number of libraries and a token id not below V
 * are errors of the input file (status 5). The byte size of any buffer,
 * weight, cache, the RoPE table, the token ids, the library table or the
 * entry points of the G passes that does not fit in size_t, and a length of
 * the file that does not fit in a uint64_t, are found after the header and
 * before anything is allocated (status 3), as is a failed allocation. A
 * library bound in the table that lacks the entry point of its call site's
 * kind (hilclaw_gemm_bf16, hilclaw_rmsnorm_bf16,
 * hilclaw_elementwise_add_bf16, hilclaw_swiglu_bf16, hilclaw_rope_bf16 or
 * hilclaw_sdpa_kv_cache_bf16) at any pass is status 6, found before the first
 * call; a library bound to no call site is not searched.
 *
 * Buffers, ADR-0166 decision 2: each weight, the RoPE table and the token ids
 * are read into arrays of their own; the activations x, h, normed, qkv_out,
 * q_in, k_in, v_in, q_rot, k_rot, attn, o_out, gate_out, up_out, act and
 * down_out are sized for S rows and shared by all layers, logits holds S*V
 * elements for "all" and V for "last", and each layer has cache_k and
 * cache_v of C*H_kv*d elements. All are allocated once, before the prefill,
 * and every activation and cache element is set to 0x7FC0 then and never
 * again. No two operands of a call share or overlap.
 *
 * The prefill (T = S, P = 0) makes the calls of ADR-0166 decision 3, rows 1
 * to 16, in that order: the embedding row copy; per layer attention_norm,
 * qkv, the Q, K and V range copies, rope_q, rope_k (freqs_cis the table from
 * row P), sdpa (m = T, l = P + T, the layer's caches from their starts), o,
 * attention_residual, ffn_norm, gate, up, ffn_activation, down,
 * ffn_residual; then norm and lm_head, (T, D, V) on normed for "all" and
 * (1, D, V) on row T - 1 of normed for "last". Decode pass k (k = 1 ...
 * G - 1) makes the same calls with T = 1 and P = S + k - 1 on the first row
 * of each activation: its one token is token id P, given token k - 1 or the
 * token selected after pass k - 1, so the last given or selected token is
 * fed to no pass; freqs_cis is row P of the table, and sdpa has m = 1,
 * l = P + 1 and the same cache buffers, which keep what the
 * earlier passes wrote. Each call of pass p uses the library the table names
 * for its call site at pass p.
 *
 * Selection, the generation mode only (ADR-0176 decision 5): after the
 * lm_head call of pass p, the selection row is the last logits row of the
 * pass (row T - 1 for "all", the one row for "last"). Its elements are
 * ordered by the value they encode, through the integer key +m for a pattern
 * with sign bit 0 and -m for one with sign bit 1, m the low 15 bits: -0
 * equals +0 and the infinities order as values. The selected token is the
 * smallest index of a greatest element; it becomes token id S + p, the
 * token of pass p + 1, and the last pass selects the G-th token. A NaN
 * pattern (exponent bits all 1, fraction not 0) anywhere in the selection
 * row stops the run before the next pass with status 7.
 *
 * Report, on the standard output the process was started with, in the
 * given-sequence mode: the S + G token ids as read (uint64_t), then the
 * logits rows as bf16 patterns, V elements each, pass by pass in pass order:
 * for "all" the T rows of each pass (S + G - 1 rows), for "last" the last row
 * of each pass (G rows); then the end mark "end\n". In the generation mode:
 * the S prompt ids as read, then the logits rows in the same order, then the
 * G selected token ids (uint64_t), then the end mark. Both are
 * 8*(S + G) + 2*rows*V + 4 bytes. Descriptor 1 is
 * pointed at standard error before the first library is loaded, so what a
 * kernel prints is not part of the report.
 *
 * Exit status:
 *   0  the end mark was written; in no other case
 *   2  the command line
 *   3  a size that cannot be held, or an allocation that failed
 *   4  a descriptor or a write of the report
 *   5  the input file: open, read or form
 *   6  a library that cannot be loaded or lacks an entry point; the line
 *      names the library's index and, for a missing entry point, its symbol,
 *      and the text of dlerror() may follow
 *   7  a NaN in the selection row of the generation mode; the line names the
 *      pass (0 the prefill), whose logits rows the report already holds
 * A status other than 0 comes with one line on standard error and without the
 * end mark; a kernel that ends the process leaves the report without it.
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

typedef void (*gemm_entry)(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b,
                           uint16_t *restrict c);
typedef void (*rmsnorm_entry)(size_t m, size_t n, float eps, const uint16_t *restrict x,
                              const uint16_t *restrict w, uint16_t *restrict y);
typedef void (*add_entry)(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b,
                          uint16_t *restrict c);
typedef void (*swiglu_entry)(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up,
                             uint16_t *restrict out);
typedef void (*rope_entry)(size_t m, size_t h, size_t d, const uint16_t *restrict x,
                           const float *restrict freqs_cis, uint16_t *restrict out);
typedef void (*sdpa_entry)(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q,
                           const uint16_t *restrict k_new, const uint16_t *restrict v_new,
                           uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);

typedef char float_is_32_bits[sizeof(float) == sizeof(uint32_t) ? 1 : -1];
typedef char uint16_is_2_bytes[sizeof(uint16_t) == 2 ? 1 : -1];
typedef char entries_fit_a_pointer[sizeof(gemm_entry) == sizeof(void *) && sizeof(rmsnorm_entry) == sizeof(void *) &&
                                           sizeof(add_entry) == sizeof(void *) &&
                                           sizeof(swiglu_entry) == sizeof(void *) &&
                                           sizeof(rope_entry) == sizeof(void *) &&
                                           sizeof(sdpa_entry) == sizeof(void *)
                                       ? 1
                                       : -1];

enum {
    STATUS_COMMAND_LINE = 2,
    STATUS_MEMORY = 3,
    STATUS_SYSTEM = 4,
    STATUS_INPUT = 5,
    STATUS_LIBRARY = 6,
    STATUS_SELECTION = 7
};

enum { HEADER_WORDS = 10, SITES = 15, NAN_BITS = 0x7FC0 };

enum {
    QKV, O, GATE, UP, DOWN, LM_HEAD, ATTENTION_NORM, FFN_NORM, NORM, ATTENTION_RESIDUAL, FFN_RESIDUAL,
    FFN_ACTIVATION, ROPE_Q, ROPE_K, SDPA
};

static const char *const site_symbol[SITES] = {
    "hilclaw_gemm_bf16", "hilclaw_gemm_bf16", "hilclaw_gemm_bf16",
    "hilclaw_gemm_bf16", "hilclaw_gemm_bf16", "hilclaw_gemm_bf16",
    "hilclaw_rmsnorm_bf16", "hilclaw_rmsnorm_bf16", "hilclaw_rmsnorm_bf16",
    "hilclaw_elementwise_add_bf16", "hilclaw_elementwise_add_bf16",
    "hilclaw_swiglu_bf16",
    "hilclaw_rope_bf16", "hilclaw_rope_bf16",
    "hilclaw_sdpa_kv_cache_bf16"};

struct pass_entries {
    gemm_entry qkv, o, gate, up, down, lm_head;
    rmsnorm_entry attention_norm, ffn_norm, norm;
    add_entry attention_residual, ffn_residual;
    swiglu_entry ffn_activation;
    rope_entry rope_q, rope_k;
    sdpa_entry sdpa;
};

struct layer {
    uint16_t *attention_norm, *qkv, *o, *ffn_norm, *gate, *up, *down, *cache_k, *cache_v;
};

struct model {
    size_t D, F, V, N, H, H_kv, d, S, G, W, C;
    int last, generate;
    float eps;
    uint64_t *table, *tokens;
    float *rope;
    uint16_t *embedding, *norm, *lm_head;
    struct layer *layers;
    uint16_t *x, *h, *normed, *qkv_out, *q_in, *k_in, *v_in, *q_rot, *k_rot, *attn, *o_out, *gate_out, *up_out,
        *act, *down_out, *logits;
};

static int report_fd = -1;

static int fail(int status, const char *subject, const char *message)
{
    fprintf(stderr, "model_forward: %s: %s\n", subject, message);
    return status;
}

static void library_failure(size_t index, const char *problem, const char *symbol)
{
    const char *detail = dlerror();

    fprintf(stderr, "model_forward: library %lu: %s%s%s%s\n", (unsigned long)index, problem, symbol,
            detail != NULL ? ": " : "", detail != NULL ? detail : "");
    exit(STATUS_LIBRARY);
}

static uint64_t times(uint64_t a, uint64_t b, const char *what)
{
    if (a != 0 && b > UINT64_MAX / a)
        exit(fail(STATUS_MEMORY, what, "its size cannot be held"));
    return a * b;
}

static uint64_t plus(uint64_t a, uint64_t b, const char *what)
{
    if (b > UINT64_MAX - a)
        exit(fail(STATUS_MEMORY, what, "its size cannot be held"));
    return a + b;
}

static uint64_t bytes(uint64_t count, size_t element, const char *what)
{
    uint64_t total = times(count, element, what);

    if (total > SIZE_MAX)
        exit(fail(STATUS_MEMORY, what, "its size cannot be held"));
    return total;
}

static void *allocate(size_t size)
{
    void *memory = malloc(size);

    if (memory == NULL)
        exit(fail(STATUS_MEMORY, "malloc", "cannot allocate a buffer"));
    return memory;
}

static void read_exactly(FILE *file, void *into, size_t size)
{
    if (fread(into, 1, size, file) != size)
        exit(fail(STATUS_INPUT, "input file", "cannot be read"));
}

static void *read_array(FILE *file, size_t size)
{
    void *array = allocate(size);

    read_exactly(file, array, size);
    return array;
}

static uint16_t *activation(size_t count)
{
    const uint16_t bits = NAN_BITS;
    uint16_t *array = allocate(count * sizeof *array);
    size_t i;

    for (i = 0; i < count; i++)
        memcpy(&array[i], &bits, sizeof bits);
    return array;
}

static void check_header(const uint64_t *word, uint32_t eps_bits)
{
    size_t i;

    for (i = 0; i < 9; i++)
        if (word[i] == 0)
            exit(fail(STATUS_INPUT, "input file", "a dimension, S or G is 0"));
    if (word[4] % word[5] != 0)
        exit(fail(STATUS_INPUT, "input file", "H is not a multiple of H_kv"));
    if (word[6] % 2 != 0)
        exit(fail(STATUS_INPUT, "input file", "d is odd"));
    if (word[9] > 3)
        exit(fail(STATUS_INPUT, "input file", "the form of lm_head_rows and mode is above 3"));
    if ((eps_bits & UINT32_C(0x80000000)) != 0 || (eps_bits & UINT32_C(0x7F800000)) == UINT32_C(0x7F800000) ||
        eps_bits == 0)
        exit(fail(STATUS_INPUT, "input file", "eps is not finite or not above 0"));
}

static uint64_t check_sizes(const uint64_t *word)
{
    const uint64_t D = word[0], F = word[1], V = word[2], N = word[3], H = word[4], H_kv = word[5], d = word[6],
                   S = word[7], G = word[8];
    const uint64_t W = times(plus(H, times(2, H_kv, "qkv_out"), "qkv_out"), d, "qkv_out");
    const uint64_t C = plus(S, G, "token ids") - 1, rows = (word[9] & 1) == 1 ? 1 : S;
    const uint64_t read_tokens = word[9] >> 1 == 1 ? S : S + G;
    uint64_t layer, total;

    bytes(times(S, D, "x"), 2, "x");
    bytes(times(S, F, "gate_out"), 2, "gate_out");
    bytes(times(S, W, "qkv_out"), 2, "qkv_out");
    bytes(times(S, times(H, d, "q_in"), "q_in"), 2, "q_in");
    bytes(times(C, times(H_kv, d, "cache"), "cache"), 2, "cache");
    bytes(times(rows, V, "logits"), 2, "logits");
    bytes(N, sizeof(struct layer), "layers");
    bytes(G, sizeof(struct pass_entries), "entry points");
    bytes(S + G, 8, "token ids");
    layer = bytes(times(D, W, "w_qkv"), 2, "w_qkv");
    layer = plus(layer, bytes(times(times(H, d, "w_o"), D, "w_o"), 2, "w_o"), "a layer");
    layer = plus(layer, times(3, bytes(times(D, F, "w_gate"), 2, "w_gate"), "a layer"), "a layer");
    layer = plus(layer, times(4, D, "a layer"), "a layer");
    total = plus(HEADER_WORDS * 8 + 4, bytes(times(SITES, G, "library table"), 8, "library table"), "input file");
    total = plus(total, bytes(times(C, d, "RoPE table"), 4, "RoPE table"), "input file");
    total = plus(total, read_tokens * 8, "input file");
    total = plus(total, times(N, layer, "input file"), "input file");
    total = plus(total, times(2, bytes(times(V, D, "embedding"), 2, "embedding"), "input file"), "input file");
    return plus(total, times(2, D, "w_norm"), "input file");
}

static FILE *open_input(const char *path, struct model *m)
{
    FILE *file = fopen(path, "rb");
    uint64_t word[HEADER_WORDS], file_bytes;
    uint32_t eps_bits;
    struct stat status;

    if (file == NULL)
        exit(fail(STATUS_INPUT, "input file", "cannot be opened"));
    if (fread(word, 1, sizeof word, file) != sizeof word || fread(&eps_bits, 1, sizeof eps_bits, file) != sizeof eps_bits)
        exit(fail(STATUS_INPUT, "input file", "too short for the header and eps"));
    check_header(word, eps_bits);
    file_bytes = check_sizes(word);
    if (fstat(fileno(file), &status) != 0 || !S_ISREG(status.st_mode))
        exit(fail(STATUS_INPUT, "input file", "is not a regular file"));
    if ((uint64_t)status.st_size < file_bytes)
        exit(fail(STATUS_INPUT, "input file", "too short for the length its header gives"));
    if ((uint64_t)status.st_size > file_bytes)
        exit(fail(STATUS_INPUT, "input file", "bytes follow the last weight"));
    m->D = (size_t)word[0];
    m->F = (size_t)word[1];
    m->V = (size_t)word[2];
    m->N = (size_t)word[3];
    m->H = (size_t)word[4];
    m->H_kv = (size_t)word[5];
    m->d = (size_t)word[6];
    m->S = (size_t)word[7];
    m->G = (size_t)word[8];
    m->last = (word[9] & 1) == 1;
    m->generate = word[9] >> 1 == 1;
    m->W = (m->H + 2 * m->H_kv) * m->d;
    m->C = m->S + m->G - 1;
    memcpy(&m->eps, &eps_bits, sizeof m->eps);
    return file;
}

static void read_inputs(FILE *file, struct model *m, size_t libraries)
{
    const size_t read_tokens = m->generate ? m->S : m->S + m->G;
    size_t i;

    m->table = read_array(file, SITES * m->G * sizeof *m->table);
    for (i = 0; i < SITES * m->G; i++)
        if (m->table[i] >= libraries)
            exit(fail(STATUS_INPUT, "input file", "a library index is out of range"));
    m->rope = read_array(file, m->C * m->d * sizeof *m->rope);
    m->tokens = allocate((m->S + m->G) * sizeof *m->tokens);
    read_exactly(file, m->tokens, read_tokens * sizeof *m->tokens);
    for (i = 0; i < read_tokens; i++)
        if (m->tokens[i] >= m->V)
            exit(fail(STATUS_INPUT, "input file", "a token id is not below V"));
}

static void read_weights(FILE *file, struct model *m)
{
    const size_t D = m->D, F = m->F, E = sizeof(uint16_t);
    size_t i;

    m->embedding = read_array(file, m->V * D * E);
    m->layers = allocate(m->N * sizeof *m->layers);
    for (i = 0; i < m->N; i++) {
        struct layer *layer = &m->layers[i];

        layer->attention_norm = read_array(file, D * E);
        layer->qkv = read_array(file, D * m->W * E);
        layer->o = read_array(file, m->H * m->d * D * E);
        layer->ffn_norm = read_array(file, D * E);
        layer->gate = read_array(file, D * F * E);
        layer->up = read_array(file, D * F * E);
        layer->down = read_array(file, F * D * E);
    }
    m->norm = read_array(file, D * E);
    m->lm_head = read_array(file, D * m->V * E);
    fclose(file);
}

static void allocate_activations(struct model *m)
{
    const size_t S = m->S, D = m->D, F = m->F, Hd = m->H * m->d, KVd = m->H_kv * m->d;
    size_t i;

    m->x = activation(S * D);
    m->h = activation(S * D);
    m->normed = activation(S * D);
    m->qkv_out = activation(S * m->W);
    m->q_in = activation(S * Hd);
    m->k_in = activation(S * KVd);
    m->v_in = activation(S * KVd);
    m->q_rot = activation(S * Hd);
    m->k_rot = activation(S * KVd);
    m->attn = activation(S * Hd);
    m->o_out = activation(S * D);
    m->gate_out = activation(S * F);
    m->up_out = activation(S * F);
    m->act = activation(S * F);
    m->down_out = activation(S * D);
    m->logits = activation((m->last ? 1 : S) * m->V);
    for (i = 0; i < m->N; i++) {
        m->layers[i].cache_k = activation(m->C * KVd);
        m->layers[i].cache_v = activation(m->C * KVd);
    }
}

static void *find(void *const *handles, const struct model *m, size_t site, size_t pass)
{
    size_t index = (size_t)m->table[site * m->G + pass];
    void *symbol;

    dlerror();
    symbol = dlsym(handles[index], site_symbol[site]);
    if (symbol == NULL)
        library_failure(index, "has no ", site_symbol[site]);
    return symbol;
}

static void bind(void *const *handles, const struct model *m, size_t pass, struct pass_entries *e)
{
    void *s[SITES];
    size_t i;

    for (i = 0; i < SITES; i++)
        s[i] = find(handles, m, i, pass);
    memcpy(&e->qkv, &s[QKV], sizeof(void *));
    memcpy(&e->o, &s[O], sizeof(void *));
    memcpy(&e->gate, &s[GATE], sizeof(void *));
    memcpy(&e->up, &s[UP], sizeof(void *));
    memcpy(&e->down, &s[DOWN], sizeof(void *));
    memcpy(&e->lm_head, &s[LM_HEAD], sizeof(void *));
    memcpy(&e->attention_norm, &s[ATTENTION_NORM], sizeof(void *));
    memcpy(&e->ffn_norm, &s[FFN_NORM], sizeof(void *));
    memcpy(&e->norm, &s[NORM], sizeof(void *));
    memcpy(&e->attention_residual, &s[ATTENTION_RESIDUAL], sizeof(void *));
    memcpy(&e->ffn_residual, &s[FFN_RESIDUAL], sizeof(void *));
    memcpy(&e->ffn_activation, &s[FFN_ACTIVATION], sizeof(void *));
    memcpy(&e->rope_q, &s[ROPE_Q], sizeof(void *));
    memcpy(&e->rope_k, &s[ROPE_K], sizeof(void *));
    memcpy(&e->sdpa, &s[SDPA], sizeof(void *));
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

static void run_pass(const struct model *m, const struct pass_entries *e, size_t T, size_t P)
{
    const size_t D = m->D, F = m->F, H = m->H, H_kv = m->H_kv, d = m->d, W = m->W, Hd = H * d, KVd = H_kv * d;
    const size_t E = sizeof(uint16_t);
    size_t i, l;

    for (i = 0; i < T; i++)
        memcpy(m->x + i * D, m->embedding + (size_t)m->tokens[P + i] * D, D * E);
    for (l = 0; l < m->N; l++) {
        const struct layer *layer = &m->layers[l];

        e->attention_norm(T, D, m->eps, m->x, layer->attention_norm, m->normed);
        e->qkv(T, D, W, m->normed, layer->qkv, m->qkv_out);
        for (i = 0; i < T; i++) {
            memcpy(m->q_in + i * Hd, m->qkv_out + i * W, Hd * E);
            memcpy(m->k_in + i * KVd, m->qkv_out + i * W + Hd, KVd * E);
            memcpy(m->v_in + i * KVd, m->qkv_out + i * W + Hd + KVd, KVd * E);
        }
        e->rope_q(T, H, d, m->q_in, m->rope + P * d, m->q_rot);
        e->rope_k(T, H_kv, d, m->k_in, m->rope + P * d, m->k_rot);
        e->sdpa(T, P + T, H, H_kv, d, m->q_rot, m->k_rot, m->v_in, layer->cache_k, layer->cache_v, m->attn);
        e->o(T, Hd, D, m->attn, layer->o, m->o_out);
        e->attention_residual(T, D, m->x, m->o_out, m->h);
        e->ffn_norm(T, D, m->eps, m->h, layer->ffn_norm, m->normed);
        e->gate(T, D, F, m->normed, layer->gate, m->gate_out);
        e->up(T, D, F, m->normed, layer->up, m->up_out);
        e->ffn_activation(T, F, m->gate_out, m->up_out, m->act);
        e->down(T, F, D, m->act, layer->down, m->down_out);
        e->ffn_residual(T, D, m->h, m->down_out, m->x);
    }
    e->norm(T, D, m->eps, m->x, m->norm, m->normed);
    if (m->last) {
        e->lm_head(1, D, m->V, m->normed + (T - 1) * D, m->lm_head, m->logits);
        emit(m->logits, m->V * E);
    } else {
        e->lm_head(T, D, m->V, m->normed, m->lm_head, m->logits);
        emit(m->logits, T * m->V * E);
    }
}

static long key(uint16_t bits)
{
    long magnitude = bits & 0x7FFF;

    return (bits & 0x8000) != 0 ? -magnitude : magnitude;
}

static void select_token(struct model *m, size_t pass, size_t T)
{
    const uint16_t *row = m->logits + (m->last ? 0 : T - 1) * m->V;
    size_t best = 0, i;

    for (i = 0; i < m->V; i++) {
        if ((row[i] & 0x7F80) == 0x7F80 && (row[i] & 0x7F) != 0) {
            fprintf(stderr, "model_forward: pass %lu: the selection row holds a NaN\n", (unsigned long)pass);
            exit(STATUS_SELECTION);
        }
        if (key(row[i]) > key(row[best]))
            best = i;
    }
    m->tokens[m->S + pass] = best;
}

static void release(struct model *m)
{
    uint16_t **arrays[] = {&m->x,    &m->h,     &m->normed, &m->qkv_out,  &m->q_in,   &m->k_in,
                                &m->v_in, &m->q_rot, &m->k_rot,  &m->attn,     &m->o_out,  &m->gate_out,
                                &m->up_out, &m->act, &m->down_out, &m->logits, &m->embedding, &m->norm,
                                &m->lm_head};
    size_t i;

    for (i = 0; i < sizeof arrays / sizeof *arrays; i++)
        free(*arrays[i]);
    for (i = 0; i < m->N; i++) {
        struct layer *layer = &m->layers[i];

        free(layer->attention_norm);
        free(layer->qkv);
        free(layer->o);
        free(layer->ffn_norm);
        free(layer->gate);
        free(layer->up);
        free(layer->down);
        free(layer->cache_k);
        free(layer->cache_v);
    }
    free(m->layers);
    free(m->tokens);
    free(m->rope);
    free(m->table);
}

int main(int argc, char **argv)
{
    struct model m;
    struct pass_entries *passes;
    size_t libraries, i;
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

    memset(&m, 0, sizeof m);
    file = open_input(argv[1], &m);
    read_inputs(file, &m, libraries);
    passes = allocate(m.G * sizeof *passes);
    for (i = 0; i < m.G; i++)
        bind(handles, &m, i, &passes[i]);
    read_weights(file, &m);
    allocate_activations(&m);

    emit(m.tokens, (m.generate ? m.S : m.S + m.G) * sizeof *m.tokens);
    for (i = 0; i < m.G; i++) {
        const size_t T = i == 0 ? m.S : 1;

        run_pass(&m, &passes[i], T, i == 0 ? 0 : m.S + i - 1);
        if (m.generate)
            select_token(&m, i, T);
    }
    if (m.generate)
        emit(m.tokens + m.S, m.G * sizeof *m.tokens);
    emit("end\n", 4);
    release(&m);
    free(passes);
    free(handles);
    return 0;
}
