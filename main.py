import asyncio
import hashlib
import hmac
import json
import logging
import os
import re
import sys
import time
import secrets
import base64
import ipaddress
from urllib.parse import parse_qsl, urlencode

import aiohttp
import libsql

from aiohttp import web
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# ============================================================
# CONFIG
# ============================================================

# IMPORTANT: put the bot token in an environment variable.
# Windows PowerShell:
#   $env:BOT_TOKEN="YOUR_NEW_TOKEN"
# Linux:
#   export BOT_TOKEN="YOUR_NEW_TOKEN"
TOKEN = os.getenv("BOT_TOKEN", "").strip()

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Set BOT_TOKEN as an environment variable.")

TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()

if not TURSO_DATABASE_URL or not TURSO_AUTH_TOKEN:
    raise RuntimeError(
        "TURSO_DATABASE_URL / TURSO_AUTH_TOKEN missing. "
        "Create a free database at https://turso.tech and set them as environment variables."
    )
WEBAPP_URL = "https://mohlahramoh-bit.github.io/rayan-coin/"
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8080"))

X_URL = "https://x.com/mohlahra18042"
TELEGRAM_URL = "https://t.me/Arba7y_Official"
ADSTERRA_URL = "https://www.profitableratecpmnetwork.com/u19dhqyq?key=6c2a30702a80cbfb6bc129abb22d894a"

# 1 Earnings point = this many USDT.
# Change this value to your real business rule.
USDT_PER_EARNING = float(os.getenv("USDT_PER_EARNING", "0.01"))

MIN_WITHDRAW_USDT = float(os.getenv("MIN_WITHDRAW_USDT", "2"))
DAILY_CHECKIN_REWARD = int(os.getenv("DAILY_CHECKIN_REWARD", "1"))
REFERRAL_REWARD = int(os.getenv("REFERRAL_REWARD", "7"))
FIXED_X_REWARD = int(os.getenv("FIXED_X_REWARD", "3"))
FIXED_TELEGRAM_REWARD = int(os.getenv("FIXED_TELEGRAM_REWARD", "3"))
AD_REWARD = int(os.getenv("AD_REWARD", "1"))
AD_DAILY_LIMIT = int(os.getenv("AD_DAILY_LIMIT", "100"))
AD_VIEWS_PER_REWARD = int(os.getenv("AD_VIEWS_PER_REWARD", "10"))
AD_REWARD_POSTBACK_SECRET = os.getenv("AD_REWARD_POSTBACK_SECRET", "").strip()
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
ADGEM_POSTBACK_KEY = os.getenv("ADGEM_POSTBACK_KEY", "").strip()
BSC_RPC_URL = os.getenv("BSC_RPC_URL", "https://bsc-dataseed.binance.org").strip()
BSC_USDT_CONTRACT = os.getenv("BSC_USDT_CONTRACT", "0x55d398326f99059fF775485246999027B3197955").strip().lower()
BSC_CONFIRMATIONS_REQUIRED = int(os.getenv("BSC_CONFIRMATIONS_REQUIRED", "3"))
TIMEWALL_POSTBACK_SECRET = os.getenv("TIMEWALL_POSTBACK_SECRET", "").strip()
TIMEWALL_HASH_MODE = os.getenv("TIMEWALL_HASH_MODE", "userid_revenue_secret").strip()
LOOTABLY_API_KEY = os.getenv("LOOTABLY_API_KEY", "").strip()
LOOTABLY_PLACEMENT_ID = os.getenv("LOOTABLY_PLACEMENT_ID", "").strip()
LOOTABLY_POSTBACK_SECRET = os.getenv("LOOTABLY_POSTBACK_SECRET", "").strip()
LOOTABLY_USER_SPLIT = float(os.getenv("LOOTABLY_USER_SPLIT", "0.25"))
TIMEWALL_PLACEMENT_URL = os.getenv("TIMEWALL_PLACEMENT_URL", "").strip()
X_CLIENT_ID = os.getenv("X_CLIENT_ID", "").strip()
X_REDIRECT_URI = os.getenv("X_REDIRECT_URI", "").strip()
X_TARGET_USERNAME = os.getenv("X_TARGET_USERNAME", "mohlahra18042").strip()
CAMPAIGN_PAYMENT_ADDRESS = os.getenv("CAMPAIGN_PAYMENT_ADDRESS", "0x75d79ef88cce039069a4746b4498151a00293de2").strip()
CAMPAIGN_PAYMENT_NETWORK = os.getenv("CAMPAIGN_PAYMENT_NETWORK", "BSC (BEP20)").strip()
CAMPAIGN_PAYMENT_CURRENCY = os.getenv("CAMPAIGN_PAYMENT_CURRENCY", "USDT").strip()  


# ============================================================
# CAMPAIGN PRICING - Rayan Coin
# ============================================================

# ============================================================
# CPAGRIP (JSON Offer Feed)
# ============================================================
# من لوحتك في CPAGrip -> Offer Tools -> JSON Offer Feed
CPAGRIP_USER_ID = os.getenv("CPAGRIP_USER_ID", "").strip()
CPAGRIP_PUBLIC_KEY = os.getenv("CPAGRIP_PUBLIC_KEY", "").strip()

CPAGRIP_FEED_URL = "https://www.cpagrip.com/common/offer_feed_json.php"

# نسبة اللي تروح للمستخدم من قيمة عرض CPAGrip (0.25 = 25%، والباقي 75% لك).
CPAGRIP_USER_SHARE = float(os.getenv("CPAGRIP_USER_SHARE", "0.25"))

# كلمة السر اللي بتحطينها في CPAGrip -> Postback Tools -> Global Postback
# (خانة "Password (Optional)") — تأكد إنها نفسها بالضبط بالمكانين.
CPAGRIP_POSTBACK_PASSWORD = os.getenv("CPAGRIP_POSTBACK_PASSWORD", "").strip()

CAMPAIGN_PRICES = {
    "youtube": {
        "subscribers": {
            "unit_quantity": 10,
            "advertiser_price": 2.00,
            "user_reward": 0.02,
        },
        "views": {
            "unit_quantity": 100,
            "advertiser_price": 6.00,
            "user_reward": 0.02,
        },
    },

    "instagram": {
        "followers": {
            "unit_quantity": 10,
            "advertiser_price": 1.50,
            "user_reward": 0.02,
        },
        "views": {
            "unit_quantity": 100,
            "advertiser_price": 3.00,
            "user_reward": 0.02,
        },
    },

    "tiktok": {
        "followers": {
            "unit_quantity": 10,
            "advertiser_price": 1.50,
            "user_reward": 0.02,
        },
        "views": {
            "unit_quantity": 100,
            "advertiser_price": 3.00,
            "user_reward": 0.02,
        },
    },

    "telegram": {
        "joins": {
            "unit_quantity": 10,
            "advertiser_price": 1.00,
            "user_reward": 0.02,
        },
    },

    "discord": {
        "joins": {
            "unit_quantity": 10,
            "advertiser_price": 1.20,
            "user_reward": 0.02,
        },
    },

    "facebook": {
        "followers": {
            "unit_quantity": 10,
            "advertiser_price": 1.50,
            "user_reward": 0.02,
        },
    },

    "snapchat": {
        "followers": {
            "unit_quantity": 10,
            "advertiser_price": 1.50,
            "user_reward": 0.02,
        },
    },

    "apps": {
        "installs": {
            "unit_quantity": 10,
            "advertiser_price": 3.00,
            "user_reward": 0.03,
        },
    },
}
dp = Dispatcher()


# ============================================================
# DATABASE
# ============================================================

class Row:
    """Lightweight stand-in for sqlite3.Row: supports row['col'] and row[0]."""
    __slots__ = ("_cols", "_data")

    def __init__(self, cols, data):
        self._cols = cols
        self._data = data

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._data[self._cols.index(key)]
        return self._data[key]

    def keys(self):
        return list(self._cols)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self):
        return f"<Row {dict(zip(self._cols, self._data))}>"


class _CursorWrapper:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        self._cursor.execute(sql, params)
        return self

    @property
    def lastrowid(self):
        return self._cursor.lastrowid

    def _cols(self):
        return [d[0] for d in (self._cursor.description or [])]

    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return Row(self._cols(), row)

    def fetchall(self):
        cols = self._cols()
        return [Row(cols, r) for r in self._cursor.fetchall()]


class _ConnectionWrapper:
    def __init__(self, conn):
        self._conn = conn

    def execute(self, sql, params=()):
        cur = self._conn.cursor()
        cur.execute(sql, params)
        return _CursorWrapper(cur)

    def executescript(self, sql):
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                self._conn.execute(statement)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type is None:
                self._conn.commit()
            else:
                self._conn.rollback()
        finally:
            self._conn.close()
        return False


def db():
    conn = libsql.connect(
        database=TURSO_DATABASE_URL,
        auth_token=TURSO_AUTH_TOKEN,
    )
    return _ConnectionWrapper(conn)


def is_unique_violation(exc: Exception) -> bool:
    """UNIQUE constraint errors carry this text regardless of driver/exception class."""
    return "UNIQUE constraint failed" in str(exc)


def init_db():
    with db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL DEFAULT '',
            username TEXT DEFAULT '',
            balance INTEGER NOT NULL DEFAULT 0,
            total_earned INTEGER NOT NULL DEFAULT 0,
            completed_tasks INTEGER NOT NULL DEFAULT 0,
            current_streak INTEGER NOT NULL DEFAULT 0,
            best_streak INTEGER NOT NULL DEFAULT 0,
            total_checkins INTEGER NOT NULL DEFAULT 0,
            last_checkin TEXT,
            referral_code TEXT UNIQUE,
            referred_by INTEGER,
            referral_rewarded INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(referred_by) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            reward INTEGER NOT NULL CHECK(reward > 0),
            budget INTEGER NOT NULL CHECK(budget > 0),
            spent INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(owner_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS campaign_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL UNIQUE,
            owner_id INTEGER NOT NULL,
            amount_usdt REAL NOT NULL CHECK(amount_usdt > 0),
            currency TEXT NOT NULL DEFAULT 'USDT',
            network TEXT NOT NULL DEFAULT 'BSC (BEP20)',
            payment_address TEXT NOT NULL,
            tx_hash TEXT UNIQUE,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            submitted_at TEXT,
            processed_at TEXT,
            FOREIGN KEY(task_id) REFERENCES tasks(id),
            FOREIGN KEY(owner_id) REFERENCES users(user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_campaign_payments_owner ON campaign_payments(owner_id);
        CREATE INDEX IF NOT EXISTS idx_campaign_payments_status ON campaign_payments(status);

        CREATE TABLE IF NOT EXISTS referral_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, day),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_referral_activity_user ON referral_activity(user_id);

        CREATE TABLE IF NOT EXISTS timewall_conversions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            revenue_usd REAL NOT NULL DEFAULT 0,
            currency_usdt REAL NOT NULL DEFAULT 0,
            reward INTEGER NOT NULL DEFAULT 0,
            event_type TEXT NOT NULL DEFAULT 'credit',
            status TEXT NOT NULL DEFAULT 'approved',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            processed_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_timewall_user ON timewall_conversions(user_id);

        CREATE TABLE IF NOT EXISTS referral_rewards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_user_id INTEGER NOT NULL UNIQUE,
            reward INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(referrer_id) REFERENCES users(user_id),
            FOREIGN KEY(referred_user_id) REFERENCES users(user_id)
        );

                CREATE TABLE IF NOT EXISTS task_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reward INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(task_id, user_id),
            FOREIGN KEY(task_id) REFERENCES tasks(id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS fixed_completions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            reward INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(kind, user_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS x_oauth_states (
            state TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            code_verifier TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS ad_reward_conversions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id TEXT NOT NULL UNIQUE,
            user_id INTEGER NOT NULL,
            reward INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS daily_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            reward INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, day),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS ad_views (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            views INTEGER NOT NULL DEFAULT 0,
            UNIQUE(user_id, day),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS withdrawals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount_usdt REAL NOT NULL,
            address TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            processed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS settings (
            user_id INTEGER PRIMARY KEY,
            lang TEXT NOT NULL DEFAULT 'ar',
            country TEXT NOT NULL DEFAULT 'DZ',
            dark_mode INTEGER NOT NULL DEFAULT 1,
            country_auto INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );
 CREATE TABLE IF NOT EXISTS offers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            provider_offer_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            tracking_url TEXT NOT NULL,
            category TEXT DEFAULT '',
            payout_usd REAL NOT NULL DEFAULT 0,
            user_reward INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'active',
            countries TEXT DEFAULT '',
            devices TEXT DEFAULT '',
            raw_data TEXT DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(provider, provider_offer_id)
        );

        CREATE TABLE IF NOT EXISTS offer_clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            offer_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            provider_offer_id TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(offer_id) REFERENCES offers(id),
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        );

        CREATE TABLE IF NOT EXISTS offer_conversions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            provider_conversion_id TEXT NOT NULL,
            offer_id INTEGER,
            user_id INTEGER NOT NULL,
            payout_usd REAL NOT NULL DEFAULT 0,
            reward INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'approved',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            processed_at TEXT,
            FOREIGN KEY(offer_id) REFERENCES offers(id),
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            UNIQUE(provider, provider_conversion_id)
        );

        CREATE INDEX IF NOT EXISTS idx_offers_status
            ON offers(status);

        CREATE INDEX IF NOT EXISTS idx_offer_clicks_user
            ON offer_clicks(user_id);

        CREATE INDEX IF NOT EXISTS idx_offer_conversions_user
            ON offer_conversions(user_id);

        CREATE INDEX IF NOT EXISTS idx_offer_conversions_provider
        ON offer_conversions(provider);

        CREATE TABLE IF NOT EXISTS adgem_conversions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT NOT NULL,
            conversion_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            payout_usd REAL NOT NULL DEFAULT 0,
            reward INTEGER NOT NULL DEFAULT 0,
            conversion_type TEXT NOT NULL DEFAULT 'reward',
            offer_id TEXT DEFAULT '',
            goal_id TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'approved',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            UNIQUE(conversion_id)
        );

        CREATE INDEX IF NOT EXISTS idx_adgem_conversions_user
        ON adgem_conversions(user_id);

        CREATE INDEX IF NOT EXISTS idx_adgem_conversions_status
        ON adgem_conversions(status);

        CREATE TABLE IF NOT EXISTS cpagrip_conversions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversion_id TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            payout_usd REAL NOT NULL DEFAULT 0,
            reward INTEGER NOT NULL DEFAULT 0,
            offer_id TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'approved',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            UNIQUE(conversion_id)
        );

        CREATE INDEX IF NOT EXISTS idx_cpagrip_conversions_user
        ON cpagrip_conversions(user_id);
        CREATE INDEX IF NOT EXISTS idx_completions_user ON task_completions(user_id);
        CREATE INDEX IF NOT EXISTS idx_withdrawals_user ON withdrawals(user_id);
        """)

        # Upgrade old database created by the original bot.py.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)").fetchall()}
        upgrades = [
            ("username", "TEXT DEFAULT ''"),
            ("total_earned", "INTEGER NOT NULL DEFAULT 0"),
            ("completed_tasks", "INTEGER NOT NULL DEFAULT 0"),
            ("current_streak", "INTEGER NOT NULL DEFAULT 0"),
            ("best_streak", "INTEGER NOT NULL DEFAULT 0"),
            ("total_checkins", "INTEGER NOT NULL DEFAULT 0"),
            ("last_checkin", "TEXT"),
            ("referral_code", "TEXT"),
            ("referred_by", "INTEGER"),
            ("referral_rewarded", "INTEGER NOT NULL DEFAULT 0"),
            ("created_at", "TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ]
        for name, typ in upgrades:
            if name not in cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {typ}")

        payment_cols = {r["name"] for r in conn.execute("PRAGMA table_info(campaign_payments)").fetchall()}
        payment_upgrades = [
            ("chain_verified", "INTEGER NOT NULL DEFAULT 0"),
            ("confirmations", "INTEGER NOT NULL DEFAULT 0"),
            ("verified_at", "TEXT"),
            ("verification_error", "TEXT"),
        ]
        for name, typ in payment_upgrades:
            if name not in payment_cols:
                conn.execute(f"ALTER TABLE campaign_payments ADD COLUMN {name} {typ}")

        withdrawal_cols = {r["name"] for r in conn.execute("PRAGMA table_info(withdrawals)").fetchall()}
        withdrawal_upgrades = [
            ("tx_hash", "TEXT"),
        ]
        for name, typ in withdrawal_upgrades:
            if name not in withdrawal_cols:
                conn.execute(f"ALTER TABLE withdrawals ADD COLUMN {name} {typ}")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_withdrawals_tx_hash ON withdrawals(tx_hash) WHERE tx_hash IS NOT NULL")

        task_cols = {r["name"] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
        task_upgrades = [
            ("platform", "TEXT DEFAULT ''"),
            ("task_type", "TEXT DEFAULT ''"),
            ("quantity", "INTEGER NOT NULL DEFAULT 0"),
            ("advertiser_price_usdt", "REAL NOT NULL DEFAULT 0"),
            ("user_reward_usdt", "REAL NOT NULL DEFAULT 0"),
        ]
        for name, typ in task_upgrades:
            if name not in task_cols:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} {typ}")


        settings_cols = {r["name"] for r in conn.execute("PRAGMA table_info(settings)").fetchall()}
        if "country_auto" not in settings_cols:
            conn.execute("ALTER TABLE settings ADD COLUMN country_auto INTEGER NOT NULL DEFAULT 1")


def record_user_activity_and_maybe_reward_referral(user_id):
    """Record one distinct UTC activity day and unlock the referral reward after 2 days."""
    today = today_utc()
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT OR IGNORE INTO referral_activity(user_id,day) VALUES(?,?)",
            (user_id, today)
        )
        row = conn.execute(
            "SELECT referred_by, referral_rewarded FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()
        if row and row["referred_by"] and not int(row["referral_rewarded"] or 0):
            days = conn.execute(
                "SELECT COUNT(*) AS c FROM referral_activity WHERE user_id=?",
                (user_id,)
            ).fetchone()["c"]
            if int(days) >= 2:
                referrer_id = int(row["referred_by"])
                try:
                    conn.execute(
                        "INSERT INTO referral_rewards(referrer_id,referred_user_id,reward) VALUES(?,?,?)",
                        (referrer_id, user_id, REFERRAL_REWARD)
                    )
                except Exception as e:
                    if not is_unique_violation(e):
                        raise
                else:
                    conn.execute(
                        "UPDATE users SET balance=balance+?, total_earned=total_earned+? WHERE user_id=?",
                        (REFERRAL_REWARD, REFERRAL_REWARD, referrer_id)
                    )
                conn.execute("UPDATE users SET referral_rewarded=1 WHERE user_id=?", (user_id,))
        conn.commit()


def ensure_user(user_id, full_name="", username="", referral_code=None):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE users SET full_name=?, username=? WHERE user_id=?",
                (full_name, username, user_id),
            )
            conn.commit()
            return False

        code = f"u{user_id}"
        referrer_id = None
        if referral_code:
            ref = conn.execute(
                "SELECT user_id FROM users WHERE referral_code=?", (referral_code,)
            ).fetchone()
            if ref and int(ref["user_id"]) != int(user_id):
                referrer_id = int(ref["user_id"])

        conn.execute(
            """INSERT INTO users
               (user_id, full_name, username, balance, referral_code, referred_by, referral_rewarded)
               VALUES (?, ?, ?, 0, ?, ?, 0)""",
            (user_id, full_name, username, code, referrer_id),
        )

        conn.commit()
        return True


def add_balance(conn, user_id, amount, earned=True):
    if amount <= 0:
        return
    if earned:
        conn.execute(
            """UPDATE users
               SET balance=balance+?, total_earned=total_earned+?
               WHERE user_id=?""",
            (amount, amount, user_id),
        )
    else:
        conn.execute(
            "UPDATE users SET balance=balance+? WHERE user_id=?",
            (amount, user_id),
        )


def today_utc():
    return time.strftime("%Y-%m-%d", time.gmtime())


def yesterday_utc():
    return time.strftime("%Y-%m-%d", time.gmtime(time.time() - 86400))


def user_json(conn, user_id):
    u = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    if not u:
        return None

    today = today_utc()
    ad = conn.execute(
        "SELECT views FROM ad_views WHERE user_id=? AND day=?",
        (user_id, today)
    ).fetchone()
    ads_left = max(0, 10 - (ad["views"] if ad else 0))

    daily = conn.execute(
        "SELECT 1 FROM daily_checkins WHERE user_id=? AND day=?",
        (user_id, today)
    ).fetchone()

    x_done = conn.execute(
        "SELECT 1 FROM fixed_completions WHERE user_id=? AND kind='x'",
        (user_id,)
    ).fetchone()
    tg_done = conn.execute(
        "SELECT 1 FROM fixed_completions WHERE user_id=? AND kind='telegram'",
        (user_id,)
    ).fetchone()

    referral_days = conn.execute(
        "SELECT COUNT(*) AS c FROM referral_activity WHERE user_id=?",
        (user_id,)
    ).fetchone()["c"]

    referral_invited = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE referred_by=?",
        (user_id,)
    ).fetchone()["c"]

    settings = conn.execute(
        "SELECT lang,country,dark_mode FROM settings WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if not settings:
        conn.execute(
            "INSERT OR IGNORE INTO settings(user_id) VALUES(?)",
            (user_id,)
        )
        settings = conn.execute(
            "SELECT lang,country,dark_mode FROM settings WHERE user_id=?",
            (user_id,)
        ).fetchone()

    earnings = int(u["balance"] or 0)
    usdt = earnings * USDT_PER_EARNING

    return {
        "telegram_id": u["user_id"],
        "name": u["full_name"],
        "username": u["username"],
        "earnings": earnings,
        "usdt_balance": round(usdt, 8),
        "completed_tasks": int(u["completed_tasks"] or 0),
        "current_streak": int(u["current_streak"] or 0),
        "best_streak": int(u["best_streak"] or 0),
        "total_checkins": int(u["total_checkins"] or 0),
        "daily_checkin_done": bool(daily),
        "ads_left_today": ads_left,
        "referral_link": f"https://t.me/{BOT_USERNAME_PLACEHOLDER}?start=ref_{u['referral_code']}",
        "referral": {
            "invited": int(referral_invited),
            "activity_days": int(referral_days),
            "required_days": 2,
            "reward_earnings": REFERRAL_REWARD,
            "reward_usdt": round(REFERRAL_REWARD * USDT_PER_EARNING, 8),
        },
        "fixed_tasks": {
            "x_done": bool(x_done),
            "telegram_done": bool(tg_done),
            "x_available": True,
            "telegram_available": True,
        },
        "settings": {
            "lang": settings["lang"],
            "country": settings["country"],
            "darkMode": bool(settings["dark_mode"]),
        }
    }


# Filled after bot creation using getMe().
BOT_USERNAME_PLACEHOLDER = "YOUR_BOT"

# يُملأ في main() بعد إنشاء الـ Bot، يُستخدم لإرسال إشعارات من داخل الـ API (aiohttp).
BOT_INSTANCE = None


async def notify_admin(text: str, reply_markup=None):
    """يرسل إشعار للأدمن (ADMIN_USER_ID)."""
    if not ADMIN_USER_ID or not BOT_INSTANCE:
        return
    try:
        await BOT_INSTANCE.send_message(ADMIN_USER_ID, text, reply_markup=reply_markup)
    except Exception:
        logging.exception("Failed to notify admin")


async def notify_user(user_id: int, text: str):
    """يرسل إشعار لمستخدم معيّن. يتجاهل الفشل بصمت (مثلاً لو حظر البوت)."""
    if not user_id or not BOT_INSTANCE:
        return
    try:
        await BOT_INSTANCE.send_message(user_id, text)
    except Exception:
        logging.info("Failed to notify user %s (probably blocked the bot)", user_id)


# ============================================================
# TELEGRAM Mini App initData verification
# ============================================================

def verify_init_data(init_data: str):
    """
    Telegram Mini App sends initData. The server must verify its hash
    using HMAC-SHA256 before trusting the Telegram user ID.
    """
    if not init_data:
        return None

    try:
        pairs = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = pairs.pop("hash", None)
        auth_date = pairs.get("auth_date")

        if not received_hash or not auth_date:
            return None

        if abs(time.time() - int(auth_date)) > 600:
            return None

        data_check_string = "\n".join(
            f"{k}={v}" for k, v in sorted(pairs.items())
        )

        secret_key = hmac.new(
            b"WebAppData",
            TOKEN.encode(),
            hashlib.sha256
        ).digest()

        calculated = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(calculated, received_hash):
            return None

        user = json.loads(pairs.get("user", "{}"))
        return user if user.get("id") else None
    except Exception:
        return None


@web.middleware
async def cors_and_errors(request, handler):
    try:
        response = await handler(request)
    except web.HTTPException as e:
        response = e
    except Exception:
        logging.exception("API error")
        response = web.json_response(
            {"detail": "Internal server error"},
            status=500
        )

    origin = request.headers.get("Origin", "")
    allowed_origin = WEBAPP_URL.rstrip("/")
    if origin == allowed_origin or origin == "https://mohlahramoh-bit.github.io":
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Vary"] = "Origin"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Telegram-Init-Data"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PATCH,OPTIONS"
    return response


def auth_user(request):
    user = verify_init_data(request.headers.get("X-Telegram-Init-Data", ""))
    if not user:
        raise web.HTTPUnauthorized(
            text=json.dumps({"detail": "Telegram initData is invalid or missing"}),
            content_type="application/json"
        )
    is_new = ensure_user(user["id"], user.get("first_name", ""), user.get("username", ""))
    record_user_activity_and_maybe_reward_referral(int(user["id"]))
    if is_new:
        uname = f"@{user.get('username')}" if user.get("username") else "بدون يوزر"
        asyncio.create_task(notify_admin(
            "🆕 <b>مستخدم جديد سجّل في Rayan Coin!</b>\n\n"
            f"الاسم: {user.get('first_name','')}\n"
            f"اليوزر: {uname}\n"
            f"المعرف: <code>{user['id']}</code>\n"
            "المصدر: فتح التطبيق مباشرة"
        ))
    return int(user["id"])
async def api_adgem_postback(request):
    if not ADGEM_POSTBACK_KEY:
        logging.error("ADGEM_POSTBACK_KEY is missing")
        raise web.HTTPServiceUnavailable(
            text="AdGem postback is not configured"
        )

    raw_body = await request.read()
    received_signature = request.headers.get("Signature", "").strip()

    if not received_signature:
        raise web.HTTPUnauthorized(text="Missing Signature")

    expected_signature = hmac.new(
        ADGEM_POSTBACK_KEY.encode("utf-8"),
        raw_body,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(
        expected_signature,
        received_signature
    ):
        logging.warning("Invalid AdGem postback signature")
        raise web.HTTPUnauthorized(text="Invalid Signature")

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise web.HTTPBadRequest(text="Invalid JSON")

    request_id = str(payload.get("request_id", "")).strip()
    data = payload.get("data") or {}

    if not request_id or not isinstance(data, dict):
        raise web.HTTPBadRequest(text="Invalid AdGem payload")

    player_id = str(data.get("player_id", "")).strip()
    conversion_id = str(data.get("conversion_id", "")).strip()
    conversion_type = str(
        data.get("conversion_type", "reward")
    ).strip().lower()

    if not player_id or not conversion_id:
        raise web.HTTPBadRequest(
            text="Missing player_id or conversion_id"
        )

    if not player_id.isdigit():
        raise web.HTTPBadRequest(text="Invalid player_id")

    user_id = int(player_id)

    if conversion_type != "reward":
        return web.json_response({
            "ok": True,
            "rewarded": False,
            "reason": "non_reward_conversion"
        })

    try:
        reward = int(data.get("amount", 0) or 0)
    except (TypeError, ValueError):
        reward = 0

    if reward <= 0:
        return web.json_response({
            "ok": True,
            "rewarded": False,
            "reason": "zero_reward"
        })

    try:
        payout_usd = float(data.get("payout", 0) or 0)
    except (TypeError, ValueError):
        payout_usd = 0.0

    offer_id = str(data.get("offer_id", "") or "")
    goal_id = str(data.get("goal_id", "") or "")

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")

        user = conn.execute(
            "SELECT user_id FROM users WHERE user_id=?",
            (user_id,)
        ).fetchone()

        if not user:
            conn.rollback()
            raise web.HTTPNotFound(text="User not found")

        existing = conn.execute(
            """
            SELECT id
            FROM adgem_conversions
            WHERE conversion_id=?
            """,
            (conversion_id,)
        ).fetchone()

        if existing:
            conn.commit()
            return web.json_response({
                "ok": True,
                "rewarded": False,
                "duplicate": True
            })

        conn.execute(
            """
            INSERT INTO adgem_conversions
            (
                request_id,
                conversion_id,
                user_id,
                payout_usd,
                reward,
                conversion_type,
                offer_id,
                goal_id,
                status
            )
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                request_id,
                conversion_id,
                user_id,
                payout_usd,
                reward,
                conversion_type,
                offer_id,
                goal_id,
                "approved"
            )
        )

        add_balance(
            conn,
            user_id,
            reward,
            earned=True
        )

        conn.commit()

    asyncio.create_task(notify_user(
        user_id,
        f"🎁 <b>مكافأة جديدة!</b>\n\n"
        f"أنجزت عرض AdGem وربحت <b>{reward} Earnings</b>."
    ))

    logging.info(
        "AdGem reward credited: user=%s reward=%s payout=%s conversion=%s",
        user_id,
        reward,
        payout_usd,
        conversion_id
    )

    return web.json_response({
        "ok": True,
        "rewarded": True,
        "reward": reward
    })

# ============================================================
# API
# ============================================================

COUNTRY_LANGUAGE = {
    "DZ": "ar", "MA": "ar", "TN": "ar", "EG": "ar", "SA": "ar", "AE": "ar",
    "FR": "fr", "DE": "en", "TR": "en", "US": "en", "GB": "en", "CA": "en"
}

async def detect_country(request):
    forwarded = request.headers.get("X-Country-Code", "").strip().upper()
    if re.fullmatch(r"[A-Z]{2}", forwarded):
        return forwarded
    ip = (request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote or "").strip()
    if not ip or ip in ("127.0.0.1", "::1"):
        return None
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://ipapi.co/{ip}/country/", timeout=aiohttp.ClientTimeout(total=2)) as resp:
                if resp.status == 200:
                    country = (await resp.text()).strip().upper()
                    if re.fullmatch(r"[A-Z]{2}", country):
                        return country
    except Exception:
        logging.info("Automatic country detection failed")
    return None

async def apply_auto_country(request, uid):
    with db() as conn:
        row = conn.execute("SELECT country,lang,country_auto FROM settings WHERE user_id=?", (uid,)).fetchone()
    if row and int(row["country_auto"] or 0) == 0:
        return
    country = await detect_country(request)
    if not country:
        return
    lang = COUNTRY_LANGUAGE.get(country, "en")
    with db() as conn:
        conn.execute(
            """INSERT INTO settings(user_id,lang,country,dark_mode,country_auto) VALUES(?,?,?,1,1)
               ON CONFLICT(user_id) DO UPDATE SET country=excluded.country, lang=excluded.lang, country_auto=1""",
            (uid, lang, country)
        )
        conn.commit()

async def api_me(request):
    uid = auth_user(request)
    await apply_auto_country(request, uid)
    with db() as conn:
        return web.json_response({
            "user": user_json(conn, uid)
        })


async def api_tasks(request):
    uid = auth_user(request)
    with db() as conn:
        rows = conn.execute("""
            SELECT t.*,
                   CASE WHEN c.id IS NULL THEN 0 ELSE 1 END AS completed
            FROM tasks t
            LEFT JOIN task_completions c
              ON c.task_id=t.id AND c.user_id=?
            WHERE t.status='active'
              AND t.spent < t.budget
              AND (t.owner_id IS NULL OR t.owner_id != ?)
            ORDER BY t.id DESC
        """, (uid, uid)).fetchall()

        tasks = [{
            "id": r["id"],
            "title": r["title"],
            "link": r["link"],
            "reward": r["reward"],
            "budget_remaining": max(0, r["budget"] - r["spent"]),
            "completed": bool(r["completed"]),
            "platform": r["platform"],
            "task_type": r["task_type"],
            "quantity": int(r["quantity"] or 0),
            "advertiser_price_usdt": float(r["advertiser_price_usdt"] or 0),
            "user_reward_usdt": float(r["user_reward_usdt"] or 0),
        } for r in rows]

        return web.json_response({"tasks": tasks})


async def api_cpagrip_offers(request):
    """يجيب قائمة عروض CPAGrip الحقيقية (JSON Offer Feed) مع تمرير معرف المستخدم كـ tracking_id."""
    uid = auth_user(request)

    if not CPAGRIP_USER_ID or not CPAGRIP_PUBLIC_KEY:
        raise web.HTTPServiceUnavailable(
            text=json.dumps({"detail": "CPAGrip غير مُفعّل على السيرفر بعد"}),
            content_type="application/json"
        )

    visitor_ip = (request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                  or request.remote or "")

    params = {
        "user_id": CPAGRIP_USER_ID,
        "pubkey": CPAGRIP_PUBLIC_KEY,
        "tracking_id": str(uid),
        "ip": visitor_ip,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(CPAGRIP_FEED_URL, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json(content_type=None)
    except Exception:
        logging.exception("Failed to fetch CPAGrip offer feed")
        raise web.HTTPBadGateway(
            text=json.dumps({"detail": "تعذر جلب عروض CPAGrip حالياً"}),
            content_type="application/json"
        )

    # ⚠️ شكل استجابة CPAGrip قد يختلف قليلاً (offers مقابل data مثلاً) — عدّلي
    # هذا السطر لو رجعت البيانات باسم حقل مختلف حسب المثال الحقيقي عندك.
    raw_offers = data.get("offers") if isinstance(data, dict) else data

    offers = []
    for o in (raw_offers or []):
        try:
            full_payout = float(o.get("amount") or o.get("payout") or 0)
        except (TypeError, ValueError):
            full_payout = 0.0

        user_payout = round(full_payout * CPAGRIP_USER_SHARE, 2)

        offers.append({
            "id": o.get("id"),
            "title": o.get("title") or o.get("name"),
            "description": o.get("description", ""),
            "payout": user_payout,
            "link": o.get("link") or o.get("url"),
            "icon": o.get("picture") or o.get("icon", ""),
        })

    return web.json_response({"ok": True, "offers": offers})


async def api_cpagrip_postback(request):
    """
    يستقبل تأكيد إنجاز العرض من CPAGrip (Global Postback).

    حسب لوحتك الحقيقية: CPAGrip يرسل POST فيه (password, payout, offer_id,
    tracking_id) — ما فيه رقم عملية فريد، فنبني واحد بأنفسنا من
    tracking_id+offer_id لمنع التكرار.
    """
    data = await request.post()

    password = str(data.get("password", "")).strip()
    if CPAGRIP_POSTBACK_PASSWORD and password != CPAGRIP_POSTBACK_PASSWORD:
        logging.warning("Invalid CPAGrip postback password")
        raise web.HTTPUnauthorized(text="Invalid password")

    user_id_raw = str(data.get("tracking_id", "")).strip()
    offer_id = str(data.get("offer_id", "")).strip()
    payout_raw = str(data.get("payout", "0")).strip()

    if not user_id_raw or not user_id_raw.isdigit():
        raise web.HTTPBadRequest(text="Invalid tracking_id")

    user_id = int(user_id_raw)
    conversion_id = str(data.get("transaction_id") or data.get("trans_id") or data.get("conversion_id") or "").strip()
    if not conversion_id:
        conversion_id = hashlib.sha256((user_id_raw + "|" + offer_id + "|" + payout_raw + "|" + str(data.get("timestamp", ""))).encode()).hexdigest()

    try:
        payout_usd = float(payout_raw)
    except (TypeError, ValueError):
        payout_usd = 0.0

    # نديك 75% من قيمة العرض ونعطي المستخدم 25% فقط.
    user_share_usd = payout_usd * CPAGRIP_USER_SHARE
    reward = int(round(user_share_usd / USDT_PER_EARNING))

    if reward <= 0:
        return web.json_response({"ok": True, "rewarded": False, "reason": "zero_reward"})

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")

        user = conn.execute(
            "SELECT user_id FROM users WHERE user_id=?", (user_id,)
        ).fetchone()

        if not user:
            conn.rollback()
            raise web.HTTPNotFound(text="User not found")

        try:
            conn.execute(
                """INSERT INTO cpagrip_conversions
                   (conversion_id, user_id, payout_usd, reward, offer_id, status)
                   VALUES (?,?,?,?,?,'approved')""",
                (conversion_id, user_id, payout_usd, reward, offer_id)
            )
        except Exception as e:
            if not is_unique_violation(e):
                raise
            conn.commit()
            return web.json_response({"ok": True, "rewarded": False, "duplicate": True})

        add_balance(conn, user_id, reward, earned=True)
        conn.commit()

    asyncio.create_task(notify_user(
        user_id,
        f"🎁 <b>مكافأة جديدة!</b>\n\n"
        f"أنجزت عرض CPAGrip وربحت <b>{reward} Earnings</b>."
    ))

    logging.info(
        "CPAGrip reward credited: user=%s reward=%s payout=%s conversion=%s",
        user_id, reward, payout_usd, conversion_id
    )

    return web.json_response({"ok": True, "rewarded": True, "reward": reward})


async def api_lootably_offers(request):
    uid = auth_user(request)
    if not LOOTABLY_API_KEY or not LOOTABLY_PLACEMENT_ID:
        raise web.HTTPServiceUnavailable(text=json.dumps({"detail":"Lootably غير مُفعّل بعد"}), content_type="application/json")
    ip = (request.headers.get("X-Forwarded-For", "").split(",")[0].strip() or request.remote or "")
    body = {
        "apiKey": LOOTABLY_API_KEY,
        "placementID": LOOTABLY_PLACEMENT_ID,
        "userData": {"userID": str(uid), "userAgentHeader": request.headers.get("User-Agent", ""), "ipAddress": ip},
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.lootably.com/api/v2/offers/get", json=body, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                data = await resp.json(content_type=None)
                if resp.status != 200 or not data.get("success"):
                    raise RuntimeError(str(data))
    except Exception:
        logging.exception("Lootably offers request failed")
        raise web.HTTPBadGateway(text=json.dumps({"detail":"تعذر تحميل عروض Lootably حالياً"}), content_type="application/json")
    offers = []
    for o in data.get("data", {}).get("offers", []):
        offers.append({
            "id": o.get("offerID"),
            "title": o.get("name"),
            "description": o.get("description", ""),
            "icon": o.get("image", ""),
            "link": o.get("link", ""),
            "reward_usdt": float(o.get("currencyReward") or 0),
            "payout_usd": float(o.get("revenue") or 0),
        })
    return web.json_response({"ok": True, "offers": offers})


async def api_lootably_webhook(request):
    if not LOOTABLY_POSTBACK_SECRET:
        raise web.HTTPServiceUnavailable(text="Lootably webhook is not configured")
    received = request.headers.get("x-lootably-webhook-secret", "")
    if not hmac.compare_digest(received, LOOTABLY_POSTBACK_SECRET):
        raise web.HTTPUnauthorized(text="Invalid Lootably webhook secret")
    try:
        payload = await request.json()
    except Exception:
        raise web.HTTPBadRequest(text="Invalid JSON")
    event = str(payload.get("event", "")).lower()
    data = payload.get("data") or {}
    if event not in ("approved", "pending", "rejected"):
        raise web.HTTPBadRequest(text="Invalid event")
    uid_raw = str(data.get("userID", "")).strip()
    txid = str(data.get("transactionID", "")).strip()
    if not uid_raw.isdigit() or not txid:
        raise web.HTTPBadRequest(text="Invalid userID or transactionID")
    uid = int(uid_raw)
    revenue = float(data.get("revenue") or 0)
    reward_usdt = float(data.get("currencyReward") or 0)
    reward = int(round(reward_usdt / USDT_PER_EARNING))
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute("SELECT user_id FROM users WHERE user_id=?", (uid,)).fetchone()
        if not user:
            conn.rollback()
            raise web.HTTPNotFound(text="User not found")
        existing = conn.execute("SELECT * FROM offer_conversions WHERE provider='lootably' AND provider_conversion_id=?", (txid,)).fetchone()
        if existing:
            old_status = str(existing["status"] or "")
            old_reward = int(existing["reward"] or 0)
            if event == "approved" and old_status != "approved":
                conn.execute("UPDATE offer_conversions SET status='approved',processed_at=CURRENT_TIMESTAMP WHERE id=?", (existing["id"],))
                if reward > 0:
                    add_balance(conn, uid, reward, earned=True)
            elif event == "rejected" and old_status == "approved" and old_reward > 0:
                conn.execute("UPDATE users SET balance=MAX(0,balance-?) WHERE user_id=?", (old_reward, uid))
                conn.execute("UPDATE offer_conversions SET status='rejected',processed_at=CURRENT_TIMESTAMP WHERE id=?", (existing["id"],))
            else:
                conn.execute("UPDATE offer_conversions SET status=? WHERE id=?", (event, existing["id"]))
            conn.commit()
            return web.json_response({"ok": True, "duplicate": True, "status": event})
        status = "approved" if event == "approved" else event
        conn.execute("INSERT INTO offer_conversions(provider,provider_conversion_id,user_id,payout_usd,reward,status,processed_at) VALUES('lootably',?,?,?,?,?,CURRENT_TIMESTAMP)", (txid,uid,revenue,reward,status))
        if event == "approved" and reward > 0:
            add_balance(conn, uid, reward, earned=True)
        conn.commit()
    return web.json_response({"ok": True})


async def api_timewall_config(request):
    auth_user(request)
    return web.json_response({"ok": True, "enabled": bool(TIMEWALL_PLACEMENT_URL), "url": TIMEWALL_PLACEMENT_URL})


async def api_timewall_postback(request):
    """TimeWall GET/POST reward callback. Hash format is configurable; default follows the common userid+revenue+secret scheme."""
    if not TIMEWALL_POSTBACK_SECRET:
        raise web.HTTPServiceUnavailable(text="TimeWall postback is not configured")

    params = dict(request.query)
    if request.method == "POST":
        try:
            params.update({k: v for k, v in (await request.post()).items()})
        except Exception:
            pass

    user_id_raw = str(params.get("userid") or params.get("userID") or "").strip()
    transaction_id = str(params.get("txid") or params.get("transactionID") or "").strip()
    revenue_raw = str(params.get("revenue") or "0").strip()
    currency_raw = str(params.get("currency") or params.get("currencyAmount") or "0").strip()
    received_hash = str(params.get("hash") or "").strip().lower()
    event_type = str(params.get("type") or "credit").strip().lower()

    if not user_id_raw.isdigit() or not transaction_id or not received_hash:
        raise web.HTTPBadRequest(text="Invalid TimeWall postback")

    try:
        revenue = float(revenue_raw or 0)
        currency_amount = float(currency_raw or 0)
    except ValueError:
        raise web.HTTPBadRequest(text="Invalid TimeWall amount")

    if TIMEWALL_HASH_MODE == "userid_revenue_secret":
        raw = user_id_raw + revenue_raw + TIMEWALL_POSTBACK_SECRET
    else:
        raw = user_id_raw + transaction_id + revenue_raw + currency_raw + TIMEWALL_POSTBACK_SECRET
    expected = hashlib.sha256(raw.encode()).hexdigest().lower()
    if not hmac.compare_digest(expected, received_hash):
        raise web.HTTPUnauthorized(text="Invalid TimeWall hash")

    uid = int(user_id_raw)
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT user_id FROM users WHERE user_id=?", (uid,)).fetchone():
            conn.rollback()
            raise web.HTTPNotFound(text="User not found")
        existing = conn.execute("SELECT * FROM timewall_conversions WHERE transaction_id=?", (transaction_id,)).fetchone()
        if existing:
            conn.commit()
            return web.Response(text="ok")

        reward_usdt = currency_amount if currency_amount > 0 else revenue
        reward = int(round(reward_usdt / USDT_PER_EARNING))
        if event_type in ("chargeback", "debit", "reversal", "reversed"):
            reward = -abs(reward)

        conn.execute(
            "INSERT INTO timewall_conversions(transaction_id,user_id,revenue_usd,currency_usdt,reward,event_type,status,processed_at) VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (transaction_id, uid, revenue, reward_usdt, reward, event_type, "approved")
        )
        if reward > 0:
            add_balance(conn, uid, reward, earned=True)
        elif reward < 0:
            conn.execute("UPDATE users SET balance=MAX(0,balance+?) WHERE user_id=?", (reward, uid))
        conn.commit()
    return web.Response(text="ok")


async def api_offers(request):
    uid = auth_user(request)

    with db() as conn:
        rows = conn.execute("""
            SELECT
                id,
                provider,
                provider_offer_id,
                title,
                description,
                image_url,
                tracking_url,
                category,
                payout_usd,
                user_reward,
                countries,
                devices
            FROM offers
            WHERE status='active'
            ORDER BY payout_usd DESC, id DESC
            LIMIT 100
        """).fetchall()

        offers = [{
            "id": r["id"],
            "provider": r["provider"],
            "provider_offer_id": r["provider_offer_id"],
            "title": r["title"],
            "description": r["description"],
            "image_url": r["image_url"],
            "tracking_url": r["tracking_url"],
            "category": r["category"],
            "payout_usd": float(r["payout_usd"] or 0),
            "user_reward": int(r["user_reward"] or 0),
            "countries": r["countries"] or "",
            "devices": r["devices"] or ""
        } for r in rows]

        return web.json_response({
            "ok": True,
            "offers": offers
        })


async def api_create_task(request):
    uid = auth_user(request)
    data = await request.json()

    title = str(data.get("title", "")).strip()
    link = str(data.get("link", "")).strip()
    platform = str(data.get("platform", "")).strip().lower()
    task_type = str(data.get("task_type", data.get("type", ""))).strip().lower()
    try:
        quantity = int(data.get("quantity", 0))
    except (TypeError, ValueError):
        quantity = 0

    selected = CAMPAIGN_PRICES.get(platform, {}).get(task_type)
    if not title or not link or not selected or quantity <= 0:
        raise web.HTTPBadRequest(text=json.dumps({"detail": "بيانات الحملة غير صحيحة"}), content_type="application/json")

    unit_quantity = int(selected["unit_quantity"])
    if quantity % unit_quantity != 0:
        raise web.HTTPBadRequest(text=json.dumps({"detail": f"الكمية يجب أن تكون من مضاعفات {unit_quantity}"}), content_type="application/json")

    units = quantity / unit_quantity
    advertiser_price = round(units * float(selected["advertiser_price"]), 8)
    user_reward_usdt = float(selected["user_reward"])
    reward = int(round(user_reward_usdt / USDT_PER_EARNING))
    budget = int(quantity * reward)

    if advertiser_price <= 0 or reward <= 0 or budget <= 0:
        raise web.HTTPBadRequest(text=json.dumps({"detail": "تعذر حساب سعر الحملة"}), content_type="application/json")

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cur = conn.execute(
            """INSERT INTO tasks(owner_id,title,link,reward,budget,status,platform,task_type,quantity,advertiser_price_usdt,user_reward_usdt)
               VALUES(?,?,?,?,?,'pending_payment',?,?,?,?,?)""",
            (uid, title, link, reward, budget, platform, task_type, quantity, advertiser_price, user_reward_usdt)
        )
        task_id = cur.lastrowid
        pcur = conn.execute(
            """INSERT INTO campaign_payments(task_id,owner_id,amount_usdt,currency,network,payment_address,status)
               VALUES(?,?,?,?,?,?,'pending')""",
            (task_id, uid, advertiser_price, CAMPAIGN_PAYMENT_CURRENCY, CAMPAIGN_PAYMENT_NETWORK, CAMPAIGN_PAYMENT_ADDRESS)
        )
        payment_id = pcur.lastrowid
        conn.commit()

    return web.json_response({
        "ok": True,
        "task_id": task_id,
        "status": "pending_payment",
        "payment": {
            "id": payment_id,
            "amount_usdt": advertiser_price,
            "currency": CAMPAIGN_PAYMENT_CURRENCY,
            "network": CAMPAIGN_PAYMENT_NETWORK,
            "address": CAMPAIGN_PAYMENT_ADDRESS,
            "status": "pending"
        },
        "user_reward_usdt": user_reward_usdt,
        "total_user_rewards_usdt": round(quantity * user_reward_usdt, 8)
    })


async def api_submit_campaign_payment(request):
    uid = auth_user(request)
    payment_id = int(request.match_info["payment_id"])
    data = await request.json()
    tx_hash = str(data.get("tx_hash", "")).strip()

    if not re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
        raise web.HTTPBadRequest(text=json.dumps({"detail": "أدخل Transaction Hash صحيح لشبكة BSC"}), content_type="application/json")

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        payment = conn.execute("SELECT * FROM campaign_payments WHERE id=? AND owner_id=?", (payment_id, uid)).fetchone()
        if not payment:
            raise web.HTTPNotFound(text=json.dumps({"detail": "طلب الدفع غير موجود"}), content_type="application/json")
        if payment["status"] != "pending":
            raise web.HTTPConflict(text=json.dumps({"detail": "تم إرسال هذا الدفع للمراجعة مسبقاً"}), content_type="application/json")
        duplicate = conn.execute("SELECT id FROM campaign_payments WHERE tx_hash=?", (tx_hash,)).fetchone()
        if duplicate:
            raise web.HTTPConflict(text=json.dumps({"detail": "هذا Transaction Hash مستخدم مسبقاً"}), content_type="application/json")
        conn.execute("UPDATE campaign_payments SET tx_hash=?,submitted_at=CURRENT_TIMESTAMP WHERE id=?", (tx_hash, payment_id))
        conn.commit()

        task = conn.execute("SELECT title FROM tasks WHERE id=?", (payment["task_id"],)).fetchone()
        owner = conn.execute("SELECT full_name, username FROM users WHERE user_id=?", (uid,)).fetchone()

    uname = f"@{owner['username']}" if owner and owner["username"] else "بدون يوزر"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ موافقة", callback_data=f"pay_ok:{payment_id}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"pay_no:{payment_id}")
        ]]
    )
    asyncio.create_task(notify_admin(
        "💳 <b>طلب دفع حملة جديد</b>\n\n"
        f"المعلن: {html.quote(owner['full_name'] if owner else '')} ({uname})\n"
        f"الحملة: {html.quote(task['title'] if task else '')}\n"
        f"المبلغ: <b>{float(payment['amount_usdt']):.2f} USDT</b> ({payment['network']})\n"
        f"Tx Hash: <code>{html.quote(tx_hash)}</code>\n"
        f"رقم الطلب: #{payment_id}",
        reply_markup=keyboard
    ))

    return web.json_response({"ok": True, "payment_id": payment_id, "status": "pending", "message": "تم إرسال الدفع وبانتظار المراجعة"})


async def api_my_campaign_payments(request):
    uid = auth_user(request)
    with db() as conn:
        rows = conn.execute(
            """SELECT p.id,p.task_id,p.amount_usdt,p.currency,p.network,p.payment_address,p.tx_hash,p.status,p.created_at,p.submitted_at,p.processed_at,
                      t.title,t.status AS campaign_status
               FROM campaign_payments p JOIN tasks t ON t.id=p.task_id
               WHERE p.owner_id=? ORDER BY p.id DESC LIMIT 50""", (uid,)
        ).fetchall()
    return web.json_response({"payments": [dict(r) for r in rows]})


async def verify_telegram_join(link: str, user_id: int):
    """
    يحاول التحقق فعلياً من انضمام المستخدم للقناة عبر البوت. إذا تعذر التحقق،
    نرجع None حتى لا نغيّر سلوك المهام الديناميكية الحالية.
    """
    if not BOT_INSTANCE or not link:
        return False
    m = re.search(r"t\.me/([A-Za-z0-9_]+)", link)
    if not m:
        return False
    channel = "@" + m.group(1)
    try:
        member = await BOT_INSTANCE.get_chat_member(channel, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        logging.exception("Telegram membership verification failed")
        return False


async def api_complete_task(request):
    uid = auth_user(request)
    task_id = int(request.match_info["task_id"])

    with db() as conn:
        precheck_task = conn.execute(
            "SELECT platform, link FROM tasks WHERE id=? AND status='active'",
            (task_id,)
        ).fetchone()

    if precheck_task and precheck_task["platform"] == "telegram":
        verified = await verify_telegram_join(precheck_task["link"], uid)
        if verified is False:
            raise web.HTTPBadRequest(
                text=json.dumps({"detail": "لازم تنضم للقناة أولاً ثم ارجع أكّد المهمة"}),
                content_type="application/json"
            )

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")

        task = conn.execute(
            "SELECT * FROM tasks WHERE id=? AND status='active'",
            (task_id,)
        ).fetchone()

        if not task:
            raise web.HTTPNotFound(
                text=json.dumps({"detail": "المهمة غير موجودة"}),
                content_type="application/json"
            )

        if task["owner_id"] is not None and int(task["owner_id"]) == uid:
            raise web.HTTPForbidden(
                text=json.dumps({"detail": "لا يمكنك تنفيذ حملتك بنفسك"}),
                content_type="application/json"
            )

        if conn.execute(
            "SELECT 1 FROM task_completions WHERE task_id=? AND user_id=?",
            (task_id, uid)
        ).fetchone():
            raise web.HTTPConflict(
                text=json.dumps({"detail": "لقد أكملت هذه المهمة مسبقاً"}),
                content_type="application/json"
            )

        if task["spent"] + task["reward"] > task["budget"]:
            raise web.HTTPBadRequest(
                text=json.dumps({"detail": "ميزانية المهمة انتهت"}),
                content_type="application/json"
            )

        # Atomic completion + budget accounting.
        conn.execute(
            """INSERT INTO task_completions(task_id,user_id,reward)
               VALUES(?,?,?)""",
            (task_id, uid, task["reward"])
        )
        conn.execute(
            "UPDATE tasks SET spent=spent+? WHERE id=?",
            (task["reward"], task_id)
        )
        conn.execute(
            """UPDATE users
               SET balance=balance+?,
                   total_earned=total_earned+?,
                   completed_tasks=completed_tasks+1
               WHERE user_id=?""",
            (task["reward"], task["reward"], uid)
        )

        new_spent = int(task["spent"]) + int(task["reward"])
        remaining = int(task["budget"]) - new_spent
        if remaining < int(task["reward"]):
            # No further completion can be paid. Release the unused reserved budget
            # back to the task owner.
            if remaining > 0 and task["owner_id"]:
                conn.execute(
                    "UPDATE users SET balance=balance+? WHERE user_id=?",
                    (remaining, task["owner_id"]),
                )
            conn.execute("UPDATE tasks SET status='completed' WHERE id=?", (task_id,))

        conn.commit()

    return web.json_response({"ok": True, "reward": task["reward"]})


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

async def api_x_start(request):
    uid = auth_user(request)
    if not X_CLIENT_ID or not X_REDIRECT_URI:
        raise web.HTTPServiceUnavailable(
            text=json.dumps({"detail": "تحقق X غير مفعّل على السيرفر بعد."}),
            content_type="application/json"
        )
    verifier = secrets.token_urlsafe(64)
    challenge = _pkce_challenge(verifier)
    state = secrets.token_urlsafe(32)
    with db() as conn:
        conn.execute("DELETE FROM x_oauth_states WHERE created_at < ?", (int(time.time()) - 900,))
        conn.execute("INSERT INTO x_oauth_states(state,user_id,code_verifier,created_at) VALUES(?,?,?,?)", (state, uid, verifier, int(time.time())))
        conn.commit()
    params = {
        "response_type": "code",
        "client_id": X_CLIENT_ID,
        "redirect_uri": X_REDIRECT_URI,
        "scope": "users.read tweet.read follows.read offline.access",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256"
    }
    return web.json_response({"authorization_url": "https://x.com/i/oauth2/authorize?" + urlencode(params)})

async def api_x_callback(request):
    error = request.query.get("error")
    if error:
        return web.HTTPFound(WEBAPP_URL + "?x_verified=0&x_error=" + error)
    state = request.query.get("state", "")
    code = request.query.get("code", "")
    if not state or not code:
        return web.HTTPFound(WEBAPP_URL + "?x_verified=0&x_error=invalid_callback")
    with db() as conn:
        row = conn.execute("SELECT * FROM x_oauth_states WHERE state=?", (state,)).fetchone()
        conn.execute("DELETE FROM x_oauth_states WHERE state=?", (state,))
        conn.commit()
    if not row or int(time.time()) - int(row["created_at"]) > 900:
        return web.HTTPFound(WEBAPP_URL + "?x_verified=0&x_error=expired_state")
    uid = int(row["user_id"])
    token_data = {
        "code": code,
        "grant_type": "authorization_code",
        "client_id": X_CLIENT_ID,
        "redirect_uri": X_REDIRECT_URI,
        "code_verifier": row["code_verifier"]
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("https://api.x.com/2/oauth2/token", data=token_data, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                token = await resp.json(content_type=None)
            if resp.status != 200 or not token.get("access_token"):
                logging.warning("X token exchange failed: %s", token)
                return web.HTTPFound(WEBAPP_URL + "?x_verified=0&x_error=token_exchange")
            access_token = token["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get("https://api.x.com/2/users/me", headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                me = await resp.json(content_type=None)
            if resp.status != 200 or not (me.get("data") or {}).get("id"):
                return web.HTTPFound(WEBAPP_URL + "?x_verified=0&x_error=user_lookup")
            x_user_id = str(me["data"]["id"])
            async with session.get(f"https://api.x.com/2/users/by/username/{X_TARGET_USERNAME}", headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                target = await resp.json(content_type=None)
            target_id = str((target.get("data") or {}).get("id", ""))
            if resp.status != 200 or not target_id:
                return web.HTTPFound(WEBAPP_URL + "?x_verified=0&x_error=target_lookup")
            following_url = f"https://api.x.com/2/users/{x_user_id}/following"
            found = False
            pagination_token = None
            while True:
                params = {"max_results": 1000, "user.fields": "id,username"}
                if pagination_token:
                    params["pagination_token"] = pagination_token
                async with session.get(following_url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    following = await resp.json(content_type=None)
                if resp.status != 200:
                    logging.warning("X following lookup failed: %s", following)
                    return web.HTTPFound(WEBAPP_URL + "?x_verified=0&x_error=following_lookup")
                if any(str(item.get("id")) == target_id for item in (following.get("data") or [])):
                    found = True
                    break
                pagination_token = (following.get("meta") or {}).get("next_token")
                if not pagination_token:
                    break
                # Avoid unbounded pagination for a task verification.
                if len((following.get("data") or [])) < 1000:
                    break
            if not found:
                return web.HTTPFound(WEBAPP_URL + "?x_verified=0&x_error=not_following")
    except Exception:
        logging.exception("X verification failed")
        return web.HTTPFound(WEBAPP_URL + "?x_verified=0&x_error=verification_failed")
    reward = FIXED_X_REWARD
    try:
        with db() as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute("INSERT INTO fixed_completions(kind,user_id,reward) VALUES('x',?,?)", (uid, reward))
            conn.execute("UPDATE users SET balance=balance+?,total_earned=total_earned+?,completed_tasks=completed_tasks+1 WHERE user_id=?", (reward, reward, uid))
            conn.commit()
    except Exception as e:
        if is_unique_violation(e):
            return web.HTTPFound(WEBAPP_URL + "?x_verified=1&x_duplicate=1")
        raise
    return web.HTTPFound(WEBAPP_URL + "?x_verified=1")

async def api_fixed_complete(request):
    uid = auth_user(request)
    kind = request.match_info["kind"]

    if kind not in ("x", "telegram"):
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "Unknown fixed task"}),
            content_type="application/json"
        )

    if kind == "x":
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "مهمة X تحتاج التحقق من حساب X أولاً."}),
            content_type="application/json"
        )

    verified = await verify_telegram_join(TELEGRAM_URL, uid)
    if not verified:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "لازم تنضم للقناة الرسمية أولاً ثم أعد المحاولة."}),
            content_type="application/json"
        )

    reward = FIXED_TELEGRAM_REWARD
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                """INSERT INTO fixed_completions(kind,user_id,reward)
                   VALUES(?,?,?)""",
                (kind, uid, reward)
            )
        except Exception as e:
            if not is_unique_violation(e):
                raise
            raise web.HTTPConflict(
                text=json.dumps({"detail": "لقد أكملت هذه المهمة مسبقاً"}),
                content_type="application/json"
            )

        conn.execute(
            """UPDATE users
               SET balance=balance+?,
                   total_earned=total_earned+?,
                   completed_tasks=completed_tasks+1
               WHERE user_id=?""",
            (reward, reward, uid)
        )
        conn.commit()

    return web.json_response({"ok": True, "reward": reward})


async def api_daily_checkin(request):
    uid = auth_user(request)
    today = today_utc()
    yesterday = yesterday_utc()

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute(
            "SELECT current_streak,best_streak,total_checkins,last_checkin FROM users WHERE user_id=?",
            (uid,)
        ).fetchone()

        try:
            conn.execute(
                "INSERT INTO daily_checkins(user_id,day,reward) VALUES(?,?,?)",
                (uid, today, DAILY_CHECKIN_REWARD)
            )
        except Exception as e:
            if not is_unique_violation(e):
                raise
            raise web.HTTPConflict(
                text=json.dumps({"detail": "تم تسجيل حضورك اليوم بالفعل"}),
                content_type="application/json"
            )

        old_streak = int(user["current_streak"] or 0)
        new_streak = old_streak + 1 if user["last_checkin"] == yesterday else 1
        best = max(int(user["best_streak"] or 0), new_streak)

        conn.execute(
            """UPDATE users
               SET balance=balance+?,
                   total_earned=total_earned+?,
                   current_streak=?,
                   best_streak=?,
                   total_checkins=total_checkins+1,
                   last_checkin=?
               WHERE user_id=?""",
            (DAILY_CHECKIN_REWARD, DAILY_CHECKIN_REWARD,
             new_streak, best, today, uid)
        )
        conn.commit()

    return web.json_response({"ok": True, "streak": new_streak, "reward": DAILY_CHECKIN_REWARD})


async def api_watch_ad(request):
    # لا تتم إضافة أي رصيد من طلب العميل. المكافأة الحقيقية تأتي فقط من
    # server-to-server postback موثوق من مزود الإعلانات.
    auth_user(request)
    raise web.HTTPBadRequest(
        text=json.dumps({"detail": "المكافأة لا تُسجل من التطبيق مباشرة. يجب أن يرسل مزود الإعلانات تأكيداً للسيرفر."}),
        content_type="application/json"
    )


async def api_ads_postback(request):
    """Secure ad provider callback. Ten verified ad completions = 1 Earnings ($0.01)."""
    if not AD_REWARD_POSTBACK_SECRET:
        raise web.HTTPServiceUnavailable(text="Ad reward postback is not configured")
    try:
        data = await request.json()
    except Exception:
        raise web.HTTPBadRequest(text="Invalid JSON")

    secret = str(data.get("secret", "")).strip()
    transaction_id = str(data.get("transaction_id", "")).strip()
    user_id_raw = str(data.get("user_id", "")).strip()
    if not hmac.compare_digest(secret, AD_REWARD_POSTBACK_SECRET):
        raise web.HTTPUnauthorized(text="Invalid postback secret")
    if not transaction_id or not user_id_raw.isdigit():
        raise web.HTTPBadRequest(text="Invalid ad postback")

    user_id = int(user_id_raw)
    today = today_utc()
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,)).fetchone():
            conn.rollback()
            raise web.HTTPNotFound(text="User not found")
        duplicate = conn.execute(
            "SELECT id FROM ad_reward_conversions WHERE transaction_id=?", (transaction_id,)
        ).fetchone()
        if duplicate:
            conn.commit()
            return web.json_response({"ok": True, "duplicate": True})
        daily = conn.execute(
            "SELECT views FROM ad_views WHERE user_id=? AND day=?", (user_id, today)
        ).fetchone()
        views = int(daily["views"] if daily else 0)
        if views >= AD_DAILY_LIMIT:
            conn.rollback()
            raise web.HTTPTooManyRequests(text="Daily ad limit reached")

        conn.execute(
            "INSERT INTO ad_reward_conversions(transaction_id,user_id,reward) VALUES(?,?,0)",
            (transaction_id, user_id)
        )
        conn.execute(
            "INSERT INTO ad_views(user_id,day,views) VALUES(?,?,1) "
            "ON CONFLICT(user_id,day) DO UPDATE SET views=views+1",
            (user_id, today)
        )
        new_views = views + 1
        reward = 0
        if new_views % max(1, AD_VIEWS_PER_REWARD) == 0:
            reward = AD_REWARD
            add_balance(conn, user_id, reward, earned=True)
        conn.commit()

    return web.json_response({
        "ok": True,
        "views_today": new_views,
        "rewarded": reward > 0,
        "reward": reward,
        "ads_per_reward": AD_VIEWS_PER_REWARD,
    })


async def api_leaderboard(request):
    auth_user(request)
    with db() as conn:
        rows = conn.execute("""
            SELECT user_id, full_name, username, total_earned
            FROM users
            ORDER BY total_earned DESC, user_id ASC
            LIMIT 100
        """).fetchall()

        return web.json_response({
            "leaderboard": [{
                "telegram_id": r["user_id"],
                "name": r["full_name"] or r["username"] or f"User {r['user_id']}",
                "earnings": r["total_earned"]
            } for r in rows]
        })


async def api_withdraw(request):
    uid = auth_user(request)
    data = await request.json()
    address = str(data.get("address", "")).strip()

    if not re.fullmatch(r"0x[a-fA-F0-9]{40}", address):
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "عنوان المحفظة يجب أن يكون عنوان BSC صالحاً"}),
            content_type="application/json"
        )

    if not address:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "عنوان المحفظة مطلوب"}),
            content_type="application/json"
        )

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        user = conn.execute(
            "SELECT balance FROM users WHERE user_id=?", (uid,)
        ).fetchone()
        amount = float(user["balance"]) * USDT_PER_EARNING

        if amount < MIN_WITHDRAW_USDT:
            raise web.HTTPBadRequest(
                text=json.dumps({"detail": f"الحد الأدنى للسحب {MIN_WITHDRAW_USDT:g} USDT"}),
                content_type="application/json"
            )

        # Reserve/zero the balance while the request is Pending.
        conn.execute(
            "UPDATE users SET balance=0 WHERE user_id=? AND balance=?",
            (uid, user["balance"])
        )
        cur = conn.execute(
            """INSERT INTO withdrawals(user_id,amount_usdt,address,status)
               VALUES(?,?,?,'Pending')""",
            (uid, amount, address)
        )
        conn.commit()

    return web.json_response({
        "ok": True,
        "withdrawal_id": cur.lastrowid,
        "status": "Pending",
        "amount_usdt": amount
    })


async def api_my_withdrawals(request):
    uid = auth_user(request)
    with db() as conn:
        rows = conn.execute(
            """SELECT id, amount_usdt, address, status, created_at, processed_at
               FROM withdrawals WHERE user_id=? ORDER BY id DESC LIMIT 20""",
            (uid,),
        ).fetchall()
    return web.json_response({"withdrawals": [dict(r) for r in rows]})


def require_admin(request):
    uid = auth_user(request)
    if not ADMIN_USER_ID or uid != ADMIN_USER_ID:
        raise web.HTTPForbidden(
            text=json.dumps({"detail": "Admin access required"}),
            content_type="application/json"
        )
    return uid


async def verify_bsc_campaign_payment(payment):
    """Verify successful BSC USDT transfer to the configured receiving address."""
    tx_hash = (payment["tx_hash"] or "").strip()
    if not re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
        return False, 0, "Invalid transaction hash"
    try:
        async with aiohttp.ClientSession() as session:
            async def rpc(method, params):
                async with session.post(BSC_RPC_URL, json={"jsonrpc":"2.0","id":1,"method":method,"params":params}, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    data = await resp.json(content_type=None)
                    if resp.status != 200 or data.get("error"):
                        raise RuntimeError(str(data.get("error") or resp.status))
                    return data.get("result")
            tx = await rpc("eth_getTransactionByHash", [tx_hash])
            receipt = await rpc("eth_getTransactionReceipt", [tx_hash])
            if not tx or not receipt or receipt.get("status") != "0x1":
                return False, 0, "Transaction not successful or not found"
            latest = await rpc("eth_blockNumber", [])
            tx_block = int(tx.get("blockNumber", "0x0"), 16)
            latest_block = int(latest or "0x0", 16)
            confirmations = max(0, latest_block - tx_block + 1) if tx_block else 0
            if confirmations < BSC_CONFIRMATIONS_REQUIRED:
                return False, confirmations, f"Only {confirmations} confirmations"
            transfer_topic = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a5df523b3ef"
            target = CAMPAIGN_PAYMENT_ADDRESS.lower().replace("0x", "").rjust(64, "0")
            amount_required = int(round(float(payment["amount_usdt"]) * 10**18))
            found = False
            for log in receipt.get("logs", []):
                if str(log.get("address", "")).lower() != BSC_USDT_CONTRACT:
                    continue
                topics = log.get("topics") or []
                if len(topics) < 3 or str(topics[0]).lower() != transfer_topic:
                    continue
                to_topic = str(topics[2]).lower().replace("0x", "").rjust(64, "0")
                if to_topic != target:
                    continue
                value = int(str(log.get("data", "0x0")), 16)
                if value >= amount_required:
                    found = True
                    break
            return (found, confirmations, "Verified" if found else "No matching USDT transfer")
    except Exception as e:
        logging.exception("BSC verification failed")
        return False, 0, str(e)


async def api_admin_campaign_payment_verify_chain(request):
    require_admin(request)
    payment_id = int(request.match_info["payment_id"])
    with db() as conn:
        payment = conn.execute("SELECT * FROM campaign_payments WHERE id=?", (payment_id,)).fetchone()
    if not payment:
        raise web.HTTPNotFound(text=json.dumps({"detail":"طلب الدفع غير موجود"}), content_type="application/json")
    ok, confirmations, reason = await verify_bsc_campaign_payment(payment)
    with db() as conn:
        conn.execute(
            "UPDATE campaign_payments SET chain_verified=?,confirmations=?,verified_at=CURRENT_TIMESTAMP,verification_error=? WHERE id=?",
            (1 if ok else 0, confirmations, "" if ok else reason, payment_id)
        )
        conn.commit()
    return web.json_response({"ok": ok, "confirmations": confirmations, "reason": reason})


async def api_admin_campaign_payments(request):
    require_admin(request)
    with db() as conn:
        rows = conn.execute(
            """SELECT p.id,p.task_id,p.owner_id,p.amount_usdt,p.currency,p.network,p.payment_address,p.tx_hash,p.status,
                      p.created_at,p.submitted_at,p.processed_at,p.chain_verified,p.confirmations,p.verified_at,p.verification_error,t.title,t.platform,t.task_type,t.quantity,
                      t.advertiser_price_usdt,t.user_reward_usdt,t.status AS campaign_status,u.full_name,u.username
               FROM campaign_payments p JOIN tasks t ON t.id=p.task_id JOIN users u ON u.user_id=p.owner_id
               ORDER BY p.id DESC LIMIT 200"""
        ).fetchall()
    return web.json_response({"payments": [dict(r) for r in rows]})


def process_campaign_payment_decision(payment_id, approve: bool, tx_hash_override=None):
    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        payment = conn.execute("SELECT * FROM campaign_payments WHERE id=?", (payment_id,)).fetchone()
        if not payment:
            conn.rollback()
            return None, "طلب دفع الحملة غير موجود"
        if payment["status"] != "pending":
            conn.rollback()
            return payment, "تمت معالجة طلب الدفع مسبقاً"

        if approve:
            final_hash = tx_hash_override or (payment["tx_hash"] or "")
            if not re.fullmatch(r"0x[a-fA-F0-9]{64}", final_hash):
                conn.rollback()
                return payment, "لا يمكن الموافقة بدون Transaction Hash صحيح"
            duplicate = conn.execute(
                "SELECT id FROM campaign_payments WHERE tx_hash=? AND id<>?",
                (final_hash, payment_id)
            ).fetchone()
            if duplicate:
                conn.rollback()
                return payment, "هذا Transaction Hash مستخدم مسبقاً"
            conn.execute("UPDATE campaign_payments SET tx_hash=?,status='approved',processed_at=CURRENT_TIMESTAMP WHERE id=?", (final_hash, payment_id))
            conn.execute("UPDATE tasks SET status='active' WHERE id=? AND status='pending_payment'", (payment["task_id"],))
        else:
            conn.execute("UPDATE campaign_payments SET status='rejected',processed_at=CURRENT_TIMESTAMP WHERE id=?", (payment_id,))
            conn.execute("UPDATE tasks SET status='rejected' WHERE id=? AND status='pending_payment'", (payment["task_id"],))
        conn.commit()

    return payment, None


async def api_admin_campaign_payment_status(request):
    require_admin(request)
    payment_id = int(request.match_info["payment_id"])
    data = await request.json()
    status = str(data.get("status", "")).strip().lower()
    tx_hash = str(data.get("tx_hash", "")).strip()

    if status not in ("approved", "rejected"):
        raise web.HTTPBadRequest(text=json.dumps({"detail": "الحالة يجب أن تكون approved أو rejected"}), content_type="application/json")

    if status == "approved":
        with db() as conn:
            current_payment = conn.execute("SELECT * FROM campaign_payments WHERE id=?", (payment_id,)).fetchone()
        if not current_payment:
            raise web.HTTPNotFound(text=json.dumps({"detail":"طلب الدفع غير موجود"}), content_type="application/json")
        effective_hash = tx_hash or (current_payment["tx_hash"] or "")
        if effective_hash and effective_hash != (current_payment["tx_hash"] or ""):
            with db() as conn:
                conn.execute("UPDATE campaign_payments SET tx_hash=? WHERE id=?", (effective_hash, payment_id))
                conn.commit()
            with db() as conn:
                current_payment = conn.execute("SELECT * FROM campaign_payments WHERE id=?", (payment_id,)).fetchone()
        ok_chain, confirmations, chain_reason = await verify_bsc_campaign_payment(current_payment)
        with db() as conn:
            conn.execute("UPDATE campaign_payments SET chain_verified=?,confirmations=?,verified_at=CURRENT_TIMESTAMP,verification_error=? WHERE id=?", (1 if ok_chain else 0, confirmations, "" if ok_chain else chain_reason, payment_id))
            conn.commit()
        if not ok_chain:
            raise web.HTTPBadRequest(text=json.dumps({"detail": f"تعذر التحقق من الدفع على BSC: {chain_reason}"}), content_type="application/json")

    payment, error = process_campaign_payment_decision(payment_id, approve=(status == "approved"), tx_hash_override=tx_hash or None)

    if error:
        code = web.HTTPNotFound if not payment else (web.HTTPBadRequest if "Transaction" in error or "مستخدم" in error else web.HTTPConflict)
        raise code(text=json.dumps({"detail": error}), content_type="application/json")

    if status == "approved":
        asyncio.create_task(notify_user(
            payment["owner_id"],
            f"✅ <b>{bt(payment['owner_id'], 'approved')}</b>\n\n"
            f"المبلغ: {float(payment['amount_usdt']):.2f} USDT\n"
            + bt(payment["owner_id"], "active")
        ))
    else:
        asyncio.create_task(notify_user(
            payment["owner_id"],
            f"❌ <b>{bt(payment['owner_id'], 'rejected')}</b>\n\n"
            f"المبلغ: {float(payment['amount_usdt']):.2f} USDT\n"
            + bt(payment["owner_id"], "pay_help")
        ))

    return web.json_response({"ok": True, "payment_id": payment_id, "status": status, "campaign_status": "active" if status == "approved" else "rejected"})


async def api_admin_withdrawals(request):
    require_admin(request)
    with db() as conn:
        rows = conn.execute(
            """SELECT w.id,w.user_id,w.amount_usdt,w.address,w.status,w.tx_hash,w.created_at,w.processed_at,
                      u.full_name,u.username
               FROM withdrawals w JOIN users u ON u.user_id=w.user_id
               ORDER BY w.id DESC LIMIT 200"""
        ).fetchall()
    return web.json_response({"withdrawals": [dict(r) for r in rows]})


async def api_admin_withdrawal_status(request):
    require_admin(request)
    withdrawal_id = int(request.match_info["withdrawal_id"])
    data = await request.json()
    status = str(data.get("status", "")).strip().capitalize()
    tx_hash = str(data.get("tx_hash", "")).strip()
    if status not in ("Approved", "Rejected", "Paid"):
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "الحالة يجب أن تكون Approved أو Rejected"}),
            content_type="application/json"
        )

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        w = conn.execute("SELECT * FROM withdrawals WHERE id=?", (withdrawal_id,)).fetchone()
        if not w:
            raise web.HTTPNotFound(
                text=json.dumps({"detail": "طلب السحب غير موجود"}),
                content_type="application/json"
            )
        if w["status"] != "Pending":
            raise web.HTTPConflict(
                text=json.dumps({"detail": "تمت معالجة طلب السحب مسبقاً"}),
                content_type="application/json"
            )

        if status == "Paid":
            if not re.fullmatch(r"0x[a-fA-F0-9]{64}", tx_hash):
                conn.rollback()
                raise web.HTTPBadRequest(
                    text=json.dumps({"detail": "لا يمكن تسجيل Paid بدون Transaction Hash صحيح"}),
                    content_type="application/json"
                )
        elif status == "Rejected":
            refund = int(round(float(w["amount_usdt"]) / USDT_PER_EARNING))
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (refund, w["user_id"]))

        if status == "Paid":
            conn.execute(
                "UPDATE withdrawals SET status=?, tx_hash=?, processed_at=CURRENT_TIMESTAMP WHERE id=?",
                (status, tx_hash, withdrawal_id),
            )
        else:
            conn.execute(
                "UPDATE withdrawals SET status=?, processed_at=CURRENT_TIMESTAMP WHERE id=?",
                (status, withdrawal_id),
            )
        conn.commit()

    if status in ("Approved", "Paid"):
        asyncio.create_task(notify_user(
            w["user_id"],
            f"✅ <b>{bt(w['user_id'], 'withdraw_approved')}</b>\n\n"
            f"Amount: {float(w['amount_usdt']):.2f} USDT\n"
            f"Address: <code>{html.quote(w['address'])}</code>\n"
            + ("\nTx Hash: <code>" + html.quote(tx_hash) + "</code>" if status == "Paid" else "\n" + bt(w["user_id"], "transfer_soon"))
        ))
    else:
        asyncio.create_task(notify_user(
            w["user_id"],
            f"❌ <b>{bt(w['user_id'], 'withdraw_rejected')}</b>\n\n"
            f"Amount: {float(w['amount_usdt']):.2f} USDT\n"
            + bt(w["user_id"], "refund") + "\n"
            + bt(w["user_id"], "contact")
        ))

    return web.json_response({"ok": True, "status": status})


async def api_settings(request):
    uid = auth_user(request)

    if request.method == "GET":
        await apply_auto_country(request, uid)
        with db() as conn:
            row = conn.execute(
                "SELECT lang,country,dark_mode,country_auto FROM settings WHERE user_id=?",
                (uid,)
            ).fetchone()
            return web.json_response({
                "lang": row["lang"],
                "country": row["country"],
                "darkMode": bool(row["dark_mode"]),
                "countryAuto": bool(row["country_auto"])
            })

    data = await request.json()
    lang = str(data.get("lang", "ar"))[:5]
    country = str(data.get("country", "DZ"))[:5].upper()
    dark = 1 if bool(data.get("darkMode", True)) else 0
    has_country = "country" in data
    if lang not in ("ar", "en", "fr"):
        lang = "ar"

    with db() as conn:
        current = conn.execute("SELECT country_auto FROM settings WHERE user_id=?", (uid,)).fetchone()
        country_auto = 0 if has_country else int(current["country_auto"] if current else 1)
        conn.execute(
            """INSERT INTO settings(user_id,lang,country,dark_mode,country_auto)
               VALUES(?,?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 lang=excluded.lang,
                 country=excluded.country,
                 dark_mode=excluded.dark_mode,
                 country_auto=excluded.country_auto""",
            (uid, lang, country, dark, country_auto)
        )
        conn.commit()

    return web.json_response({"ok": True, "lang": lang, "country": country, "darkMode": bool(dark)})


async def health(request):
    return web.json_response({"ok": True, "service": "Rayan Coin API"})


async def options_handler(request):
    return web.Response(status=204)


# ============================================================
# TELEGRAM BOT
# ============================================================

BOT_TRANSLATIONS = {
    "ar": {
        "welcome": "مرحباً بك يا {name} في منصة Rayan Coin! 🪙\n\nتم تسجيل حسابك. افتح التطبيق لعرض بياناتك الحقيقية.",
        "open": "🚀 فتح التطبيق", "tasks": "🎯 المهام", "account": "👤 حسابي",
        "profile": "👤 معلومات الحساب", "back": "⬅️ عودة", "tasks_msg": "🎯 <b>المهام</b>\n\nافتح التطبيق لعرض المهام الحقيقية وتنفيذها وتسجيل المكافآت.",
        "welcome_again": "مرحباً بك مجدداً يا {name} في <b>Rayan Coin</b>! 🪙",
        "approved": "تمت الموافقة على دفعة حملتك!", "rejected": "تعذّر تأكيد دفعة حملتك.",
        "active": bt(payment["owner_id"], "active"), "pay_help": bt(payment["owner_id"], "pay_help")
    },
    "en": {
        "welcome": "Welcome {name} to Rayan Coin! 🪙\n\nYour account has been registered. Open the app to view your real data.",
        "open": "🚀 Open App", "tasks": "🎯 Tasks", "account": "👤 Account",
        "profile": "👤 Account information", "back": "⬅️ Back", "tasks_msg": "🎯 <b>Tasks</b>\n\nOpen the app to view and complete real tasks and receive rewards.",
        "welcome_again": "Welcome back {name} to <b>Rayan Coin</b>! 🪙",
        "approved": "Your campaign payment was approved!", "rejected": "Your campaign payment could not be confirmed.",
        "active": "Your campaign is now active and visible to users.", "pay_help": "Check the Transaction Hash and contact us if you need help.",
        "withdraw_approved": "Your withdrawal request was approved!", "withdraw_rejected": "Your withdrawal request was rejected.", "transfer_soon": "The transfer will arrive shortly.", "refund": "The amount has been returned to your balance.", "contact": "Contact us if you need clarification."
    },
    "fr": {
        "welcome": "Bienvenue {name} sur Rayan Coin ! 🪙\n\nVotre compte a été enregistré. Ouvrez l’application pour voir vos données réelles.",
        "open": "🚀 Ouvrir l’application", "tasks": "🎯 Tâches", "account": "👤 Compte",
        "profile": "👤 Informations du compte", "back": "⬅️ Retour", "tasks_msg": "🎯 <b>Tâches</b>\n\nOuvrez l’application pour voir et effectuer les tâches réelles et recevoir vos récompenses.",
        "welcome_again": "Bon retour {name} sur <b>Rayan Coin</b> ! 🪙",
        "approved": "Le paiement de votre campagne a été approuvé !", "rejected": "Le paiement de votre campagne n’a pas pu être confirmé.",
        "active": "Votre campagne est maintenant active et visible par les utilisateurs.", "pay_help": "Vérifiez le Transaction Hash et contactez-nous si vous avez besoin d’aide.",
        "withdraw_approved": "Votre demande de retrait a été approuvée !", "withdraw_rejected": "Votre demande de retrait a été refusée.", "transfer_soon": "Le transfert arrivera bientôt.", "refund": "Le montant a été rendu à votre solde.", "contact": "Contactez-nous si vous avez besoin d’une précision."
    }
}

def get_user_lang(user_id: int) -> str:
    try:
        with db() as conn:
            row = conn.execute("SELECT lang FROM settings WHERE user_id=?", (user_id,)).fetchone()
            return row["lang"] if row and row["lang"] in BOT_TRANSLATIONS else "ar"
    except Exception:
        return "ar"

def bt(user_id: int, key: str, **kwargs) -> str:
    lang = get_user_lang(user_id)
    return BOT_TRANSLATIONS.get(lang, BOT_TRANSLATIONS["ar"])[key].format(**kwargs)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user = message.from_user
    args = (message.text or "").split(maxsplit=1)
    referral = None
    if len(args) == 2 and args[1].startswith("ref_"):
        referral = args[1][4:].strip()

    is_new = ensure_user(
        user.id,
        user.full_name,
        user.username or "",
        referral_code=referral
    )

    if is_new:
        uname = f"@{user.username}" if user.username else "بدون يوزر"
        asyncio.create_task(notify_admin(
            "🆕 <b>مستخدم جديد سجّل في Rayan Coin!</b>\n\n"
            f"الاسم: {html.quote(user.full_name)}\n"
            f"اليوزر: {uname}\n"
            f"المعرف: <code>{user.id}</code>\n"
            f"عبر إحالة: {'نعم' if referral else 'لا'}\n"
            "المصدر: أمر /start"
        ))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=bt(user.id, "open"),
                web_app=WebAppInfo(url=WEBAPP_URL)
            )],
            [
                InlineKeyboardButton(text=bt(user.id, "tasks"), callback_data="tasks"),
                InlineKeyboardButton(text=bt(user.id, "account"), callback_data="profile")
            ]
        ]
    )

    await message.answer(
        bt(user.id, "welcome", name=f"<b>{html.quote(user.full_name)}</b>"),
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery):
    uid = callback.from_user.id
    ensure_user(uid, callback.from_user.full_name, callback.from_user.username or "")
    with db() as conn:
        u = user_json(conn, uid)

    await callback.message.edit_text(
        f"{bt(uid, 'profile')}\n\n"
        f"• Name: {html.quote(u['name'])}\n"
        f"• ID: <code>{uid}</code>\n"
        f"• Balance: <b>{u['earnings']} Earnings</b>\n"
        f"• USDT: <b>{u['usdt_balance']:.2f}</b>\n"
        f"• Streak: <b>{u['current_streak']}</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text=bt(uid, "back"),
                callback_data="back_home"
            )]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "tasks")
async def tasks_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        bt(callback.from_user.id, "tasks_msg"),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=bt(callback.from_user.id, "open"),
                    web_app=WebAppInfo(url=WEBAPP_URL)
                )],
                [InlineKeyboardButton(
                    text="⬅️ عودة",
                    callback_data="back_home"
                )]
            ]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "back_home")
async def back_home_callback(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=bt(callback.from_user.id, "open"),
                web_app=WebAppInfo(url=WEBAPP_URL)
            )],
            [
                InlineKeyboardButton(text=bt(callback.from_user.id, "tasks"), callback_data="tasks"),
                InlineKeyboardButton(text=bt(callback.from_user.id, "account"), callback_data="profile")
            ]
        ]
    )

    await callback.message.edit_text(
        bt(callback.from_user.id, "welcome_again", name=f"<b>{html.quote(callback.from_user.full_name)}</b>"),
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("pay_ok:") | F.data.startswith("pay_no:"))
async def campaign_payment_decision_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("هذا الزر للأدمن فقط.", show_alert=True)
        return

    action, raw_id = callback.data.split(":", 1)
    payment_id = int(raw_id)
    approve = action == "pay_ok"

    payment, error = process_campaign_payment_decision(payment_id, approve=approve)

    if error:
        await callback.answer(error, show_alert=True)
        return

    if approve:
        await notify_user(
            payment["owner_id"],
            f"✅ <b>{bt(payment['owner_id'], 'approved')}</b>\n\n"
            f"المبلغ: {float(payment['amount_usdt']):.2f} USDT\n"
            + bt(payment["owner_id"], "active")
        )
        result_line = "✅ تمت الموافقة"
    else:
        await notify_user(
            payment["owner_id"],
            f"❌ <b>{bt(payment['owner_id'], 'rejected')}</b>\n\n"
            f"المبلغ: {float(payment['amount_usdt']):.2f} USDT\n"
            + bt(payment["owner_id"], "pay_help")
        )
        result_line = "❌ تم الرفض"

    try:
        await callback.message.edit_text(callback.message.text + f"\n\n{result_line}")
    except Exception:
        pass

    await callback.answer("تم تسجيل القرار.")


# ============================================================
# SERVER + BOT
# ============================================================

async def create_app():
    app = web.Application(middlewares=[cors_and_errors])

    app.router.add_route("OPTIONS", "/{tail:.*}", options_handler)
    app.router.add_get("/health", health)
    app.router.add_get("/api/me", api_me)
    app.router.add_get("/api/tasks", api_tasks)
    app.router.add_get("/api/offers", api_offers)
    app.router.add_post("/api/adgem/postback", api_adgem_postback)
    app.router.add_get("/api/x/start", api_x_start)
    app.router.add_get("/api/x/callback", api_x_callback)
    app.router.add_post("/api/ads/postback", api_ads_postback)
    app.router.add_get("/api/cpagrip/offers", api_cpagrip_offers)
    app.router.add_post("/api/cpagrip/postback", api_cpagrip_postback)
    app.router.add_get("/api/lootably/offers", api_lootably_offers)
    app.router.add_post("/api/lootably/webhook", api_lootably_webhook)
    app.router.add_get("/api/timewall/config", api_timewall_config)
    app.router.add_route("GET", "/api/timewall/postback", api_timewall_postback)
    app.router.add_route("POST", "/api/timewall/postback", api_timewall_postback)
    app.router.add_post("/api/tasks", api_create_task)
    app.router.add_post("/api/campaign-payments/{payment_id}/submit", api_submit_campaign_payment)
    app.router.add_get("/api/campaign-payments", api_my_campaign_payments)
    app.router.add_post("/api/tasks/{task_id}/complete", api_complete_task)
    app.router.add_post("/api/tasks/fixed/{kind}/complete", api_fixed_complete)
    app.router.add_post("/api/tasks/daily-checkin", api_daily_checkin)
    app.router.add_post("/api/ads/watch", api_watch_ad)
    app.router.add_get("/api/leaderboard", api_leaderboard)
    app.router.add_post("/api/withdrawals", api_withdraw)
    app.router.add_get("/api/withdrawals", api_my_withdrawals)
    app.router.add_get("/api/admin/withdrawals", api_admin_withdrawals)
    app.router.add_get("/api/admin/campaign-payments", api_admin_campaign_payments)
    app.router.add_patch("/api/admin/campaign-payments/{payment_id}", api_admin_campaign_payment_status)
    app.router.add_post("/api/admin/campaign-payments/{payment_id}/verify-chain", api_admin_campaign_payment_verify_chain)
    app.router.add_patch("/api/admin/withdrawals/{withdrawal_id}", api_admin_withdrawal_status)
    app.router.add_get("/api/settings", api_settings)
    app.router.add_patch("/api/settings", api_settings)

    return app


async def main():
    global BOT_USERNAME_PLACEHOLDER, BOT_INSTANCE

    init_db()

    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    BOT_INSTANCE = bot

    me = await bot.get_me()
    BOT_USERNAME_PLACEHOLDER = me.username or "YOUR_BOT"

    app = await create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    await site.start()

    logging.info("Rayan Coin API running on %s:%s", HOST, PORT)
    logging.info("Telegram bot: @%s", BOT_USERNAME_PLACEHOLDER)

    try:
        await dp.start_polling(bot)
    finally:
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
