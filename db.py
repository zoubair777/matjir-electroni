"""
db.py
وحدة الاتصال بقاعدة بيانات SQLite الخاصة بموقع متجر الأثاث.
"""
import sqlite3
from flask import g, current_app

DATABASE = "store.db"


def get_db():
    """يفتح اتصالاً جديدًا بقاعدة البيانات إن لم يكن موجودًا ضمن سياق الطلب الحالي."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)


SCHEMA = """
CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    site_name TEXT NOT NULL DEFAULT 'ليفان للأثاث الفاخر',
    tagline TEXT NOT NULL DEFAULT 'حيث يلتقي الفخامة بالراحة',
    logo_path TEXT NOT NULL DEFAULT 'images/logo.jpg',
    phone TEXT NOT NULL DEFAULT '0927569139',
    whatsapp_number TEXT NOT NULL DEFAULT '218927569139',
    address TEXT NOT NULL DEFAULT 'طرابلس، ليبيا',
    about_text TEXT NOT NULL DEFAULT 'نقدم أثاثًا فاخرًا مصنوعًا بعناية فائقة من أجود الأقمشة والخامات، لنجعل من منزلك تحفة من الراحة والأناقة.',
    facebook_url TEXT DEFAULT '',
    instagram_url TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    price REAL DEFAULT 0,
    category_id INTEGER,
    image_path TEXT DEFAULT '',
    is_featured INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    image_path TEXT DEFAULT '',
    discount_percent INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS media (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    media_type TEXT NOT NULL CHECK (media_type IN ('image','video')),
    file_path TEXT NOT NULL,
    title TEXT DEFAULT '',
    section TEXT DEFAULT 'gallery',
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now'))
);
"""
