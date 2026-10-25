import os
import shutil

import numpy as np
import pytest

from hilclaw import clang_build
from hilclaw.local_run import run
from hilclaw.model_build import PROGRAM_SOURCE, build_kernel_library

BUILD_TIMEOUT = 120
RUN_TIMEOUT = 60
END = b"end\n"
NAN_BITS = 0x7FC0
SOURCE = PROGRAM_SOURCE.with_name("model_forward.c")
KERNEL_FLAGS = ("-O2", "-ffp-contract=off")
SITES = (
    "qkv",
    "o",
    "gate",
    "up",
    "down",
    "lm_head",
    "attention_norm",
    "ffn_norm",
    "norm",
    "attention_residual",
    "ffn_residual",
    "ffn_activation",
    "rope_q",
    "rope_k",
    "sdpa",
)
KIND_OF_SITE = (
    ("gemm",) * 6
    + ("rmsnorm",) * 3
    + ("add",) * 2
    + ("swiglu",)
    + ("rope",) * 2
    + ("sdpa",)
)
KINDS = ("gemm", "rmsnorm", "add", "swiglu", "rope", "sdpa")

PRELUDE = """\
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static float widen(uint16_t bits)
{
    uint32_t word = (uint32_t)bits << 16;
    float value;

    memcpy(&value, &word, sizeof value);
    return value;
}

static uint16_t narrow(float value)
{
    uint32_t word;

    memcpy(&word, &value, sizeof word);
    word += UINT32_C(0x7FFF) + ((word >> 16) & 1u);
    return (uint16_t)(word >> 16);
}
"""

GEMM = """
void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a,
                       const uint16_t *restrict b, uint16_t *restrict c)
{
    size_t i, j, p;

    for (i = 0; i < m; i++)
        for (j = 0; j < @COLUMNS@; j++) {
            float sum = @START@;

            for (p = 0; p < k; p++)
                sum = sum + widen(a[i * k + p]) * widen(b[p * n + j]);
            c[i * n + j] = narrow(sum);
        }
}
"""

RMSNORM = """
void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x,
                          const uint16_t *restrict w, uint16_t *restrict y)
{
    size_t i, j;

    for (i = 0; i < m; i++) {
        float s = 0.0f, denom;

        for (j = 0; j < n; j++)
            s = s + widen(x[i * n + j]) * widen(x[i * n + j]);
        denom = s / (float)n + eps;
        for (j = 0; j < n; j++)
            y[i * n + j] = narrow(widen(x[i * n + j]) * widen(w[j]) / denom);
    }
}
"""

ADD = """
void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a,
                                  const uint16_t *restrict b, uint16_t *restrict c)
{
    size_t i;
@EXTRA@
    for (i = 0; i < m * n; i++)
        c[i] = narrow(widen(a[i]) + widen(b[i]));
}
"""

SWIGLU = """
void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate,
                         const uint16_t *restrict up, uint16_t *restrict out)
{
    size_t i;
@EXTRA@
    for (i = 0; i < m * n; i++) {
        float g = widen(gate[i]), t = g * g;

        t = 1.0f + t;
        t = g / t;
        out[i] = narrow(t * widen(up[i]));
    }
}
"""

ROPE = """
void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x,
                       const float *restrict freqs_cis, uint16_t *restrict out)
{
    size_t i, j, p;

    for (i = 0; i < m; i++)
        for (j = 0; j < h; j++)
            for (p = 0; p < d / 2; p++) {
                size_t at = (i * h + j) * d + 2 * p;
                float x0 = widen(x[at]), x1 = widen(x[at + 1]);
                float c = freqs_cis[i * d + 2 * p], s = freqs_cis[i * d + 2 * p + 1];

                out[at] = narrow(x0 * c - x1 * s);
                out[at + 1] = narrow(x0 * s + x1 * c);
            }
}
"""

SDPA = """
void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d,
                                const uint16_t *restrict q, const uint16_t *restrict k_new,
                                const uint16_t *restrict v_new, uint16_t *restrict cache_k,
                                uint16_t *restrict cache_v, uint16_t *restrict out)
{
    size_t P = l - m, i, j, e, t, f;

    for (i = 0; i < m * h_kv * d; i++) {
        cache_k[P * h_kv * d + i] = k_new[i];
        cache_v[P * h_kv * d + i] = v_new[i];
    }
    for (i = 0; i < m; i++)
        for (j = 0; j < h; j++) {
            size_t g = j / (h / h_kv);

            for (e = 0; e < d; e++) {
                float acc = 0.0f;

                for (t = 0; t <= P + i; t++) {
                    float dot = 0.0f, w;

                    for (f = 0; f < d; f++)
                        dot = dot + widen(q[(i * h + j) * d + f]) * widen(cache_k[(t * h_kv + g) * d + f]);
                    w = dot / (1.0f + dot * dot);
                    acc = acc + w * widen(cache_v[(t * h_kv + g) * d + e]);
                }
                out[(i * h + j) * d + e] = narrow(acc);
            }
        }
}
"""

PRINT = '    puts("kernel says hello");\n    fflush(stdout);\n'


def gemm_source(start="0.0f", columns="n"):
    return GEMM.replace("@START@", start).replace("@COLUMNS@", columns)


KERNEL_SOURCES = {
    "gemm": gemm_source(),
    "rmsnorm": RMSNORM,
    "add": ADD.replace("@EXTRA@", ""),
    "swiglu": SWIGLU.replace("@EXTRA@", ""),
    "rope": ROPE,
    "sdpa": SDPA,
}

LIBRARIES = {
    **{kind: (KERNEL_SOURCES[kind],) for kind in KINDS},
    "all": tuple(KERNEL_SOURCES[kind] for kind in KINDS),
    "gemm_offset": (gemm_source(start="0.25f"),),
    "gemm_partial": (gemm_source(columns="n - 1"),),
    "add_printing": (ADD.replace("@EXTRA@", PRINT),),
    "swiglu_abort": (SWIGLU.replace("@EXTRA@", "    abort();\n"),),
}

SEPARATE = list(KINDS)
SEPARATE_TABLE = [KINDS.index(kind) for kind in KIND_OF_SITE]

D, F, V, N, H, H_KV, HEAD = 8, 12, 10, 2, 4, 2, 4
W = (H + 2 * H_KV) * HEAD
EPS = np.float32(0.5)


@pytest.fixture(scope="session")
def built(tmp_path_factory):
    if os.name != "posix":
        pytest.skip("the forward program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")
    directory = tmp_path_factory.mktemp("forward")
    program = directory / "model_forward"
    result = clang_build.build(
        (SOURCE,), program, timeout_s=BUILD_TIMEOUT, flags=("-O2",)
    )
    assert result.ok, result.log
    libraries = {}

    def library(name):
        if name not in libraries:
            if name == "no_entry":
                text = "int other_entry(int x)\n{\n    return x + 1;\n}\n"
            else:
                text = PRELUDE + "".join(LIBRARIES[name])
            source = directory / f"{name}.c"
            source.write_text(text, encoding="ascii", newline="\n")
            output = directory / f"lib{name}.so"
            result = build_kernel_library(
                source, output, timeout_s=BUILD_TIMEOUT, flags=KERNEL_FLAGS
            )
            assert result.ok, result.log
            libraries[name] = str(output)
        return libraries[name]

    return program, library


def widen(bits):
    return (np.asarray(bits, dtype=np.uint16).astype(np.uint32) << 16).view(np.float32)


def narrow(values):
    word = np.asarray(values, dtype=np.float32).view(np.uint32)
    return ((word + np.uint32(0x7FFF) + ((word >> 16) & 1)) >> 16).astype(np.uint16)


def gemm(a, b, start=0.0):
    a, b = widen(a), widen(b)
    total = np.full((a.shape[0], b.shape[1]), start, dtype=np.float32)
    for p in range(a.shape[1]):
        total = total + a[:, p : p + 1] * b[p : p + 1, :]
    return narrow(total)


def rmsnorm(x, w, eps):
    x, w = widen(x), widen(w)
    s = np.zeros(x.shape[0], dtype=np.float32)
    for j in range(x.shape[1]):
        s = s + x[:, j] * x[:, j]
    denom = s / np.float32(x.shape[1]) + eps
    return narrow(x * w[None, :] / denom[:, None])


def add(a, b):
    return narrow(widen(a) + widen(b))


def swiglu(gate, up):
    g = widen(gate)
    t = g * g
    t = np.float32(1.0) + t
    t = g / t
    return narrow(t * widen(up))


def rope(x, table):
    x = widen(x)
    x0, x1 = x[:, :, 0::2], x[:, :, 1::2]
    c, s = table[:, None, 0::2], table[:, None, 1::2]
    out = np.empty(x.shape, dtype=np.uint16)
    out[:, :, 0::2] = narrow(x0 * c - x1 * s)
    out[:, :, 1::2] = narrow(x0 * s + x1 * c)
    return out


def sdpa(q, k_new, v_new, cache_k, cache_v, position):
    m, h, d = q.shape
    h_kv = k_new.shape[1]
    cache_k[position : position + m] = k_new
    cache_v[position : position + m] = v_new
    q, keys, values = widen(q), widen(cache_k), widen(cache_v)
    out = np.empty((m, h, d), dtype=np.uint16)
    one = np.float32(1.0)
    for i in range(m):
        for j in range(h):
            g = j // (h // h_kv)
            acc = np.zeros(d, dtype=np.float32)
            for t in range(position + i + 1):
                dot = np.float32(0.0)
                for f in range(d):
                    dot = dot + q[i, j, f] * keys[t, g, f]
                weight = dot / (one + dot * dot)
                acc = acc + weight * values[t, g, :]
            out[i, j] = narrow(acc)
    return out


def bf16_values(generator, shape):
    values = generator.integers(-4, 5, size=shape).astype(np.float32) / np.float32(8)
    return (values.view(np.uint32) >> 16).astype(np.uint16)


def make_model(seed, prompt=3, given=1):
    generator = np.random.default_rng(seed)
    positions = prompt + given - 1
    layers = []
    for _ in range(N):
        layers.append(
            {
                "attention_norm": bf16_values(generator, (D,)),
                "qkv": bf16_values(generator, (D, W)),
                "o": bf16_values(generator, (H * HEAD, D)),
                "ffn_norm": bf16_values(generator, (D,)),
                "gate": bf16_values(generator, (D, F)),
                "up": bf16_values(generator, (D, F)),
                "down": bf16_values(generator, (F, D)),
            }
        )
    return {
        "S": prompt,
        "G": given,
        "tokens": generator.integers(0, V, size=prompt + given).astype(np.uint64),
        "rope": generator.uniform(-1, 1, size=(positions, HEAD)).astype(np.float32),
        "embedding": bf16_values(generator, (V, D)),
        "layers": layers,
        "norm": bf16_values(generator, (D,)),
        "lm_head": bf16_values(generator, (D, V)),
    }


def header_words(model, last, **changes):
    words = {
        "D": D,
        "F": F,
        "V": V,
        "N": N,
        "H": H,
        "H_kv": H_KV,
        "d": HEAD,
        "S": model["S"],
        "G": model["G"],
        "lm_head_rows": int(last),
    }
    words.update(changes)
    return np.array(list(words.values()), dtype=np.uint64).tobytes()


def encode(model, table, last=False, eps=EPS, **changes):
    parts = [
        header_words(model, last, **changes),
        np.array([eps], dtype=np.float32).tobytes(),
        np.array(table, dtype=np.uint64).tobytes(),
        model["rope"].tobytes(),
        model["tokens"].tobytes(),
        model["embedding"].tobytes(),
    ]
    for layer in model["layers"]:
        for name in ("attention_norm", "qkv", "o", "ffn_norm", "gate", "up", "down"):
            parts.append(layer[name].tobytes())
    parts += [model["norm"].tobytes(), model["lm_head"].tobytes()]
    return b"".join(parts)


def prefill(model, last=False, lm_start=0.0):
    prompt = model["S"]
    positions = prompt + model["G"] - 1
    x = model["embedding"][model["tokens"][:prompt].astype(np.intp)]
    hd, kvd = H * HEAD, H_KV * HEAD
    for layer in model["layers"]:
        cache_k = np.full((positions, H_KV, HEAD), NAN_BITS, dtype=np.uint16)
        cache_v = cache_k.copy()
        normed = rmsnorm(x, layer["attention_norm"], EPS)
        qkv = gemm(normed, layer["qkv"])
        q_in = qkv[:, :hd].reshape(prompt, H, HEAD)
        k_in = qkv[:, hd : hd + kvd].reshape(prompt, H_KV, HEAD)
        v_in = qkv[:, hd + kvd :].reshape(prompt, H_KV, HEAD)
        q_rot = rope(q_in, model["rope"][:prompt])
        k_rot = rope(k_in, model["rope"][:prompt])
        attn = sdpa(q_rot, k_rot, v_in, cache_k, cache_v, 0)
        o_out = gemm(attn.reshape(prompt, hd), layer["o"])
        h = add(x, o_out)
        normed = rmsnorm(h, layer["ffn_norm"], EPS)
        act = swiglu(gemm(normed, layer["gate"]), gemm(normed, layer["up"]))
        x = add(h, gemm(act, layer["down"]))
    normed = rmsnorm(x, model["norm"], EPS)
    if last:
        normed = normed[-1:]
    return gemm(normed, model["lm_head"], lm_start)


def report(model, logits):
    return model["tokens"].tobytes() + logits.astype(np.uint16).tobytes() + END


def start(built, tmp_path, data, names):
    program, library = built
    path = tmp_path / "input.bin"
    path.write_bytes(data)
    return run(
        [program, str(path), *(library(name) for name in names)], timeout_s=RUN_TIMEOUT
    )


def assert_failed(result, status, text):
    assert result.returncode == status, result.stderr
    assert result.stdout == b""
    assert result.stderr.startswith(b"model_forward: ")
    assert result.stderr.count(b"\n") == 1 and result.stderr.endswith(b"\n")
    assert text in result.stderr


@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize("seed", [1, 2])
def test_prefill_equals_the_recomputation_bit_for_bit(built, tmp_path, last, seed):
    model = make_model(seed)
    result = start(built, tmp_path, encode(model, SEPARATE_TABLE, last), SEPARATE)
    assert result.returncode == 0, result.stderr
    logits = prefill(model, last)
    assert logits.shape == ((1 if last else model["S"]), V)
    assert not np.any(logits == NAN_BITS)
    assert result.stdout == report(model, logits)
    rows = 1 if last else model["S"]
    assert len(result.stdout) == 8 * (model["S"] + model["G"]) + 2 * rows * V + 4
    assert result.stderr == b""


def test_a_longer_prompt_and_a_given_token(built, tmp_path):
    model = make_model(7, prompt=5)
    model["tokens"][-1] = V - 1
    result = start(built, tmp_path, encode(model, SEPARATE_TABLE), SEPARATE)
    assert result.returncode == 0, result.stderr
    assert result.stdout == report(model, prefill(model))


def test_one_library_with_every_kind(built, tmp_path):
    model = make_model(3)
    result = start(built, tmp_path, encode(model, [0] * 15, True), ["all"])
    assert result.returncode == 0, result.stderr
    assert result.stdout == report(model, prefill(model, True))


def test_the_table_chooses_the_library_of_each_call_site(built, tmp_path):
    model = make_model(4)
    table = list(SEPARATE_TABLE)
    table[SITES.index("lm_head")] = len(SEPARATE)
    names = [*SEPARATE, "gemm_offset"]
    result = start(built, tmp_path, encode(model, table), names)
    assert result.returncode == 0, result.stderr
    assert result.stdout == report(model, prefill(model, lm_start=0.25))
    assert result.stdout != report(model, prefill(model))


def test_a_library_bound_to_no_call_site_is_not_searched(built, tmp_path):
    model = make_model(5)
    names = [*SEPARATE, "no_entry"]
    result = start(built, tmp_path, encode(model, SEPARATE_TABLE), names)
    assert result.returncode == 0, result.stderr
    assert result.stdout == report(model, prefill(model))


def test_logits_left_unwritten_keep_the_fill(built, tmp_path):
    model = make_model(6)
    table = list(SEPARATE_TABLE)
    table[SITES.index("lm_head")] = len(SEPARATE)
    result = start(built, tmp_path, encode(model, table), [*SEPARATE, "gemm_partial"])
    assert result.returncode == 0, result.stderr
    logits = prefill(model)
    logits[:, -1] = NAN_BITS
    assert result.stdout == report(model, logits)


def test_kernel_output_goes_to_standard_error(built, tmp_path):
    model = make_model(8)
    table = list(SEPARATE_TABLE)
    for site in ("attention_residual", "ffn_residual"):
        table[SITES.index(site)] = len(SEPARATE)
    names = [*SEPARATE, "add_printing"]
    result = start(built, tmp_path, encode(model, table), names)
    assert result.returncode == 0, result.stderr
    assert result.stdout == report(model, prefill(model))
    assert result.stderr == b"kernel says hello\n" * (2 * N)


def test_a_kernel_that_aborts_leaves_no_end_mark(built, tmp_path):
    model = make_model(9)
    table = list(SEPARATE_TABLE)
    table[SITES.index("ffn_activation")] = len(SEPARATE)
    names = [*SEPARATE, "swiglu_abort"]
    result = start(built, tmp_path, encode(model, table), names)
    assert result.returncode != 0
    assert not result.stdout.endswith(END)


@pytest.mark.parametrize("count", [0, 1])
def test_wrong_argument_count(built, tmp_path, count):
    program, library = built
    arguments = [str(tmp_path / "input.bin"), library("all")][:count]
    result = run([program, *arguments], timeout_s=RUN_TIMEOUT)
    assert_failed(result, 2, b"usage")


def test_missing_input_file(built, tmp_path):
    program, library = built
    result = run(
        [program, str(tmp_path / "absent.bin"), library("all")], timeout_s=RUN_TIMEOUT
    )
    assert_failed(result, 5, b"cannot be opened")


def test_input_that_is_a_directory(built, tmp_path):
    program, library = built
    result = run([program, str(tmp_path), library("all")], timeout_s=RUN_TIMEOUT)
    assert_failed(result, 5, b"input file")


@pytest.mark.parametrize(
    ("cut", "text"),
    [
        (0, b"too short for the header"),
        (40, b"too short for the header"),
        (82, b"too short for the header"),
        (84, b"too short for the length"),
        (84 + 15 * 8 + 3, b"too short for the length"),
        (-1, b"too short for the length"),
    ],
)
def test_short_file(built, tmp_path, cut, text):
    data = encode(make_model(1), [0] * 15)
    result = start(built, tmp_path, data[:cut], ["all"])
    assert_failed(result, 5, text)


def test_trailing_bytes(built, tmp_path):
    data = encode(make_model(1), [0] * 15) + b"\0"
    result = start(built, tmp_path, data, ["all"])
    assert_failed(result, 5, b"bytes follow the last weight")


@pytest.mark.parametrize("name", ["D", "F", "V", "N", "H", "H_kv", "d", "S", "G"])
def test_zero_dimension(built, tmp_path, name):
    data = encode(make_model(1), [0] * 15, **{name: 0})
    assert_failed(start(built, tmp_path, data, ["all"]), 5, b"is 0")


@pytest.mark.parametrize(
    ("changes", "text"),
    [
        ({"H": 3}, b"H is not a multiple of H_kv"),
        ({"d": 3}, b"d is odd"),
        ({"lm_head_rows": 2}, b"lm_head_rows"),
        ({"G": 2}, b"decode passes are not supported"),
    ],
)
def test_header_refusals(built, tmp_path, changes, text):
    data = encode(make_model(1), [0] * 15, **changes)
    assert_failed(start(built, tmp_path, data, ["all"]), 5, text)


@pytest.mark.parametrize("eps", [0.0, -0.0, -0.5, np.nan, -np.nan, np.inf, -np.inf])
def test_eps_refusals(built, tmp_path, eps):
    data = encode(make_model(1), [0] * 15, eps=eps)
    assert_failed(start(built, tmp_path, data, ["all"]), 5, b"eps")


def test_a_subnormal_eps_is_above_zero(built, tmp_path):
    eps = np.array([1], dtype=np.uint32).view(np.float32)[0]
    data = encode(make_model(1), [0] * 15, eps=eps)
    result = start(built, tmp_path, data, ["all"])
    assert result.returncode == 0, result.stderr
    assert result.stdout.endswith(END)


@pytest.mark.parametrize("site", [0, 14])
def test_library_index_out_of_range(built, tmp_path, site):
    table = [0] * 15
    table[site] = 1
    data = encode(make_model(1), table)
    assert_failed(start(built, tmp_path, data, ["all"]), 5, b"library index")


@pytest.mark.parametrize("position", [0, -1])
def test_token_id_not_below_vocabulary(built, tmp_path, position):
    model = make_model(1)
    model["tokens"][position] = V
    data = encode(model, [0] * 15)
    assert_failed(start(built, tmp_path, data, ["all"]), 5, b"token id")


def test_library_that_cannot_be_loaded(built, tmp_path):
    program, library = built
    path = tmp_path / "input.bin"
    path.write_bytes(encode(make_model(1), [0] * 15))
    result = run(
        [program, str(path), library("all"), str(tmp_path / "libabsent.so")],
        timeout_s=RUN_TIMEOUT,
    )
    assert_failed(result, 6, b"library 1: cannot be loaded")


@pytest.mark.parametrize(
    ("kind", "symbol"),
    [
        ("gemm", b"hilclaw_gemm_bf16"),
        ("rmsnorm", b"hilclaw_rmsnorm_bf16"),
        ("add", b"hilclaw_elementwise_add_bf16"),
        ("swiglu", b"hilclaw_swiglu_bf16"),
        ("rope", b"hilclaw_rope_bf16"),
        ("sdpa", b"hilclaw_sdpa_kv_cache_bf16"),
    ],
)
def test_bound_library_without_the_entry_point(built, tmp_path, kind, symbol):
    table = [0 if site_kind == kind else 1 for site_kind in KIND_OF_SITE]
    other = "gemm" if kind != "gemm" else "rmsnorm"
    data = encode(make_model(1), table)
    result = start(built, tmp_path, data, [other, "all"])
    assert_failed(result, 6, b"library 0: has no " + symbol)


@pytest.mark.parametrize(
    "changes",
    [
        {"D": 2**62},
        {"F": 2**62},
        {"V": 2**63},
        {"N": 2**62},
        {"d": 2**62},
        {"H": 2**63, "H_kv": 2**62},
        {"H_kv": 2**63, "H": 2**63},
        {"S": 2**64 - 1},
        {"S": 2**62},
        {"V": 2**61, "D": 2},
        {"N": 2**56},
    ],
)
def test_sizes_that_cannot_be_held(built, tmp_path, changes):
    data = header_words(make_model(1), False, **changes) + EPS.tobytes()
    assert_failed(start(built, tmp_path, data, ["all"]), 3, b"cannot be held")
