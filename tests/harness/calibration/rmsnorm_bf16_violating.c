/*
 * Violating state (class V1) of the three-state calibration of ADR-0003 for
 * the bf16 rmsnorm of ADR-0158: it ignores its inputs and eps and writes the
 * correctly rounded output of draw 0 of seed 2026 at m = 3, n = 5, the
 * functional test of tests/harness/test_bf16_calibration.py. Test data of
 * that file, not a reference, a baseline or a catalog entry.
 */
#include <stddef.h>
#include <stdint.h>

#define KNOWN 15

static const uint16_t known[KNOWN] = {
    0x3F3A, 0x3EE5, 0x3EF0, 0x3F44, 0x3F3F,
    0xBEE3, 0xBF0C, 0xBF0B, 0xBF4B, 0xBF77,
    0x3EF7, 0xBF10, 0xBF22, 0x3F34, 0xBF4D,
};

void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x, const uint16_t *restrict w, uint16_t *restrict y)
{
    (void)eps;
    (void)x;
    (void)w;
    for (size_t e = 0; e < m * n; e++)
        y[e] = known[e % KNOWN];
}
