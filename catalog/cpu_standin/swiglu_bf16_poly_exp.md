# swiglu_bf16_poly_exp

## Applies to

- kind: swiglu
- dtype: bf16
- layout: row_major
- language: c

## When

Worth trying when an earlier attempt that walks the `m * n` elements in one contiguous loop and calls `expf` once per element has passed the check, and `m * n` is large. A call to a library function in the loop body generally keeps the compiler from vectorising that loop, and the exponential is the costliest step of each element. When `m * n` is small, the call of the kernel itself dominates, and there is little to gain.

## Guidance

The three arrays hold bf16 bit patterns in `uint16_t` elements, and element (i, j) of each is at the same index `i * n + j`. Treat each of them as one array of `count = m * n` elements, a `size_t` computed once: the product is the number of elements of each array, so it fits in a `size_t`. The kernel computes out = silu(gate) * up for each element, with silu(g) = g / (1 + e^-g); `gate` is the operand of SiLU and `up` the other factor, and swapping them computes something else.

Convert at the boundary, inside the kernel. A bf16 pattern widens to the `float` with the same sign, exponent and leading fraction bits, exactly: put the 16 bits in the upper half of a `uint32_t` and copy that into a `float` with `memcpy`, in a `static inline` function such as `static inline float widen(uint16_t x) { uint32_t u = (uint32_t)x << 16; float f; memcpy(&f, &u, sizeof f); return f; }`. The contract fixes the conversion of each output to bf16 as round to nearest, ties to even: in a second `static inline` function, copy the `float` value into a `uint32_t` `u` with `memcpy`, add `0x7FFF` plus bit 16 of `u` (`(u >> 16) & 1`), and return the upper 16 bits of the result as a `uint16_t`.

Write the kernel as one loop over t from 0 to `count`. In its body, widen `gate[t]` to `g` and `up[t]` to `u`, compute `e`, an approximation of e^-g, with the inline steps below, then `float v = (g * u) / (1.0f + e);`, and store the bf16 rounding of `v` to `out[t]`. Put the steps in a `static inline` function so that the body holds no call that stays a call.

The exponential, in `float` throughout, as e^-g = 2^s with s = -g * log2(e):

1. `float s = -g * 1.44269504f;`, the `float` nearest to log2(e).
2. Limit s to the range [-126, 126]: `s = s < 126.0f ? s : 126.0f;` then `s = s > -126.0f ? s : -126.0f;`. Within the contract's input domain s already lies in that range; the limit keeps the conversion of the next step defined for every input, since C leaves the conversion of an out-of-range `float` to an integer undefined.
3. `int k = (int)s;`, which truncates toward zero, and `float f = s - (float)k;`. f lies strictly between -1 and 1, and this subtraction is exact.
4. Approximate 2^f = e^y with `float y = f * 0.693147182f;`, the `float` nearest to ln(2), and the polynomial 1 + y + y^2/2 + y^3/6 + y^4/24 + y^5/120 + y^6/720 + y^7/5040 in Horner form, with each coefficient written as a `float` constant.
5. Scale by 2^k: form the `float` whose bits are `(uint32_t)(k + 127) << 23`, with `memcpy`, and multiply the polynomial by it. With k between -126 and 126 that `float` is the normal value 2^k.

The steps hold no branch: the two limits are selections that the compiler can turn into lane-wise minimum and maximum operations, so the whole loop body is open to vectorisation.

Keep every intermediate value a `float` (or a wider format), and round to bf16 only the final `v`: neither the exponential, nor `1 + e`, nor the SiLU value, nor the product may be rounded to bf16 or to any other 16-bit format. The contract asks the value `v` to be within a relative 2^-11 of the exact silu(g) * u over its input domain, and the evaluation `(g * u) / (1 + e)` with correctly rounded `float` operations meets that bound whenever `e` is within a relative 2^-12 of e^-g. These steps stay well within 2^-12 there: the polynomial of degree 7 on |y| < ln(2) errs by a relative amount below 2^-17, and the rounding of s and of the two constants adds an amount of the same order. Do not shorten the polynomial or replace these steps by an estimate built from the bits of the argument alone without first checking that the relative error stays within 2^-12 for every |g| up to 126 * ln(2), about 87.34.

Every `m` and `n` of at least 1 is handled, since the loop runs over every one of the `m * n` elements whatever their split into rows. `out` is only written, by the store of the loop body, and never read, so it is not read before it is written; `gate` and `up` are only read. Read the arrays through `uint16_t` pointers and assume no alignment beyond that of `uint16_t`.

Keep everything else of the contract: exactly one definition of `hilclaw_swiglu_bf16` with the prototype `void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out);`, no `main`, no other external name that starts with `hilclaw_` (give the conversion functions, the exponential and any other helper `static`), and no header beyond those of the C standard library (`<stddef.h>`, `<stdint.h>` and `<string.h>` are enough). Keep the `restrict` qualifiers on the parameters and on any local pointer derived from them.
