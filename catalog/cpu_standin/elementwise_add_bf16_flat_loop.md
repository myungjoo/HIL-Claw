# elementwise_add_bf16_flat_loop

## Applies to

- kind: elementwise_add
- dtype: bf16
- layout: row_major
- language: c

## When

Worth trying when the kernel of an earlier attempt runs a loop over the rows inside which it computes the index `i * n + j` of every element, or converts each element through a function call that is not inlined or through a branch, so that its innermost loop does more than load, add and store. All three operands have one shape and one layout, so only the product `m * n` matters to this technique, and it suits any shape once a plain kernel has passed the check. When `m * n` is small, the call itself dominates, and there is little to gain.

## Guidance

The three arrays hold bf16 bit patterns in `uint16_t` elements, and element (i, j) of each is at the same index `i * n + j`. Treat each of them as one array of `count = m * n` elements, a `size_t` computed once: the product is the number of elements of each array, so it fits in a `size_t`.

Convert at the boundary, inside the kernel. A bf16 pattern widens to the `float` with the same sign, exponent and leading fraction bits, exactly: put the 16 bits in the upper half of a `uint32_t` and copy that into a `float` with `memcpy`, in a `static inline` function such as `static inline float widen(uint16_t x) { uint32_t u = (uint32_t)x << 16; float f; memcpy(&f, &u, sizeof f); return f; }`. The contract fixes the conversion of each output to bf16 as round to nearest, ties to even: in a second `static inline` function, copy the `float` into a `uint32_t` `u` with `memcpy`, add `0x7FFF` plus bit 16 of `u` (`(u >> 16) & 1`), and return the upper 16 bits of the result as a `uint16_t`. This gives the nearest bf16 value for every finite sum, an even last bit on a tie, and an infinity of the right sign for a finite sum beyond the bf16 range.

Write the kernel as one loop over t from 0 to `count` whose body is `c[t] = round_bf16(widen(a[t]) + widen(b[t]));`: two widenings, one `float` addition and one rounding, with no branch and no call that stays a call. Such a body loads both inputs and stores the output at consecutive addresses, and it leaves the compiler a loop it can vectorise.

The contract asks for each element of `c` to be the correctly rounded bf16 value of the exact sum, and a `float` addition followed by the rounding above gives exactly that value, including the infinity of a sum beyond the bf16 range, +0 for the sum of a value and its negation, and -0 for the sum of two negative zeros. So do not add in a format narrower than `float`, such as a 16-bit format, and do not replace the rounding by keeping the upper 16 bits without the added `0x7FFF` and bit 16, which truncates instead of rounding.

Every `m` and `n` of at least 1 is handled, since the loop runs over every one of the `m * n` elements whatever their split into rows. `c` is only written, by the store of the loop body, and never read, so it is not read before it is written; `a` and `b` are only read. Read the arrays through `uint16_t` pointers and assume no alignment beyond that of `uint16_t`.

Keep everything else of the contract: exactly one definition of `hilclaw_elementwise_add_bf16` with the prototype `void hilclaw_elementwise_add_bf16(size_t m, size_t n, const uint16_t *restrict a, const uint16_t *restrict b, uint16_t *restrict c);`, no `main`, no other external name that starts with `hilclaw_` (give the conversion functions and any other helper `static`), and no header beyond those of the C standard library (`<stddef.h>`, `<stdint.h>` and `<string.h>` are enough). Keep the `restrict` qualifiers on the parameters and on any local pointer derived from them.
