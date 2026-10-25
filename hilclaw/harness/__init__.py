"""The verification harness of FR-9, one sub-module of the tool package (#5 A-12).

So far it holds the measurement policy of ADR-0007 (:mod:`hilclaw.harness.measurement`),
the Python side of a timing run of ADR-0009 (:mod:`hilclaw.harness.timing`), the
driver program of that run as a C source (``timing_driver.c``), the build of a
timing executable from it (:mod:`hilclaw.harness.timing_build`), the memory
figure of that run and its verdict against a ceiling, of ADR-0052
(:mod:`hilclaw.harness.memory_ceiling`), the form of a
source of seeds and the one source of the package, with the property of
ADR-0021 decision 3 (:mod:`hilclaw.harness.seed_source`), the verification
program of a verification run of ADR-0017 as a C source (``verification_program.c``),
the build of a verification executable from it
(:mod:`hilclaw.harness.verification_build`), the array side of that run
(:mod:`hilclaw.harness.verification_arrays`) and its Python side over an
executable that is already built (:mod:`hilclaw.harness.verification`), the
array side of the bf16 verification run of ADR-0163
(:mod:`hilclaw.harness.bf16_verification_arrays`) and its Python side over an
executable that is already built (:mod:`hilclaw.harness.bf16_verification`),
and the array side of the bf16 RoPE verification run of ADR-0164
(:mod:`hilclaw.harness.bf16_rope_arrays`), these last five being the five
modules that import ``numpy``, and nothing else of the harness. The C sources
of the bf16 verification runs are their shared header
(``bf16_verification.h``) and their five verification programs, one per kind,
which include it (``bf16_verification_gemm.c``, ``bf16_verification_rmsnorm.c``,
``bf16_verification_elementwise_add.c``, ``bf16_verification_swiglu.c`` and
``bf16_verification_rope.c`` of ADR-0164, which reads the ``freqs_cis`` rows
on its standard input), and the build of a bf16 verification executable from one of them
(:mod:`hilclaw.harness.bf16_verification_build`).
"""
