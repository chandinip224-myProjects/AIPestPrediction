from flask import Flask, request, jsonify, session
from flask_cors import CORS

import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os
import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = "supersecretkey"
CORS(app, supports_credentials=True)


# ---------------- DATABASE ----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fullname TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)
    conn.commit()
    conn.close()

init_db()


# ---------------- SIGNUP ----------------
@app.route("/signup", methods=["POST"])
def signup():

    data = request.get_json()

    if not data:
        return jsonify({"status":"error","message":"No data received"})

    fullname = data.get("fullname")
    email = data.get("email")
    password = data.get("password")

    if not fullname or not email or not password:
        return jsonify({"status":"error","message":"Missing fields"})

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO users(fullname,email,password) VALUES (?,?,?)",
            (fullname,email,generate_password_hash(password))
        )
        conn.commit()
        conn.close()

        return jsonify({"status":"success","message":"Account created successfully"})

    except Exception as e:
        logging.error(f"ERROR: {e}")
        return jsonify({"status":"error","message":"User already exists"})


# ---------------- LOGIN ----------------
@app.route("/login", methods=["POST"])
def login():

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE email=?",(email,)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user["password"],password):

        session["user"] = user["fullname"]

        return jsonify({
            "status":"success",
            "user": user["fullname"]
        })

    else:
        return jsonify({"status":"error","message":"Invalid credentials"})


# ---------------- CHECK LOGIN ----------------
@app.route("/check-login")
def check_login():

    if "user" in session:
        return jsonify({
            "logged_in":True,
            "user":session["user"]
        })

    return jsonify({"logged_in":False})


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("user",None)
    return jsonify({"status":"logged_out"})


if __name__ == "__main__":
    app.run(port=9000, debug=True)