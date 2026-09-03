"""
init_db.py
شغّل هذا الملف مرة واحدة فقط لإنشاء قاعدة البيانات وتعبئتها ببيانات تجريبية
وإنشاء حساب المالك الافتراضي للوحة التحكم.

الاستخدام:
    python init_db.py
"""
import sqlite3
from werkzeug.security import generate_password_hash
from db import SCHEMA, DATABASE

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Liwan@2026"  # يُنصح بتغييرها فورًا من صفحة الإعدادات لاحقًا

SAMPLE_CATEGORIES = ["أرائك", "وسائد وزينة", "طاولات", "ديكور"]

SAMPLE_PRODUCTS = [
    ("أريكة \"ليوان\" المخملية", "أريكة فاخرة بخياطة يدوية دقيقة وقماش مخمل ناعم بدرجات الأخضر الرصاصي.", 2450.0, "أرائك", 1),
    ("طقم وسائد الزخرفة الهندسية", "وسائد زخرفية بنقشة إغريقية منسوجة وحواف مطرزة، تمنح الأريكة لمسة أنيقة.", 180.0, "وسائد وزينة", 1),
    ("مخدة أسطوانية مخملية", "مخدة أسطوانية بلونين متدرجين وزر ذهبي مركزي، تفصيل يدوي فاخر.", 220.0, "وسائد وزينة", 1),
    ("طاولة وسط رخامية", "طاولة وسط بقاعدة نحاسية وسطح رخامي طبيعي، تناسب صالونات الاستقبال.", 1350.0, "طاولات", 0),
]

SAMPLE_OFFERS = [
    ("عروض نهاية الموسم", "خصم يصل حتى 30% على تشكيلة الوسائد والمخدات المخملية.", 30, 1),
]


def main():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)

    # الإعدادات الافتراضية (صف واحد بمعرف ثابت = 1)
    conn.execute(
        "INSERT OR IGNORE INTO settings (id) VALUES (1)"
    )

    # حساب المالك
    existing = conn.execute(
        "SELECT id FROM admins WHERE username = ?", (DEFAULT_ADMIN_USERNAME,)
    ).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO admins (username, password_hash) VALUES (?, ?)",
            (DEFAULT_ADMIN_USERNAME, generate_password_hash(DEFAULT_ADMIN_PASSWORD)),
        )

    # التصنيفات
    cat_ids = {}
    for name in SAMPLE_CATEGORIES:
        conn.execute("INSERT OR IGNORE INTO categories (name) VALUES (?)", (name,))
    for row in conn.execute("SELECT id, name FROM categories"):
        cat_ids[row["name"]] = row["id"]

    # منتجات تجريبية (تُضاف فقط إذا كان الجدول فارغًا)
    count = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count == 0:
        for name, desc, price, cat_name, featured in SAMPLE_PRODUCTS:
            conn.execute(
                """INSERT INTO products (name, description, price, category_id, image_path, is_featured, is_active)
                   VALUES (?, ?, ?, ?, '', ?, 1)""",
                (name, desc, price, cat_ids.get(cat_name), featured),
            )

    # عرض تجريبي
    ocount = conn.execute("SELECT COUNT(*) AS c FROM offers").fetchone()["c"]
    if ocount == 0:
        for title, desc, discount, active in SAMPLE_OFFERS:
            conn.execute(
                """INSERT INTO offers (title, description, image_path, discount_percent, is_active)
                   VALUES (?, ?, '', ?, ?)""",
                (title, desc, discount, active),
            )

    conn.commit()
    conn.close()
    print("تم إنشاء قاعدة البيانات بنجاح: store.db")
    print(f"بيانات دخول لوحة التحكم -> اسم المستخدم: {DEFAULT_ADMIN_USERNAME} | كلمة المرور: {DEFAULT_ADMIN_PASSWORD}")
    print("يرجى تغيير كلمة المرور بعد أول تسجيل دخول.")


if __name__ == "__main__":
    main()
