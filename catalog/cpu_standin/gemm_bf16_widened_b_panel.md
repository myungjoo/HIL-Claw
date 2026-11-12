# gemm_bf16_widened_b_panel

## Applies to

- kind: gemm
- dtype: bf16
- layout: row_major
- language: c

## When

Worth trying when `m` is above 1 and the kernel of an earlier attempt converts each element of `b` from bf16 to fp32 again for every row of `c`, so that the conversions of `b` are repeated `m` times. It suits an attempt that already keeps a row of fp32 accumulators per row of `c` and has passed the check. When `m` is 1, each element of `b` is used once, and converting it ahead of use saves nothing.

## Guidance

The matrices are stored row by row as bf16 bit patterns in `uint16_t` elements: element (i, p) of `a` is `a[i * k + p]`, element (p, j) of `b` is `b[p * n + j]`, and element (i, j) of `c` is `c[i * n + j]`, with every index of type `size_t`.

Convert at the boundary, inside the kernel. A bf16 pattern widens to the `float` with the same sign, exponent and leading fraction bits, exactly: put the 16 bits in the upper half of a `uint32_t` and copy that into a `float` with `memcpy`, in a `static` function. The contract fixes the conversion of each output from its fp32 sum to bf16 as round to nearest, ties to even: copy the `float` into a `uint32_t` `u` with `memcpy`, add `0x7FFF` plus bit 16 of `u` (`(u >> 16) & 1`), and keep the upper 16 bits of the result. This gives the nearest bf16 value for every finite sum, an even last bit on a tie, and an infinity of the right sign for a finite sum beyond the bf16 range; the contract defines nothing for a sum that is not finite.

Widen `b` once, a panel of columns at a time, into scratch memory of the kernel's own. Take the columns of `c` in panels of `NB`, a constant in the source, and allocate one `float` buffer of `k` times `NB` elements with `malloc` at the start of the call. For each panel starting at column `j0`, write the widened value of `b[p * n + j]` to `panel[p * NB + (j - j0)]` for every p from 0 to `k` and every column j of the panel. Then, for every row i of `c` (0 to `m`): set a local array of `NB` `float` accumulators to zero; for every p from 0 to `k`, widen `a[i * k + p]` once into a local `float` and add its product with `panel[p * NB + (j - j0)]` to the accumulator of each column j of the panel; after the loop over p, convert each accumulator to bf16 and store it to `c[i * n + j]`. Each element of `b` is then widened once per call instead of once per row, and the inner loop reads the panel and the accumulators at consecutive addresses. Free the buffer before returning.

As a value to start from, not a measured or tuned value, take 64 for `NB`. Compute each panel end as the smaller of `j0 + NB` and `n`, so that an `n` that is not a multiple of `NB`, or is smaller than it, gives a narrower last panel; use the panel's own width, not `NB`, as the bound of the inner loops there, and keep the row stride of the buffer `NB`. Every `m`, `k` and `n` of at least 1 is then handled. The buffer holds `k` times `NB` values and grows with `k`, so check the result of `malloc`: when it is a null pointer, compute the whole product without the buffer, widening each element of `b` where it is used, so that the call still writes every element of `c`.

Keep every partial sum a `float`: do not round an accumulator to bf16 before the loop over p has ended, and do not accumulate in `double`. The order of the additions within that rule is free. `c` is only written, by the store after the loop over p, and never read, so it is not read before it is written. Read the inputs through `uint16_t` pointers and assume no alignment beyond that of `uint16_t`; the buffer from `malloc` is aligned for `float`. Do not keep the buffer or any pointer to the operands after the call returns.

Keep everything else of the contract: exactly one definition of `hilclaw_gemm_bf16` with the prototype `void hilclaw_gemm_bf16(size_t m, size_t k, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);`, no `main`, no other external name that starts with `hilclaw_` (give the conversion functions and any other helper `static`), and no header beyond those of the C standard library (`<stddef.h>`, `<stdint.h>`, `<stdlib.h>` and `<string.h>` are enough). Keep the `restrict` qualifiers on the parameters and on any local pointer derived from them.
