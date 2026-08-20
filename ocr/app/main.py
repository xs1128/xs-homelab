from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import HTMLResponse
from PIL import Image
import io
import os
import tempfile
import pdf2image
import yaml
from rapidocr_onnxruntime import RapidOCR
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

app = FastAPI(title="OCR Service (RapidOCR)", version="2.0.0")

# --- Load engines ---
MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/app/models"))

# Use importlib to find the rapidocr_onnxruntime package location dynamically
def _get_pkg_models_dir() -> Path:
    import rapidocr_onnxruntime
    pkg_dir = Path(rapidocr_onnxruntime.__file__).parent
    return pkg_dir / "models"

PKG_MODELS = _get_pkg_models_dir()

def find_package_model(name: str) -> Path:
    """Find a model bundled with rapidocr_onnxruntime package."""
    p = PKG_MODELS / name
    if p.exists():
        return p
    raise FileNotFoundError(f"Package model {name} not found at {p}")


def build_config(rec_model_path: str) -> dict:
    return {
        "Global": {
            "text_score": 0.4,
            "use_det": True,
            "use_cls": True,
            "use_rec": True,
            "print_verbose": False,
            "min_height": 20,
            "width_height_ratio": 10,
            "max_side_len": 4096,
            "min_side_len": 20,
            "return_word_box": False,
            "intra_op_num_threads": -1,
            "inter_op_num_threads": -1,
        },
        "Det": {
            "intra_op_num_threads": -1,
            "inter_op_num_threads": -1,
            "use_cuda": False,
            "use_dml": False,
            "model_path": str(find_package_model("ch_PP-OCRv4_det_infer.onnx")),
            "limit_side_len": 960,
            "limit_type": "min",
            "std": [0.5, 0.5, 0.5],
            "mean": [0.5, 0.5, 0.5],
            "thresh": 0.2,
            "box_thresh": 0.3,
            "max_candidates": 2000,
            "unclip_ratio": 1.6,
            "use_dilation": True,
            "score_mode": "fast",
        },
        "Cls": {
            "intra_op_num_threads": -1,
            "inter_op_num_threads": -1,
            "use_cuda": False,
            "use_dml": False,
            "model_path": str(find_package_model("ch_ppocr_mobile_v2.0_cls_infer.onnx")),
            "cls_image_shape": [3, 48, 192],
            "cls_batch_num": 6,
            "cls_thresh": 0.9,
            "label_list": ["0", "180"],
        },
        "Rec": {
            "intra_op_num_threads": -1,
            "inter_op_num_threads": -1,
            "use_cuda": False,
            "use_dml": False,
            "model_path": rec_model_path,
            "rec_img_shape": [3, 48, 320],
            "rec_batch_num": 6,
        },
    }


def _init_engine(config_dict: dict) -> RapidOCR:
    cfg_path = Path("/tmp") / f"ocr_cfg_{id(config_dict)}.yaml"
    with open(cfg_path, "w") as f:
        yaml.dump(config_dict, f)
    return RapidOCR(config_path=str(cfg_path))


# Engine 1: Default CJK + English (ch_PP-OCRv4_rec)
engine_cjk = _init_engine(build_config(
    str(find_package_model("ch_PP-OCRv4_rec_infer.onnx"))
))

# Engine 2: Japanese (japan_PP-OCRv3_rec)
jp_model = MODELS_DIR / "japan_PP-OCRv3_rec_infer.onnx"
engine_jp = None
if jp_model.exists():
    engine_jp = _init_engine(build_config(str(jp_model)))

print(f"Engine CJK+EN: loaded ({'OK' if engine_cjk else 'FAIL'})")
print(f"Engine JP: {'loaded' if engine_jp else 'not found, skipping'}")


MAX_SIDE = 3000  # max pixel dimension before OCR


def preprocess_image(img: Image.Image) -> Image.Image:
    """Resize very large images to a manageable size while preserving detail."""
    if img.mode != "RGB":
        img = img.convert("RGB")
    w, h = img.size
    if max(w, h) > MAX_SIDE:
        ratio = MAX_SIDE / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)
    return img


def _sort_reading_order(results: list) -> list:
    """Sort OCR results by reading order: top-to-bottom, left-to-right within same line.

    Returns list of (line_text,) tuples — one per visual line, with fragments joined.
    """
    if not results:
        return []

    def top_y(box):
        return (box[0][1] + box[1][1]) / 2

    def mid_x(box):
        return (box[0][0] + box[2][0]) / 2

    def box_height(box):
        return abs(box[0][1] - box[3][1])

    sorted_by_y = sorted(results, key=lambda r: top_y(r[0]))
    lines = []
    current_line = [sorted_by_y[0]]
    current_y = top_y(sorted_by_y[0][0])

    for item in sorted_by_y[1:]:
        item_y = top_y(item[0])
        h = box_height(item[0])
        # Threshold: cap at 40px to avoid merging across paragraph breaks
        threshold = min(h * 1.5, 40)
        if abs(item_y - current_y) < threshold:
            current_line.append(item)
        else:
            current_line.sort(key=lambda r: mid_x(r[0]))
            lines.append(current_line)
            current_line = [item]
            current_y = item_y

    current_line.sort(key=lambda r: mid_x(r[0]))
    lines.append(current_line)

    return lines


def ocr_image(img: Image.Image) -> str:
    """Run OCR on a PIL Image using both engines, merge results."""
    img = preprocess_image(img)
    img_array = img

    def run_engine(engine, label):
        try:
            result, elapse = engine(img_array)
            if not result:
                return label, [], 0
            lines = _sort_reading_order(result)
            # Join fragments within each visual line (no space for CJK)
            texts = ["".join(item[1] for item in line) for line in lines]
            total = sum(len(t) for t in texts)
            return label, texts, total
        except Exception:
            return label, [], 0

    engines = [("cjk", engine_cjk)]
    if engine_jp:
        engines.append(("jp", engine_jp))

    results = {}
    with ThreadPoolExecutor(max_workers=len(engines)) as pool:
        futures = {pool.submit(run_engine, eng, label): label for label, eng in engines}
        for future in as_completed(futures):
            label, texts, total = future.result()
            results[label] = (texts, total)

    cjk_texts, cjk_total = results.get("cjk", ([], 0))
    jp_texts, jp_total = results.get("jp", ([], 0))

    if not engine_jp or not jp_texts:
        return "\n".join(cjk_texts) if cjk_texts else ""

    # Only use JP engine when CJK found very little text (heavy hiragana/katakana)
    if cjk_total < 20 and jp_total > cjk_total:
        return "\n".join(jp_texts)
    else:
        return "\n".join(cjk_texts)


def extract_text(data: bytes, filename: str) -> str:
    """Extract text from image or PDF bytes."""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext == "pdf":
        with tempfile.TemporaryDirectory() as tmpdir:
            images = pdf2image.convert_from_bytes(data, dpi=300)
            pages = []
            for i, img in enumerate(images):
                text = ocr_image(img)
                if text.strip():
                    pages.append(f"--- Page {i + 1} ---\n{text}")
            return "\n\n".join(pages) if pages else ""

    try:
        img = Image.open(io.BytesIO(data))
        return ocr_image(img)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Cannot process image: {e}")


@app.get("/", response_class=HTMLResponse)
async def web_ui():
    return HTML_CONTENT


@app.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    """OCR an uploaded image or PDF file. Returns extracted text."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")

    try:
        text = extract_text(data, file.filename)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {e}")

    return {"text": text, "filename": file.filename}


@app.get("/languages")
async def list_languages():
    """List available OCR languages."""
    langs = ["English", "Chinese (Simplified)", "Chinese (Traditional)"]
    if engine_jp:
        langs.append("Japanese")
    return {"languages": langs, "auto_detect": True}


HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>OCR Service</title>
<style>
  :root { --bg: #0a0a0b; --card: #141416; --border: #2a2a2e; --text: #e4e4e7; --muted: #71717a; --accent: #22c55e; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
  .container { max-width: 720px; margin: 0 auto; padding: 2rem 1rem; }
  h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
  .sub { color: var(--muted); font-size: 0.875rem; margin-bottom: 2rem; }
  .dropzone {
    border: 2px dashed var(--border); border-radius: 12px; padding: 3rem 2rem;
    text-align: center; cursor: pointer; transition: border-color 0.2s, background 0.2s;
    position: relative;
  }
  .dropzone:hover, .dropzone.dragover { border-color: var(--accent); background: rgba(34,197,94,0.04); }
  .dropzone input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
  .dropzone p { color: var(--muted); }
  .dropzone .icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .preview { margin-top: 1rem; }
  .preview img { max-width: 100%; max-height: 300px; border-radius: 8px; border: 1px solid var(--border); }
  .controls { display: flex; gap: 1rem; margin-top: 1rem; align-items: center; flex-wrap: wrap; }
  select {
    background: var(--card); color: var(--text); border: 1px solid var(--border);
    border-radius: 8px; padding: 0.5rem 1rem; font-size: 0.875rem;
  }
  button {
    background: var(--accent); color: #000; border: none; border-radius: 8px;
    padding: 0.5rem 1.5rem; font-size: 0.875rem; font-weight: 600; cursor: pointer;
    transition: opacity 0.2s;
  }
  button:hover { opacity: 0.9; }
  button:disabled { opacity: 0.4; cursor: not-allowed; }
  .result {
    margin-top: 1.5rem; background: var(--card); border: 1px solid var(--border);
    border-radius: 12px; padding: 1rem;
  }
  .result pre {
    white-space: pre-wrap; word-break: break-word; font-family: 'SF Mono', 'Fira Code', monospace;
    font-size: 0.875rem; line-height: 1.6; max-height: 500px; overflow-y: auto;
  }
  .result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem; }
  .result-header span { color: var(--muted); font-size: 0.8rem; }
  .copy-btn {
    background: transparent; color: var(--muted); border: 1px solid var(--border);
    padding: 0.25rem 0.75rem; font-size: 0.75rem;
  }
  .copy-btn:hover { color: var(--text); border-color: var(--text); }
  .spinner { display: inline-block; width: 1rem; height: 1rem; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.6s linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .badge { background: var(--accent); color: #000; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.7rem; font-weight: 600; }
</style>
</head>
<body>
<div class="container">
  <h1>⚡ OCR</h1>
  <p class="sub">RapidOCR — drop an image or PDF, get text instantly (auto language detection)</p>

  <div class="dropzone" id="dropzone">
    <input type="file" id="fileInput" accept="image/*,.pdf" />
    <div class="icon">📄</div>
    <p>Drop image or PDF here, or click to browse</p>
    <div class="preview" id="preview"></div>
  </div>

  <div class="controls">
    <span class="badge">AUTO</span>
    <span style="color: var(--muted); font-size: 0.8rem;">English · 中文 · 日本語</span>
    <button id="ocrBtn" disabled>Extract Text</button>
    <span id="status"></span>
  </div>

  <div class="result" id="result" style="display:none">
    <div class="result-header">
      <span id="resultInfo"></span>
      <button class="copy-btn" onclick="copyText()">Copy</button>
    </div>
    <pre id="resultText"></pre>
  </div>
</div>

<script>
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const ocrBtn = document.getElementById('ocrBtn');
const preview = document.getElementById('preview');
const result = document.getElementById('result');
const resultText = document.getElementById('resultText');
const resultInfo = document.getElementById('resultInfo');
const status = document.getElementById('status');
let selectedFile = null;

fileInput.addEventListener('change', e => { if (e.target.files[0]) setFile(e.target.files[0]); });
dropzone.addEventListener('dragover', e => { e.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', e => {
  e.preventDefault(); dropzone.classList.remove('dragover');
  if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
});

function setFile(file) {
  selectedFile = file;
  ocrBtn.disabled = false;
  preview.innerHTML = '';
  if (file.type.startsWith('image/')) {
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    preview.appendChild(img);
  } else {
    preview.innerHTML = '<p>📎 ' + file.name + ' (' + (file.size/1024).toFixed(1) + ' KB)</p>';
  }
  result.style.display = 'none';
}

ocrBtn.addEventListener('click', async () => {
  if (!selectedFile) return;
  const fd = new FormData();
  fd.append('file', selectedFile);
  ocrBtn.disabled = true;
  ocrBtn.textContent = '';
  status.innerHTML = '<span class="spinner"></span>';
  try {
    const res = await fetch('/ocr', { method: 'POST', body: fd });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'OCR failed');
    resultText.textContent = data.text || '(no text detected)';
    resultInfo.textContent = data.filename;
    result.style.display = 'block';
  } catch (e) {
    resultText.textContent = 'Error: ' + e.message;
    result.style.display = 'block';
  } finally {
    ocrBtn.disabled = false;
    ocrBtn.textContent = 'Extract Text';
    status.innerHTML = '';
  }
});

function copyText() {
  navigator.clipboard.writeText(resultText.textContent).then(() => {
    document.querySelector('.copy-btn').textContent = 'Copied!';
    setTimeout(() => document.querySelector('.copy-btn').textContent = 'Copy', 1500);
  });
}
</script>
</body>
</html>
"""
