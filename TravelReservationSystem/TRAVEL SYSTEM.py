from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import hashlib
import os

app = Flask(__name__)
app.secret_key = "travel_reservation_secret_key"

DATABASE = "travel_reservation.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            contact TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservations (
            reservation_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            passenger_name TEXT NOT NULL,
            contact TEXT NOT NULL,
            starting_location TEXT NOT NULL,
            origin TEXT NOT NULL,
            destination TEXT NOT NULL,
            travel_date TEXT NOT NULL,
            travel_time TEXT NOT NULL,
            vehicle TEXT NOT NULL,
            passengers INTEGER NOT NULL,
            distance REAL DEFAULT 0,
            fare REAL DEFAULT 0,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    admin_password = hashlib.sha256("admin123".encode()).hexdigest()

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (full_name, username, password, contact)
        VALUES (?, ?, ?, ?)
    """, (
        "System Administrator",
        "admin",
        admin_password,
        "Admin"
    ))

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"].strip()
        password = hash_password(request.form["password"])

        conn = get_db()

        user = conn.execute("""
            SELECT * FROM users
            WHERE username = ? AND password = ?
        """, (username, password)).fetchone()

        conn.close()

        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            session["full_name"] = user["full_name"]

            if username == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        full_name = request.form["full_name"].strip()
        username = request.form["username"].strip()
        contact = request.form["contact"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for("register"))

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return redirect(url_for("register"))

        conn = get_db()

        try:
            conn.execute("""
                INSERT INTO users
                (full_name, username, password, contact)
                VALUES (?, ?, ?, ?)
            """, (
                full_name,
                username,
                hash_password(password),
                contact
            ))

            conn.commit()

        except sqlite3.IntegrityError:
            conn.close()
            flash("Username already exists.", "error")
            return redirect(url_for("register"))

        conn.close()

        flash("Registration successful. You can now login.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template(
        "dashboard.html",
        full_name=session["full_name"]
    )


@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    if session["username"] != "admin":
        flash("Admin access only.", "error")
        return redirect(url_for("dashboard"))

    conn = get_db()

    reservations = conn.execute("""
        SELECT
            r.*,
            u.full_name AS account_name,
            u.username
        FROM reservations r
        JOIN users u
            ON r.user_id = u.user_id
        ORDER BY r.reservation_id DESC
    """).fetchall()

    users = conn.execute("""
        SELECT user_id, full_name, username, contact
        FROM users
        ORDER BY user_id DESC
    """).fetchall()

    conn.close()

    return render_template(
        "admin.html",
        reservations=reservations,
        users=users
    )



@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("login"))


if __name__ == "__main__":

    init_database()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )