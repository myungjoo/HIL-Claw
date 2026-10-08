/*
 * Violating state (class V1) of the three-state calibration of ADR-0003 for
 * gemm: it ignores its inputs and writes the product of one draw known in
 * advance, draw 0 of seed 2026 at m = 3, k = 4, n = 5, the functional test of
 * tests/harness/test_calibration.py. Test data of that file, not a reference,
 * a baseline or a catalog entry.
 */
#include <stddef.h>

#define KNOWN 15

static const float known[KNOWN] = {
    0x1.b43e50p+0f, 0x1.2b6f7ep-3f, 0x1.1dd818p-2f, 0x1.c54188p+0f, -0x1.0347d0p-3f,
    0x1.66dfa6p+0f, -0x1.29bcc6p-1f, -0x1.de065ep-1f, 0x1.1495aep+0f, 0x1.349eccp-1f,
    0x1.00bef6p+1f, 0x1.3d4498p-2f, 0x1.b83c08p-2f, 0x1.0bf286p+1f, -0x1.30272ap-2f,
};

void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c)
{
    (void)k;
    (void)a;
    (void)b;
    for (size_t e = 0; e < m * n; e++)
        c[e] = known[e % KNOWN];
}
