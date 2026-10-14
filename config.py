import os

from dotenv import load_dotenv

load_dotenv(override=True)

# Vercel hanya mengizinkan penulisan di /tmp (ephemeral).
# Deteksi otomatis lewat env VERCEL yang diset platform Vercel.
IS_VERCEL = os.getenv("VERCEL") == "1"

if IS_VERCEL:
    # Model u2net (remove background) disimpan di /tmp, bukan di ~/.u2net yang read-only.
    os.environ.setdefault("U2NET_HOME", "/tmp/.u2net")

class Config:

    # =========================
    # FLASK SESSION
    # Dipakai untuk menyimpan keranjang belanja (session-based).
    # =========================
    SECRET_KEY = os.getenv(
        "SECRET_KEY"
    ) or "webkonveksi-dev-secret-key"

    # =========================
    # MONGODB
    # =========================
    MONGO_URI = os.getenv(
        "MONGO_URI"
    )

    # =========================
    # PENYIMPANAN FILE DESAIN
    # Secara default memakai folder lokal di static/.
    # Di Vercel otomatis diarahkan ke /tmp (ephemeral).
    # Di Render bisa diarahkan ke persistent disk lewat env, contoh:
    #   UPLOAD_FOLDER=/var/data/uploads
    #   REMOVED_FOLDER=/var/data/removed
    # =========================
    _DEFAULT_UPLOAD = "/tmp/uploads" if IS_VERCEL else "public/static/uploads"

    _DEFAULT_REMOVED = "/tmp/removed" if IS_VERCEL else "public/static/removed"

    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER"
    ) or _DEFAULT_UPLOAD

    REMOVED_FOLDER = os.getenv(
        "REMOVED_FOLDER"
    ) or _DEFAULT_REMOVED

    # =========================
    # FLASK MAIL
    # =========================
    MAIL_SERVER = "smtp.gmail.com"

    MAIL_PORT = 587

    MAIL_USE_TLS = True

    # Diisi di file .env. Tidak ada nilai default agar kredensial
    # tidak ikut ter-commit ke repository.
    MAIL_USERNAME = os.getenv(
        "MAIL_USERNAME"
    ) or ""

    MAIL_PASSWORD = os.getenv(
        "MAIL_PASSWORD"
    ) or ""

    # Pengirim email (FROM).
    MAIL_DEFAULT_SENDER = MAIL_USERNAME

    # =========================
    # WHATSAPP CLOUD API (META)
    # Dipakai untuk mengirim kode OTP ke nomor WhatsApp customer.
    # Semua nilai diisi lewat file .env
    # =========================
    WA_API_VERSION = os.getenv(
        "WA_API_VERSION"
    ) or "v21.0"

    WA_PHONE_NUMBER_ID = os.getenv(
        "WA_PHONE_NUMBER_ID"
    ) or ""

    WA_ACCESS_TOKEN = os.getenv(
        "WA_ACCESS_TOKEN"
    ) or ""

    # Nama template pesan yang sudah di-approve Meta
    WA_TEMPLATE_NAME = os.getenv(
        "WA_TEMPLATE_NAME"
    ) or "otp_verification"

    WA_TEMPLATE_LANG = os.getenv(
        "WA_TEMPLATE_LANG"
    ) or "id"

    # Placeholder template yang diisi server, pisahkan dengan koma.
    # Tersedia: otp, kode_order
    WA_TEMPLATE_PARAMS = os.getenv(
        "WA_TEMPLATE_PARAMS"
    ) or "otp"