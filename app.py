import json
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from pymongo import MongoClient
from pymongo.errors import PyMongoError

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data.json"

app = Flask(__name__)

_client = None


def get_collection():
    """Create the MongoDB client lazily so the app can start (and /api can
    work) even when MONGO_URI is missing or Atlas is unreachable."""
    global _client
    uri = os.getenv("MONGO_URI")
    if not uri:
        raise RuntimeError("MONGO_URI is not set. Add your MongoDB Atlas connection string to .env")
    if _client is None:
        _client = MongoClient(uri, serverSelectionTimeoutMS=5000)
    db = _client[os.getenv("MONGO_DB", "flask_app")]
    return db[os.getenv("MONGO_COLLECTION", "submissions")]


# ---------- Task 1: JSON API ----------
@app.route("/api")
def api():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return jsonify({"error": "data.json not found"}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "data.json contains invalid JSON"}), 500
    return jsonify(data)


# ---------- Task 2: Form + MongoDB Atlas ----------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", error=None, form={})


@app.route("/submit", methods=["POST"])
def submit():
    form = {
        "name": request.form.get("name", "").strip(),
        "email": request.form.get("email", "").strip(),
        "message": request.form.get("message", "").strip(),
    }

    # Validation errors: shown on the same page, no redirect
    if not form["name"] or not form["email"] or not form["message"]:
        return render_template("index.html", error="All fields are required.", form=form), 400
    if "@" not in form["email"] or "." not in form["email"].split("@")[-1]:
        return render_template("index.html", error="Please enter a valid email address.", form=form), 400

    try:
        get_collection().insert_one({**form, "created_at": datetime.now(timezone.utc)})
    except PyMongoError as exc:
        # Connection, auth, timeout and write errors from MongoDB Atlas
        return render_template("index.html", error=f"Database error: {exc}", form=form), 500
    except RuntimeError as exc:
        # Configuration error (missing MONGO_URI)
        return render_template("index.html", error=str(exc), form=form), 500

    return redirect(url_for("success"))


@app.route("/success")
def success():
    return render_template("success.html")


if __name__ == "__main__":
    app.run(debug=True)
