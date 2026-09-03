"""
app.py
تطبيق Flask لموقع متجر أثاث فاخر + لوحة تحكم كاملة للمالك.
قاعدة البيانات: SQLite (عبر db.py)
"""
import os
import functools
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, g, send_from_directory, abort
)
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash

import db

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_IMAGE = {"png", "jpg", "jpeg", "webp", "gif"}
ALLOWED_VIDEO = {"mp4", "webm", "mov"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "غيّر-هذا-المفتاح-السري-قبل-النشر-الفعلي")
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25MB لكل ملف مرفوع
db.init_app(app)


# ---------------------------------------------------------------------------
# أدوات مساعدة
# ---------------------------------------------------------------------------

def allowed_file(filename, allowed_set):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_set


def save_upload(file_storage, subfolder):
    """يحفظ ملفًا مرفوعًا ويعيد المسار النسبي (تحت static/) أو '' إن لم يوجد ملف."""
    if not file_storage or file_storage.filename == "":
        return ""
    filename = secure_filename(file_storage.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_IMAGE and ext not in ALLOWED_VIDEO:
        flash("صيغة الملف غير مدعومة.", "error")
        return ""
    stamped = f"{int(datetime.now().timestamp())}_{filename}"
    folder_abs = os.path.join(UPLOAD_ROOT, subfolder)
    os.makedirs(folder_abs, exist_ok=True)
    file_storage.save(os.path.join(folder_abs, stamped))
    return f"uploads/{subfolder}/{stamped}"


def delete_upload(relative_path):
    if not relative_path:
        return
    abs_path = os.path.join(BASE_DIR, "static", relative_path)
    if os.path.isfile(abs_path):
        try:
            os.remove(abs_path)
        except OSError:
            pass


def get_settings():
    row = db.get_db().execute("SELECT * FROM settings WHERE id = 1").fetchone()
    return row


@app.context_processor
def inject_globals():
    """يجعل إعدادات الموقع (الاسم، الشعار، واتساب...) متاحة في كل القوالب."""
    unread = 0
    if session.get("admin_id"):
        unread = db.get_db().execute(
            "SELECT COUNT(*) c FROM messages WHERE is_read = 0"
        ).fetchone()["c"]
    return {"site": get_settings(), "current_year": datetime.now().year, "unread_messages": unread}


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_id"):
            return redirect(url_for("admin_login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# الصفحات العامة (الواجهة الأمامية)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    conn = db.get_db()
    featured = conn.execute(
        "SELECT * FROM products WHERE is_active = 1 AND is_featured = 1 ORDER BY created_at DESC LIMIT 8"
    ).fetchall()
    latest = conn.execute(
        "SELECT * FROM products WHERE is_active = 1 ORDER BY created_at DESC LIMIT 8"
    ).fetchall()
    offers = conn.execute(
        "SELECT * FROM offers WHERE is_active = 1 ORDER BY created_at DESC LIMIT 4"
    ).fetchall()
    gallery = conn.execute(
        "SELECT * FROM media WHERE media_type = 'image' ORDER BY created_at DESC LIMIT 6"
    ).fetchall()
    videos = conn.execute(
        "SELECT * FROM media WHERE media_type = 'video' ORDER BY created_at DESC LIMIT 3"
    ).fetchall()
    return render_template(
        "index.html", featured=featured, latest=latest,
        offers=offers, gallery=gallery, videos=videos
    )


@app.route("/products")
def products():
    conn = db.get_db()
    category_id = request.args.get("category", type=int)
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    base_query = """SELECT products.*, categories.name AS category_name
                    FROM products LEFT JOIN categories ON products.category_id = categories.id
                    WHERE products.is_active = 1"""
    if category_id:
        rows = conn.execute(
            base_query + " AND products.category_id = ? ORDER BY products.created_at DESC",
            (category_id,),
        ).fetchall()
    else:
        rows = conn.execute(base_query + " ORDER BY products.created_at DESC").fetchall()
    return render_template(
        "products.html", products=rows, categories=categories,
        selected_category=category_id
    )


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        message = request.form.get("message", "").strip()
        if not name or not phone or not message:
            flash("يرجى تعبئة جميع الحقول قبل الإرسال.", "error")
        else:
            db.get_db().execute(
                "INSERT INTO messages (name, phone, message) VALUES (?, ?, ?)",
                (name, phone, message),
            )
            db.get_db().commit()
            flash("تم إرسال رسالتك بنجاح، سنتواصل معك في أقرب وقت ممكن.", "success")
            return redirect(url_for("contact"))
    return render_template("contact.html")


# ---------------------------------------------------------------------------
# لوحة تحكم المالك — تسجيل الدخول
# ---------------------------------------------------------------------------

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if session.get("admin_id"):
        return redirect(url_for("admin_dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        row = db.get_db().execute(
            "SELECT * FROM admins WHERE username = ?", (username,)
        ).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            session.clear()
            session["admin_id"] = row["id"]
            session["admin_username"] = row["username"]
            return redirect(request.args.get("next") or url_for("admin_dashboard"))
        flash("اسم المستخدم أو كلمة المرور غير صحيحة.", "error")
    return render_template("admin/login.html")


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# ---------------------------------------------------------------------------
# لوحة تحكم المالك — الرئيسية
# ---------------------------------------------------------------------------

@app.route("/admin")
@login_required
def admin_dashboard():
    conn = db.get_db()
    stats = {
        "products": conn.execute("SELECT COUNT(*) c FROM products").fetchone()["c"],
        "offers": conn.execute("SELECT COUNT(*) c FROM offers WHERE is_active = 1").fetchone()["c"],
        "media": conn.execute("SELECT COUNT(*) c FROM media").fetchone()["c"],
        "messages": conn.execute("SELECT COUNT(*) c FROM messages WHERE is_read = 0").fetchone()["c"],
    }
    recent_messages = conn.execute(
        "SELECT * FROM messages ORDER BY created_at DESC LIMIT 5"
    ).fetchall()
    return render_template("admin/dashboard.html", stats=stats, recent_messages=recent_messages)


# ---------------------------------------------------------------------------
# لوحة تحكم المالك — المنتجات
# ---------------------------------------------------------------------------

@app.route("/admin/products")
@login_required
def admin_products():
    conn = db.get_db()
    rows = conn.execute(
        """SELECT products.*, categories.name AS category_name
           FROM products LEFT JOIN categories ON products.category_id = categories.id
           ORDER BY products.created_at DESC"""
    ).fetchall()
    return render_template("admin/products.html", products=rows)


@app.route("/admin/products/new", methods=["GET", "POST"])
@login_required
def admin_product_new():
    conn = db.get_db()
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "0") or 0
        category_id = request.form.get("category_id") or None
        is_featured = 1 if request.form.get("is_featured") else 0
        is_active = 1 if request.form.get("is_active") else 0
        image_path = save_upload(request.files.get("image"), "products")
        if not name:
            flash("اسم المنتج مطلوب.", "error")
        else:
            conn.execute(
                """INSERT INTO products (name, description, price, category_id, image_path, is_featured, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (name, description, float(price), category_id, image_path, is_featured, is_active),
            )
            conn.commit()
            flash("تمت إضافة المنتج بنجاح.", "success")
            return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=None, categories=categories)


@app.route("/admin/products/<int:product_id>/edit", methods=["GET", "POST"])
@login_required
def admin_product_edit(product_id):
    conn = db.get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        abort(404)
    categories = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        description = request.form.get("description", "").strip()
        price = request.form.get("price", "0") or 0
        category_id = request.form.get("category_id") or None
        is_featured = 1 if request.form.get("is_featured") else 0
        is_active = 1 if request.form.get("is_active") else 0
        new_image = save_upload(request.files.get("image"), "products")
        image_path = new_image or product["image_path"]
        if new_image and product["image_path"]:
            delete_upload(product["image_path"])
        conn.execute(
            """UPDATE products SET name=?, description=?, price=?, category_id=?,
               image_path=?, is_featured=?, is_active=? WHERE id=?""",
            (name, description, float(price), category_id, image_path, is_featured, is_active, product_id),
        )
        conn.commit()
        flash("تم تحديث المنتج بنجاح.", "success")
        return redirect(url_for("admin_products"))
    return render_template("admin/product_form.html", product=product, categories=categories)


@app.route("/admin/products/<int:product_id>/delete", methods=["POST"])
@login_required
def admin_product_delete(product_id):
    conn = db.get_db()
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if product:
        delete_upload(product["image_path"])
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        flash("تم حذف المنتج.", "success")
    return redirect(url_for("admin_products"))


@app.route("/admin/categories/new", methods=["POST"])
@login_required
def admin_category_new():
    name = request.form.get("name", "").strip()
    if name:
        try:
            db.get_db().execute("INSERT INTO categories (name) VALUES (?)", (name,))
            db.get_db().commit()
            flash("تمت إضافة التصنيف.", "success")
        except Exception:
            flash("هذا التصنيف موجود مسبقًا.", "error")
    return redirect(request.referrer or url_for("admin_products"))


# ---------------------------------------------------------------------------
# لوحة تحكم المالك — العروض
# ---------------------------------------------------------------------------

@app.route("/admin/offers")
@login_required
def admin_offers():
    rows = db.get_db().execute("SELECT * FROM offers ORDER BY created_at DESC").fetchall()
    return render_template("admin/offers.html", offers=rows)


@app.route("/admin/offers/new", methods=["GET", "POST"])
@login_required
def admin_offer_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        discount = request.form.get("discount_percent", "0") or 0
        is_active = 1 if request.form.get("is_active") else 0
        image_path = save_upload(request.files.get("image"), "offers")
        if not title:
            flash("عنوان العرض مطلوب.", "error")
        else:
            db.get_db().execute(
                """INSERT INTO offers (title, description, image_path, discount_percent, is_active)
                   VALUES (?, ?, ?, ?, ?)""",
                (title, description, image_path, int(discount), is_active),
            )
            db.get_db().commit()
            flash("تمت إضافة العرض بنجاح.", "success")
            return redirect(url_for("admin_offers"))
    return render_template("admin/offer_form.html", offer=None)


@app.route("/admin/offers/<int:offer_id>/edit", methods=["GET", "POST"])
@login_required
def admin_offer_edit(offer_id):
    conn = db.get_db()
    offer = conn.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()
    if not offer:
        abort(404)
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        discount = request.form.get("discount_percent", "0") or 0
        is_active = 1 if request.form.get("is_active") else 0
        new_image = save_upload(request.files.get("image"), "offers")
        image_path = new_image or offer["image_path"]
        if new_image and offer["image_path"]:
            delete_upload(offer["image_path"])
        conn.execute(
            """UPDATE offers SET title=?, description=?, image_path=?, discount_percent=?, is_active=?
               WHERE id=?""",
            (title, description, image_path, int(discount), is_active, offer_id),
        )
        conn.commit()
        flash("تم تحديث العرض بنجاح.", "success")
        return redirect(url_for("admin_offers"))
    return render_template("admin/offer_form.html", offer=offer)


@app.route("/admin/offers/<int:offer_id>/delete", methods=["POST"])
@login_required
def admin_offer_delete(offer_id):
    conn = db.get_db()
    offer = conn.execute("SELECT * FROM offers WHERE id = ?", (offer_id,)).fetchone()
    if offer:
        delete_upload(offer["image_path"])
        conn.execute("DELETE FROM offers WHERE id = ?", (offer_id,))
        conn.commit()
        flash("تم حذف العرض.", "success")
    return redirect(url_for("admin_offers"))


# ---------------------------------------------------------------------------
# لوحة تحكم المالك — الصور ومقاطع الفيديو
# ---------------------------------------------------------------------------

@app.route("/admin/media")
@login_required
def admin_media():
    rows = db.get_db().execute("SELECT * FROM media ORDER BY created_at DESC").fetchall()
    return render_template("admin/media.html", media_items=rows)


@app.route("/admin/media/new", methods=["POST"])
@login_required
def admin_media_new():
    title = request.form.get("title", "").strip()
    section = request.form.get("section", "gallery")
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("يرجى اختيار ملف لرفعه.", "error")
        return redirect(url_for("admin_media"))
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    media_type = "image" if ext in ALLOWED_IMAGE else ("video" if ext in ALLOWED_VIDEO else None)
    if not media_type:
        flash("صيغة الملف غير مدعومة. الصور: jpg/png/webp — الفيديو: mp4/webm/mov", "error")
        return redirect(url_for("admin_media"))
    path = save_upload(file, "media")
    if path:
        db.get_db().execute(
            "INSERT INTO media (media_type, file_path, title, section) VALUES (?, ?, ?, ?)",
            (media_type, path, title, section),
        )
        db.get_db().commit()
        flash("تم رفع الملف بنجاح.", "success")
    return redirect(url_for("admin_media"))


@app.route("/admin/media/<int:media_id>/delete", methods=["POST"])
@login_required
def admin_media_delete(media_id):
    conn = db.get_db()
    item = conn.execute("SELECT * FROM media WHERE id = ?", (media_id,)).fetchone()
    if item:
        delete_upload(item["file_path"])
        conn.execute("DELETE FROM media WHERE id = ?", (media_id,))
        conn.commit()
        flash("تم حذف الملف.", "success")
    return redirect(url_for("admin_media"))


# ---------------------------------------------------------------------------
# لوحة تحكم المالك — الإعدادات العامة (الاسم، الشعار، واتساب...)
# ---------------------------------------------------------------------------

@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    conn = db.get_db()
    if request.method == "POST":
        site_name = request.form.get("site_name", "").strip()
        tagline = request.form.get("tagline", "").strip()
        phone = request.form.get("phone", "").strip()
        whatsapp_number = request.form.get("whatsapp_number", "").strip()
        address = request.form.get("address", "").strip()
        about_text = request.form.get("about_text", "").strip()
        facebook_url = request.form.get("facebook_url", "").strip()
        instagram_url = request.form.get("instagram_url", "").strip()

        current = get_settings()
        new_logo = save_upload(request.files.get("logo"), "logo")
        logo_path = new_logo or current["logo_path"]

        conn.execute(
            """UPDATE settings SET site_name=?, tagline=?, logo_path=?, phone=?, whatsapp_number=?,
               address=?, about_text=?, facebook_url=?, instagram_url=? WHERE id=1""",
            (site_name, tagline, logo_path, phone, whatsapp_number, address,
             about_text, facebook_url, instagram_url),
        )
        conn.commit()
        flash("تم حفظ الإعدادات بنجاح.", "success")
        return redirect(url_for("admin_settings"))
    return render_template("admin/settings.html", settings=get_settings())


@app.route("/admin/settings/password", methods=["POST"])
@login_required
def admin_change_password():
    current_password = request.form.get("current_password", "")
    new_password = request.form.get("new_password", "")
    confirm_password = request.form.get("confirm_password", "")
    conn = db.get_db()
    row = conn.execute("SELECT * FROM admins WHERE id = ?", (session["admin_id"],)).fetchone()

    if not check_password_hash(row["password_hash"], current_password):
        flash("كلمة المرور الحالية غير صحيحة.", "error")
    elif len(new_password) < 6:
        flash("يجب ألا تقل كلمة المرور الجديدة عن 6 أحرف.", "error")
    elif new_password != confirm_password:
        flash("كلمتا المرور الجديدتان غير متطابقتين.", "error")
    else:
        conn.execute(
            "UPDATE admins SET password_hash = ? WHERE id = ?",
            (generate_password_hash(new_password), session["admin_id"]),
        )
        conn.commit()
        flash("تم تغيير كلمة المرور بنجاح.", "success")
    return redirect(url_for("admin_settings"))


# ---------------------------------------------------------------------------
# لوحة تحكم المالك — رسائل التواصل
# ---------------------------------------------------------------------------

@app.route("/admin/messages")
@login_required
def admin_messages():
    rows = db.get_db().execute("SELECT * FROM messages ORDER BY created_at DESC").fetchall()
    return render_template("admin/messages.html", messages=rows)


@app.route("/admin/messages/<int:message_id>/read", methods=["POST"])
@login_required
def admin_message_read(message_id):
    db.get_db().execute("UPDATE messages SET is_read = 1 WHERE id = ?", (message_id,))
    db.get_db().commit()
    return redirect(url_for("admin_messages"))


@app.route("/admin/messages/<int:message_id>/delete", methods=["POST"])
@login_required
def admin_message_delete(message_id):
    db.get_db().execute("DELETE FROM messages WHERE id = ?", (message_id,))
    db.get_db().commit()
    flash("تم حذف الرسالة.", "success")
    return redirect(url_for("admin_messages"))


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
