"""Download and verify the local text model before serving semantic search."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.data_infrastructure.adapters.text_embedding_adapter import load_model, MODEL_NAME


if __name__ == '__main__':
    try:
        model = load_model()
    except Exception:
        model = load_model(download=True)
    vector = next(model.embed(['query: Tìm văn phòng phẩm để ghi chép']))
    assert len(vector) == 384
    print(f'Ready: {MODEL_NAME} ({len(vector)} dimensions).')
