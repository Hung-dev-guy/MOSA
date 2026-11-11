"""Local multilingual text embeddings; download is an explicit setup operation."""
from functools import lru_cache

from backend.shared.paths import PROJECT_ROOT


MODEL_NAME = 'intfloat/multilingual-e5-small'
MODEL_VERSION = MODEL_NAME + ':onnx-fp32:mean:l2:query-passage:v1'
CACHE_DIRECTORY = PROJECT_ROOT / 'instance' / 'text-search-model'


@lru_cache(maxsize=1)
def load_model(download=False):
    from fastembed import TextEmbedding
    from fastembed.common.model_description import ModelSource, PoolingType
    if not any(m['model'] == MODEL_NAME for m in TextEmbedding.list_supported_models()):
        TextEmbedding.add_custom_model(
            model=MODEL_NAME, pooling=PoolingType.MEAN, normalization=True,
            sources=ModelSource(hf=MODEL_NAME), dim=384,
            model_file='onnx/model.onnx', license='mit', size_in_gb=.47)
    return TextEmbedding(model_name=MODEL_NAME, cache_dir=str(CACHE_DIRECTORY),
                         threads=2, local_files_only=not download)


@lru_cache(maxsize=8)
def encode_documents(documents):
    return tuple(load_model().embed(['passage: ' + document for document in documents], batch_size=16))


def encode_query(query):
    return next(load_model().embed(['query: ' + query]))
