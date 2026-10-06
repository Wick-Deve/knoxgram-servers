import os
import sqlite3
import hashlib
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="KnoxGram Server")

DB = "knoxgram.db"


def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    conn.commit()
    return conn


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


class Auth(BaseModel):
    username: str
    password: str


class Message(BaseModel):
    sender: str
    receiver: str
    text: str


@app.get("/")
def home():
    return {
        "name": "KnoxGram",
        "status": "online",
        "version": "1.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "KnoxGram"
    }


@app.post("/register")
def register(data: Auth):
    if len(data.username) < 3:
        raise HTTPException(400, "Username too short")

    if len(data.password) < 6:
        raise HTTPException(400, "Password too short")

    db = get_db()

    try:
        db.execute(
            """
            INSERT INTO users
            (username, password, created_at)
            VALUES (?, ?, ?)
            """,
            (
                data.username,
                hash_password(data.password),
                datetime.now(timezone.utc).isoformat()
            )
        )

        db.commit()

    except sqlite3.IntegrityError:
        raise HTTPException(409, "Username already exists")

    finally:
        db.close()

    return {
        "ok": True,
        "username": data.username
    }


@app.post("/login")
def login(data: Auth):
    db = get_db()

    user = db.execute(
        """
        SELECT username, password
        FROM users
        WHERE username = ?
        """,
        (data.username,)
    ).fetchone()

    db.close()

    if not user:
        raise HTTPException(401, "Invalid username or password")

    if user["password"] != hash_password(data.password):
        raise HTTPException(401, "Invalid username or password")

    return {
        "ok": True,
        "username": user["username"]
    }


@app.post("/messages")
def send_message(data: Message):
    if not data.text.strip():
        raise HTTPException(400, "Message is empty")

    db = get_db()

    created = datetime.now(timezone.utc).isoformat()

    db.execute(
        """
        INSERT INTO messages
        (sender, receiver, text, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            data.sender,
            data.receiver,
            data.text,
            created
        )
    )

    db.commit()
    db.close()

    return {
        "ok": True,
        "sender": data.sender,
        "receiver": data.receiver,
        "text": data.text,
        "created_at": created
    }


@app.get("/messages/{username}")
def messages(username: str):
    db = get_db()

    rows = db.execute(
        """
        SELECT sender, receiver, text, created_at
        FROM messages
        WHERE sender = ? OR receiver = ?
        ORDER BY id ASC
        """,
        (username, username)
    ).fetchall()

    db.close()

    return {
        "messages": [dict(row) for row in rows]
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 10000))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
  )
