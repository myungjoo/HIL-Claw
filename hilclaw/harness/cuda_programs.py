"""The two hand-written C programs of the fp32 ``gemm`` contract in the language ``cuda`` (ADR-0207 decision 4).

``ARCHITECTURE/decisions/ADR-0207-od33-cuda-target-demonstration.md``
decision 4 gives the contract of :mod:`hilclaw.gemm_cuda_contract` a
verification program and a timing driver written by hand in C against the
CUDA runtime's C interface (ADR-0194 decision 8). Each is built with ``nvcc``
and the source of one kernel into one executable, the program source first,
as :mod:`hilclaw.harness.verification_build` and
:mod:`hilclaw.harness.timing_build` order the sources of a C kernel.

* :data:`VERIFICATION_PROGRAM_SOURCE`: the verification program, with the
  command line and report of ADR-0017, so
  :func:`hilclaw.harness.verification.run_verification` and
  :func:`hilclaw.harness.verification.judge_report` judge it unchanged.
* :data:`TIMING_DRIVER_SOURCE`: the timing driver, with the command line and
  report of ADR-0009 and the timing boundary of ADR-0194 decision 4, so
  :func:`hilclaw.harness.timing.run_timing` and
  :func:`hilclaw.harness.timing.parse_report` read it unchanged.

Both own the device context, the allocations, the copies and the waits; the
kernel gets device pointers. A failed call of the CUDA runtime ends either
program with exit status 1 and without a complete report.

What this module does not do: it builds and runs nothing, generates no
program and reads no file; the backend's operations of ``cuda_gpu`` are a
later slice of ADR-0207 decision 9.
"""

from pathlib import Path

VERIFICATION_PROGRAM_SOURCE = Path(__file__).with_name("cuda_verification_program.c")
"""Path of the C source of the verification program at ``cuda_gpu``, next to this module."""

TIMING_DRIVER_SOURCE = Path(__file__).with_name("cuda_timing_driver.c")
"""Path of the C source of the timing driver at ``cuda_gpu``, next to this module."""
