# cache_blocking

## Applies to

- kind: gemm
- dtype: fp32
- layout: row_major
- language: c

## When

Worth trying when `m` is above 1 and `b`, of `k` times `n` elements, is too large to stay in the processor's caches while the rows of `a` pass over it, so that each row of `c` reads the whole of `b` again from memory. It suits an attempt that already runs its loops in the order i, p, j (rows of `c`, then `k`, then columns of `c`) and has passed the check. When `m` is 1, each element of `b` is used once, and splitting the loops into blocks has little reuse to keep in cache.

## Guidance

The matrices are stored row by row: element (i, p) of `a` is `a[i * k + p]`, element (p, j) of `b` is `b[p * n + j]`, and element (i, j) of `c` is `c[i * n + j]`, with every index of type `size_t`.

Start from three nested loops in the order i, p, j: rows i of `c` (0 to `m`), then p (0 to `k`), then columns j of `c` (0 to `n`), the inner loop adding `a[i * k + p] * b[p * n + j]` to `c[i * n + j]`. Then split each loop into blocks. Choose three block sizes, `MB` for the rows of `c`, `KB` for `k` and `NB` for the columns of `c`, as constants in the source (an `enum` or `static const size_t` values). Add three outer loops that step a block start by its block size: `j0` from 0 to `n` by `NB`, inside it `p0` from 0 to `k` by `KB`, inside it `i0` from 0 to `m` by `MB`. Inside those, run the i, p, j loops over one block only: i from `i0` to its block end, p from `p0` to its block end, j from `j0` to its block end. The block of `b` (rows `p0` on, columns `j0` on) is then used again by every row of the `i0` blocks while it may still be in cache, and the inner loop still walks a row of `b` and a row of `c` at consecutive addresses.

As a value to start from, not a measured or tuned value, take 64 for each of `MB`, `KB` and `NB`. Keep them in the source; do not read them from the environment or ask for them at build time.

Remainders: a dimension need not be a multiple of its block size, and may be smaller than it. Compute each block end as the smaller of the block start plus the block size and the dimension, for example `size_t i1 = (m - i0 < MB) ? m : i0 + MB;`, and run the inner loops up to it. The last block of each dimension is then shorter, a dimension smaller than its block size gives one short block, and every `m`, `k` and `n` of at least 1 is handled.

The kernel must not read `c` before writing it, and the blocks over `k` add into `c` across several passes. So set all `m` times `n` elements of `c` to zero before the block loops start, or set the part of `c` that a block covers to zero when that block runs with `p0` equal to 0. Every element of `c` is then written before it is read. Use plain `float` reads and writes through the three pointers, which assume no alignment beyond that of `float`.

Keep everything else of the contract: exactly one definition of `hilclaw_gemm` with the prototype `void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);`, no `main`, no other external name that starts with `hilclaw_` (give any helper function `static`), and no header beyond those of the C standard library. Keep the `restrict` qualifiers on the parameters and on any local pointer derived from them.
