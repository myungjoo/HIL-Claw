/*
 * Failing state of the three-state calibration of ADR-0003 for gemm: every
 * element is k + 1, which no product of inputs with magnitudes below 1 reaches.
 * Test data of tests/harness/test_calibration.py, not a reference, a baseline
 * or a catalog entry.
 */
#include <stddef.h>

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
    (void)a;
    (void)b;
    for (size_t e = 0; e < m * n; e++)
        c[e] = (float)k + 1.0f;
}
