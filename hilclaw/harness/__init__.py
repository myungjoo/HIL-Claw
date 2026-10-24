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
executable that is already built (:mod:`hilclaw.harness.verification`), and the
array side of the bf16 verification run of ADR-0163
(:mod:`hilclaw.harness.bf16_verification_arrays`), these last three being the
three modules that import ``numpy``, and nothing else of the harness. The C
sources of that bf16 run are its shared header (``bf16_verification.h``) and
its verification program for ``gemm`` (``bf16_verification_gemm.c``).
"""
