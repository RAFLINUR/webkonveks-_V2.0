from flask import Blueprint
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import session
from flask import jsonify

from werkzeug.utils import secure_filename

from datetime import datetime

from bson import ObjectId

import os
import uuid

# Database
from models.database import mongo

# Katalog produk & harga (server-side)
from utils.products import (
    PRODUCTS,
    SIZES,
    JENIS,
    get_product,
    is_apparel,
    parse_variasi,
    hitung_apparel,
    hitung_simple,
    format_rupiah,
    cart_total,
    cart_count,
)

# Helper yang sudah ada di order.py (hindari duplikasi)
from routes.order import (
    generate_order_code,
    save_log,
    normalize_phone,
    allowed_file,
    UPLOAD_FOLDER,
)

from config import Config

cart_bp = Blueprint("cart", __name__)

# Folder hasil remove background (produk apparel)
REMOVED_FOLDER = Config.REMOVED_FOLDER

# Gambar QRIS statis
QRIS_IMAGE = "img/kris.jpeg"


# =========================
# SESSION CART HELPER
# =========================
def get_cart():

    return session.get("cart", [])


def set_cart(cart):

    session["cart"] = cart

    session.modified = True


def cart_count_session():

    return cart_count(get_cart())


# =========================
# SIMPAN FILE DESAIN (+ remove bg untuk apparel)
# =========================
def save_desain(file, produk):

    if not file or file.filename == "":

        return None

    if not allowed_file(file.filename):

        return None

    nama_file = secure_filename(file.filename)

    file_path = os.path.join(
        UPLOAD_FOLDER,
        nama_file
    )

    file.save(file_path)

    if is_apparel(produk):

        try:

            from PIL import Image
            from rembg import remove

            input_image = Image.open(file_path)

            output_image = remove(input_image)

            removed_filename = (
                "removed_"
                + nama_file.rsplit(".", 1)[0]
                + ".png"
            )

            removed_path = os.path.join(
                REMOVED_FOLDER,
                removed_filename
            )

            output_image.save(removed_path)

            return removed_filename

        except Exception as e:

            print("Remove background error:", e)

    return nama_file


# =========================
# HALAMAN TAMBAH KE KERANJANG (pilih ukuran/jumlah/desain)
# =========================
@cart_bp.route("/keranjang/tambah", methods=["GET", "POST"])
def tambah():

    produk_pilihan = request.args.get("produk")

    if request.method == "POST":

        produk = request.form.get("produk")

        data = get_product(produk)

        if not data:

            return render_template(
                "cart_tambah.html",
                produk_pilihan=produk_pilihan,
                products_meta=PRODUCTS,
                sizes=SIZES,
                jenis_list=JENIS,
                error="Produk tidak valid."
            )

        catatan = request.form.get("catatan") or ""

        # =========================
        # HITUNG VARIASI / QTY
        # =========================
        if data["tipe"] == "apparel":

            variasi, qty = parse_variasi(
                produk,
                request.form
            )

            harga = hitung_apparel(
                produk,
                variasi
            )

        else:

            variasi = []

            qty = int(
                request.form.get("simpleQty") or 0
            )

            harga = hitung_simple(
                produk,
                qty
            )

        # =========================
        # VALIDASI
        # =========================
        if qty <= 0:

            return render_template(
                "cart_tambah.html",
                produk_pilihan=produk,
                products_meta=PRODUCTS,
                sizes=SIZES,
                jenis_list=JENIS,
                error="Minimal isi jumlah pesanan."
            )

        if qty < data.get("minimal", 1):

            return render_template(
                "cart_tambah.html",
                produk_pilihan=produk,
                products_meta=PRODUCTS,
                sizes=SIZES,
                jenis_list=JENIS,
                error=f"Minimal order {produk} adalah "
                      f"{data['minimal']} pcs."
            )

        # =========================
        # UPLOAD DESAIN
        # =========================
        desain = save_desain(
            request.files.get("desain"),
            produk
        )

        # =========================
        # SIMPAN KE CART SESSION
        # =========================
        cart = get_cart()

        cart.append({

            "id": uuid.uuid4().hex,

            "produk": produk,

            "tipe": data["tipe"],

            "variasi": variasi,

            "qty": qty,

            "harga": harga,

            "catatan": catatan,

            "desain": desain

        })

        set_cart(cart)

        return redirect(
            url_for("cart.keranjang")
        )

    return render_template(
        "cart_tambah.html",
        produk_pilihan=produk_pilihan,
        products_meta=PRODUCTS,
        sizes=SIZES,
        jenis_list=JENIS
    )


# =========================
# HALAMAN KERANJANG
# =========================
@cart_bp.route("/keranjang")
def keranjang():

    cart = get_cart()

    return render_template(
        "cart.html",
        cart=cart,
        total=cart_total(cart),
        total_qty=cart_count(cart)
    )


# =========================
# UPDATE QTY (produk simple)
# =========================
@cart_bp.route("/keranjang/update", methods=["POST"])
def update():

    item_id = request.form.get("id")

    qty = int(
        request.form.get("qty") or 0
    )

    cart = get_cart()

    for item in cart:

        if item["id"] != item_id:

            continue

        if item["tipe"] == "simple":

            if qty <= 0:

                cart.remove(item)

            else:

                item["qty"] = qty

                item["harga"] = hitung_simple(
                    item["produk"],
                    qty
                )

        break

    set_cart(cart)

    return redirect(
        url_for("cart.keranjang")
    )


# =========================
# HAPUS ITEM
# =========================
@cart_bp.route("/keranjang/hapus", methods=["POST"])
def hapus():

    item_id = request.form.get("id")

    cart = [
        item for item in get_cart()
        if item["id"] != item_id
    ]

    set_cart(cart)

    return redirect(
        url_for("cart.keranjang")
    )


# =========================
# CHECKOUT (data customer)
# =========================
@cart_bp.route("/checkout", methods=["GET", "POST"])
def checkout():

    cart = get_cart()

    if not cart:

        return redirect(
            url_for("cart.keranjang")
        )

    if request.method == "GET":

        return render_template(
            "checkout.html",
            cart=cart,
            total=cart_total(cart),
            total_qty=cart_count(cart)
        )

    # =========================
    # VALIDASI CUSTOMER
    # =========================
    nama = request.form.get("nama")

    email = (request.form.get("email") or "").strip()

    whatsapp = request.form.get("whatsapp") or ""

    alamat = request.form.get("alamat") or ""

    catatan = request.form.get("catatan") or ""

    if not nama or not whatsapp or not email:

        return render_template(
            "checkout.html",
            cart=cart,
            total=cart_total(cart),
            total_qty=cart_count(cart),
            error="Nama, WhatsApp, dan Email wajib diisi."
        )

    if request.form.get("website"):

        return render_template(
            "checkout.html",
            cart=cart,
            total=cart_total(cart),
            total_qty=cart_count(cart),
            error="Pemesanan gagal. Silakan coba lagi."
        )

    # =========================
    # RINGKASAN (kompatibel dengan mobile)
    # =========================
    grand_total = cart_total(cart)

    total_qty = cart_count(cart)

    variasi_all = []

    for item in cart:

        for v in item.get("variasi", []):

            variasi_all.append(v)

    produk_summary = ", ".join(
        dict.fromkeys(
            item["produk"] for item in cart
        )
    )

    file_desain = next(
        (
            item.get("desain")
            for item in cart
            if item.get("desain")
        ),
        None
    )

    # =========================
    # BUAT ORDER
    # =========================
    kode_order = generate_order_code()

    mongo.db.orders.insert_one({

        "kode_order": kode_order,

        "nama_customer": nama,

        "email": email,

        "whatsapp": whatsapp,

        "whatsapp_norm": normalize_phone(whatsapp),

        "alamat": alamat,

        "ip_address": request.remote_addr,

        # Agregat (dipakai app mobile)
        "produk": produk_summary,

        "jumlah": total_qty,

        "variasi": variasi_all,

        "file_desain": file_desain,

        "catatan": catatan,

        "harga": grand_total,

        # Detail per item
        "items": [
            {
                "produk": item["produk"],
                "tipe": item["tipe"],
                "variasi": item.get("variasi", []),
                "qty": item["qty"],
                "harga": item["harga"],
                "catatan": item.get("catatan", ""),
                "desain": item.get("desain")
            }
            for item in cart
        ],

        "status": "pending",

        "payment_status": "menunggu_pembayaran",

        "is_verified": True,

        "struk_sent": False,

        "created_at": datetime.now()

    })

    save_log(
        f"Order baru (keranjang): {kode_order}",
        request.remote_addr
    )

    # Kosongkan keranjang setelah order dibuat
    set_cart([])

    return redirect(
        url_for(
            "cart.pembayaran",
            kode_order=kode_order
        )
    )


# =========================
# HALAMAN PEMBAYARAN QRIS
# =========================
@cart_bp.route("/pembayaran/<kode_order>")
def pembayaran(kode_order):

    try:

        order = mongo.db.orders.find_one({
            "kode_order": kode_order
        })

    except Exception:

        order = None

    if not order:

        return redirect(url_for("cart.keranjang"))

    return render_template(
        "pembayaran.html",
        order=order,
        total=order.get("harga", 0),
        qris_image=QRIS_IMAGE,
        dikonfirmasi=(
            order.get("payment_status")
            == "menunggu_verifikasi"
        )
    )


# =========================
# KONFIRMASI SUDAH BAYAR
# =========================
@cart_bp.route(
    "/pembayaran/<kode_order>/konfirmasi",
    methods=["POST"]
)
def konfirmasi(kode_order):

    try:

        order = mongo.db.orders.find_one({
            "kode_order": kode_order
        })

    except Exception:

        order = None

    if not order:

        return redirect(url_for("cart.keranjang"))

    mongo.db.orders.update_one(

        {"_id": order["_id"]},

        {"$set": {
            "payment_status": "menunggu_verifikasi",
            "paid_reported_at": datetime.now()
        }}

    )

    save_log(
        f"Konfirmasi bayar: {kode_order}",
        request.remote_addr
    )

    return redirect(
        url_for(
            "cart.pembayaran",
            kode_order=kode_order
        )
    )


# =========================
# API JUMLAH ITEM KERANJANG
# =========================
@cart_bp.route("/api/cart/count")
def api_cart_count():

    return jsonify({

        "success": True,

        "count": cart_count_session()

    })


# =========================
# CONTEXT HELPER (dipakai layout untuk badge)
# =========================
def inject_cart():

    return {
        "cart_count": cart_count_session()
    }
