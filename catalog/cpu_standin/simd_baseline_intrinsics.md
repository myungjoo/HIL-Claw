# simd_baseline_intrinsics

## Applies to

- kind: gemm
- dtype: fp32
- layout: row_major
- language: c

## When

Worth trying when `n` is at least 4, so that a row of `c` holds at least one group of four adjacent elements, and the more so the larger `n` is against 4. It suits an attempt whose kernel is plain scalar code and has passed the check, whatever `m` is, `m` of 1 included, since the vectors run along a row of `c`. When `n` is below 4, every element goes through the scalar path and there is nothing to gain.

## Guidance

The matrices are stored row by row: element (i, p) of `a` is `a[i * k + p]`, element (p, j) of `b` is `b[p * n + j]`, and element (i, j) of `c` is `c[i * n + j]`, with every index of type `size_t`.

Compute four adjacent elements of a row of `c` at once, in a 128-bit vector of four `float` values. For each row i of `c` and each group of four columns starting at j, while `j + 4` is at most `n`: set a vector sum to zero; for every p from 0 to `k`, multiply the value `a[i * k + p]`, copied into all four lanes, by the four values of `b` that start at `b + p * n + j`, and add the product to the sum; after the loop over p, store the sum to the four elements of `c` that start at `c + i * n + j`. Then compute the remaining columns of the row, from the last j on to `n`, with the scalar path. `c` is only written by these stores and never read, so it is not read before it is written.

Select the code for the processor with the preprocessor, in the kernel source:

- Under `#if defined(__x86_64__)`, include `<immintrin.h>` and use SSE and SSE2 intrinsics only: `_mm_setzero_ps` for the zero sum, `_mm_set1_ps` to copy the value of `a` into four lanes, `_mm_loadu_ps` to load four values of `b`, `_mm_mul_ps` and then `_mm_add_ps`, and `_mm_storeu_ps` to store four elements of `c`. Do not use an intrinsic of SSE3 or of any later extension, since it is not part of the x86-64 baseline.
- Under `#elif defined(__aarch64__)`, include `<arm_neon.h>` and use Advanced SIMD: `vdupq_n_f32` for the zero sum and to copy the value of `a` into four lanes, `vld1q_f32` to load four values of `b`, `vfmaq_f32` for the explicit fused multiply-add of the sum, and `vst1q_f32` to store four elements of `c`.
- Under `#else`, use the scalar path for the whole row, so the kernel builds and computes the product on any other processor.

Put each `#include` inside its own branch, so that no processor sees a header it lacks. The scalar path computes one element at a time: a `float` sum set to zero, the products `a[i * k + p] * b[p * n + j]` added over every p, and the sum stored to `c[i * n + j]`. Write it once, as a `static` function or a loop shared by the three branches, and use it for the remaining columns under the first two branches too. With it, every `m`, `k` and `n` of at least 1 is handled: an `n` below 4 runs the scalar path only, and `m` and `k` are walked over their full range in every path.

Use only the unaligned loads and stores, `_mm_loadu_ps` and `_mm_storeu_ps` on x86-64 and `vld1q_f32` and `vst1q_f32` on arm64: the caller promises no alignment beyond that of `float`, so `b + p * n + j` and `c + i * n + j` may sit at any multiple of four bytes, and `_mm_load_ps` or `_mm_store_ps` could then fault. Do not give a function a target attribute, and do not use any instruction set beyond the baseline of each processor: SSE2 is part of every x86-64 processor and Advanced SIMD of every arm64 processor, so this code builds and runs everywhere with the fixed build settings and needs no check of the processor at run time.

The fused multiply-add on arm64 rounds once per step, where the x86-64 path and the scalar path round after the multiply and again after the add, so the results of the three paths may differ in their last bits; whether a result is close enough is the check's tolerance, not something the kernel can promise.

Keep everything else of the contract: exactly one definition of `hilclaw_gemm` with the prototype `void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);`, no `main`, no other external name that starts with `hilclaw_` (give any helper function `static`), and no header beyond those of the C standard library and the two intrinsics headers named here.
