__global__ void broken(float *x {
    x[threadIdx.x] = 0.0f;
}
