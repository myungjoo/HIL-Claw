# loop_order_ikj

## Applies to

- kind: gemm
- dtype: fp32
- layout: row_major
- language: c

## When

Worth trying when `n` is above 1 and the kernel of an earlier attempt runs the loop over the columns of `c` outside the loop over `k`, so that its innermost loop steps down a column of `b` with a stride of `n` elements. It is a change of loop order only, so it suits a first attempt after a plain kernel has passed the check. When `n` is 1, `b` is a single column that is read contiguously in either order, and there is little to gain.

## Guidance

The matrices are stored row by row: element (i, p) of `a` is `a[i * k + p]`, element (p, j) of `b` is `b[p * n + j]`, and element (i, j) of `c` is `c[i * n + j]`, with every index of type `size_t`.

Write the product as three nested loops in the order i, p, j: the outer loop over the rows i of `c` (0 to `m`), the middle loop over p (0 to `k`), and the inner loop over the columns j of `c` (0 to `n`). In the inner loop, add `a[i * k + p] * b[p * n + j]` to `c[i * n + j]`. The inner loop then reads one row of `b` and updates one row of `c`, both at consecutive addresses. The value `a[i * k + p]` is the same for the whole inner loop: load it into a local `float` once, before that loop.

The caller leaves the content of `c` unspecified, and the kernel must not read it before writing it. For each row i, set the `n` elements of row i of `c` to zero before the loop over p starts; or write the products of the first step (p equal to 0) with a plain assignment and accumulate from p equal to 1 on. Every element of `c` is then written before it is read.

Each loop runs over the full range of its dimension, so the change leaves no remainder, and every `m`, `k` and `n` of at least 1 is handled, a dimension of 1 included. Use plain `float` reads and writes through the three pointers, which assume no alignment beyond that of `float`.

Keep everything else of the contract: exactly one definition of `hilclaw_gemm` with the prototype `void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);`, no `main`, no other external name that starts with `hilclaw_` (give any helper function `static`), and no header beyond those of the C standard library. Keep the `restrict` qualifiers, and put them on any local pointer to a row of `b` or `c`: they tell the compiler that `c` does not overlap `a` or `b`, so it may keep the loaded value of `a` in a register and vectorise the inner loop by itself.
