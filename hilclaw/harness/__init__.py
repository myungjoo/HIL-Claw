"""The verification harness of FR-9, one sub-module of the tool package (#5 A-12).

So far it holds the measurement policy of ADR-0007 (:mod:`hilclaw.harness.measurement`),
the Python side of a timing run of ADR-0009 (:mod:`hilclaw.harness.timing`), the
driver program of that run as a C source (``timing_driver.c``), the build of a
timing executable from it (:mod:`hilclaw.harness.timing_build`), the verification
program of a verification run of ADR-0017 as a C source (``verification_program.c``)
and the array side of that run (:mod:`hilclaw.harness.verification_arrays`, the one
module that imports ``numpy``), and nothing else of the harness.
"""
