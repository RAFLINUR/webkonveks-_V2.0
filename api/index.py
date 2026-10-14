import os
import sys

# Tambahkan root project ke sys.path supaya bisa `import app`
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# Vercel akan memakai objek `app` (WSGI) ini sebagai handler
from app import app  # noqa: E402,F401
