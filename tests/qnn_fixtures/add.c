#include <stdio.h>

#include "QnnInterface.h"
#include "QnnOpDef.h"
#include "QnnTypes.h"

#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#define OPEN(path) ((void *)LoadLibraryA(path))
#define SYMBOL(lib, name) ((void *)GetProcAddress((HMODULE)(lib), name))
#else
#include <dlfcn.h>
#define OPEN(path) dlopen(path, RTLD_NOW | RTLD_LOCAL)
#define SYMBOL(lib, name) dlsym(lib, name)
#endif

#define COUNT 4

typedef Qnn_ErrorHandle_t (*GetProviders)(const QnnInterface_t ***, uint32_t *);

static uint32_t dims[1] = {COUNT};

static Qnn_Tensor_t tensor(const char *name, Qnn_TensorType_t type)
{
    Qnn_Tensor_t t = QNN_TENSOR_INIT;
    t.version = QNN_TENSOR_VERSION_1;
    t.v1.name = name;
    t.v1.type = type;
    t.v1.dataFormat = QNN_TENSOR_DATA_FORMAT_FLAT_BUFFER;
    t.v1.dataType = QNN_DATATYPE_UFIXED_POINT_8;
    t.v1.quantizeParams.encodingDefinition = QNN_DEFINITION_DEFINED;
    t.v1.quantizeParams.quantizationEncoding = QNN_QUANTIZATION_ENCODING_SCALE_OFFSET;
    t.v1.quantizeParams.scaleOffsetEncoding.scale = 1.0f;
    t.v1.quantizeParams.scaleOffsetEncoding.offset = 0;
    t.v1.rank = 1;
    t.v1.dimensions = dims;
    t.v1.memType = QNN_TENSORMEMTYPE_RAW;
    t.v1.clientBuf.dataSize = COUNT;
    return t;
}

static int fail(const char *step, Qnn_ErrorHandle_t status)
{
    fprintf(stderr, "%s failed: %lu\n", step, (unsigned long)status);
    return 1;
}

int main(int argc, char **argv)
{
    uint8_t a[COUNT] = {1, 2, 3, 4};
    uint8_t b[COUNT] = {10, 20, 30, 40};
    uint8_t sum[COUNT] = {0};
    const QnnInterface_t **providers = NULL;
    uint32_t count = 0;
    QNN_INTERFACE_VER_TYPE qnn;
    Qnn_BackendHandle_t backend = NULL;
    Qnn_ContextHandle_t context = NULL;
    Qnn_GraphHandle_t graph = NULL;
    Qnn_ErrorHandle_t status;
    uint32_t i;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <QNN backend library>\n", argv[0]);
        return 2;
    }
    void *library = OPEN(argv[1]);
    if (library == NULL) {
        fprintf(stderr, "cannot load %s\n", argv[1]);
        return 1;
    }
    GetProviders get = (GetProviders)SYMBOL(library, "QnnInterface_getProviders");
    if (get == NULL)
        return fail("QnnInterface_getProviders lookup", 0);
    status = get(&providers, &count);
    if (status != QNN_SUCCESS || count == 0)
        return fail("QnnInterface_getProviders", status);
    for (i = 0; i < count; i++)
        if (providers[i]->apiVersion.coreApiVersion.major == QNN_API_VERSION_MAJOR)
            break;
    if (i == count)
        return fail("matching provider", 0);
    qnn = providers[i]->QNN_INTERFACE_VER_NAME;

    if ((status = qnn.backendCreate(NULL, NULL, &backend)) != QNN_SUCCESS)
        return fail("QnnBackend_create", status);
    if ((status = qnn.contextCreate(backend, NULL, NULL, &context)) != QNN_SUCCESS)
        return fail("QnnContext_create", status);
    if ((status = qnn.graphCreate(context, "add", NULL, &graph)) != QNN_SUCCESS)
        return fail("QnnGraph_create", status);

    Qnn_Tensor_t inputs[2] = {
        tensor("a", QNN_TENSOR_TYPE_APP_WRITE),
        tensor("b", QNN_TENSOR_TYPE_APP_WRITE),
    };
    Qnn_Tensor_t outputs[1] = {tensor("sum", QNN_TENSOR_TYPE_APP_READ)};
    for (i = 0; i < 2; i++)
        if ((status = qnn.tensorCreateGraphTensor(graph, &inputs[i])) != QNN_SUCCESS)
            return fail("QnnTensor_createGraphTensor", status);
    if ((status = qnn.tensorCreateGraphTensor(graph, &outputs[0])) != QNN_SUCCESS)
        return fail("QnnTensor_createGraphTensor", status);

    Qnn_OpConfig_t op = QNN_OPCONFIG_INIT;
    op.version = QNN_OPCONFIG_VERSION_1;
    op.v1.name = "add";
    op.v1.packageName = QNN_OP_PACKAGE_NAME_QTI_AISW;
    op.v1.typeName = QNN_OP_ELEMENT_WISE_ADD;
    op.v1.numOfInputs = 2;
    op.v1.inputTensors = inputs;
    op.v1.numOfOutputs = 1;
    op.v1.outputTensors = outputs;
    if ((status = qnn.graphAddNode(graph, op)) != QNN_SUCCESS)
        return fail("QnnGraph_addNode", status);
    if ((status = qnn.graphFinalize(graph, NULL, NULL)) != QNN_SUCCESS)
        return fail("QnnGraph_finalize", status);

    inputs[0].v1.clientBuf.data = a;
    inputs[1].v1.clientBuf.data = b;
    outputs[0].v1.clientBuf.data = sum;
    status = qnn.graphExecute(graph, inputs, 2, outputs, 1, NULL, NULL);
    if (status != QNN_SUCCESS)
        return fail("QnnGraph_execute", status);
    for (i = 0; i < COUNT; i++) {
        if (sum[i] != a[i] + b[i]) {
            fprintf(stderr, "element %u: %u, expected %u\n", i, sum[i], a[i] + b[i]);
            return 1;
        }
    }
    qnn.contextFree(context, NULL);
    qnn.backendFree(backend);
    printf("sum %u %u %u %u\n", sum[0], sum[1], sum[2], sum[3]);
    return 0;
}
