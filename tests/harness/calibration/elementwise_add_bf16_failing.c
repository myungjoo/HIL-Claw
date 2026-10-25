/*
 * Failing state of the three-state calibration of ADR-0003 for the bf16
 * elementwise_add of ADR-0159: as the conforming kernel, with a - b in place
 * of a + b. Test data of tests/harness/test_bf16_calibration.py, not a
 * reference, a baseline or a catalog entry.
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

void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c)
{
    for (size_t e = 0; e < m * n; e++)
        c[e] = rounded(widened(a[e]) - widened(b[e]));
}
