# register_blocking

## Applies to

- kind: gemm
- dtype: fp32
- layout: row_major
- language: c

## When

Worth trying when `m` and `n` are each above 1 and the kernel of an earlier attempt reads and writes an element of `c` in memory at every step of the loop over `k`, so that each multiply-add costs a load and a store of `c` besides the loads of `a` and `b`. When `m` is 1, only a tile of one row by a few columns applies, and the gain is limited to keeping those columns of `c` out of memory across the loop over `k`.

## Guidance

The matrices are stored row by row: element (i, p) of `a` is `a[i * k + p]`, element (p, j) of `b` is `b[p * n + j]`, and element (i, j) of `c` is `c[i * n + j]`, with every index of type `size_t`.

Compute `c` one small tile at a time: `MR` rows by `NR` columns, with `MR` and `NR` constants in the source. For a tile whose first row is `i0` and whose first column is `j0`, keep its `MR` times `NR` sums in local `float` variables, or in a small local array that the compiler can hold in registers, and set each to zero. Then run the whole loop over p, from 0 to `k`: load the `MR` values `a[(i0 + r) * k + p]` and the `NR` values `b[p * n + j0 + s]` once each, and add every product of one value of `a` and one value of `b` to its sum. After the loop over p, store each sum into its element `c[(i0 + r) * n + j0 + s]` with a plain assignment. Each loaded value of `a` is used `NR` times and each loaded value of `b` `MR` times, and `c` is touched once per element.

As a value to start from, not a measured or tuned value, take 4 for `MR` and 4 for `NR`. A tile larger than the processor's registers can hold makes the compiler move sums to memory, which takes away what the technique keeps.

`c` is only written, by the store after the loop over p, and never read, so the kernel meets the rule that `c` is not read before it is written. Run the loop over p over the full range of `k` for each tile; a tile that stopped part-way through `k` would have to read its partial sums back from `c`.

Remainders: `m` need not be a multiple of `MR`, nor `n` of `NR`, and either may be smaller than its tile size. Run the full tiles while `i0 + MR` is at most `m` and `j0 + NR` is at most `n`. Then compute the remaining columns on the right, for the rows the full tiles cover, and after them the remaining rows at the bottom, across every column, with a general path: a tile whose loop bounds are the smaller of the tile size and what is left, or a plain loop that computes one element as its sum over p and stores it. Every element of `c` must be written exactly once by one of these paths, the bottom right corner included; check the bounds for an `m` below `MR` or an `n` below `NR`, where the general path covers that whole dimension. Use plain `float` reads and writes through the three pointers, which assume no alignment beyond that of `float`.

Keep everything else of the contract: exactly one definition of `hilclaw_gemm` with the prototype `void hilclaw_gemm(size_t m, size_t k, size_t n, const float *restrict a, const float *restrict b, float *restrict c);`, no `main`, no other external name that starts with `hilclaw_` (give any helper function `static`), and no header beyond those of the C standard library. Keep the `restrict` qualifiers on the parameters and on any local pointer derived from them.
