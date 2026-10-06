import math
import random
from decimal import Decimal

import pytest

from hilclaw.harness import measurement
from hilclaw.harness.measurement import (
    CONFIDENCE,
    CV_MAX,
    DELTA,
    N_MAX_DEFAULT,
    N_MIN,
    RESAMPLES,
    SEED,
    TRIM,
    InvalidSamplesError,
    State,
    coefficient_of_variation,
    is_different,
    ratio_interval,
    stopping_state,
    trimmed_mean,
)

# The worked example of ADR-0007: synthetic values, no unit, no direction.
A = [104, 99, 101, 100, 102]
B = [93, 90, 91, 89, 92]
C = [130, 100, 96, 104, 98, 101, 97, 103, 99, 102]
D = [100, 97, 99, 101, 98]

# Two noisy sequences whose trimmed means are 100 and 103.
NOISY_LOW = [90, 110, 100, 95, 105]
NOISY_HIGH = [93, 113, 103, 98, 108]

FLOAT_MAX = 1.7976931348623157e308
GOOD = [100, 101, 99, 100, 102, 98, 100]
NOT_SEQUENCES = [None, "12345", {1: 2}, 5, 5.0, {1.0, 2.0}, range(1, 8), b"12345"]
BAD_ELEMENTS = [
    True,
    "1",
    None,
    [1.0],
    Decimal(1),
    0,
    0.0,
    -1,
    -1.5,
    float("nan"),
    float("inf"),
    float("-inf"),
]
# Every public function as a function of one sequence, with the name of that argument.
BY_ARGUMENT = [
    (coefficient_of_variation, "samples"),
    (stopping_state, "samples"),
    (trimmed_mean, "values"),
    (lambda values: ratio_interval(values, GOOD), "a"),
    (lambda values: ratio_interval(GOOD, values), "b"),
    (lambda values: is_different(values, GOOD), "a"),
    (lambda values: is_different(GOOD, values), "b"),
]
IDS = [
    "cv",
    "stopping",
    "trimmed",
    "interval-a",
    "interval-b",
    "different-a",
    "different-b",
]


def spread(n, d):
    return [100 - d] + [100] * (n - 2) + [100 + d]


def test_constants_are_those_of_the_record():
    assert (N_MIN, N_MAX_DEFAULT, CV_MAX, TRIM) == (5, 10, 0.05, 1)
    assert (DELTA, CONFIDENCE, RESAMPLES) == (0.02, 0.95, 2000)
    assert type(SEED) is int


@pytest.mark.parametrize(
    ("samples", "percent"),
    [(A, 1.9), (B, 1.7), (D, 1.6), (C[:5], 13.2), (C, 9.5)],
)
def test_cv_of_the_worked_example(samples, percent):
    assert round(coefficient_of_variation(samples) * 100, 1) == percent


def test_cv_uses_the_n_minus_1_divisor_over_all_values():
    assert coefficient_of_variation([1, 3]) == pytest.approx(math.sqrt(2) / 2)
    assert coefficient_of_variation([2, 4, 4, 4, 5, 5, 7, 9]) == pytest.approx(
        math.sqrt(32 / 7) / 5
    )
    assert coefficient_of_variation([7, 7, 7]) == 0.0


def test_cv_keeps_its_value_at_extreme_magnitudes():
    shape = [1.0, 1.2, 0.8, 1.0, 1.0]
    expected = coefficient_of_variation(shape)
    for scale in (1e-200, 1e200, 5e-320):
        scaled = [value * scale for value in shape]
        assert coefficient_of_variation(scaled) == pytest.approx(expected, rel=1e-3)


@pytest.mark.parametrize("samples", [A, B, D])
def test_stopping_state_of_converged_examples(samples):
    states = [stopping_state(samples[:n]) for n in range(len(samples) + 1)]
    assert states == [State.CONTINUE] * 5 + [State.CONVERGED]


def test_stopping_state_of_the_example_that_does_not_converge():
    states = [stopping_state(C[:n]) for n in range(len(C) + 1)]
    assert states == [State.CONTINUE] * 10 + [State.NOT_CONVERGED]


@pytest.mark.parametrize("n", range(N_MIN))
def test_fewer_than_n_min_samples_is_continue_whatever_the_spread(n):
    assert stopping_state([100] * n) is State.CONTINUE
    assert stopping_state(tuple([1, 1000] * 2)[:n]) is State.CONTINUE


def test_identical_samples_converge_at_n_min():
    assert stopping_state([100] * N_MIN) is State.CONVERGED
    assert stopping_state([0.1] * N_MIN) is State.CONVERGED


@pytest.mark.parametrize(
    ("n", "below", "above", "state_above"),
    [
        (5, 7, 7.1, State.CONTINUE),
        (7, 8.6, 8.7, State.CONTINUE),
        (10, 10.6, 10.7, State.NOT_CONVERGED),
    ],
)
def test_cv_just_below_and_just_above_cv_max(n, below, above, state_above):
    assert 0.049 < coefficient_of_variation(spread(n, below)) < CV_MAX
    assert CV_MAX < coefficient_of_variation(spread(n, above)) < 0.051
    assert stopping_state(spread(n, below)) is State.CONVERGED
    assert stopping_state(spread(n, above)) is state_above


def test_noisy_at_n_min_and_converged_later():
    samples = [92.9, 107.1, 100, 100, 100, 100]
    assert stopping_state(samples[:5]) is State.CONTINUE
    assert stopping_state(samples) is State.CONVERGED


def test_n_max_equal_to_n_min_decides_at_once():
    assert stopping_state(A, n_max=N_MIN) is State.CONVERGED
    assert stopping_state(C[:5], n_max=N_MIN) is State.NOT_CONVERGED
    assert stopping_state(C[:4], n_max=N_MIN) is State.CONTINUE


def test_larger_n_max_keeps_going():
    assert stopping_state(C, n_max=30) is State.CONTINUE
    assert stopping_state(C * 3, n_max=30) is State.NOT_CONVERGED
    assert stopping_state(A * 4, n_max=30) is State.CONVERGED


def test_more_samples_than_n_max_is_an_error():
    with pytest.raises(
        InvalidSamplesError, match=r"samples: .*at most n_max = 10.*got 11"
    ):
        stopping_state([100] * 11)
    with pytest.raises(InvalidSamplesError, match=r"at most n_max = 5.*got 6"):
        stopping_state([100] * 6, n_max=5)


@pytest.mark.parametrize("n_max", [4, 0, -1, True, 10.0, "10", None])
def test_invalid_n_max(n_max):
    with pytest.raises(
        InvalidSamplesError, match=r"n_max: must be an int of at least 5"
    ):
        stopping_state(A, n_max=n_max)
    with pytest.raises(InvalidSamplesError, match=r"n_max: "):
        stopping_state([], n_max=n_max)


@pytest.mark.parametrize(
    ("samples", "expected"),
    [(A, 101.0), (B, 91.0), (C, 100.5), (D, 99.0)],
)
def test_trimmed_mean_of_the_worked_example(samples, expected):
    result = trimmed_mean(samples)
    assert type(result) is float
    assert result == expected


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([3, 1, 2], 2.0),
        ([4, 1, 3, 2], 2.5),
        ([50, 10, 40, 20, 30], 30.0),
        ([1, 1, 1, 5, 9, 9, 9], 5.0),
        ([1, 1, 2, 9, 9], 4.0),
        ([100, 101, 102, 103, 10**9], 102.0),
        ([1e-9, 100, 101, 102, 103], 101.0),
        ([0.5, 0.25, 0.75], 0.5),
    ],
)
def test_trimmed_mean_branches(values, expected):
    assert trimmed_mean(values) == expected


@pytest.mark.parametrize("n", [0, 1, 2])
def test_trimmed_mean_needs_three_values(n):
    with pytest.raises(
        InvalidSamplesError, match=rf"values: .*at least 3 values, got {n}"
    ):
        trimmed_mean([100] * n)


@pytest.mark.parametrize("n", [0, 1])
def test_cv_needs_two_values(n):
    with pytest.raises(
        InvalidSamplesError, match=rf"samples: .*at least 2 values, got {n}"
    ):
        coefficient_of_variation([100] * n)


@pytest.mark.parametrize(
    ("b", "different", "low_range", "high_range"),
    [
        (B, True, (0.86, 0.89), (0.90, 0.94)),
        (D, False, (0.94, 0.97), (0.99, 1.02)),
        (C, False, (0.95, 0.98), (1.04, 1.12)),
    ],
)
def test_verdicts_of_the_worked_example(b, different, low_range, high_range):
    low, high = ratio_interval(A, b)
    assert low_range[0] < low < low_range[1]
    assert high_range[0] < high < high_range[1]
    assert is_different(A, b) is different


def test_different_with_the_interval_above_the_upper_bound():
    low, high = ratio_interval(B, A)
    assert 1 + DELTA < low < high
    assert is_different(B, A) is True


def test_identical_sequences_are_not_different():
    low, high = ratio_interval(A, A)
    assert low < 1 < high
    assert is_different(A, A) is False
    assert is_different(C, C) is False


@pytest.mark.parametrize(
    ("level_a", "level_b", "different"),
    [
        (100, 103, True),
        (100, 102, False),
        (100, 101, False),
        (100, 100, False),
        (100, 99, False),
        (102, 100, False),
        (100, 98, True),
    ],
)
def test_point_intervals_pin_both_strict_comparisons(level_a, level_b, different):
    a, b = [level_a] * 5, [level_b] * 6
    assert ratio_interval(a, b) == (level_b / level_a, level_b / level_a)
    assert is_different(a, b) is different


def test_the_two_bounds_meet_the_point_intervals_exactly():
    assert 102 / 100 == 1 + DELTA
    assert 100 / 102 == 1 / (1 + DELTA)


def test_sequences_of_different_lengths():
    assert is_different(B, C) is True
    assert is_different(C, B) is True
    assert is_different(C, A) is False


def test_noisy_sequences_three_percent_apart_are_not_different():
    assert trimmed_mean(NOISY_HIGH) / trimmed_mean(NOISY_LOW) > 1 + DELTA
    assert is_different(NOISY_LOW, NOISY_HIGH) is False
    assert is_different(NOISY_HIGH, NOISY_LOW) is False


def test_interval_is_the_documented_ranks_of_the_documented_replicates():
    rng = random.Random(SEED)
    ratios = []
    for _ in range(RESAMPLES):
        drawn_a = [A[int(rng.random() * len(A))] for _ in A]
        drawn_c = [C[int(rng.random() * len(C))] for _ in C]
        ratios.append(trimmed_mean(drawn_c) / trimmed_mean(drawn_a))
    ratios.sort()
    assert ratio_interval(A, C) == (ratios[50], ratios[1949])
    assert ratios[49] < ratios[50] and ratios[1949] < ratios[1950]


def test_same_call_twice_gives_the_same_result():
    assert ratio_interval(A, C) == ratio_interval(A, C)
    assert is_different(A, D) is is_different(A, D)


def test_global_random_generator_is_left_alone():
    random.seed(12345)
    before = random.getstate()
    ratio_interval(A, B)
    is_different(A, B)
    assert random.getstate() == before
    first = ratio_interval(A, B)
    random.seed(54321)
    assert ratio_interval(A, B) == first


def test_arguments_are_not_modified():
    a, c = list(A), list(C)
    stopping_state(c)
    coefficient_of_variation(c)
    trimmed_mean(c)
    ratio_interval(a, c)
    is_different(a, c)
    assert (a, c) == (A, C)


def test_list_and_tuple_int_and_float_give_the_same_results():
    floats_a, floats_c = tuple(float(v) for v in A), tuple(float(v) for v in C)
    assert coefficient_of_variation(floats_c) == coefficient_of_variation(C)
    assert stopping_state(floats_c) is stopping_state(C)
    assert stopping_state(tuple(A)) is stopping_state(A)
    assert trimmed_mean(floats_c) == trimmed_mean(C)
    assert ratio_interval(floats_a, floats_c) == ratio_interval(A, C)
    assert is_different(floats_a, tuple(B)) is is_different(A, B)


@pytest.mark.parametrize(("function", "argument"), BY_ARGUMENT, ids=IDS)
@pytest.mark.parametrize("value", NOT_SEQUENCES, ids=lambda value: type(value).__name__)
def test_not_a_list_or_tuple(function, argument, value):
    with pytest.raises(
        InvalidSamplesError, match=rf"^{argument}: must be a list or a tuple"
    ):
        function(value)


@pytest.mark.parametrize(("function", "argument"), BY_ARGUMENT, ids=IDS)
def test_a_generator_is_not_a_sequence(function, argument):
    with pytest.raises(InvalidSamplesError, match=rf"^{argument}: .*got generator"):
        function(value for value in GOOD)


@pytest.mark.parametrize(("function", "argument"), BY_ARGUMENT, ids=IDS)
@pytest.mark.parametrize("element", BAD_ELEMENTS, ids=repr)
@pytest.mark.parametrize("position", [0, 3, 6])
def test_invalid_element(function, argument, element, position):
    values = list(GOOD)
    values[position] = element
    pattern = rf"^{argument}\[{position}\]: must be an int or a float that is positive and finite"
    with pytest.raises(InvalidSamplesError, match=pattern):
        function(values)
    with pytest.raises(ValueError, match=type(element).__name__):
        function(tuple(values))


@pytest.mark.parametrize("function", [ratio_interval, is_different])
@pytest.mark.parametrize("n", [0, 4])
def test_verdict_needs_two_measurements(function, n):
    with pytest.raises(InvalidSamplesError, match=rf"^a: .*at least 5 values, got {n}"):
        function([100] * n, A)
    with pytest.raises(InvalidSamplesError, match=rf"^b: .*at least 5 values, got {n}"):
        function(A, [100] * n)


def test_first_argument_is_checked_first():
    with pytest.raises(InvalidSamplesError, match=r"^a\[0\]: "):
        is_different([0] * 5, [0] * 5)


@pytest.mark.parametrize(("function", "argument"), BY_ARGUMENT, ids=IDS)
@pytest.mark.parametrize(
    "values",
    [[1e308] * 5 + [1.0] * 2, [10**400] + [1] * 6, [10**5000] * 7, [FLOAT_MAX] * 7],
    ids=["float", "int", "long-int", "float-max"],
)
def test_sums_that_would_leave_the_float_range(function, argument, values):
    with pytest.raises(
        InvalidSamplesError, match=rf"^{argument}: .*len \* max within the float"
    ):
        function(values)


def test_largest_values_inside_the_float_range():
    values = [FLOAT_MAX / 8] * 8
    assert coefficient_of_variation(values) == 0.0
    assert stopping_state(values) is State.CONVERGED
    assert trimmed_mean(values) == FLOAT_MAX / 8
    assert ratio_interval(values, values) == (1.0, 1.0)
    assert trimmed_mean([2**1000] * 3) == float(2**1000)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ([1e-200] * 5, [1e200] * 5),
        ([1e200] * 5, [1e-200] * 5),
        ([5e-324] * 5, [1.0] * 5),
    ],
)
def test_ratios_that_would_leave_the_float_range(a, b):
    with pytest.raises(InvalidSamplesError, match=r"^a, b: .*ratios stay within half"):
        ratio_interval(a, b)
    with pytest.raises(InvalidSamplesError, match=r"^a, b: "):
        is_different(a, b)


def test_extreme_but_valid_ratios():
    assert ratio_interval([1e-150] * 5, [1e150] * 5) == (1e150 / 1e-150,) * 2
    assert is_different([1e-150] * 5, [1e150] * 5) is True
    assert is_different([1e150] * 5, [1e-150] * 5) is True
    assert is_different([5e-324] * 5, [5e-324] * 5) is False


def test_error_is_a_value_error_and_state_has_three_members():
    assert issubclass(InvalidSamplesError, ValueError)
    assert [state.name for state in State] == ["CONTINUE", "CONVERGED", "NOT_CONVERGED"]
    assert not hasattr(measurement, "main")


@pytest.mark.parametrize(("function", "argument"), BY_ARGUMENT, ids=IDS)
@pytest.mark.parametrize(
    ("element", "shown"),
    [(-(10**5000), "int"), ([10**5000], "list")],
    ids=["int", "list"],
)
def test_invalid_element_too_long_to_show(function, argument, element, shown):
    with pytest.raises(
        InvalidSamplesError, match=rf"^{argument}\[1\]: .*, got {shown} "
    ) as error:
        function([100, element, 100, 100, 100, 100, 100])
    assert len(str(error.value)) < 200


def test_invalid_n_max_too_long_to_show():
    with pytest.raises(InvalidSamplesError, match=r"^n_max: .*, got list ") as error:
        stopping_state(A, n_max=[10**5000])
    assert len(str(error.value)) < 200
