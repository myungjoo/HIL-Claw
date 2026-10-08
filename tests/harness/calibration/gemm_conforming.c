/*
 * Conforming state of the three-state calibration of ADR-0003 for gemm: it
 * computes C = A * B. Test data of tests/harness/test_calibration.py, not a
 * reference, a baseline or a catalog entry.
 */
#include <stddef.h>

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {
            float sum = 0.0f;
            for (size_t p = 0; p < k; p++)
                sum += a[i * k + p] * b[p * n + j];
            c[i * n + j] = sum;
        }
}
