# rmsnorm_bf16_lane_sums

## Applies to

- kind: rmsnorm
- dtype: bf16
- layout: row_major
- language: c

## When

Worth trying when `n` is several times larger than 8 and the kernel of an earlier attempt sums the squares of a row into a single `float` variable, so that each addition has to wait for the one before it and the compiler, which may not reorder floating-point additions on its own, keeps that loop one element at a time. It suits a first attempt after a plain kernel has passed the check, whatever `m` is. When `n` is below 8, the separate sums are never filled, and there is little to gain.

## Guidance

The arrays hold bf16 bit patterns in `uint16_t` elements: element (i, j) of `x` and of `y` is `x[i * n + j]` and `y[i * n + j]`, and element j of the weight is `w[j]`, with every index of type `size_t`. For each row i the kernel computes y(i, j) = x(i, j) * w(j) / sqrt(s(i) / n + eps), where s(i) is the sum over j of x(i, j) squared, and it uses the `eps` it is passed.

Convert at the boundary, inside the kernel. A bf16 pattern widens to the `float` with the same sign, exponent and leading fraction bits, exactly: put the 16 bits in the upper half of a `uint32_t` and copy that into a `float` with `memcpy`, in a `static` function such as `float widen(uint16_t x) { uint32_t u = (uint32_t)x << 16; float f; memcpy(&f, &u, sizeof f); return f; }`. The contract fixes the conversion of each output to bf16 as round to nearest, ties to even: copy the `float` result into a `uint32_t` `u` with `memcpy`, add `0x7FFF` plus bit 16 of `u` (`(u >> 16) & 1`), and keep the upper 16 bits of the result. This gives the nearest bf16 value for every finite result, an even last bit on a tie, and an infinity of the right sign for a finite result beyond the bf16 range.

Make two passes over each row. In the first pass, sum the squares of the row into `NA` separate `float` accumulators held in a local array, a constant `NA` in the source: set them to zero; for each j from 0 while `j + NA <= n`, stepping by `NA`, widen `x[i * n + j + q]` and add its square to accumulator q, for every q from 0 to `NA`; add the squares of the last `n % NA` elements of the row to the accumulators as well; then add the `NA` accumulators together in a `float`. The accumulators are independent of each other, so the compiler can keep them in the lanes of a vector register. As a value to start from, not a measured or tuned value, take 8 for `NA`. The contract fixes the precision of this sum: every partial sum is a `float`, neither narrower nor wider, so do not accumulate in `double` and do not round a partial sum to bf16. The order of the additions is free as long as each square enters exactly once, and the split into `NA` sums is such an order.

Then compute the scale of the row once, from the `float` sum s: `float r = (float)(1.0 / sqrt((double)s / (double)n + (double)eps));`, with `sqrt` from `<math.h>`. These steps may be held in `double` or `float`, never in a narrower format, and the contract asks the reciprocal square root for a relative error of at most 2^-11; a correctly rounded `sqrt` and division in `double`, rounded once to `float`, stays far within that. Do not use a reciprocal square root estimate without the refinement that brings it within that bound.

In the second pass, for each j from 0 to `n`, widen `x[i * n + j]` and `w[j]` again, compute `x * r * w` with two `float` multiplications, and store the bf16 rounding of the product to `y[i * n + j]`. Round to bf16 only there: no value between the normalisation and the multiplication by the weight is rounded to bf16 or to any other 16-bit format.

Every `m` and `n` of at least 1 is handled: a row shorter than `NA` takes only the loop over the last elements, and a row whose length is no multiple of `NA` adds its remainder in the same way. `y` is only written, by the second pass, and never read, so it is not read before it is written; `x` and `w` are only read. Read every array through `uint16_t` pointers and assume no alignment beyond that of `uint16_t`.

Keep everything else of the contract: exactly one definition of `hilclaw_rmsnorm_bf16` with the prototype `void hilclaw_rmsnorm_bf16(size_t m, size_t n, float eps, const uint16_t *restrict x, const uint16_t *restrict w, uint16_t *restrict y);`, no `main`, no other external name that starts with `hilclaw_` (give the conversion functions and any other helper `static`), and no header beyond those of the C standard library (`<stddef.h>`, `<stdint.h>`, `<string.h>` and `<math.h>` are enough). Keep the `restrict` qualifiers on the parameters and on any local pointer to a row of `x` or `y`.
