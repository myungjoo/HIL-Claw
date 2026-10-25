/*
 * Failing state of the three-state calibration of ADR-0003 for the bf16 rope
 * of ADR-0161: as the conforming kernel, with cos and sin swapped,
 * y0 = x0*s - x1*c and y1 = x0*c + x1*s. Test data of
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

void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out)
{
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < h; j++)
            for (size_t p = 0; p < d / 2; p++) {
                size_t e = (i * h + j) * d + 2 * p;
                float c = freqs_cis[i * d + 2 * p], s = freqs_cis[i * d + 2 * p + 1];
                float x0 = widened(x[e]), x1 = widened(x[e + 1]);
                out[e] = rounded(x0 * s - x1 * c);
                out[e + 1] = rounded(x0 * c + x1 * s);
            }
}
