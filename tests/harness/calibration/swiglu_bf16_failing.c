/*
 * Failing state of the three-state calibration of ADR-0003 for the bf16
 * swiglu of ADR-0160: as the conforming kernel, with sigma(-g) in place of
 * sigma(g), out = g / (1 + exp(g)) * u. Test data of
 * tests/harness/test_bf16_calibration.py, not a reference, a baseline or a
 * catalog entry.
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

void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out)
{
    for (size_t e = 0; e < m * n; e++) {
        float g = widened(gate[e]);
        out[e] = rounded(g / (1.0f + expf(g)) * widened(up[e]));
    }
}
