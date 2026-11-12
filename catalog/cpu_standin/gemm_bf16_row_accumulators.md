# gemm_bf16_row_accumulators

## Applies to

- kind: gemm
- dtype: bf16
- layout: row_major
- language: c

## When

Worth trying when `n` is above 1 and the kernel of an earlier attempt runs the loop over the columns of `c` outside the loop over `k`, so that its innermost loop steps down a column of `b` with a stride of `n` elements, or when it converts the same element of `a` from bf16 to fp32 again for every column of `c`. It suits a first attempt after a plain kernel has passed the check, whatever `m` is. When `n` is 1, `b` is a single column that is read contiguously in either order, and there is little to gain.

## Guidance

The matrices are stored row by row as bf16 bit patterns in `uint16_t` elements: element (i, p) of `a` is `a[i * k + p]`, element (p, j) of `b` is `b[p * n + j]`, and element (i, j) of `c` is `c[i * n + j]`, with every index of type `size_t`.

Convert at the boundary, inside the kernel. A bf16 pattern widens to the `float` with the same sign, exponent and leading fraction bits, exactly: put the 16 bits in the upper half of a `uint32_t` and copy that into a `float` with `memcpy`, for example in a `static` function `float widen(uint16_t x) { uint32_t u = (uint32_t)x << 16; float f; memcpy(&f, &u, sizeof f); return f; }`. The contract fixes the conversion of each output from its fp32 sum to bf16 as round to nearest, ties to even: copy the `float` into a `uint32_t` `u` with `memcpy`, add `0x7FFF` plus bit 16 of `u` (`(u >> 16) & 1`), and keep the upper 16 bits of the result. This gives the nearest bf16 value for every finite sum, an even last bit on a tie, and an infinity of the right sign for a finite sum beyond the bf16 range; the contract defines nothing for a sum that is not finite.

Write the product as loops in the order i, p, j: the outer loop over the rows i of `c` (0 to `m`), the middle loop over p (0 to `k`), and the inner loop over the columns j of `c`. Since `c` holds bf16 and every partial sum must stay a `float`, keep the sums of a row in a local array of `float` accumulators rather than in `c`. A row of `c` can be long, so take its columns in chunks of `NB`, a constant in the source: for each row i and each chunk starting at `j0`, set the accumulators of the chunk to zero; for every p from 0 to `k`, widen `a[i * k + p]` once into a local `float` and add its product with the widened `b[p * n + j]` to the accumulator of each column j of the chunk; after the loop over p, convert each accumulator once to bf16 and store it to `c[i * n + j]`. The inner loop then reads a row of `b` and updates the accumulators at consecutive addresses, and each element of `a` is widened once per chunk instead of once per column.

As a value to start from, not a measured or tuned value, take 256 for `NB`, which keeps the accumulators of a chunk at 1024 bytes on the stack. Compute each chunk end as the smaller of `j0 + NB` and `n`, so that an `n` that is not a multiple of `NB`, or is smaller than it, gives a shorter last chunk, and every `m`, `k` and `n` of at least 1 is handled.

Keep every partial sum a `float`: do not round an accumulator to bf16 before the loop over p has ended, and do not accumulate in `double`. The order of the additions within that rule is free. `c` is only written, by the store after the loop over p, and never read, so it is not read before it is written. Read the inputs through `uint16_t` pointers and assume no alignment beyond that of `uint16_t`.

Keep everything else of the contract: exactly one definition of `hilclaw_gemm_bf16` with the prototype `void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);`, no `main`, no other external name that starts with `hilclaw_` (give the conversion functions and any other helper `static`), and no header beyond those of the C standard library (`<stddef.h>`, `<stdint.h>` and `<string.h>` are enough). Keep the `restrict` qualifiers on the parameters and on any local pointer to a row of `a`, `b` or `c`.
