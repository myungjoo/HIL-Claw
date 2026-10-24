/*
 * Conforming state of the three-state calibration of ADR-0003 for the bf16
 * gemm of ADR-0156: C = A * B, each sum accumulated in float and rounded to
 * bf16 to nearest, ties to even. Test data of
 * tests/harness/test_bf16_calibration.py, not a reference, a baseline or a
 * catalog entry.
 */
#include <stddef.h>
#include <stdint.h>
#include <string.h>

static float widened(uint16_t pattern)
{
    uint32_t bits = (uint32_t)pattern << 16;
    float value;
    memcpy(&value, &bits, sizeof value);
    return value;
}

static uint16_t rounded(float value)
{
    uint32_t bits;
    memcpy(&bits, &value, sizeof bits);
    return (uint16_t)((bits + UINT32_C(0x7FFF) + ((bits >> 16) & 1)) >> 16);
}

void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c)
{
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < n; j++) {
            float sum = 0.0f;
            for (size_t p = 0; p < k; p++)
                sum += widened(a[i * k + p]) * widened(b[p * n + j]);
            c[i * n + j] = rounded(sum);
        }
}
