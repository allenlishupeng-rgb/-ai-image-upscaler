import base64
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
import uuid
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

ROOT = Path(__file__).resolve().parent
JOBS = ROOT / "jobs"
VENDOR = ROOT / "vendor" / "realesrgan"
EXE = VENDOR / "realesrgan-ncnn-vulkan.exe"
MODELS = {
    "photo": "realesrgan-x4plus",
    "clean": "realesrgan-x4plus",
    "anime": "realesrgan-x4plus-anime",
}

class UpscalerHandler(SimpleHTTPRequestHandler):
    server_version = "AIUpscaler/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if self.path == "/api/health":
            self.send_json({
                "ok": EXE.exists(),
                "engine": "Real-ESRGAN NCNN Vulkan",
                "exe": str(EXE),
                "models": MODELS,
            })
            return
        return super().do_GET()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_POST(self):
        if self.path != "/api/upscale":
            self.send_error(404)
            return
        try:
            self.send_json(upscale(self.read_json()))
        except Exception as exc:
            self.send_json({"ok": False, "error": str(exc)}, status=500)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            raise ValueError("Empty request")
        if length > 220 * 1024 * 1024:
            raise ValueError("Image payload is too large")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def end_headers(self):
        self.send_cors_headers()
        super().end_headers()

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

def upscale(payload):
    if not EXE.exists():
        raise RuntimeError("Real-ESRGAN engine is not installed. Download vendor/realesrgan first.")
    scale = int(payload.get("scale", 4))
    if scale not in (2, 3, 4):
        raise ValueError("Scale must be 2, 3, or 4")
    model_key = payload.get("model", "photo")
    model = MODELS.get(model_key, MODELS["photo"])
    ensure_model_exists(model)
    filename = safe_name(payload.get("filename") or "input.png")
    encoded = payload.get("image")
    if not encoded:
        raise ValueError("Missing image")
    if "," in encoded:
        encoded = encoded.split(",", 1)[1]
    image_bytes = base64.b64decode(encoded)
    job = JOBS / time.strftime("%Y%m%d-%H%M%S") / uuid.uuid4().hex
    job.mkdir(parents=True, exist_ok=True)
    input_path = job / filename
    output_path = job / "output.png"
    input_path.write_bytes(image_bytes)
    completed = subprocess.run([
        str(EXE), "-i", str(input_path), "-o", str(output_path),
        "-n", model, "-s", str(scale), "-t", "256", "-f", "png",
    ], cwd=str(VENDOR), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
       timeout=1800, check=False)
    if completed.returncode != 0 or not output_path.exists():
        message = completed.stderr.strip() or completed.stdout.strip() or "Real-ESRGAN failed"
        raise RuntimeError(message)
    result_bytes = output_path.read_bytes()
    return {
        "ok": True,
        "filename": output_name(filename, scale, model_key),
        "mime": "image/png",
        "image": base64.b64encode(result_bytes).decode("ascii"),
        "bytes": len(result_bytes),
        "log": (completed.stderr or completed.stdout)[-4000:],
    }

def safe_name(name):
    stem, ext = os.path.splitext(Path(name).name)
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._") or "input"
    ext = ext.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"
    return stem[:80] + ext

def ensure_model_exists(model):
    model_dir = VENDOR / "models"
    param = model_dir / f"{model}.param"
    binary = model_dir / f"{model}.bin"
    if not param.exists() or not binary.exists():
        available = sorted(path.stem for path in model_dir.glob("*.param"))
        raise RuntimeError("模型文件不存在：" f"{model}。当前可用模型：{', '.join(available) or '无'}")

def output_name(name, scale, model):
    stem = Path(name).stem or "upscaled"
    return f"{stem}_AI_{model}_{scale}x.png"

def main():
    JOBS.mkdir(exist_ok=True)
    mimetypes.add_type("application/javascript", ".js")
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5173
    server = ThreadingHTTPServer(("127.0.0.1", port), UpscalerHandler)
    print(f"AI upscaler running at http://localhost:{port}/index.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
