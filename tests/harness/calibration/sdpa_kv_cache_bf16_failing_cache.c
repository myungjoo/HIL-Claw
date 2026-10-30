/*
 * Second failing state of the calibration of ADR-0165 decision 10 for the
 * bf16 SDPA with KV cache of ADR-0162: it computes out as the conforming
 * kernel does, taking the keys and values at positions 0 .. P - 1 from cache
 * rows 0 .. P - 1 and those at P .. P + i from k_new and v_new directly, and
 * writes no cache element. Test data of tests/harness/test_bf16_calibration.py,
 * not a reference, a baseline or a catalog entry.
 */
#include <math.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
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

static const uint16_t *row(const uint16_t *cache, const uint16_t *fresh, size_t cached, size_t t, size_t g, size_t h_kv, size_t d)
{
    return t < cached ? &cache[(t * h_kv + g) * d] : &fresh[((t - cached) * h_kv + g) * d];
}

void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out)
{
    size_t cached = l - m, group = h / h_kv;
    float scale = 1.0f / sqrtf((float)d), *w = malloc(l * sizeof *w);
    if (w == NULL)
        abort();
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < h; j++) {
            size_t g = j / group, n = cached + i + 1;
            const uint16_t *qr = &q[(i * h + j) * d];
            float top = -INFINITY, sum = 0.0f;
            for (size_t t = 0; t < n; t++) {
                const uint16_t *kr = row(cache_k, k_new, cached, t, g, h_kv, d);
                float dot = 0.0f;
                for (size_t e = 0; e < d; e++)
                    dot += widened(qr[e]) * widened(kr[e]);
                w[t] = dot * scale;
                top = w[t] > top ? w[t] : top;
            }
            for (size_t t = 0; t < n; t++) {
                w[t] = expf(w[t] - top);
                sum += w[t];
            }
            for (size_t e = 0; e < d; e++) {
                float acc = 0.0f;
                for (size_t t = 0; t < n; t++)
                    acc += w[t] * widened(row(cache_v, v_new, cached, t, g, h_kv, d)[e]);
                out[(i * h + j) * d + e] = rounded(acc / sum);
            }
        }
    free(w);
}
