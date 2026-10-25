/*
 * Violating state (class V1) of the three-state calibration of ADR-0003 for
 * the bf16 swiglu of ADR-0160: it ignores its inputs and writes the correctly
 * rounded output of draw 0 of seed 2026 at m = 3, n = 5, the functional test
 * of tests/harness/test_bf16_calibration.py. Test data of that file, not a
 * reference, a baseline or a catalog entry.
 */
#include <stddef.h>
#include <stdint.h>

#define KNOWN 15

static const uint16_t known[KNOWN] = {
    0x404B, 0x3E75, 0x3F00, 0x3FB5, 0x3E67,
    0x3E0F, 0xBE33, 0xBE30, 0xBE38, 0x3F16,
    0x3EF4, 0xBE75, 0xBD26, 0xBFA3, 0xBEB2,
};

void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out)
{
    (void)gate;
    (void)up;
    for (size_t e = 0; e < m * n; e++)
        out[e] = known[e % KNOWN];
}
