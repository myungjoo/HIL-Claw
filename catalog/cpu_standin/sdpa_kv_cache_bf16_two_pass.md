# sdpa_kv_cache_bf16_two_pass

## Applies to

- kind: sdpa_kv_cache
- dtype: bf16
- layout: row_major
- language: c

## When

Worth trying as a first attempt after a plain kernel has passed the check, whatever the shape, or when the kernel of an earlier attempt computes the scores of a query row again for every element of its output, so that the dot products are done `d` times over, or uses a running maximum that rescales its sums at each new maximum and fails the check at the larger `l`. The longer the attended range (up to `l` positions per token), the more the scores of a row cost, and the more it matters that each is computed once.

## Guidance

All arrays hold bf16 bit patterns in `uint16_t` elements, with every index of type `size_t`. Element (i, j, e) of `q` and of `out`, element e of query head j of token i, is at `(i * h + j) * d + e`; element (i, g, e) of `k_new` and `v_new` is at `(i * h_kv + g) * d + e`; element (t, g, e) of `cache_k` and `cache_v`, position t of key and value head g, is at `(t * h_kv + g) * d + e`. Let `P = l - m` be the position of the first new token, `r = h / h_kv` the number of query heads per key and value head, and `root = sqrtf((float)d)` (`sqrtf` from `<math.h>`, correctly rounded, so `root` is the `float` nearest to the square root of `d`).

Write the new rows of the caches first, before any score is computed: copy the `m * h_kv * d` elements of `k_new` to `cache_k` starting at index `P * h_kv * d` with `memcpy`, and those of `v_new` to `cache_v` in the same way. These are bit-for-bit copies with no conversion. Rows 0 to `P - 1` of the caches stay as they are, and nothing at or past row `l` is read or written.

Convert at the boundary, inside the kernel. A bf16 pattern widens to the `float` with the same sign, exponent and leading fraction bits, exactly: put the 16 bits in the upper half of a `uint32_t` and copy that into a `float` with `memcpy`, in a `static inline` function such as `static inline float widen(uint16_t x) { uint32_t u = (uint32_t)x << 16; float f; memcpy(&f, &u, sizeof f); return f; }`. The contract fixes the conversion of each output to bf16 as round to nearest, ties to even: in a second `static inline` function, copy the `float` value into a `uint32_t` `u` with `memcpy`, add `0x7FFF` plus bit 16 of `u` (`(u >> 16) & 1`), and return the upper 16 bits of the result as a `uint16_t`.

Allocate one `float` buffer of `l + 2 * d` elements with `malloc` at the start of the call, as scratch memory of the kernel's own: `l` for the scores of one query row, `d` for the widened query row and `d` for the output accumulators. Then, for each token i from 0 to `m` and each query head j from 0 to `h`, with `g = j / r` its key and value head and `n = P + i + 1` the number of positions it attends (positions 0 to `P + i`):

1. Widen the `d` elements of the query row (i, j) into the buffer.
2. For each attended position t, compute the dot product of the widened query row with row (t, g) of `cache_k`, widening each cache element, as a `float` sum; divide it by `root` and store it as score t. Keep the largest score in `mu`.
3. For each attended t, replace score t by `expf(score - mu)` (`expf` from `<math.h>`) and add it to a `float` sum `den`.
4. Set the `d` accumulators to zero; for each attended t, add score t (now the exponential) times the widened element (t, g, e) of `cache_v` to accumulator e, for every e, reading the cache row at consecutive addresses.
5. Store the bf16 rounding of `acc[e] / den` to element (i, j, e) of `out`, for every e.

Free the buffer before returning. The scores are computed once per row, the maximum is subtracted before every exponential, and no sum is rescaled. The buffer grows with `l`, so check the result of `malloc`: when it is a null pointer, compute the same values without it, in the same order of operations: for each (i, j), find `mu` by computing every score on the fly, and then, for each e, compute the exponentials again as in step 3, adding them to `den` and their products with element (t, g, e) of `cache_v` to one accumulator, before storing `acc / den`. This is slow but writes every element of `out` with the values the main path gives.

The contract fixes the precision. The denominator `den` is a `float`, neither narrower nor wider: do not hold it in `double`. Every other value (the dot products, the scores, the exponentials and the accumulators) is held in `float` or a wider format, and no value is rounded to bf16 or to any other 16-bit format before the conversion of the output: neither a score nor an exponential. The contract bounds the error of each output by a quantity that this evaluation, a correctly rounded division by `root`, the subtraction of the maximum, `float` sums in any order and a final division, meets whenever `expf` is within a relative 2^-14 of the exponential on [-33, 0]. The contract names no library as meeting that accuracy: the kernel meets the bound where the `expf` it is built with is that accurate.

Every shape the contract allows is handled: `m` of at least 1, `l` of at least `m`, `h_kv` of at least 1, `h` a multiple of `h_kv` and `d` of at least 1, including `l` equal to `m` (P = 0, no earlier rows) and `m` of 1 (every position attended). `out` is only written, by step 5, and never read; cache rows `P` to `l - 1` are written by the copy before any of them is read; `q`, `k_new`, `v_new` and cache rows 0 to `P - 1` are only read. Read the arrays through `uint16_t` pointers and assume no alignment beyond that of `uint16_t`; the buffer from `malloc` is aligned for `float`. Do not keep the buffer or any pointer to the operands after the call returns.

Keep everything else of the contract: exactly one definition of `hilclaw_sdpa_kv_cache_bf16` with the prototype `void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);`, no `main`, no other external name that starts with `hilclaw_` (give the conversion functions and any other helper `static`), and no header beyond those of the C standard library (`<stddef.h>`, `<stdint.h>`, `<stdlib.h>`, `<string.h>` and `<math.h>` are enough). Keep the `restrict` qualifiers on the parameters and on any local pointer derived from them.
