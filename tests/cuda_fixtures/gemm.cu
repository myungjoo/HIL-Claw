/*
 * Test fixture: a kernel of the fp32 gemm contract in the language cuda
 * (ADR-0207 decision 4), placed by a test. One thread per element of c, 16 x 16
 * threads a block, launched on the default stream; a, b and c are device
 * pointers. With GEMM_WRONG defined to 1 (gemm_wrong.cu) it adds 1 to every
 * element of c, so the verification run judges it a fail.
 */
#include <cstddef>

#ifndef GEMM_WRONG
#define GEMM_WRONG 0
#endif

#define SIDE 16

__global__ static void product(size_t m, size_t k, size_t n, const float *a, const float *b, float *c)
{
    size_t i = (size_t)blockIdx.y * SIDE + threadIdx.y;
    size_t j = (size_t)blockIdx.x * SIDE + threadIdx.x;
    float sum = 0.0f;
    size_t p;

    if (i >= m || j >= n)
        return;
    for (p = 0; p < k; p++)
        sum += a[i * k + p] * b[p * n + j];
    c[i * n + j] = GEMM_WRONG ? sum + 1.0f : sum;
}

extern "C" void hilclaw_gemm(size_t m, size_t k, size_t n, const float *a, const float *b, float *c)
{
    dim3 threads(SIDE, SIDE);
    dim3 blocks((unsigned)((n + SIDE - 1) / SIDE), (unsigned)((m + SIDE - 1) / SIDE));

    product<<<blocks, threads>>>(m, k, n, a, b, c);
}
