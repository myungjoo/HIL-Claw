"""Python side of a timing run of ADR-0009: start it, read its report, replay the rule.

``ARCHITECTURE/decisions/ADR-0009-od13-cpu-standin-timing-run.md`` is the rule.
A timing executable (the driver program of the harness built with one kernel)
takes the repeats of one measurement in a process of its own and reports them
on its standard output. :func:`run_timing` starts that process for an
executable that is already built, :func:`parse_report` reads the report, and
the run is accepted only if replaying
:func:`hilclaw.harness.measurement.stopping_state` on every prefix of the
reported intervals agrees with it (decisions 7 and 8).

Command line of the driver program (decision 9 leaves spelling and order to the
code; the C side is written against this text). Exactly eight arguments, in
this order::

    <executable> <m> <k> <n> <n_min> <n_max> <cv_max> <sample_form> <seed>

- ``m``, ``k``, ``n``, ``n_min``, ``n_max``, ``seed``: decimal digits only, no
  sign, no leading zero, no space. ``m``, ``k`` and ``n`` are at least 1,
  ``n_min`` is :data:`measurement.N_MIN` (``5``), ``n_max`` is at least
  ``n_min``, and ``seed`` is below 2**64. No upper bound is put on the others:
  the driver program refuses what it cannot hold or allocate.
- ``cv_max``: ``repr(measurement.CV_MAX)``, which is ``0.05``; a decimal
  number that ``strtod`` reads.
- ``sample_form``: the word ``interval`` or ``reciprocal``.

Report read from the standard output (decision 8), every line ASCII and ended
by one LF, with nothing before, between or after: one ``resolution_ns <i>``
line, zero or more ``interval_ns <i>`` lines, one last line ``stop converged``
or ``stop not_converged``.

Conventions of this module (not rules of the record):

- ``<i>`` is written as ``0`` or as digits that do not start with ``0``, the one
  spelling ``printf`` gives a value; a sign, a leading zero or a digit string
  the interpreter refuses to convert is a line of another form.
  ``resolution_ns 0`` is of the form: the record decides no threshold on it.
- The conditions of a completed run are tested in the order of
  :class:`Broken`, and the first that fails is the one reported. A signal is
  not told apart from a non-zero exit status; ``run.returncode`` shows it.
- ``executable`` is a path or a sequence used as a command prefix, as
  ``compiler`` in :func:`hilclaw.clang_build.build`.
- A caller's mistake raises :class:`TimingArgumentError` before anything is
  started; what :func:`hilclaw.local_run.run` raises for the executable, the
  time limit, ``cwd`` or ``env`` is passed on.

What this module does not do: it builds nothing and reads no clock; it does not
defend against forged timing (decision 10); it does not retry, repair, store or
judge a broken run or one that is not converged; it gives no default to the
sample form, the seed or the time limit; and it summarises nothing.
"""

import enum
import os
import re
import reprlib
from typing import NamedTuple

from hilclaw import local_run
from hilclaw.harness import measurement
from hilclaw.harness.measurement import N_MAX_DEFAULT, State

SAMPLE_FORMS = ("interval", "reciprocal")
SEED_LIMIT = 2**64

_INTEGER = re.compile(rb"0|[1-9][0-9]*")
_STOP = {
    b"stop converged": State.CONVERGED,
    b"stop not_converged": State.NOT_CONVERGED,
}


class TimingArgumentError(ValueError):
    """A parameter of a timing run is outside what this module states; nothing was started."""


class Broken(enum.Enum):
    """The condition of a completed run (decision 8) that a broken run failed first."""

    TIMEOUT = enum.auto()
    EXIT_STATUS = enum.auto()
    REPORT_FORM = enum.auto()
    ZERO_INTERVAL = enum.auto()
    REPLAY = enum.auto()


class Report(NamedTuple):
    """A standard output of the form of decision 8, as :func:`parse_report` read it."""

    resolution_ns: int
    intervals_ns: tuple[int, ...]
    state: State


class TimingResult(NamedTuple):
    """Outcome of one :func:`run_timing` call.

    For a completed run ``broken`` is ``None``, ``intervals_ns`` holds the
    lengths of the timed intervals in nanoseconds in the order taken,
    ``resolution_ns`` the reported clock resolution and ``state`` is
    ``State.CONVERGED`` or ``State.NOT_CONVERGED``. For a broken run ``broken``
    names the failed condition and the three other fields are ``None``: no
    interval of a broken run is offered. ``run`` is what the runner captured,
    in both cases.
    """

    broken: Broken | None
    state: State | None
    intervals_ns: tuple[int, ...] | None
    resolution_ns: int | None
    run: local_run.RunResult


def driver_arguments(*, m, k, n, n_max, sample_form, seed):
    """Return the eight arguments of the driver program as a tuple of ``str``.

    The order and spelling are those of the module docstring; ``n_min`` and
    ``cv_max`` come from :mod:`hilclaw.harness.measurement`. ``m``, ``k`` and
    ``n`` are exactly ``int`` and at least 1, ``n_max`` is an ``int`` of at
    least :data:`measurement.N_MIN`, ``sample_form`` is one of
    :data:`SAMPLE_FORMS` and ``seed`` an ``int`` with
    0 <= ``seed`` < :data:`SEED_LIMIT`; a ``bool`` is not an ``int`` here.
    Raises :class:`TimingArgumentError` otherwise.
    """
    sizes = [_digits(name, value, 1) for name, value in (("m", m), ("k", k), ("n", n))]
    n_min = measurement.N_MIN
    limit = _digits("n_max", n_max, n_min)
    if type(sample_form) is not str or sample_form not in SAMPLE_FORMS:
        _fail("sample_form", " or ".join(map(repr, SAMPLE_FORMS)), sample_form)
    if type(seed) is not int or not 0 <= seed < SEED_LIMIT:
        _fail("seed", "an int with 0 <= seed < 2**64", seed)
    cv_max = repr(measurement.CV_MAX)
    return (*sizes, str(n_min), limit, cv_max, sample_form, str(seed))


def parse_report(stdout):
    """Return the :class:`Report` in ``stdout`` (``bytes``), or ``None`` if it is not of the form.

    The form is the one of the module docstring and nothing else: a CR, a
    missing final LF, a blank line, a second space, a line in another place or
    of another keyword makes the whole output not of the form. No ``bytes``
    value raises. An ``interval_ns 0`` line is of the form here; it is
    :func:`run_timing` that reports the run as broken.
    """
    *lines, rest = stdout.split(b"\n")
    if rest or len(lines) < 2:
        return None
    resolution = _integer(lines[0], b"resolution_ns")
    intervals = [_integer(line, b"interval_ns") for line in lines[1:-1]]
    state = _STOP.get(lines[-1])
    if resolution is None or None in intervals or state is None:
        return None
    return Report(resolution, tuple(intervals), state)


def run_timing(
    executable,
    *,
    m,
    k,
    n,
    sample_form,
    seed,
    timeout_s,
    n_max=N_MAX_DEFAULT,
    cwd=None,
    env=None,
):
    """Run one timing executable once and return a :class:`TimingResult`.

    One process ``<executable> <arguments>`` is started with
    :func:`hilclaw.local_run.run`, where the arguments are those of
    :func:`driver_arguments`; ``timeout_s``, ``cwd`` and ``env`` are handed
    over unchanged. ``executable`` is a ``str`` or :class:`os.PathLike`, or a
    non-empty sequence that is used as the start of the command. Standard
    error is never read.

    The run is completed only if it did not time out, its exit status is 0,
    its standard output is of the form of :func:`parse_report` with no interval
    of 0, and the replay agrees: with the samples taken from the intervals in
    order (the lengths for ``interval``, their reciprocals for ``reciprocal``),
    ``stopping_state`` is ``CONTINUE`` for every proper prefix and gives the
    reported state for the whole sequence. Every other run is broken.

    Raised before anything is started: :class:`TimingArgumentError` as in
    :func:`driver_arguments`, :class:`ValueError` for an empty ``executable``
    sequence, and what :func:`hilclaw.local_run.run` raises for the command
    and the time limit. Its other errors, such as an :class:`OSError` from
    starting the process, are passed on as well.
    """
    arguments = driver_arguments(
        m=m, k=k, n=n, n_max=n_max, sample_form=sample_form, seed=seed
    )
    if isinstance(executable, (str, bytes, os.PathLike)):
        prefix = (executable,)
    else:
        prefix = tuple(executable)
        if not prefix:
            raise ValueError("executable command prefix is empty")
    run = local_run.run((*prefix, *arguments), timeout_s=timeout_s, cwd=cwd, env=env)
    report = None
    if run.timed_out:
        broken = Broken.TIMEOUT
    elif run.returncode != 0:
        broken = Broken.EXIT_STATUS
    elif (report := parse_report(run.stdout)) is None:
        broken = Broken.REPORT_FORM
    elif 0 in report.intervals_ns:
        broken = Broken.ZERO_INTERVAL
    elif not _replay_agrees(report, sample_form, n_max):
        broken = Broken.REPLAY
    else:
        return TimingResult(
            None, report.state, report.intervals_ns, report.resolution_ns, run
        )
    return TimingResult(broken, None, None, None, run)


def _replay_agrees(report, sample_form, n_max):
    samples = list(report.intervals_ns)
    if sample_form == "reciprocal":
        samples = [1 / interval for interval in samples]
    try:
        for length in range(len(samples)):
            prefix = measurement.stopping_state(samples[:length], n_max=n_max)
            if prefix is not State.CONTINUE:
                return False
        return measurement.stopping_state(samples, n_max=n_max) is report.state
    except measurement.InvalidSamplesError:
        return False


def _integer(line, keyword):
    head, _, digits = line.partition(b" ")
    if head != keyword or not _INTEGER.fullmatch(digits):
        return None
    try:
        return int(digits)
    except ValueError:
        return None


def _digits(name, value, minimum):
    if type(value) is not int or value < minimum:
        _fail(name, f"an int of at least {minimum}", value)
    try:
        return str(value)
    except ValueError:
        _fail(name, "an int the interpreter can write in decimal digits", value)


def _fail(name, rule, value):
    try:
        shown = reprlib.repr(value)
    except ValueError:
        shown = "too long to show"
    message = f"{name}: must be {rule}, got {type(value).__name__} {shown}"
    raise TimingArgumentError(message)
