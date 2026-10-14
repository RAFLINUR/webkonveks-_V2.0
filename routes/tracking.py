from flask import Blueprint
from flask import render_template
from flask import request

from models.database import mongo

tracking_bp = Blueprint(
    "tracking",
    __name__
)

# =========================
# HALAMAN INPUT TRACKING
# =========================
@tracking_bp.route(
    "/tracking",
    methods=["GET"]
)
def tracking_page():

    return render_template(
        "tracking_search.html"
    )

# =========================
# HASIL TRACKING
# =========================
@tracking_bp.route(
    "/tracking-result",
    methods=["POST"]
)
def tracking_result():

    kode_order = request.form.get("kode_order")

    # Ambil order yang sudah diverifikasi & paling baru.
    # Kalau ada kode_order duplikat (data lama), ini memastikan yang
    # tampil adalah order yang benar-benar aktif/terbaru.
    order = mongo.db.orders.find_one(

        {
            "kode_order": kode_order,
            "is_verified": True
        },

        sort=[("_id", -1)]

    ) or mongo.db.orders.find_one(

        {
            "kode_order": kode_order
        },

        sort=[("_id", -1)]

    )

    if not order:

        return render_template(

            "tracking_search.html",

            error="Kode order tidak ditemukan. Silakan periksa kembali kode Anda."

        )

    # =========================
    # PROGRESS
    # =========================

    progress = 25

    if order.get("status") == "SEWING":

        progress = 50

    elif order.get("status") == "PRINTING":

        progress = 75

    elif order.get("status") == "DONE":

        progress = 100

    return render_template(

        "tracking.html",

        order=order,

        progress=progress,

    )