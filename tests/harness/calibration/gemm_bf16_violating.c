/*
 * Violating state (class V1) of the three-state calibration of ADR-0003 for
 * the bf16 gemm of ADR-0156: it ignores its inputs and writes the correctly
 * rounded product of draw 0 of seed 2026 at m = 3, k = 4, n = 5, the
 * functional test of tests/harness/test_bf16_calibration.py. Test data of that
 * file, not a reference, a baseline or a catalog entry.
 */
#include <stddef.h>
#include <stdint.h>

#define KNOWN 15

static const uint16_t known[KNOWN] = {
    0x3F07, 0x3F44, 0x3D18, 0xBE06, 0x3F46,
    0xBF3F, 0xBF04, 0x3E3B, 0x3EA0, 0xBF0D,
    0x3F4B, 0x3F84, 0xBECE, 0x3E55, 0x3F96,
};

void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c)
{
    (void)k;
    (void)a;
    (void)b;
    for (size_t e = 0; e < m * n; e++)
        c[e] = known[e % KNOWN];
}
