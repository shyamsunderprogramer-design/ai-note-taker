"""Benchmark native OCR against a supplied local test image."""
import base64
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'backend'))
from lib.native_ocr import extract_native_text
image = Path(sys.argv[1])
start = time.perf_counter()
text = extract_native_text(base64.b64encode(image.read_bytes()).decode())
report = {'image': image.name, 'text': text, 'seconds': time.perf_counter()-start, 'available': text is not None}
Path(sys.argv[2]).write_text(json.dumps(report, indent=2))
print(json.dumps({'available': report['available'], 'seconds': report['seconds'], 'characters': len(text or '')}))
raise SystemExit(0 if report['available'] else 1)
