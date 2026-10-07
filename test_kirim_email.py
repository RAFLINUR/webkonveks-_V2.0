"""
Test kirim email OTP tanpa harus checkout.

Cara pakai:
    venv/bin/python test_kirim_email.py

Hasil:
    OK   -> kredensial SMTP benar, email test terkirim
    GAGAL -> lihat pesan dari Gmail (biasanya 535 = App Password salah)
"""

import os
import sys
import smtplib
import traceback

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_USERNAME = os.getenv("MAIL_USERNAME") or "raflinurikhwanabdi@gmail.com"
MAIL_PASSWORD = (os.getenv("MAIL_PASSWORD") or "").strip()


def main():
    print("SERVER  :", MAIL_SERVER, MAIL_PORT)
    print("USER    :", MAIL_USERNAME)
    print("PASSWORD:", ("*" * len(MAIL_PASSWORD)) if MAIL_PASSWORD else "(KOSONG)")

    if not MAIL_PASSWORD:
        print("\nGAGAL: MAIL_PASSWORD belum diisi di file .env")
        sys.exit(1)

    try:
        smtp = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=30)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()

        # Login resmi (bukan AUTH mentah) supaya benar
        smtp.login(MAIL_USERNAME, MAIL_PASSWORD)
        print("RESPON AUTH: 235 login diterima Gmail")
        smtp.quit()

        from flask import Flask
        from flask_mail import Message
        from extensions import mail

        app = Flask(__name__)
        app.config.update(
            MAIL_SERVER=MAIL_SERVER,
            MAIL_PORT=MAIL_PORT,
            MAIL_USE_TLS=True,
            MAIL_USERNAME=MAIL_USERNAME,
            MAIL_PASSWORD=MAIL_PASSWORD,
            MAIL_DEFAULT_SENDER=MAIL_USERNAME,
        )
        mail.init_app(app)

        with app.app_context():
            msg = Message(
                "[Test] Kode OTP WebKonveksi",
                recipients=[MAIL_USERNAME],
            )
            msg.body = (
                "Email test dari WebKonveksi.\n\n"
                "Jika kamu menerima email ini, kirim OTP sudah siap dipakai.\n"
                "Kode OTP: 123456\n"
            )
            mail.send(msg)

        print("\nOK: login berhasil dan email test terkirim ke", MAIL_USERNAME)
        print("Cek inbox (dan folder Spam).")

    except smtplib.SMTPAuthenticationError as e:
        print("\nGAGAL: AUTH ditolak ->", e.smtp_code, e.smtp_error)
        sys.exit(2)
    except Exception:
        print("\nGAGAL:")
        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()
