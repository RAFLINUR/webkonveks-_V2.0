import os

from dotenv import load_dotenv

load_dotenv(override=True)

class Config:

    # =========================
    # MONGODB
    # =========================
    MONGO_URI = os.getenv(
        "MONGO_URI"
    )

    # =========================
    # FLASK MAIL
    # =========================
    MAIL_SERVER = "smtp.gmail.com"

    MAIL_PORT = 587

    MAIL_USE_TLS = True

    # Diisi di file .env. Jika kosong, akan memakai nilai default di bawah.
    MAIL_USERNAME = os.getenv(
        "MAIL_USERNAME"
    ) or "raflinurikhwanabdi@gmail.com"

    MAIL_PASSWORD = os.getenv(
        "MAIL_PASSWORD"
    ) or "pnje idra ollp pqcd"

    # Pengirim email (FROM). Sebelumnya masih placeholder "EMAIL_GMAIL_KAMU"
    # yang membuat SMTP menolak pengiriman.
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