# swiglu_bf16_flat_loop

## Applies to

- kind: swiglu
- dtype: bf16
- layout: row_major
- language: c

## When

Worth trying when the kernel of an earlier attempt runs a loop over the rows inside which it computes the index `i * n + j` of every element, computes the SiLU value in `double` with `exp` where `float` suffices, or rounds the SiLU value to bf16 before the multiplication by `up`, which the contract does not allow. All three operands have one shape and one layout, so only the product `m * n` matters to this technique, and it suits a first attempt after a plain kernel has passed the check.

## Guidance

The three arrays hold bf16 bit patterns in `uint16_t` elements, and element (i, j) of each is at the same index `i * n + j`. Treat each of them as one array of `count = m * n` elements, a `size_t` computed once: the product is the number of elements of each array, so it fits in a `size_t`. The kernel computes out = silu(gate) * up for each element, with silu(g) = g / (1 + e^-g); `gate` is the operand of SiLU and `up` the other factor, and swapping them computes something else.

Convert at the boundary, inside the kernel. A bf16 pattern widens to the `float` with the same sign, exponent and leading fraction bits, exactly: put the 16 bits in the upper half of a `uint32_t` and copy that into a `float` with `memcpy`, in a `static inline` function such as `static inline float widen(uint16_t x) { uint32_t u = (uint32_t)x << 16; float f; memcpy(&f, &u, sizeof f); return f; }`. The contract fixes the conversion of each output to bf16 as round to nearest, ties to even: in a second `static inline` function, copy the `float` value into a `uint32_t` `u` with `memcpy`, add `0x7FFF` plus bit 16 of `u` (`(u >> 16) & 1`), and return the upper 16 bits of the result as a `uint16_t`.

Write the kernel as one loop over t from 0 to `count`. In its body, widen `gate[t]` to `g` and `up[t]` to `u`, compute `float p = g * u;`, `float e = expf(-g);` with `expf` from `<math.h>`, and `float v = p / (1.0f + e);`, and store the bf16 rounding of `v` to `out[t]`. Multiplying `g` by `u` first and dividing once by `1 + e^-g` is an association the contract allows, and it keeps the body to one exponential, one multiplication, one addition and one division.

Keep every intermediate value a `float` (or a wider format), and round to bf16 only the final `v`: neither the exponential, nor `1 + e`, nor the SiLU value, nor the product may be rounded to bf16 or to any other 16-bit format. The contract asks the value `v` to be within a relative 2^-11 of the exact silu(g) * u over its input domain, and this evaluation with correctly rounded `float` operations meets that bound whenever the exponential is within a relative 2^-12 of e^-g over that domain. The contract names no library as meeting that accuracy: the kernel meets the bound where the `expf` it is built with is that accurate. Do not replace it by an estimate coarser than 2^-12, such as an exponential built from the bits of the argument without a refinement.

Every `m` and `n` of at least 1 is handled, since the loop runs over every one of the `m * n` elements whatever their split into rows. `out` is only written, by the store of the loop body, and never read, so it is not read before it is written; `gate` and `up` are only read. Read the arrays through `uint16_t` pointers and assume no alignment beyond that of `uint16_t`.

Keep everything else of the contract: exactly one definition of `hilclaw_swiglu_bf16` with the prototype `void hilclaw_swiglu_bf16(size_t m, size_t n, const uint16_t *restrict gate, const uint16_t *restrict up, uint16_t *restrict out);`, no `main`, no other external name that starts with `hilclaw_` (give the conversion functions and any other helper `static`), and no header beyond those of the C standard library (`<stddef.h>`, `<stdint.h>`, `<string.h>` and `<math.h>` are enough). Keep the `restrict` qualifiers on the parameters and on any local pointer derived from them.
