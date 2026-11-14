/* Test fixture: a kernel of the fp32 gemm contract in the language cuda that ends its process with status 3 before any report is complete. */
#include <cstddef>
#include <cstdlib>

extern "C" void hilclaw_gemm(size_t m, size_t k, size_t n, const float *a, const float *b, float *c)
{
    (void)m;
    (void)k;
    (void)n;
    (void)a;
    (void)b;
    (void)c;
    std::exit(3);
}
