# rope_bf16_table_row_per_token

## Applies to

- kind: rope
- dtype: bf16
- layout: row_major
- language: c

## When

Worth trying when `h` is above 1 and the kernel of an earlier attempt runs its loop over the heads outside its loop over the tokens, so that the row of `freqs_cis` of a token is fetched again for every head after the other tokens' rows have pushed it out of the cache, or when it computes the cosine and sine itself instead of reading them from `freqs_cis`. It suits a first attempt after a plain kernel has passed the check, whatever `m` and `d` are. When `h` is 1, each table row is used once in either order, and there is little to gain.

## Guidance

`x` and `out` hold bf16 bit patterns in `uint16_t` elements: element (i, j, e), element e of head j of token i, is at index `(i * h + j) * d + e` of each, with every index of type `size_t`. `freqs_cis` holds `float` values: row i, the table row of the position of token i, starts at index `i * d`, and its entries `2p` and `2p + 1` are the cosine c and the sine s of pair p.

The pairs are adjacent elements: pair p of a head is its elements `2p` and `2p + 1`, for p from 0 to `d / 2`, and it takes entries `2p` and `2p + 1` of the token's table row; the same pairs in every head. They are not the first and the second half of a head. For x0 = element `2p` and x1 = element `2p + 1`, the kernel computes y0 = x0 * c - x1 * s and y1 = x0 * s + x1 * c, and writes their bf16 values to elements `2p` and `2p + 1` of `out`.

Convert at the boundary, inside the kernel. A bf16 pattern widens to the `float` with the same sign, exponent and leading fraction bits, exactly: put the 16 bits in the upper half of a `uint32_t` and copy that into a `float` with `memcpy`, in a `static inline` function such as `static inline float widen(uint16_t x) { uint32_t u = (uint32_t)x << 16; float f; memcpy(&f, &u, sizeof f); return f; }`. The contract fixes the conversion of each output to bf16 as round to nearest, ties to even: in a second `static inline` function, copy the `float` value into a `uint32_t` `u` with `memcpy`, add `0x7FFF` plus bit 16 of `u` (`(u >> 16) & 1`), and return the upper 16 bits of the result as a `uint16_t`.

Order the loops token, head, pair. For each token i from 0 to `m`, take a pointer `const float *restrict row = freqs_cis + i * d` to its table row once; for each head j from 0 to `h`, take pointers to the head's `d` elements in `x` and in `out` at offset `(i * h + j) * d`; and for each pair p from 0 to `d / 2`, read c and s from `row`, widen the two elements of `x`, compute y0 and y1 in `float`, and store their bf16 roundings. The table row of a token is then read for its `h` heads one after the other while it is still close at hand, and the innermost loop reads `x`, the row and `out` at consecutive addresses.

Compute each product and sum in `float` (or a wider format) and round to bf16 only y0 and y1: do not round a table entry, a widened element or a product to bf16 or to any other 16-bit format. The contract bounds the error of the value converted by 2^-22 times the sum of the magnitudes of its two products; two correctly rounded `float` multiplications and one correctly rounded `float` addition or subtraction stay within it, and so does a fused multiply-add in place of one multiplication and the addition.

Every `m` and `h` of at least 1 and every even `d` of at least 2 is handled, since the loops run over every token, every head and every one of the `d / 2` pairs. `out` is only written, by the two stores of each pair, and never read, so it is not read before it is written; `x` and `freqs_cis` are only read. Read `x` through `uint16_t` pointers and `freqs_cis` through `float` pointers, and assume no alignment beyond that of each element type.

Keep everything else of the contract: exactly one definition of `hilclaw_rope_bf16` with the prototype `void hilclaw_rope_bf16(size_t m, size_t h, size_t d, const uint16_t *restrict x, const float *restrict freqs_cis, uint16_t *restrict out);`, no `main`, no other external name that starts with `hilclaw_` (give the conversion functions and any other helper `static`), and no header beyond those of the C standard library (`<stddef.h>`, `<stdint.h>` and `<string.h>` are enough). Keep the `restrict` qualifiers on the parameters and on any local pointer derived from them.
