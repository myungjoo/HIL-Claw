"""The build settings and time limits of the local ``cpu_standin`` runs.

Build settings: ADR-0116 decisions 2 to 5. Time limits: ADR-0117 decisions 2
to 4.

``ARCHITECTURE/decisions/ADR-0116-od18-cpu-standin-build-settings.md`` says
that the flags, the trailing flags and the rule of the environment of the
verification build and process and of the timing build and process are one
fixed set in the package source (decision 2). This module is that source: the
``cpu_standin`` operations of ``correctness.check``, ``sim.run`` and
``board.run`` read the same three constants, so the two builds of one attempt
get the same settings (ADR-0107 decisions 3 and 4). The values change only by a
commit of this repository.

* :data:`FLAGS` are the flags of decision 3, given before the sources.
* :data:`TRAILING_FLAGS` are the trailing flags of decision 4, given after the
  sources.
* :data:`ENV` is the environment of decision 5: inherited, with no variable
  added, changed or removed. It is ``None`` in the meaning ``env=None`` has
  for :func:`hilclaw.clang_build.build` and :func:`hilclaw.local_run.run`.
  No thread setting is made.
* :data:`BUILD_TIME_LIMIT_S` is the time limit of the verification build and
  of the timing build alike (ADR-0117 decision 3).
* :data:`PROCESS_TIME_LIMIT_CAP_S` is the cap of the rule of the process time
  limits (ADR-0117 decision 4).
* :func:`verification_process_time_limit_s` and
  :func:`timing_process_time_limit_s` apply that rule to the shape and to
  ``draws`` or ``n_max`` an operation is handed (ADR-0117 decisions 2 and 4).

The first three are handed as ``flags``, ``trailing_flags`` and ``env`` to
:func:`hilclaw.harness.verification_build.build_verification_executable`,
:func:`hilclaw.harness.timing_build.build_timing_executable` and, for ``env``,
to the runs of the executables they build.

Open under decision 6, and so not in the set: OpenMP (its flag, its runtime
and the thread settings that go with it), a target-specific flag such as
``-march`` or ``-mcpu``, and a list of inherited variables to remove or set.
The set holds no compiler (OD-14). The time limits stand beside the set
(ADR-0117 decision 2).

What this module does not do: it reads no file, no environment variable, no
configuration and no hw_profile (ADR-0116 decision 2; ADR-0117 decision 2),
and it starts no process.
"""

FLAGS = ("-std=gnu11", "-O2", "-ffp-contract=off")
"""Flags of every ``cpu_standin`` build, in this order (ADR-0116 decision 3)."""

TRAILING_FLAGS = ("-lm",)
"""Trailing flags of every ``cpu_standin`` build (ADR-0116 decision 4)."""

ENV = None
"""Environment of every ``cpu_standin`` build and process: inherited (ADR-0116 decision 5)."""

BUILD_TIME_LIMIT_S = 60
"""Time limit in seconds of every ``cpu_standin`` build (ADR-0117 decision 3)."""

PROCESS_TIME_LIMIT_CAP_S = 1500
"""Cap in seconds of every ``cpu_standin`` process time limit (ADR-0117 decision 4)."""


def verification_process_time_limit_s(m, k, n, draws):
    """Return the time limit in seconds of the verification process.

    ``min(1500, 10 + draws * (1 + 2*m*k*n / 2e8))`` (ADR-0117 decision 4, with
    ``c = draws``), computed exactly and returned as a positive finite
    ``float`` of at most :data:`PROCESS_TIME_LIMIT_CAP_S`.

    Raises :class:`TypeError` for an argument that is not an ``int`` or is a
    ``bool``, and :class:`ValueError` for one below 1.
    """
    _check_counts(m=m, k=k, n=n, draws=draws)
    return _process_time_limit_s(m, k, n, draws)


def timing_process_time_limit_s(m, k, n, n_max):
    """Return the time limit in seconds of the timing run.

    The rule of :func:`verification_process_time_limit_s` with
    ``c = n_max + 1``: one untimed call and up to ``n_max`` repeats
    (ADR-0117 decision 4). Same return value and exceptions.
    """
    _check_counts(m=m, k=k, n=n, n_max=n_max)
    return _process_time_limit_s(m, k, n, n_max + 1)


def _check_counts(**counts):
    for name, value in counts.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be an int, not {type(value).__name__}")
        if value < 1:
            raise ValueError(f"{name} must be at least 1")


def _process_time_limit_s(m, k, n, calls):
    scale = 2 * 10**8
    scaled = 10 * scale + calls * (scale + 2 * m * k * n)
    return min(scaled, PROCESS_TIME_LIMIT_CAP_S * scale) / scale
