import math
import os
import shutil

import numpy as np
import pytest
import test_model_forward as forward
import test_model_forward_execute as forward_execute
import test_model_forward_run as forward_run

from hilclaw import model_forward_check, model_forward_execute, model_reference
from hilclaw.model_binding import KernelReference, ModelDimensions, rmsnorm_eps
from hilclaw.model_forward_run import ForwardReport
from hilclaw.model_reference import LogitComparison, compare, reference_logits
from hilclaw.rope_table import build

DIMENSIONS = forward_run.DIMENSIONS
ROPE = forward_run.ROPE
EPS = forward_run.EPS
D, F, V, N = forward.D, forward.F, forward.V, forward.N
H, H_KV, HEAD = forward.H, forward.H_KV, forward.HEAD
NAN, INF, MINUS_INF = 0x7FC0, 0x7F80, 0xFF80
ONE, ONE_AND_HALF = 0x3F80, 0x3FC0


def arguments(model, **changes):
    tokens = [int(token) for token in model["tokens"]]
    values = {
        "eps": EPS,
        "rope": ROPE,
        "weights": forward_run.weights_of(model),
        "prompt": tokens[: model["S"]],
        "given": tokens[model["S"] :],
        "lm_head_rows": "all",
    }
    values.update(changes)
    return values


def wide(bits):
    return forward.widen(bits).astype(np.float64)


def naive(model, last):
    """Pass-by-pass float64 re-computation with an explicit KV cache, element by element."""
    prompt, passes = model["S"], model["G"]
    positions = prompt + passes - 1
    table = build(head_dim=HEAD, positions=positions, **ROPE._asdict())
    eps = rmsnorm_eps(EPS)
    layers = model["layers"]
    cache_k = np.zeros((N, positions, H_KV, HEAD))
    cache_v = np.zeros((N, positions, H_KV, HEAD))

    def norm(row, w):
        mean = sum(value * value for value in row) / len(row)
        return [row[j] * float(w[j]) / math.sqrt(mean + eps) for j in range(len(row))]

    def product(row, matrix):
        return [
            sum(row[p] * float(matrix[p, c]) for p in range(len(row)))
            for c in range(matrix.shape[1])
        ]

    def rotate(vector, position):
        out = list(vector)
        for p in range(HEAD // 2):
            c, s = float(table[position, 2 * p]), float(table[position, 2 * p + 1])
            x0, x1 = vector[2 * p], vector[2 * p + 1]
            out[2 * p], out[2 * p + 1] = x0 * c - x1 * s, x0 * s + x1 * c
        return out

    rows = []
    for p in range(passes):
        start, count = (0, prompt) if p == 0 else (prompt + p - 1, 1)
        hidden = [
            list(wide(model["embedding"][int(model["tokens"][position])]))
            for position in range(start, start + count)
        ]
        for n, layer in enumerate(layers):
            weights = {name: wide(value) for name, value in layer.items()}
            queries = []
            for i, x in enumerate(hidden):
                qkv = product(norm(x, weights["attention_norm"]), weights["qkv"])
                position = start + i
                queries.append(
                    [rotate(qkv[j * HEAD : (j + 1) * HEAD], position) for j in range(H)]
                )
                for g in range(H_KV):
                    base = H * HEAD + g * HEAD
                    cache_k[n, position, g] = rotate(qkv[base : base + HEAD], position)
                    base += H_KV * HEAD
                    cache_v[n, position, g] = qkv[base : base + HEAD]
            updated = []
            for i, x in enumerate(hidden):
                attended = []
                for j in range(H):
                    g = j // (H // H_KV)
                    scores = [
                        sum(queries[i][j][e] * cache_k[n, t, g, e] for e in range(HEAD))
                        / math.sqrt(HEAD)
                        for t in range(start + i + 1)
                    ]
                    top = max(scores)
                    exps = [math.exp(score - top) for score in scores]
                    total = sum(exps)
                    attended += [
                        sum(
                            exps[t] / total * cache_v[n, t, g, e]
                            for t in range(len(exps))
                        )
                        for e in range(HEAD)
                    ]
                h = [a + b for a, b in zip(x, product(attended, weights["o"]))]
                normed = norm(h, weights["ffn_norm"])
                gate = product(normed, weights["gate"])
                up = product(normed, weights["up"])
                act = [g / (1 + math.exp(-g)) * u for g, u in zip(gate, up)]
                updated.append(
                    [a + b for a, b in zip(h, product(act, weights["down"]))]
                )
            hidden = updated
        selected = hidden[-1:] if last else hidden
        for x in selected:
            rows.append(product(norm(x, wide(model["norm"])), wide(model["lm_head"])))
    return np.array(rows)


@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize(("seed", "prompt", "given"), [(61, 3, 3), (62, 2, 4)])
def test_reference_equals_a_pass_by_pass_recomputation(seed, prompt, given, last):
    model = forward_run.model_of(seed, prompt=prompt, given=given)
    rows = "last" if last else "all"
    expected = naive(model, last)
    result = reference_logits(DIMENSIONS, **arguments(model, lm_head_rows=rows))
    assert result.dtype == np.float64
    assert result.shape == ((given if last else prompt + given - 1), V)
    assert np.all(np.isfinite(result))
    assert np.allclose(result, expected, rtol=1e-12, atol=1e-12)
    assert np.max(np.abs(result)) > 0.1


def test_last_rows_are_the_last_row_of_each_pass():
    model = forward_run.model_of(63, prompt=3, given=4)
    every = reference_logits(DIMENSIONS, **arguments(model))
    last = reference_logits(DIMENSIONS, **arguments(model, lm_head_rows="last"))
    assert np.array_equal(last, every[2:])


def test_one_token_one_head_by_hand():
    dimensions = ModelDimensions(
        hidden=2,
        intermediate=1,
        vocabulary=2,
        layers=1,
        heads=1,
        kv_heads=1,
        head_dim=2,
    )

    def bf16(*values):
        return forward.narrow(np.array(values, dtype=np.float32).reshape(-1))

    weights = forward_run.Weights(
        embedding=bf16(1.0, 1.0, 2.0, 0.0).reshape(2, 2),
        attention_norm=[bf16(1.0, 1.0)],
        qkv=[np.zeros((2, 6), dtype=np.uint16)],
        o=[bf16(1.0, 0.0, 0.0, 1.0).reshape(2, 2)],
        ffn_norm=[bf16(1.0, 1.0)],
        gate=[np.zeros((2, 1), dtype=np.uint16)],
        up=[bf16(1.0, 1.0).reshape(2, 1)],
        down=[bf16(1.0, 1.0).reshape(1, 2)],
        norm=bf16(1.0, 1.0),
        lm_head=bf16(1.0, 0.0, 0.0, 2.0).reshape(2, 2),
    )
    result = reference_logits(
        dimensions,
        eps=0.25,
        rope=ROPE,
        weights=weights,
        prompt=[1],
        given=[0],
        lm_head_rows="all",
    )
    # x = (2, 0); q, k, v = 0 so attention is 0 and h = x; the gate is 0 so
    # SiLU gives 0 and x stays (2, 0); RMSNorm: 2 / sqrt(2 + 0.25) = 4/3.
    assert result.shape == (1, 2)
    assert np.allclose(result, [[4 / 3, 0.0]], rtol=1e-15, atol=0)


def test_arguments_are_not_modified():
    model = forward_run.model_of(64)
    values = arguments(model)
    copies = {
        name: [array.copy() for array in value]
        if isinstance(value, list)
        else value.copy()
        for name, value in values["weights"]._asdict().items()
    }
    prompt, given = list(values["prompt"]), list(values["given"])
    reference_logits(DIMENSIONS, **values)
    for name, value in values["weights"]._asdict().items():
        if isinstance(value, list):
            assert all(np.array_equal(a, b) for a, b in zip(value, copies[name]))
        else:
            assert np.array_equal(value, copies[name])
    assert values["prompt"] == prompt and values["given"] == given


def test_a_non_finite_weight_propagates_to_the_reference():
    model = forward_run.model_of(65)
    lm_head = model["lm_head"].copy()
    lm_head[0, 3] = NAN
    weights = forward_run.weights_of(model)._replace(lm_head=lm_head)
    result = reference_logits(DIMENSIONS, **arguments(model, weights=weights))
    assert np.all(np.isnan(result[:, 3]))
    assert np.all(np.isfinite(np.delete(result, 3, axis=1)))


def test_generation_mode_is_refused():
    model = forward_run.model_of(66)
    with pytest.raises(ValueError, match="^given: is None; the teacher-forced"):
        reference_logits(DIMENSIONS, **arguments(model, given=None))


@pytest.mark.parametrize("given", ["abc", 5, iter([1, 2])])
def test_given_that_is_no_sequence_is_refused(given):
    model = forward_run.model_of(66)
    with pytest.raises(TypeError, match="^given: must be a sequence"):
        reference_logits(DIMENSIONS, **arguments(model, given=given))


@pytest.mark.parametrize(
    ("change", "text"),
    [
        ({"lm_head_rows": "first"}, "lm_head_rows"),
        ({"prompt": []}, "prompt: is empty"),
        ({"given": [0, V, 1]}, "given[1]: token id"),
        ({"eps": 0.0}, "eps: "),
        ({"eps": math.nan}, "eps: "),
        ({"rope": ROPE._replace(theta=-1.0)}, "rope.theta: "),
        ({"weights": "shape"}, "weights.norm: has the shape"),
        ({"weights": "element"}, "weights.up[1]: has the element type"),
        ({"weights": "layers"}, "weights.qkv: has 1 arrays"),
    ],
)
def test_invalid_input_is_refused_as_the_check_reports_it(change, text):
    model = forward_run.model_of(67)
    weights = forward_run.weights_of(model)
    if change.get("weights") == "shape":
        change = {"weights": weights._replace(norm=model["norm"][:-1])}
    elif change.get("weights") == "element":
        up = list(weights.up)
        up[1] = up[1].astype(np.float32)
        change = {"weights": weights._replace(up=up)}
    elif change.get("weights") == "layers":
        change = {"weights": weights._replace(qkv=weights.qkv[:1])}
    with pytest.raises(ValueError) as caught:
        reference_logits(DIMENSIONS, **arguments(model, **change))
    assert text in str(caught.value)


def test_several_reasons_are_joined():
    model = forward_run.model_of(67)
    with pytest.raises(ValueError) as caught:
        reference_logits(DIMENSIONS, **arguments(model, eps=-1.0, given=[0, 1, V]))
    reasons = str(caught.value).split("; ")
    assert reasons[0].startswith("eps: ")
    assert any(reason.startswith("given[2]: token id") for reason in reasons)


@pytest.mark.parametrize(
    ("change", "parameter"),
    [
        ({"eps": 1}, "eps"),
        ({"rope": (1.0, 2.0, 1.0, 4.0, 8)}, "rope"),
        ({"weights": {}}, "weights"),
        ({"weights": "array"}, "weights.embedding"),
    ],
)
def test_malformed_arguments_raise_the_type_error_of_the_check(change, parameter):
    model = forward_run.model_of(68)
    if change.get("weights") == "array":
        weights = forward_run.weights_of(model)
        change = {"weights": weights._replace(embedding=model["embedding"].tolist())}
    with pytest.raises(TypeError) as caught:
        reference_logits(DIMENSIONS, **arguments(model, **change))
    assert caught.value.parameter == parameter


@pytest.mark.parametrize(
    "dimensions",
    [DIMENSIONS._replace(heads=3), DIMENSIONS._replace(head_dim=3), tuple(DIMENSIONS)],
)
def test_malformed_dimensions_raise_as_the_check_raises(dimensions):
    model = forward_run.model_of(68)
    values = arguments(model)
    with pytest.raises((TypeError, ValueError)) as expected:
        model_forward_check.check(
            dimensions, {}, dtype="bf16", generation_length=3, **values
        )
    with pytest.raises(type(expected.value)) as caught:
        reference_logits(dimensions, **values)
    assert str(caught.value) == str(expected.value)
    assert getattr(caught.value, "parameter", None) == getattr(
        expected.value, "parameter", None
    )


def test_no_argument_has_a_default():
    model = forward_run.model_of(68)
    values = arguments(model)
    for name in values:
        partial = {key: value for key, value in values.items() if key != name}
        with pytest.raises(TypeError, match=name):
            reference_logits(DIMENSIONS, **partial)
    report = ForwardReport(np.zeros(1, np.uint64), np.zeros((1, 1), np.uint16))
    with pytest.raises(TypeError, match="rtol"):
        compare(report, np.zeros((1, 1)), atol=0.0)
    with pytest.raises(TypeError, match="atol"):
        compare(report, np.zeros((1, 1)), rtol=0.0)


def report_of(*rows):
    logits = np.array(rows, dtype=np.uint16)
    return ForwardReport(np.zeros(3, dtype=np.uint64), logits)


@pytest.mark.parametrize(
    ("output", "expected", "rtol", "atol", "passes"),
    [
        (ONE, 1.25, 0, 0.25, True),
        (ONE, 1.25, 0, math.nextafter(0.25, 0), False),
        (ONE, 0.75, 0.0, 0.25, True),
        (ONE_AND_HALF, 2.0, 0.25, 0, True),
        (ONE_AND_HALF, 2.0, math.nextafter(0.25, 0), 0, False),
        (ONE_AND_HALF, -2.0, 0.25, 0, False),
        (ONE, 1.0, 0, 0, True),
        (0x8000, 0.0, 0, 0, True),
    ],
)
def test_the_bound_is_inclusive(output, expected, rtol, atol, passes):
    result = compare(
        report_of([output, ONE]), np.array([[expected, 1.0]]), rtol=rtol, atol=atol
    )
    assert result.ok is passes
    assert result.failed == (0 if passes else 1)
    assert result.first == (None if passes else (0, 0))
    assert result.row_failures == ((0,) if passes else (1,))


@pytest.mark.parametrize("pattern", [NAN, INF, MINUS_INF, 0xFFC1])
def test_a_non_finite_output_fails_whatever_the_tolerance(pattern):
    result = compare(
        report_of([ONE, pattern]), np.array([[1.0, 1.0]]), rtol=1e300, atol=1e300
    )
    assert result == LogitComparison(False, 1, 1, 0, (1,), (0, 1))


@pytest.mark.parametrize(
    ("output", "expected"),
    [
        (ONE, math.inf),
        (INF, math.inf),
        (MINUS_INF, -math.inf),
        (ONE, math.nan),
        (NAN, math.nan),
    ],
)
def test_a_non_finite_reference_fails_its_element(output, expected):
    result = compare(report_of([output]), np.array([[expected]]), rtol=1.0, atol=1e300)
    assert result.ok is False
    assert result.failed == 1
    assert result.reference_non_finite == 1
    assert result.non_finite == (0 if output == ONE else 1)


def test_counts_rows_and_the_first_failure_in_row_major_order():
    report = report_of([ONE, ONE, ONE], [ONE, NAN, ONE], [ONE, ONE, INF])
    expected = np.array([[1.0, 1.0, 1.0], [1.0, 1.0, 9.0], [1.0, math.nan, 1.0]])
    result = compare(report, expected, rtol=0, atol=0.5)
    assert result == LogitComparison(False, 4, 2, 1, (0, 2, 2), (1, 1))
    assert isinstance(result.failed, int) and isinstance(result.row_failures[1], int)


def test_an_empty_result_has_no_first_failure():
    result = compare(report_of([ONE, ONE]), np.array([[1.0, 1.0]]), rtol=0, atol=0)
    assert result == LogitComparison(True, 0, 0, 0, (0,), None)


def test_compare_modifies_nothing():
    report = report_of([ONE, NAN])
    expected = np.array([[2.0, 1.0]])
    before = (report.logits.copy(), expected.copy())
    compare(report, expected, rtol=0.5, atol=0)
    assert np.array_equal(report.logits, before[0])
    assert np.array_equal(expected, before[1])


@pytest.mark.parametrize(
    ("name", "value", "error"),
    [
        ("rtol", None, TypeError),
        ("rtol", "0.1", TypeError),
        ("rtol", True, TypeError),
        ("rtol", np.float64(0.1), TypeError),
        ("rtol", -0.1, ValueError),
        ("rtol", -1, ValueError),
        ("rtol", math.nan, ValueError),
        ("rtol", math.inf, ValueError),
        ("rtol", 10**400, ValueError),
        ("atol", None, TypeError),
        ("atol", [0.1], TypeError),
        ("atol", -0.0001, ValueError),
        ("atol", -math.inf, ValueError),
        ("atol", math.nan, ValueError),
    ],
)
def test_refused_tolerance(name, value, error):
    tolerance = {"rtol": 0.1, "atol": 0.1, name: value}
    with pytest.raises(error) as caught:
        compare(report_of([ONE]), np.array([[1.0]]), **tolerance)
    assert caught.value.parameter == name
    assert str(caught.value).startswith(f"{name}: ")


def test_integer_tolerances_are_accepted():
    result = compare(report_of([ONE]), np.array([[3.0]]), rtol=0, atol=2)
    assert result.ok is True


def test_rtol_is_checked_before_atol_and_both_before_the_report():
    with pytest.raises(ValueError) as caught:
        compare(None, None, rtol=-1.0, atol=-1.0)
    assert caught.value.parameter == "rtol"
    with pytest.raises(ValueError) as caught:
        compare(None, None, rtol=1.0, atol=-1.0)
    assert caught.value.parameter == "atol"


@pytest.mark.parametrize(
    ("report", "expected", "error", "parameter", "text"),
    [
        (None, np.zeros((1, 1)), TypeError, "report", "must be a ForwardReport"),
        (
            (np.zeros(1), np.zeros((1, 1), np.uint16)),
            np.zeros((1, 1)),
            TypeError,
            "report",
            "must be a ForwardReport",
        ),
        (
            ForwardReport(None, np.zeros((1, 1), np.float32)),
            np.zeros((1, 1)),
            TypeError,
            "report",
            "uint16",
        ),
        (
            ForwardReport(None, np.zeros(2, np.uint16)),
            np.zeros((1, 2)),
            TypeError,
            "report",
            "1 dimensions",
        ),
        (
            ForwardReport(None, [[ONE]]),
            np.zeros((1, 1)),
            TypeError,
            "report",
            "got list",
        ),
        (report_of([ONE]), [[1.0]], TypeError, "expected", "got list"),
        (
            report_of([ONE]),
            np.zeros((1, 1), np.float32),
            TypeError,
            "expected",
            "float64",
        ),
        (report_of([ONE]), np.zeros((1, 1, 1)), TypeError, "expected", "3 dimensions"),
        (
            report_of([ONE], [ONE]),
            np.zeros((1, 1)),
            ValueError,
            "report",
            "shape (2, 1)",
        ),
        (
            report_of([ONE, ONE]),
            np.zeros((1, 3)),
            ValueError,
            "report",
            "not that of expected, (1, 3)",
        ),
    ],
)
def test_refused_report_and_expected(report, expected, error, parameter, text):
    with pytest.raises(error) as caught:
        compare(report, expected, rtol=0.1, atol=0.1)
    assert caught.value.parameter == parameter
    assert text in str(caught.value)


def test_a_report_of_other_rows_than_the_reference_is_refused():
    model = forward_run.model_of(69, prompt=3, given=3)
    expected = reference_logits(DIMENSIONS, **arguments(model))
    report = ForwardReport(model["tokens"], forward.narrow(expected[1:]))
    with pytest.raises(ValueError, match="shape"):
        compare(report, expected, rtol=0.1, atol=0.1)


def test_public_names_and_fields():
    public = {name for name in vars(model_reference) if not name.startswith("_")}
    imported = {
        "math",
        "NamedTuple",
        "np",
        "model_binding",
        "model_forward_check",
        "rope_table",
        "ForwardReport",
    }
    assert public - imported == {"LogitComparison", "reference_logits", "compare"}
    assert LogitComparison._fields == (
        "ok",
        "failed",
        "non_finite",
        "reference_non_finite",
        "row_failures",
        "first",
    )


# Fixture kernels of each kind's real operation in binary32, without libm.
REAL_PRELUDE = (
    forward.PRELUDE
    + """
static float fx_sqrt(float v)
{
    double y = v > 1.0f ? v : 1.0;
    int n;

    for (n = 0; n < 64; n++)
        y = 0.5 * (y + v / y);
    return (float)y;
}

static float fx_exp(float x)
{
    double r, term = 1.0, sum = 1.0;
    long k;
    int n;
    union { double d; uint64_t u; } scale;

    if (x < -80.0f)
        return 0.0f;
    k = (long)(x * 1.4426950408889634 + (x < 0.0f ? -0.5 : 0.5));
    r = (double)x - (double)k * 0.6931471805599453;
    for (n = 1; n < 16; n++) {
        term = term * r / n;
        sum = sum + term;
    }
    scale.u = (uint64_t)(k + 1023) << 52;
    return (float)(sum * scale.d);
}
"""
)

REAL_RMSNORM = """
void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x,
                          const uint16_t *restrict w, uint16_t *restrict y)
{
    size_t i, j;

    for (i = 0; i < m; i++) {
        float s = 0.0f, r;

        for (j = 0; j < n; j++)
            s = s + widen(x[i * n + j]) * widen(x[i * n + j]);
        r = fx_sqrt(s / (float)n + eps);
        for (j = 0; j < n; j++)
            y[i * n + j] = narrow(widen(x[i * n + j]) * widen(w[j]) / r);
    }
}
"""

REAL_SWIGLU = """
void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate,
                         const uint16_t *restrict up, uint16_t *restrict out)
{
    size_t i;

    for (i = 0; i < m * n; i++) {
        float g = widen(gate[i]);

        out[i] = narrow(g / (1.0f + fx_exp(-g)) * widen(up[i]));
    }
}
"""

REAL_ROPE = forward.ROPE.replace(
    "float c = freqs_cis[i * d + 2 * p], s = freqs_cis[i * d + 2 * p + 1];",
    "float c = freqs_cis[i * d + 2 * p + @COS@], s = freqs_cis[i * d + 2 * p + @SIN@];",
)

REAL_SDPA = """
void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d,
                                const uint16_t *restrict q, const uint16_t *restrict k_new,
                                const uint16_t *restrict v_new, uint16_t *restrict cache_k,
                                uint16_t *restrict cache_v, uint16_t *restrict out)
{
    size_t P = l - m, i, j, e, t, f;
    float scale = 1.0f / fx_sqrt((float)d), scores[64];

    for (i = 0; i < m * h_kv * d; i++) {
        cache_k[P * h_kv * d + i] = k_new[i];
        cache_v[P * h_kv * d + i] = v_new[i];
    }
    for (i = 0; i < m; i++)
        for (j = 0; j < h; j++) {
            size_t g = j / (h / h_kv), first = @FIRST@;
            float top = -1e30f, total = 0.0f;

            for (t = first; t <= P + i; t++) {
                float dot = 0.0f;

                for (f = 0; f < d; f++)
                    dot = dot + widen(q[(i * h + j) * d + f]) * widen(cache_k[(t * h_kv + g) * d + f]);
                scores[t] = dot * scale;
                if (scores[t] > top)
                    top = scores[t];
            }
            for (t = first; t <= P + i; t++) {
                scores[t] = fx_exp(scores[t] - top);
                total = total + scores[t];
            }
            for (e = 0; e < d; e++) {
                float acc = 0.0f;

                for (t = first; t <= P + i; t++)
                    acc = acc + scores[t] * widen(cache_v[(t * h_kv + g) * d + e]);
                out[(i * h + j) * d + e] = narrow(acc / total);
            }
        }
}
"""

REAL_SOURCES = {
    "gemm": forward.KERNEL_SOURCES["gemm"],
    "rmsnorm": REAL_RMSNORM,
    "add": forward.KERNEL_SOURCES["add"],
    "swiglu": REAL_SWIGLU,
    "rope": REAL_ROPE.replace("@COS@", "0").replace("@SIN@", "1"),
    "sdpa": REAL_SDPA.replace("@FIRST@", "0"),
}
MISWIRED = {
    "rope_swapped": ("rope", REAL_ROPE.replace("@COS@", "1").replace("@SIN@", "0")),
    "sdpa_dropped_row": ("sdpa", REAL_SDPA.replace("@FIRST@", "m == 1 && P > 0")),
}


@pytest.fixture(scope="session")
def clang():
    if os.name != "posix":
        pytest.skip("the forward program needs a POSIX system")
    if shutil.which("clang") is None:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            pytest.fail("clang is not on PATH of the CI runner")
        pytest.skip("clang is not on PATH")


def real_binding(directory, miswired=None):
    sources = dict(REAL_SOURCES)
    names = {kind: kind for kind in forward.KINDS}
    if miswired is not None:
        kind, text = MISWIRED[miswired]
        sources[kind] = text
        names[kind] = miswired
    kernels = {}
    for kind in forward.KINDS:
        source = directory / f"{names[kind]}.c"
        source.write_text(REAL_PRELUDE + sources[kind], encoding="ascii", newline="\n")
        kernels[kind] = KernelReference(
            (source,), forward_execute.CONTRACTS[kind], forward.KERNEL_FLAGS
        )
    return forward_execute.binding_of(kernels)


def executed(tmp_path, model, rows, miswired=None):
    builds = tmp_path / "builds"
    builds.mkdir()
    result = model_forward_execute.execute(
        DIMENSIONS,
        real_binding(tmp_path, miswired),
        **arguments(model, lm_head_rows=rows),
        build_timeout_s=forward.BUILD_TIMEOUT,
        run_timeout_s=forward.RUN_TIMEOUT,
        program_flags=("-O2",),
        program_trailing_flags=("-ldl",),
        parent=builds,
    )
    assert result.check.ok, result.check.outcomes
    assert result.build_failed is None, result.build_failed
    assert result.run.failed is None, result.run.run.stderr
    return result.run.report


def sharp_model(seed, prompt, given):
    """A synthetic model whose QKV weights are 8 times larger.

    Its attention scores reach a few units, so the RoPE rotation and each
    cache row move the attention weights well beyond the rounding of the
    run; with the weights of ``model_of`` the scores stay near 0 and a
    swapped rotation hides inside the tolerance.
    """
    model = forward_run.model_of(seed, prompt=prompt, given=given)
    for layer in model["layers"]:
        layer["qkv"] = forward.narrow(forward.widen(layer["qkv"]) * np.float32(8))
    return model


def tolerance(expected):
    """The tolerance of the synthetic run with the real fixture kernels.

    Each kernel output on the way to a logit is rounded once to bf16, a
    relative error of at most 2**-9 (the binary32 accumulation adds far
    less); a logit lies behind 27 such roundings (per layer the two norms,
    QKV, the two RoPE outputs, SDPA, O, the two residuals, gate and up,
    SwiGLU and down; then the final norm and lm_head). Roundings to nearest
    are unbiased, so their sum grows like the square root of their number:
    sqrt(27) * 2**-9 < 2**-6. The softmax amplifies a score's error by up to
    the score's size, a few units here, hence ``rtol`` 2**-5. A logit is a
    dot product that can cancel, so its error is bounded relative to the
    magnitude of its row's terms, not to itself: ``atol`` is 2**-5 times the
    largest |reference| of the run. The largest deviation seen over these
    seeds is below 2**-7 of that magnitude; each miswiring below gives more
    than 2**-3.
    """
    return 2**-5, 2**-5 * float(np.max(np.abs(expected)))


@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize(("seed", "prompt", "given"), [(71, 3, 3), (72, 2, 4)])
def test_the_executor_with_real_kernels_matches_the_reference(
    clang, tmp_path, seed, prompt, given, last
):
    model = sharp_model(seed, prompt, given)
    rows = "last" if last else "all"
    report = executed(tmp_path, model, rows)
    expected = reference_logits(DIMENSIONS, **arguments(model, lm_head_rows=rows))
    rtol, atol = tolerance(expected)
    result = compare(report, expected, rtol=rtol, atol=atol)
    assert result.ok, result
    assert not np.array_equal(forward.widen(report.logits), expected)


@pytest.mark.parametrize("last", [False, True])
@pytest.mark.parametrize("miswired", sorted(MISWIRED))
@pytest.mark.parametrize(("seed", "prompt", "given"), [(71, 3, 3), (72, 2, 4)])
def test_a_miswired_kernel_fails_the_comparison(
    clang, tmp_path, seed, prompt, given, last, miswired
):
    model = sharp_model(seed, prompt, given)
    rows = "last" if last else "all"
    report = executed(tmp_path, model, rows, miswired)
    expected = reference_logits(DIMENSIONS, **arguments(model, lm_head_rows=rows))
    rtol, atol = tolerance(expected)
    result = compare(report, expected, rtol=rtol, atol=atol)
    assert not result.ok
    assert result.non_finite == 0 and result.reference_non_finite == 0
    deviation = np.abs(forward.widen(report.logits) - expected)
    assert np.max(deviation) > 2**-3 * np.max(np.abs(expected))
