from flask import Blueprint
from flask import render_template
from flask import request
from flask import redirect
from flask import url_for
from flask import jsonify

from werkzeug.utils import secure_filename

from datetime import datetime
from datetime import timedelta

from rembg import remove
from PIL import Image

from bson import ObjectId

from flask_mail import Message

import re
import os

# Database
from models.database import mongo

# Mail (pengiriman struk nota)
from extensions import mail

order_bp = Blueprint(
    'order',
    __name__
)

# Upload Folder
UPLOAD_FOLDER = "static/uploads"

# Allowed File
ALLOWED_EXTENSIONS = {
    "png",
    "jpg",
    "jpeg",
    "pdf"
}

# =========================
# VALIDASI FILE
# =========================
def allowed_file(filename):

    return "." in filename and \
           filename.rsplit(
               ".", 1
           )[1].lower() in ALLOWED_EXTENSIONS

# =========================
# NORMALISASI NOMOR WHATSAPP
# 0812xxx -> 62812xxx (dipakai untuk rate limit per nomor)
# =========================
def normalize_phone(phone):

    p = re.sub(
        r"\D",
        "",
        phone or ""
    )

    if p.startswith("62"):

        return p

    if p.startswith("0"):

        return "62" + p[1:]

    if p.startswith("8"):

        return "62" + p

    return p

# =========================
# KIRIM STRUK NOTA VIA EMAIL
# Dikirim otomatis setelah admin menyetujui order (approve)
# =========================
def send_struk_email(order):

    email = (
        order.get("email")
        or ""
    ).strip()

    if not email:

        raise Exception(
            "Email customer kosong, struk tidak bisa dikirim."
        )

    html = render_template(

        "email/struk.html",

        order=order

    )

    msg = Message(

        f"Struk Nota {order.get('kode_order')} - WebKonveksi",

        recipients=[email]

    )

    msg.html = html

    mail.send(msg)

    return True

# =========================
# ACTIVITY LOG
# =========================
def save_log(activity, ip):

    mongo.db.logs.insert_one({

        "activity": activity,

        "ip_address": ip,

        "created_at": datetime.now()

    })

# =========================
# GENERATE ORDER CODE
# =========================
def generate_order_code():

    tahun = datetime.now().year

    prefix = f"ORD{tahun}"

    # Pakai nomor urut TERBESAR tahun ini, bukan jumlah order.
    # Kalau pakai jumlah order, kode bisa terpakai ulang setelah
    # order dihapus (menyebabkan kode_order duplikat).
    max_num = 0

    for order in mongo.db.orders.find(
        {
            "kode_order": {
                "$regex": f"^{prefix}\\d+$"
            }
        },
        {
            "kode_order": 1
        }
    ):

        try:

            num = int(
                order["kode_order"][len(prefix):]
            )

            if num > max_num:
                max_num = num

        except (KeyError, ValueError, TypeError):

            continue

    nomor = max_num + 1

    kode_order = f"{prefix}{nomor:03d}"

    # Pastikan benar-benar unik (jaga-jaga race condition).
    while mongo.db.orders.count_documents({
        "kode_order": kode_order
    }) > 0:

        nomor += 1

        kode_order = f"{prefix}{nomor:03d}"

    return kode_order

# =========================
# ORDER
# =========================
@order_bp.route(
    "/order",
    methods=["GET", "POST"]
)
def order():

    produk_pilihan = request.args.get(
        "produk"
    )

    if request.method == "POST":

        # =========================
        # FORM DATA
        # =========================

        nama = request.form.get(
            "nama"
        )

        email = request.form.get(
            "email"
        ) or ""

        whatsapp = request.form.get(
            "whatsapp"
        ) or ""

        # =========================
        # VALIDASI WHATSAPP (SEBELUM SIMPAN ORDER)
        # Nomor WhatsApp dipakai untuk mengirim kode OTP,
        # jadi wajib ada sebelum order dibuat.
        # Email hanya disimpan opsional, tidak dipakai untuk OTP.
        # =========================

        if not whatsapp:

            return render_template(

                "order.html",

                produk_pilihan=produk_pilihan,

                error="Nomor WhatsApp wajib diisi untuk menerima kode OTP."

            )

        if not email:

            return render_template(

                "order.html",

                produk_pilihan=produk_pilihan,

                error="Email wajib diisi untuk pengiriman struk nota."

            )

        # =========================
        # HONEYPOT ANTI BOT
        # Field tersembunyi di form.
        # Manusia tidak pernah mengisi field ini.
        # =========================

        if request.form.get("website"):

            return render_template(

                "order.html",

                produk_pilihan=produk_pilihan,

                error="Pemesanan gagal. Silakan coba lagi."

            )

        # =========================
        # RATE LIMIT ANTI ASAL ORDER
        # 1 IP = maksimal 3 order per jam
        # (Limit per nomor WhatsApp sudah dihapus)
        # =========================

        now = datetime.now()

        whatsapp_norm = normalize_phone(whatsapp)

        if mongo.db.orders.count_documents({

            "ip_address": request.remote_addr,

            "created_at": {
                "$gte": now - timedelta(hours=1)
            }

        }) >= 3:

            return render_template(

                "order.html",

                produk_pilihan=produk_pilihan,

                error="Terlalu banyak pesanan dari jaringan Anda. "
                      "Silakan coba lagi dalam satu jam."

            )

        produk = request.form.get(
            "produk"
        )

        catatan = request.form.get(
            "catatan"
        )

        harga = int(
            request.form.get(
                "harga"
            ) or 0
        )

        jumlah = 0
        variasi = []

        # =========================
        # PRODUK APPAREL
        # =========================

        if (

            produk == "Kaos Sablon"

            or

            produk == "Polo Bordir"

        ):

            s_pendek = int(
                request.form.get(
                    "s_pendek"
                ) or 0
            )

            s_panjang = int(
                request.form.get(
                    "s_panjang"
                ) or 0
            )

            m_pendek = int(
                request.form.get(
                    "m_pendek"
                ) or 0
            )

            m_panjang = int(
                request.form.get(
                    "m_panjang"
                ) or 0
            )

            l_pendek = int(
                request.form.get(
                    "l_pendek"
                ) or 0
            )

            l_panjang = int(
                request.form.get(
                    "l_panjang"
                ) or 0
            )

            xl_pendek = int(
                request.form.get(
                    "xl_pendek"
                ) or 0
            )

            xl_panjang = int(
                request.form.get(
                    "xl_panjang"
                ) or 0
            )

            jumlah = (

                s_pendek +

                s_panjang +

                m_pendek +

                m_panjang +

                l_pendek +

                l_panjang +

                xl_pendek +

                xl_panjang

            )

            variasi = [

                {
                    "size": "S",
                    "jenis": "Pendek",
                    "qty": s_pendek
                },

                {
                    "size": "S",
                    "jenis": "Panjang",
                    "qty": s_panjang
                },

                {
                    "size": "M",
                    "jenis": "Pendek",
                    "qty": m_pendek
                },

                {
                    "size": "M",
                    "jenis": "Panjang",
                    "qty": m_panjang
                },

                {
                    "size": "L",
                    "jenis": "Pendek",
                    "qty": l_pendek
                },

                {
                    "size": "L",
                    "jenis": "Panjang",
                    "qty": l_panjang
                },

                {
                    "size": "XL",
                    "jenis": "Pendek",
                    "qty": xl_pendek
                },

                {
                    "size": "XL",
                    "jenis": "Panjang",
                    "qty": xl_panjang
                }

            ]

        else:

            jumlah = int(
                request.form.get(
                    "simpleQty"
                ) or 0
            )

        # =========================
        # UPLOAD FILE
        # =========================

        file = request.files.get(
            "desain"
        )

        nama_file = None

        if file and file.filename != "":

            if allowed_file(file.filename):

                nama_file = secure_filename(
                    file.filename
                )

                file_path = os.path.join(

                    UPLOAD_FOLDER,

                    nama_file

                )

                # SAVE ORIGINAL
                file.save(file_path)

                # =========================
                # REMOVE BACKGROUND
                # =========================

                if (

                    produk == "Kaos Sablon"

                    or

                    produk == "Polo Bordir"

                ):

                    try:

                        input_image = Image.open(
                            file_path
                        )

                        output_image = remove(
                            input_image
                        )

                        removed_filename = (

                            "removed_"

                            +

                            nama_file.rsplit(
                                ".", 1
                            )[0]

                            +

                            ".png"

                        )

                        removed_path = os.path.join(

                            "static/removed",

                            removed_filename

                        )

                        output_image.save(
                            removed_path
                        )

                        nama_file = removed_filename

                    except Exception as e:

                        print(

                            "Remove background error:",

                            e

                        )

        # =========================
        # ORDER CODE
        # =========================

        kode_order = generate_order_code()

        # =========================
        # SAVE ORDER
        # (Tanpa OTP: order langsung masuk daftar admin,
        #  proteksi anti spam ditangani rate limit + honeypot)
        # =========================

        mongo.db.orders.insert_one({

            "kode_order": kode_order,

            "nama_customer": nama,

            "email": email,

            "whatsapp": whatsapp,

            "whatsapp_norm": whatsapp_norm,

            "ip_address": request.remote_addr,

            "produk": produk,

            "jumlah": jumlah,

            "variasi": variasi,

            "catatan": catatan,

            "file_desain": nama_file,

            "harga": harga,

            "status": "pending",

            "is_verified": True,

            "struk_sent": False,

            "created_at": datetime.now()

        })

        # =========================
        # SAVE LOG
        # =========================

        save_log(

            f"Order baru: {kode_order}",

            request.remote_addr

        )

        # =========================
        # REDIRECT SUKSES
        # =========================

        return redirect(

            url_for(

                "order.sukses",

                kode_order=kode_order

            )

        )

    return render_template(

        "order.html",

        produk_pilihan=produk_pilihan

    )

# =========================
# API ORDERS
# =========================
@order_bp.route(
    "/api/orders",
    methods=["GET"]
)
def api_orders():

    orders = mongo.db.orders.find({

        "is_verified": True

    }).sort(

        "created_at",

        -1

    )

    data = []

    for order in orders:

        data.append({

            "id": str(
                order["_id"]
            ),

            "kode_order":
                order.get(
                    "kode_order"
                ),

            "nama_customer":
                order.get(
                    "nama_customer"
                ),

            "produk":
                order.get(
                    "produk"
                ),

            "jumlah":
                order.get(
                    "jumlah"
                ),

            "status":
                order.get(
                    "status"
                ),
            
            "variasi":
                order.get(
                    "variasi",
                    []
                ),

            "items":
                order.get(
                    "items",
                    []
                ),
            
            "catatan":
                order.get(
                    "catatan",
                    ""
                ),

            "file_desain":
                order.get(
                    "file_desain"
                ),
            
            "harga":
            order.get(
                "harga",
                0
            ),

            "email":
                order.get(
                    "email",
                    ""
                ),

            "struk_sent":
                order.get(
                    "struk_sent",
                    False
                ),

            "approved_at":
                str(
                    order.get(
                        "approved_at",
                        ""
                    )
                ),

            "created_at": str(

                order.get(
                    "created_at"
                )

            )

        })

    return jsonify({

        "success": True,

        "data": data

    })

# =========================
# DASHBOARD MONITOR
# =========================
@order_bp.route(
    "/api/dashboard",
    methods=["GET"]
)
def dashboard():

    total_order = (
        mongo.db.orders
        .count_documents({

            "is_verified": True

        })
    )

    pending = (
        mongo.db.orders
        .count_documents({

            "status": "pending",

            "is_verified": True

        })
    )

    sewing = (
        mongo.db.orders
        .count_documents({

            "status": "SEWING",

            "is_verified": True

        })
    )

    printing = (
        mongo.db.orders
        .count_documents({

            "status": "PRINTING",

            "is_verified": True

        })
    )

    done = (
        mongo.db.orders
        .count_documents({

            "status": "DONE",

            "is_verified": True

        })
    )

    return jsonify({

        "success": True,

        "data": {

            "total_order":
                total_order,

            "pending":
                pending,

            "sewing":
                sewing,

            "printing":
                printing,

            "done":
                done

        }

    })

# =========================
# UPDATE STATUS
# =========================
@order_bp.route(
    "/api/update-status/<id>",
    methods=["PUT"]
)
def update_status(id):

    data = request.json

    status = data.get(
        "status"
    )

    mongo.db.orders.update_one(

        {
            "_id": ObjectId(id)
        },

        {
            "$set": {

                "status": status

            }

        }

    )

    # SAVE LOG
    save_log(

        f"Update status: {status}",

        request.remote_addr

    )

    return jsonify({

        "success": True,

        "message":
            "Status berhasil diupdate"

    })


# =========================
# STATUS YANG SUDAH DISETUJUI
# =========================
APPROVED_STATUSES = {
    "approved",
    "printing",
    "sewing",
    "done"
}

# =========================
# APPROVE ORDER (ADMIN)
# Setujui order -> status "APPROVED"
# + kirim struk nota ke email customer
# =========================
@order_bp.route(
    "/api/orders/<id>/approve",
    methods=["POST"]
)
def approve_order(id):

    try:

        order = mongo.db.orders.find_one({
            "_id": ObjectId(id)
        })

    except Exception:

        order = None

    if not order:

        return jsonify({

            "success": False,

            "message": "Order tidak ditemukan"

        }), 404

    if not order.get("is_verified"):

        return jsonify({

            "success": False,

            "message": "Order belum diverifikasi OTP"

        }), 400

    # Sudah pernah disetujui, tidak kirim struk dua kali
    if (

        order.get(
            "status",
            ""
        ).lower() in APPROVED_STATUSES

    ):

        return jsonify({

            "success": True,

            "already": True,

            "status": order.get("status"),

            "struk_sent": order.get(
                "struk_sent",
                False
            ),

            "message":
                "Order sudah disetujui sebelumnya"

        })

    mongo.db.orders.update_one(

        {
            "_id": order["_id"]
        },

        {
            "$set": {
                "status": "APPROVED",
                "approved_at": datetime.now(),
                "struk_sent": False
            }
        }

    )

    order["status"] = "APPROVED"

    # =========================
    # KIRIM STRUK NOTA
    # =========================

    struk_sent = False

    struk_error = None

    try:

        send_struk_email(order)

        struk_sent = True

    except Exception as e:

        print("GAGAL KIRIM STRUK:", e)

        struk_error = str(e)

    mongo.db.orders.update_one(

        {
            "_id": order["_id"]
        },

        {
            "$set": {
                "struk_sent": struk_sent
            }
        }

    )

    save_log(

        f"Approve order: {order.get('kode_order')} "
        f"(struk: {'terkirim' if struk_sent else 'gagal'})",

        request.remote_addr

    )

    return jsonify({

        "success": True,

        "status": "APPROVED",

        "struk_sent": struk_sent,

        "struk_error": struk_error,

        "message":
            "Order disetujui. Struk nota dikirim ke email."
            if struk_sent
            else
            "Order disetujui, tetapi struk gagal dikirim ke email. "
            "Tekan Kirim Ulang Struk."

    })


# =========================
# KIRIM ULANG STRUK NOTA
# =========================
@order_bp.route(
    "/api/orders/<id>/resend-struk",
    methods=["POST"]
)
def resend_struk(id):

    try:

        order = mongo.db.orders.find_one({
            "_id": ObjectId(id)
        })

    except Exception:

        order = None

    if not order:

        return jsonify({

            "success": False,

            "message": "Order tidak ditemukan"

        }), 404

    if (

        order.get(
            "status",
            ""
        ).lower() not in APPROVED_STATUSES

    ):

        return jsonify({

            "success": False,

            "message": "Order belum disetujui admin"

        }), 400

    try:

        send_struk_email(order)

    except Exception as e:

        print("GAGAL KIRIM ULANG STRUK:", e)

        return jsonify({

            "success": False,

            "message": str(e)

        }), 502

    mongo.db.orders.update_one(

        {
            "_id": order["_id"]
        },

        {
            "$set": {
                "struk_sent": True
            }
        }

    )

    save_log(

        f"Kirim ulang struk: {order.get('kode_order')}",

        request.remote_addr

    )

    return jsonify({

        "success": True,

        "struk_sent": True,

        "message":
            "Struk nota dikirim ulang ke email customer."

    })


# =========================
# DELETE ORDER
# =========================
@order_bp.route(
    "/api/orders/<id>",
    methods=["DELETE"]
)
def delete_order(id):

    result = mongo.db.orders.delete_one({

        "_id": ObjectId(id)

    })

    if result.deleted_count == 0:

        return jsonify({

            "success": False,

            "message": "Order tidak ditemukan"

        }),404

    save_log(

        f"Hapus order {id}",

        request.remote_addr

    )

    return jsonify({

        "success": True,

        "message": "Order berhasil dihapus"

    })


# =========================
# BULK DELETE ORDER
# Hapus beberapa order sekaligus berdasarkan daftar id
# =========================
@order_bp.route(
    "/api/orders/bulk-delete",
    methods=["POST"]
)
def bulk_delete_orders():

    data = request.get_json(silent=True) or {}

    ids = data.get("ids") or []

    object_ids = []

    for item in ids:

        try:

            object_ids.append(
                ObjectId(item)
            )

        except Exception:

            continue

    if not object_ids:

        return jsonify({
            "success": False,
            "message": "Tidak ada order yang dipilih"
        }), 400

    result = mongo.db.orders.delete_many({
        "_id": {
            "$in": object_ids
        }
    })

    save_log(
        f"Hapus {result.deleted_count} order sekaligus",
        request.remote_addr
    )

    return jsonify({
        "success": True,
        "deleted": result.deleted_count,
        "message":
            f"{result.deleted_count} order berhasil dihapus"
    })


# =========================
# SUCCESS
# =========================
@order_bp.route(
    "/sukses"
)
def sukses():

    kode_order = request.args.get(
        "kode_order"
    )

    return render_template(

        "sukses.html",

        kode_order=kode_order

    )