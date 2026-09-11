
import asyncio
import hashlib
import hmac
import json
import logging
import os
import sqlite3
import sys
import time
from urllib.parse import parse_qsl

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

DB_PATH = os.getenv("DB_PATH", "bot_database.db")
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
REFERRAL_REWARD = int(os.getenv("REFERRAL_REWARD", "10"))
FIXED_X_REWARD = int(os.getenv("FIXED_X_REWARD", "50"))
FIXED_TELEGRAM_REWARD = int(os.getenv("FIXED_TELEGRAM_REWARD", "50"))
AD_REWARD = int(os.getenv("AD_REWARD", "1"))
ADMIN_USER_ID = int(os.getenv("ADMIN_USER_ID", "0"))
ADGEM_POSTBACK_KEY = os.getenv("i7gc8676i76i4el4f8jb871g", "").strip()  


# ============================================================
# CAMPAIGN PRICING - Rayan Coin
# ============================================================

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
}
dp = Dispatcher()


# ============================================================
# DATABASE
# ============================================================

def db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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
               CREATE INDEX IF NOT EXISTS idx_offer_conversions_provider
            ON offer_conversions(provider);
        CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
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


def ensure_user(user_id, full_name="", username="", referral_code=None):
    with db() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE users SET full_name=?, username=? WHERE user_id=?",
                (full_name, username, user_id),
            )
            conn.commit()
            return

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

        # Give the referrer one server-side reward, exactly once.
        if referrer_id:
            conn.execute(
                """UPDATE users
                   SET balance=balance+?, total_earned=total_earned+?
                   WHERE user_id=?""",
                (REFERRAL_REWARD, REFERRAL_REWARD, referrer_id),
            )
            conn.execute(
                "UPDATE users SET referral_rewarded=1 WHERE user_id=?",
                (user_id,),
            )
        conn.commit()


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

        if abs(time.time() - int(auth_date)) > 86400:
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

    response.headers["Access-Control-Allow-Origin"] = "*"
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
    ensure_user(user["id"], user.get("first_name", ""), user.get("username", ""))
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

async def api_me(request):
    uid = auth_user(request)
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
            ORDER BY t.id DESC
        """, (uid,)).fetchall()

        tasks = [{
            "id": r["id"],
            "title": r["title"],
            "link": r["link"],
            "reward": r["reward"],
            "budget_remaining": max(0, r["budget"] - r["spent"]),
            "completed": bool(r["completed"]),
        } for r in rows]

        return web.json_response({"tasks": tasks})
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
    reward = int(data.get("reward", 0))
    budget = int(data.get("budget", 0))

    if not title or not link or reward <= 0 or budget <= 0:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "بيانات المهمة غير صحيحة"}),
            content_type="application/json"
        )

    if budget < reward:
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "الميزانية يجب أن تكون أكبر أو تساوي المكافأة"}),
            content_type="application/json"
        )

    with db() as conn:
        # Reserve the entire task budget immediately.
        user = conn.execute(
            "SELECT balance FROM users WHERE user_id=?", (uid,)
        ).fetchone()

        if not user or user["balance"] < budget:
            raise web.HTTPBadRequest(
                text=json.dumps({"detail": "رصيدك غير كافٍ لميزانية المهمة"}),
                content_type="application/json"
            )

        conn.execute(
            "UPDATE users SET balance=balance-? WHERE user_id=? AND balance>=?",
            (budget, uid, budget)
        )
        cur = conn.execute(
            """INSERT INTO tasks(owner_id,title,link,reward,budget)
               VALUES(?,?,?,?,?)""",
            (uid, title, link, reward, budget)
        )
        conn.commit()

        return web.json_response({"ok": True, "task_id": cur.lastrowid})


async def api_complete_task(request):
    uid = auth_user(request)
    task_id = int(request.match_info["task_id"])

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


async def api_fixed_complete(request):
    uid = auth_user(request)
    kind = request.match_info["kind"]

    if kind not in ("x", "telegram"):
        raise web.HTTPBadRequest(
            text=json.dumps({"detail": "Unknown fixed task"}),
            content_type="application/json"
        )

    # These rewards can be changed in env vars.
    reward = FIXED_X_REWARD if kind == "x" else FIXED_TELEGRAM_REWARD

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                """INSERT INTO fixed_completions(kind,user_id,reward)
                   VALUES(?,?,?)""",
                (kind, uid, reward)
            )
        except sqlite3.IntegrityError:
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
        except sqlite3.IntegrityError:
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
    uid = auth_user(request)
    today = today_utc()

    with db() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT views FROM ad_views WHERE user_id=? AND day=?",
            (uid, today)
        ).fetchone()
        views = int(row["views"]) if row else 0

        if views >= 10:
            raise web.HTTPBadRequest(
                text=json.dumps({"detail": "انتهت إعلانات اليوم"}),
                content_type="application/json"
            )

        if row:
            conn.execute(
                "UPDATE ad_views SET views=views+1 WHERE user_id=? AND day=?",
                (uid, today)
            )
        else:
            conn.execute(
                "INSERT INTO ad_views(user_id,day,views) VALUES(?,?,1)",
                (uid, today)
            )

        # Adsterra handles the ad. This reward is only granted after
        # the server records the view request; production should add
        # the ad network's server-side callback before real payouts.
        reward = AD_REWARD
        conn.execute(
            """UPDATE users SET balance=balance+?, total_earned=total_earned+?
               WHERE user_id=?""",
            (reward, reward, uid)
        )
        conn.commit()

    return web.json_response({"ok": True, "reward": reward, "ad_url": ADSTERRA_URL})


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


async def api_admin_withdrawals(request):
    require_admin(request)
    with db() as conn:
        rows = conn.execute(
            """SELECT w.id,w.user_id,w.amount_usdt,w.address,w.status,w.created_at,w.processed_at,
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
    if status not in ("Approved", "Rejected"):
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

        if status == "Rejected":
            refund = int(round(float(w["amount_usdt"]) / USDT_PER_EARNING))
            conn.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (refund, w["user_id"]))

        conn.execute(
            "UPDATE withdrawals SET status=?, processed_at=CURRENT_TIMESTAMP WHERE id=?",
            (status, withdrawal_id),
        )
        conn.commit()

    return web.json_response({"ok": True, "status": status})


async def api_settings(request):
    uid = auth_user(request)

    if request.method == "GET":
        with db() as conn:
            row = conn.execute(
                "SELECT lang,country,dark_mode FROM settings WHERE user_id=?",
                (uid,)
            ).fetchone()
            return web.json_response({
                "lang": row["lang"],
                "country": row["country"],
                "darkMode": bool(row["dark_mode"])
            })

    data = await request.json()
    lang = str(data.get("lang", "ar"))[:5]
    country = str(data.get("country", "DZ"))[:5]
    dark = 1 if bool(data.get("darkMode", True)) else 0

    with db() as conn:
        conn.execute(
            """INSERT INTO settings(user_id,lang,country,dark_mode)
               VALUES(?,?,?,?)
               ON CONFLICT(user_id) DO UPDATE SET
                 lang=excluded.lang,
                 country=excluded.country,
                 dark_mode=excluded.dark_mode""",
            (uid, lang, country, dark)
        )
        conn.commit()

    return web.json_response({"ok": True})


async def health(request):
    return web.json_response({"ok": True, "service": "Rayan Coin API"})


async def options_handler(request):
    return web.Response(status=204)


# ============================================================
# TELEGRAM BOT
# ============================================================

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user = message.from_user
    args = (message.text or "").split(maxsplit=1)
    referral = None
    if len(args) == 2 and args[1].startswith("ref_"):
        referral = args[1][4:].strip()

    ensure_user(
        user.id,
        user.full_name,
        user.username or "",
        referral_code=referral
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="🚀 فتح التطبيق",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )],
            [
                InlineKeyboardButton(text="🎯 المهام", callback_data="tasks"),
                InlineKeyboardButton(text="👤 حسابي", callback_data="profile")
            ]
        ]
    )

    await message.answer(
        f"مرحباً بك يا <b>{html.quote(user.full_name)}</b> في منصة <b>Rayan Coin</b>! 🪙\n\n"
        "تم تسجيل حسابك. افتح التطبيق لعرض بياناتك الحقيقية.",
        reply_markup=keyboard
    )


@dp.callback_query(F.data == "profile")
async def profile_callback(callback: CallbackQuery):
    uid = callback.from_user.id
    ensure_user(uid, callback.from_user.full_name, callback.from_user.username or "")
    with db() as conn:
        u = user_json(conn, uid)

    await callback.message.edit_text(
        f"👤 <b>معلومات الحساب</b>\n\n"
        f"• الاسم: {html.quote(u['name'])}\n"
        f"• المعرف: <code>{uid}</code>\n"
        f"• الرصيد: <b>{u['earnings']} Earnings</b>\n"
        f"• USDT: <b>{u['usdt_balance']:.2f}</b>\n"
        f"• Streak: <b>{u['current_streak']} يوم</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(
                text="⬅️ عودة",
                callback_data="back_home"
            )]]
        )
    )
    await callback.answer()


@dp.callback_query(F.data == "tasks")
async def tasks_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎯 <b>المهام</b>\n\n"
        "افتح التطبيق لعرض المهام الحقيقية وتنفيذها وتسجيل المكافآت.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text="🚀 فتح التطبيق",
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
                text="🚀 فتح التطبيق",
                web_app=WebAppInfo(url=WEBAPP_URL)
            )],
            [
                InlineKeyboardButton(text="🎯 المهام", callback_data="tasks"),
                InlineKeyboardButton(text="👤 حسابي", callback_data="profile")
            ]
        ]
    )

    await callback.message.edit_text(
        f"مرحباً بك مجدداً يا <b>{html.quote(callback.from_user.full_name)}</b> في <b>Rayan Coin</b>! 🪙",
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


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
app.router.add_post("/api/tasks", api_create_task)
    app.router.add_post("/api/tasks/{task_id}/complete", api_complete_task)
    app.router.add_post("/api/tasks/fixed/{kind}/complete", api_fixed_complete)
    app.router.add_post("/api/tasks/daily-checkin", api_daily_checkin)
    app.router.add_post("/api/ads/watch", api_watch_ad)
    app.router.add_get("/api/leaderboard", api_leaderboard)
    app.router.add_post("/api/withdrawals", api_withdraw)
    app.router.add_get("/api/withdrawals", api_my_withdrawals)
    app.router.add_get("/api/admin/withdrawals", api_admin_withdrawals)
    app.router.add_patch("/api/admin/withdrawals/{withdrawal_id}", api_admin_withdrawal_status)
    app.router.add_get("/api/settings", api_settings)
    app.router.add_patch("/api/settings", api_settings)

    return app


async def main():
    global BOT_USERNAME_PLACEHOLDER

    init_db()

    bot = Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

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
