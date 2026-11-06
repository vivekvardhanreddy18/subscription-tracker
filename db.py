"""MySQL helper functions for the Subscription Tracker."""
import os
from pathlib import Path

import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME", "subscription_tracker")
_BASE_CFG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
}


def get_conn(with_db=True):
    cfg = dict(_BASE_CFG)
    if with_db:
        cfg["database"] = DB_NAME
    return mysql.connector.connect(**cfg)


def init_db():
    """Create the database and tables if they don't exist yet."""
    conn = get_conn(with_db=False)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4")
    conn.database = DB_NAME
    schema = (Path(__file__).parent / "schema.sql").read_text()
    for stmt in schema.split(";"):
        if stmt.strip():
            cur.execute(stmt)
    conn.commit()
    cur.close()
    conn.close()


def fetch_all(sql, params=None):
    conn = get_conn()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params or ())
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def execute(sql, params=None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(sql, params or ())
    conn.commit()
    last_id = cur.lastrowid
    cur.close()
    conn.close()
    return last_id


# ---------- Domain queries ----------

def get_categories():
    return fetch_all("SELECT id, name FROM categories ORDER BY name")


def get_or_create_category(name):
    name = name.strip()
    execute("INSERT IGNORE INTO categories (name) VALUES (%s)", (name,))
    return fetch_all("SELECT id FROM categories WHERE name = %s", (name,))[0]["id"]


def get_subscriptions():
    return fetch_all(
        """
        SELECT s.id, s.name, s.category_id, c.name AS category, s.cost, s.billing_cycle,
               s.start_date, s.status, s.notes,
               (SELECT COUNT(*) FROM usage_log u
                 WHERE u.subscription_id = s.id
                   AND u.used_on >= CURDATE() - INTERVAL 30 DAY) AS uses_30d
        FROM subscriptions s
        LEFT JOIN categories c ON c.id = s.category_id
        ORDER BY s.name
        """
    )


def add_subscription(name, category_id, cost, cycle, start_date, notes):
    return execute(
        """INSERT INTO subscriptions (name, category_id, cost, billing_cycle, start_date, notes)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (name, category_id, cost, cycle, start_date, notes or None),
    )


def update_subscription(sub_id, name, category_id, cost, cycle, start_date, status, notes):
    execute(
        """UPDATE subscriptions
           SET name=%s, category_id=%s, cost=%s, billing_cycle=%s,
               start_date=%s, status=%s, notes=%s
           WHERE id=%s""",
        (name, category_id, cost, cycle, start_date, status, notes or None, sub_id),
    )


def delete_subscription(sub_id):
    execute("DELETE FROM subscriptions WHERE id = %s", (sub_id,))


def log_usage(sub_id, used_on):
    execute("INSERT INTO usage_log (subscription_id, used_on) VALUES (%s, %s)", (sub_id, used_on))


def get_recent_usage(limit=20):
    return fetch_all(
        """SELECT u.used_on, s.name
           FROM usage_log u JOIN subscriptions s ON s.id = u.subscription_id
           ORDER BY u.used_on DESC, u.id DESC LIMIT %s""",
        (limit,),
    )
