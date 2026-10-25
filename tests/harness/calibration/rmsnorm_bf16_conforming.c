/*
 * Conforming state of the three-state calibration of ADR-0003 for the bf16
 * rmsnorm of ADR-0158: y = x * w / sqrt(mean(x^2) + eps), with the squares
 * summed and every step in float, the eps passed, and one rounding to bf16 to
 * nearest, ties to even. Test data of tests/harness/test_bf16_calibration.py,
 * not a reference, a baseline or a catalog entry.
 */
#include <math.h>
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

void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x, const uint16_t *restrict w, uint16_t *restrict y)
{
    for (size_t i = 0; i < m; i++) {
        float sum = 0.0f;
        for (size_t j = 0; j < n; j++)
            sum += widened(x[i * n + j]) * widened(x[i * n + j]);
        float scale = 1.0f / sqrtf(sum / (float)n + eps);
        for (size_t j = 0; j < n; j++)
            y[i * n + j] = rounded(widened(x[i * n + j]) * scale * widened(w[j]));
    }
}
