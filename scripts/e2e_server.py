import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app import create_app

runtime=ROOT/'.test-runtime'
runtime.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(dir=runtime) as tmp:
    app=create_app({'DATABASE':str(Path(tmp)/'e2e.sqlite'),'SECRET_KEY':'e2e-only','DEMO_MODE':True})
    app.run(host='127.0.0.1',port=5099,debug=False)
