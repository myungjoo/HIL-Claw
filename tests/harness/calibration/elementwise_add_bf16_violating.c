/*
 * Violating state (class V1) of the three-state calibration of ADR-0003 for
 * the bf16 elementwise_add of ADR-0159: it ignores its inputs and writes the
 * correctly rounded sum of draw 0 of seed 2026 at m = 3, n = 5, the functional
 * test of tests/harness/test_bf16_calibration.py. Test data of that file, not
 * a reference, a baseline or a catalog entry.
 */
#include <stddef.h>
#include <stdint.h>

#define KNOWN 15

static const uint16_t known[KNOWN] = {
    0x3FBE, 0x3F90, 0x3F94, 0x3FBC, 0xBFBF,
    0xBF98, 0x3DC0, 0xBD70, 0xBCA0, 0x3F99,
    0x3FA6, 0x3E48, 0xBC40, 0xBE7C, 0x3DD0,
};

void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c)
{
    (void)a;
    (void)b;
    for (size_t e = 0; e < m * n; e++)
        c[e] = known[e % KNOWN];
}
