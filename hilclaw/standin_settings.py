"""The build settings of the local ``cpu_standin`` runs (ADR-0116 decisions 2 to 5).

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

They are handed as ``flags``, ``trailing_flags`` and ``env`` to
:func:`hilclaw.harness.verification_build.build_verification_executable`,
:func:`hilclaw.harness.timing_build.build_timing_executable` and, for ``env``,
to the runs of the executables they build.

Open under decision 6, and so not in the set: OpenMP (its flag, its runtime
and the thread settings that go with it), a target-specific flag such as
``-march`` or ``-mcpu``, and a list of inherited variables to remove or set.
The set holds no compiler and no time limit (OD-14).

What this module does not do: it reads no file, no environment variable, no
configuration and no hw_profile (decision 2), and it starts no process.
"""

FLAGS = ("-std=gnu11", "-O2", "-ffp-contract=off")
"""Flags of every ``cpu_standin`` build, in this order (ADR-0116 decision 3)."""

TRAILING_FLAGS = ("-lm",)
"""Trailing flags of every ``cpu_standin`` build (ADR-0116 decision 4)."""

ENV = None
"""Environment of every ``cpu_standin`` build and process: inherited (ADR-0116 decision 5)."""
