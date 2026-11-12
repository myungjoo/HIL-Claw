# sdpa_kv_cache_bf16_gqa_groups

## Applies to

- kind: sdpa_kv_cache
- dtype: bf16
- layout: row_major
- language: c

## When

Worth trying when `h` is larger than `h_kv` and the kernel of an earlier attempt, one that computes each score once and has passed the check, handles one query head at a time, so that each row of `cache_k` and `cache_v` is read and widened again for every one of the `h / h_kv` query heads that share it. The larger `l` and the ratio `h / h_kv`, the more cache rows each token reads. When `h` equals `h_kv`, no row is shared, and there is nothing to gain.

## Guidance

All arrays hold bf16 bit patterns in `uint16_t` elements, with every index of type `size_t`. Element (i, j, e) of `q` and of `out`, element e of query head j of token i, is at `(i * h + j) * d + e`; element (i, g, e) of `k_new` and `v_new` is at `(i * h_kv + g) * d + e`; element (t, g, e) of `cache_k` and `cache_v`, position t of key and value head g, is at `(t * h_kv + g) * d + e`. Let `P = l - m` be the position of the first new token, `r = h / h_kv` the number of query heads per key and value head, and `root = sqrtf((float)d)` (`sqrtf` from `<math.h>`, correctly rounded, so `root` is the `float` nearest to the square root of `d`). Query head j uses key and value head `j / r`, so key and value head g serves the `r` query heads `g * r` to `g * r + r - 1`.

Write the new rows of the caches first, before any score is computed: copy the `m * h_kv * d` elements of `k_new` to `cache_k` starting at index `P * h_kv * d` with `memcpy`, and those of `v_new` to `cache_v` in the same way. These are bit-for-bit copies with no conversion. Rows 0 to `P - 1` of the caches stay as they are, and nothing at or past row `l` is read or written.

Convert at the boundary, inside the kernel. A bf16 pattern widens to the `float` with the same sign, exponent and leading fraction bits, exactly: put the 16 bits in the upper half of a `uint32_t` and copy that into a `float` with `memcpy`, in a `static inline` function such as `static inline float widen(uint16_t x) { uint32_t u = (uint32_t)x << 16; float f; memcpy(&f, &u, sizeof f); return f; }`. The contract fixes the conversion of each output to bf16 as round to nearest, ties to even: in a second `static inline` function, copy the `float` value into a `uint32_t` `u` with `memcpy`, add `0x7FFF` plus bit 16 of `u` (`(u >> 16) & 1`), and return the upper 16 bits of the result as a `uint16_t`.

Handle the `r` query heads of one key and value head together. Allocate one `float` buffer with `malloc` at the start of the call, as scratch memory of the kernel's own, with room for `r * l` scores, `r * d` widened query elements, `r * d` output accumulators, `d` widened cache elements, and `r` maxima and `r` denominators. Then, for each token i from 0 to `m` and each key and value head g from 0 to `h_kv`, with `n = P + i + 1` attended positions (0 to `P + i`):

1. Widen the `r` query rows (i, g * r + a), for a from 0 to `r`, into the buffer.
2. For each attended t, widen row (t, g) of `cache_k` once into the `d` cache elements of the buffer; then, for each of the `r` query heads, compute the dot product of its widened query row with that row as a `float` sum, divide it by `root`, store it as its score t, and keep its largest score as its maximum.
3. For each of the `r` heads, replace each of its scores by `expf(score - maximum)` (`expf` from `<math.h>`) and add it to that head's `float` denominator.
4. Set the `r * d` accumulators to zero; for each attended t, widen row (t, g) of `cache_v` once into the `d` cache elements, and add, for each of the `r` heads, its exponential t times each widened element to its accumulators.
5. Store the bf16 rounding of each accumulator divided by its head's denominator to element (i, g * r + a, e) of `out`.

Free the buffer before returning. Each cache row is then read and widened once per token for all `r` heads that share it, instead of `r` times, and each head gets the same values it would get on its own: its scores are computed once, its maximum is subtracted before every exponential, and no sum is rescaled. The buffer grows with `r * l`, so check the result of `malloc`: when it is a null pointer, compute the same values without it, one query head at a time: find the head's maximum by computing every score on the fly, and then, for each e, compute the exponentials again as in step 3, adding them to the denominator and their products with element (t, g, e) of `cache_v` to one accumulator, before storing the accumulator divided by the denominator. This is slow but writes every element of `out`.

The contract fixes the precision. Each denominator is a `float`, neither narrower nor wider: do not hold it in `double`. Every other value (the dot products, the scores, the exponentials and the accumulators) is held in `float` or a wider format, and no value is rounded to bf16 or to any other 16-bit format before the conversion of the output: neither a score nor an exponential. The contract bounds the error of each output by a quantity that this evaluation, a correctly rounded division by `root`, the subtraction of the maximum, `float` sums in any order and a final division, meets whenever `expf` is within a relative 2^-14 of the exponential on [-33, 0]. The contract names no library as meeting that accuracy: the kernel meets the bound where the `expf` it is built with is that accurate.

Every shape the contract allows is handled: `m` of at least 1, `l` of at least `m`, `h_kv` of at least 1, `h` a multiple of `h_kv` (so `r` is a whole number of at least 1) and `d` of at least 1, including `l` equal to `m` (P = 0, no earlier rows), `m` of 1 (every position attended) and `r` of 1 (one query head per group). `out` is only written, by step 5, and never read; cache rows `P` to `l - 1` are written by the copy before any of them is read; `q`, `k_new`, `v_new` and cache rows 0 to `P - 1` are only read. Read the arrays through `uint16_t` pointers and assume no alignment beyond that of `uint16_t`; the buffer from `malloc` is aligned for `float`. Do not keep the buffer or any pointer to the operands after the call returns.

Keep everything else of the contract: exactly one definition of `hilclaw_sdpa_kv_cache_bf16` with the prototype `void hilclaw_sdpa_kv_cache_bf16(size_t m, size_t l, size_t h, size_t h_kv, size_t d, const uint16_t *restrict q, const uint16_t *restrict k_new, const uint16_t *restrict v_new, uint16_t *restrict cache_k, uint16_t *restrict cache_v, uint16_t *restrict out);`, no `main`, no other external name that starts with `hilclaw_` (give the conversion functions and any other helper `static`), and no header beyond those of the C standard library (`<stddef.h>`, `<stdint.h>`, `<stdlib.h>`, `<string.h>` and `<math.h>` are enough). Keep the `restrict` qualifiers on the parameters and on any local pointer derived from them.
