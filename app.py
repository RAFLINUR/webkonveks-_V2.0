import os
from flask import Flask

# Config
from config import Config
from extensions import mail

# auth
from routes.auth import auth_bp

# stok
from routes.stok import stok_bp

# Database
from models.database import mongo

# Blueprint
from routes.home import home_bp
from routes.order import order_bp
from routes.tracking import tracking_bp
from routes.ai import ai_bp

# Keranjang & pembayaran
from routes.cart import cart_bp, inject_cart

# upload desain
from flask import send_from_directory

app = Flask(
    __name__,
    static_folder="public/static",
    static_url_path="/static",
)

app.config.from_object(Config)

mail.init_app(app)

# MongoDB Config
app.config["MONGO_URI"] = Config.MONGO_URI
# Init MongoDB
mongo.init_app(app)

# Pastikan folder penyimpanan desain tersedia (mis. saat pakai persistent disk)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["REMOVED_FOLDER"], exist_ok=True)

# Register Blueprint
app.register_blueprint(home_bp)
app.register_blueprint(order_bp)
app.register_blueprint(tracking_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(stok_bp)
app.register_blueprint(ai_bp)
app.register_blueprint(cart_bp)

# Inject jumlah item keranjang ke semua template (badge navbar)
@app.context_processor
def _inject_cart():
    return inject_cart()

@app.route("/test-db")
def test_db():

    mongo.db.orders.insert_one({
        "nama_customer": "Rafli",
        "produk": "Kaos Sablon",
        "status": "pending"
    })

    return "Data berhasil disimpan!"

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

# Sajikan file desain yang tersimpan di persistent disk (Render)
# dengan URL yang sama seperti sebelumnya (/static/uploads, /static/removed)
@app.route("/static/uploads/<path:filename>")
def serve_upload_design(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename
    )

@app.route("/static/removed/<path:filename>")
def serve_removed_design(filename):

    return send_from_directory(
        app.config["REMOVED_FOLDER"],
        filename
    )

# Run App
if __name__ == "__main__":

    app.run(

        debug=True,

        host="0.0.0.0",

        port=5000

    )