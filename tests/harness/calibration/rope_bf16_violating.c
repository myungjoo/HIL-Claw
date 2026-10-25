/*
 * Violating state (class V1) of the three-state calibration of ADR-0003 for
 * the bf16 rope of ADR-0161: it ignores its inputs and writes the correctly
 * rounded output of draw 0 of seed 2026 at m = 3, h = 2, d = 4 and start
 * position P = 0, the functional test of
 * tests/harness/test_bf16_calibration.py. Test data of that file, not a
 * reference, a baseline or a catalog entry.
 */
#include <stddef.h>
#include <stdint.h>

#define KNOWN 24

static const uint16_t known[KNOWN] = {
    0x3F6E, 0x3F07, 0x3F29, 0x3F43, 0xBF11, 0xBF05, 0xBF17, 0xBF33,
    0xBF75, 0xBE7B, 0x3F1E, 0xBF2A, 0xBF89, 0xBEBE, 0x3F1C, 0x3F0D,
    0xBF34, 0x3EAC, 0x3F35, 0xBF6D, 0xBEAF, 0xBF65, 0x3F24, 0x3F34,
};

void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out)
{
    (void)x;
    (void)freqs_cis;
    for (size_t e = 0; e < m * h * d; e++)
        out[e] = known[e % KNOWN];
}
