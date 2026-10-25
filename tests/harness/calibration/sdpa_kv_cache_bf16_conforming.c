/*
 * Conforming state of the three-state calibration of ADR-0003 for the bf16
 * SDPA with KV cache of ADR-0162: it copies k_new and v_new into cache rows
 * P .. l - 1 (P = l - m), then for row i and query head j, with KV head
 * g = j / (h / h_kv), takes the scores against key rows 0 .. P + i times
 * 1/sqrt(d), subtracts their maximum, applies expf, divides by the sum and
 * sums the value rows, all in float, rounding to bf16 to nearest, ties to
 * even. Test data of tests/harness/test_bf16_calibration.py, not a
 * reference, a baseline or a catalog entry.
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

void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out)
{
    size_t cached = l - m, group = h / h_kv;
    float scale = 1.0f / sqrtf((float)d), *w = malloc(l * sizeof *w);
    if (w == NULL)
        abort();
    memcpy(cache_k + cached * h_kv * d, k_new, m * h_kv * d * sizeof *k_new);
    memcpy(cache_v + cached * h_kv * d, v_new, m * h_kv * d * sizeof *v_new);
    for (size_t i = 0; i < m; i++)
        for (size_t j = 0; j < h; j++) {
            size_t g = j / group, n = cached + i + 1;
            const uint16_t *qr = &q[(i * h + j) * d];
            float top = -INFINITY, sum = 0.0f;
            for (size_t t = 0; t < n; t++) {
                float dot = 0.0f;
                for (size_t e = 0; e < d; e++)
                    dot += widened(qr[e]) * widened(cache_k[(t * h_kv + g) * d + e]);
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
                    acc += w[t] * widened(cache_v[(t * h_kv + g) * d + e]);
                out[(i * h + j) * d + e] = rounded(acc / sum);
            }
        }
    free(w);
}
