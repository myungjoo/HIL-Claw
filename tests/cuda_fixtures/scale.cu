#include <cstdio>

__global__ void scale(float *x, float a, int n)
{
    int i = blockIdx.x * blockDim.x + threadIdx.x;
    if (i < n)
        x[i] *= a;
}

int main()
{
    std::puts("built");
    return 0;
}
