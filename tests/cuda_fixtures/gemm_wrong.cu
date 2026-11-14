/* Test fixture: gemm.cu with every element of c off by 1, a kernel the verification run judges a fail. */
#define GEMM_WRONG 1
#include "gemm.cu"
