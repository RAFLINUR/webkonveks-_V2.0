"""
Remove background minimalis berbasis model u2net.

Dipakai sebagai pengganti paket `rembg` agar dependency yang perlu
di-bundle jauh lebih kecil (hanya onnxruntime + numpy + pillow),
sehingga muat di batas ukuran function Vercel.

Hanya mengimplementasikan jalur yang dipakai aplikasi ini:
remove(img) -> PIL Image RGBA (naive cutout), tanpa alpha matting.
"""

import hashlib
import os
import urllib.request

import numpy as np
import onnxruntime as ort
from PIL import Image
from PIL import ImageOps

ort.set_default_logger_severity(3)

_MODEL_NAME = "u2net.onnx"
_MODEL_URL = (
    "https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx"
)
_MODEL_MD5 = "60024c5c889badc19c04ad937298a77b"

_MEAN = (0.485, 0.456, 0.406)
_STD = (0.229, 0.224, 0.225)
_INPUT_SIZE = (320, 320)

_session = None


def _u2net_home():
    return os.path.expanduser(
        os.getenv(
            "U2NET_HOME",
            os.path.join(os.getenv("XDG_DATA_HOME", "~"), ".u2net"),
        )
    )


def _md5(path):
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ensure_model():
    home = _u2net_home()
    os.makedirs(home, exist_ok=True)
    path = os.path.join(home, _MODEL_NAME)

    if os.path.exists(path):
        try:
            if _md5(path) == _MODEL_MD5:
                return path
        except OSError:
            pass

    tmp_path = path + ".tmp"
    urllib.request.urlretrieve(_MODEL_URL, tmp_path)

    if _md5(tmp_path) != _MODEL_MD5:
        os.remove(tmp_path)
        raise RuntimeError("Model u2net gagal diverifikasi (md5 tidak cocok).")

    os.replace(tmp_path, path)
    return path


def _get_session():
    global _session
    if _session is None:
        _session = ort.InferenceSession(
            _ensure_model(),
            providers=["CPUExecutionProvider"],
        )
    return _session


def _normalize(img, mean, std, size):
    im = img.convert("RGB").resize(size, Image.Resampling.LANCZOS)

    im_ary = np.array(im)
    im_ary = im_ary / max(np.max(im_ary), 1e-6)

    tmp = np.zeros((im_ary.shape[0], im_ary.shape[1], 3))
    for c in range(3):
        tmp[:, :, c] = (im_ary[:, :, c] - mean[c]) / std[c]
    tmp = tmp.transpose((2, 0, 1))

    sess = _get_session()
    return {
        sess.get_inputs()[0].name: np.expand_dims(tmp, 0).astype(np.float32)
    }


def _naive_cutout(img, mask):
    empty = Image.new("RGBA", img.size, 0)
    return Image.composite(img, empty, mask)


def remove(data):
    """Hapus background dari gambar, kembalikan PIL Image RGBA."""
    if not isinstance(data, Image.Image):
        data = Image.fromarray(data)

    img = ImageOps.exif_transpose(data)

    sess = _get_session()
    ort_outs = sess.run(None, _normalize(img, _MEAN, _STD, _INPUT_SIZE))

    pred = ort_outs[0][:, 0, :, :]
    ma = np.max(pred)
    mi = np.min(pred)
    pred = (pred - mi) / (ma - mi)
    pred = np.squeeze(pred)

    mask = Image.fromarray((pred.clip(0, 1) * 255).astype("uint8"), mode="L")
    mask = mask.resize(img.size, Image.Resampling.LANCZOS)

    return _naive_cutout(img, mask)
