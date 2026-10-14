# =========================
# KATALOG PRODUK (SERVER-SIDE)
# Sumber tunggal untuk harga & aturan bisnis.
# Harga TIDAK boleh diambil dari input client.
# =========================

SIZES = ["S", "M", "L", "XL"]

JENIS = ["Pendek", "Panjang"]

PRODUCTS = {

    "Kaos Sablon": {

        "nama": "Kaos Sablon",

        "tipe": "apparel",

        "harga": {
            "Pendek": 70000,
            "Panjang": 80000
        },

        "minimal": 12

    },

    "Polo Bordir": {

        "nama": "Polo Bordir",

        "tipe": "apparel",

        "harga": {
            "Pendek": 85000,
            "Panjang": 95000
        },

        "minimal": 12

    },

    "Totebag": {

        "nama": "Totebag",

        "tipe": "simple",

        "harga": {
            "Pendek": 40000
        },

        "minimal": 1

    },

    "ID Card + Lanyard": {

        "nama": "ID Card + Lanyard",

        "tipe": "simple",

        "harga": {
            "Pendek": 25000
        },

        "minimal": 1

    }

}


def get_product(nama):

    return PRODUCTS.get(nama)


def is_apparel(nama):

    produk = PRODUCTS.get(nama)

    return bool(produk and produk["tipe"] == "apparel")


def parse_variasi(produk, form):

    """
    Baca matriks size dari form.
    Field: s_pendek, s_panjang, m_pendek, ... (sesuai order.html).
    Kembalikan (variasi, total_qty).
    """

    variasi = []

    total = 0

    if not get_product(produk):

        return variasi, total

    for size in SIZES:

        for jenis in JENIS:

            qty = int(
                form.get(
                    f"{size.lower()}_{jenis.lower()}"
                ) or 0
            )

            if qty < 0:

                qty = 0

            if qty > 0:

                variasi.append({
                    "size": size,
                    "jenis": jenis,
                    "qty": qty
                })

            total += qty

    return variasi, total


def hitung_apparel(produk, variasi):

    data = get_product(produk)

    if not data:

        return 0

    total = 0

    for item in variasi or []:

        harga = data["harga"].get(
            item.get("jenis"),
            0
        )

        total += harga * int(item.get("qty") or 0)

    return total


def hitung_simple(produk, qty):

    data = get_product(produk)

    if not data:

        return 0

    return data["harga"]["Pendek"] * int(qty or 0)


def format_rupiah(nilai):

    return "Rp " + format(
        int(nilai),
        ",d"
    ).replace(",", ".")


def cart_total(cart):

    return sum(
        int(item.get("harga") or 0)
        for item in (cart or [])
    )


def cart_count(cart):

    return sum(
        int(item.get("qty") or 0)
        for item in (cart or [])
    )
