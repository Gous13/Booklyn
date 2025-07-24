from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime,timedelta

app = Flask(__name__)
CORS(app)
app.secret_key = "mysecretkey123"  # Change to a secure key in production

DB_PATH = os.path.join("instance", "library.db")
@app.template_filter("datetimeformat") 
def datetimeformat(value, format="%Y-%m-%d"): 
    return datetime.strptime(value, "%Y-%m-%d")

# ------------ DATABASE INITIALIZATION ------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
        )
    """)

    # Books Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT,
            quantity INTEGER DEFAULT 1,
            added_date TEXT
        )
    """)

    # Members Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            membership_date TEXT
        )
    """)

    # Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            book_id INTEGER,
            issue_date TEXT,
            return_date TEXT,
            fine REAL DEFAULT 0,
            FOREIGN KEY(member_id) REFERENCES members(id),
            FOREIGN KEY(book_id) REFERENCES books(id)
        )
    """)

    # Book Requests Table (FIXED MISSING PARENTHESIS ✅)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS book_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            book_title TEXT NOT NULL,
            author TEXT,
            request_date TEXT,
            status TEXT DEFAULT 'Pending',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Default Admin
    cursor.execute("SELECT * FROM users WHERE role='admin'")
    if cursor.fetchone() is None:
        cursor.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                       ("Admin", "admin@library.com", "admin123", "admin"))

    conn.commit()
    conn.close()

init_db()

# ------------ COMMON ROUTES ------------

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["user_name"] = user[1]
            session["role"] = user[4]

            if user[4] == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
        else:
            flash("Invalid email or password", "danger")

    return render_template("login.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                           (name, email, password, "user"))
            conn.commit()
            flash("Signup successful! Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Email already exists", "danger")
        finally:
            conn.close()
    return render_template("signup.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ------------ ADMIN ROUTES ------------

@app.route("/admin/dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM books")
    total_books = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM members")
    total_members = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE return_date IS NULL")
    issued_books = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(fine) FROM transactions")
    total_fines = cursor.fetchone()[0] or 0

    conn.close()

    return render_template("admin/admin_dashboard.html",
                           total_books=total_books,
                           total_members=total_members,
                           issued_books=issued_books,
                           total_fines=total_fines)

# --- Manage Books ---
@app.route("/admin/manage_books", methods=["GET", "POST"])
def manage_books():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        category = request.form["category"]
        quantity = request.form["quantity"]
        added_date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("INSERT INTO books (title,author,category,quantity,added_date) VALUES (?,?,?,?,?)",
                       (title, author, category, quantity, added_date))
        conn.commit()
        flash("Book added successfully!", "success")

    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    conn.close()
    return render_template("admin/manage_books.html", books=books)

@app.route("/admin/delete_book/<int:book_id>")
def delete_book(book_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()
    flash("Book deleted successfully!", "success")
    return redirect(url_for("manage_books"))

# ------------ ADMIN MANAGE BOOK REQUESTS ------------

@app.route("/admin/manage_requests")
def manage_requests():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT br.id, u.name, br.book_title, br.author, br.request_date, br.status
        FROM book_requests br
        JOIN users u ON br.user_id = u.id
    """)
    requests = cursor.fetchall()
    conn.close()

    return render_template("admin/manage_requests.html", requests=requests)

@app.route("/admin/update_request/<int:request_id>/<string:action>")
def update_request(request_id, action):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    status = "Approved" if action == "approve" else "Rejected"

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE book_requests SET status=? WHERE id=?", (status, request_id))
    conn.commit()
    conn.close()

    flash(f"Request {status.lower()} successfully!", "info")
    return redirect(url_for("manage_requests"))

# --- Manage Members ---
@app.route("/admin/manage_members", methods=["GET", "POST"])
def manage_members():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        phone = request.form["phone"]
        membership_date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("INSERT INTO members (name,email,phone,membership_date) VALUES (?,?,?,?)",
                       (name, email, phone, membership_date))
        conn.commit()
        flash("Member added successfully!", "success")

    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()
    conn.close()
    return render_template("admin/manage_members.html", members=members)

@app.route("/admin/delete_member/<int:member_id>")
def delete_member(member_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM members WHERE id=?", (member_id,))
    conn.commit()
    conn.close()
    flash("Member deleted successfully!", "success")
    return redirect(url_for("manage_members"))

# --- Transactions (Issue/Return Books) ---
@app.route("/admin/transactions", methods=["GET", "POST"])
def transactions():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "POST":
        member_id = request.form["member_id"]
        book_id = request.form["book_id"]
        issue_date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("INSERT INTO transactions (member_id, book_id, issue_date) VALUES (?,?,?)",
                       (member_id, book_id, issue_date))
        conn.commit()
        flash("Book issued successfully!", "success")

    cursor.execute("""
        SELECT t.id, m.name, b.title, t.issue_date, t.return_date, t.fine
        FROM transactions t
        JOIN members m ON t.member_id=m.id
        JOIN books b ON t.book_id=b.id
    """)
    records = cursor.fetchall()

    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()

    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()

    conn.close()
    return render_template("admin/transactions.html", records=records, members=members, books=books)

@app.route("/admin/return_book/<int:transaction_id>")
def return_book(transaction_id):
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    today = datetime.now()
    fine = 0

    cursor.execute("SELECT issue_date FROM transactions WHERE id=?", (transaction_id,))
    issue_date = datetime.strptime(cursor.fetchone()[0], "%Y-%m-%d")
    days_diff = (today - issue_date).days

    if days_diff > 7:
        fine = (days_diff - 7) * 10

    cursor.execute("UPDATE transactions SET return_date=?, fine=? WHERE id=?",
                   (today.strftime("%Y-%m-%d"), fine, transaction_id))
    conn.commit()
    conn.close()

    flash(f"Book returned. Fine: Rs.{fine}", "info")
    return redirect(url_for("transactions"))

# --- Reports ---
@app.route("/admin/reports")
def reports():
    if session.get("role") != "admin":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE date(issue_date)=date('now')")
    daily_issues = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE strftime('%W', issue_date)=strftime('%W','now')")
    weekly_issues = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM transactions WHERE strftime('%m', issue_date)=strftime('%m','now')")
    monthly_issues = cursor.fetchone()[0]

    conn.close()
    return render_template("admin/reports.html", daily_issues=daily_issues, weekly_issues=weekly_issues, monthly_issues=monthly_issues)

# ------------ USER BOOK REQUEST ROUTES ------------
@app.route("/user/request_book", methods=["GET", "POST"])
def request_book():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if request.method == "POST":
        title = request.form["title"]
        author = request.form["author"]
        request_date = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("INSERT INTO book_requests (user_id, book_title, author, request_date) VALUES (?,?,?,?)",
                       (session["user_id"], title, author, request_date))
        conn.commit()
        flash("Book request submitted successfully!", "success")

    cursor.execute("SELECT book_title, author, request_date, status FROM book_requests WHERE user_id=?",
                   (session["user_id"],))
    requests = cursor.fetchall()

    conn.close()
    return render_template("user/request_books.html", requests=requests)

# ------------ USER ROUTES ------------
@app.route("/user/dashboard")
def user_dashboard():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    conn.close()
    return render_template("user/user_dashboard.html", books=books)

@app.route("/user/my_books")
@app.route("/user/my_books")
def my_books():
    if session.get("role") != "user":
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT b.title, t.issue_date, t.return_date, t.fine
        FROM transactions t
        JOIN books b ON t.book_id=b.id
        JOIN members m ON t.member_id=m.id
        WHERE m.email=(SELECT email FROM users WHERE id=?)
    """, (session["user_id"],))

    my_records = cursor.fetchall()
    conn.close()

    # ✅ Pass timedelta explicitly to Jinja
    return render_template("user/my_books.html", my_records=my_records, timedelta=timedelta, datetime=datetime)


@app.route("/user/issue_book/<int:book_id>")
def issue_book(book_id):
    if session.get("role") != "user":
        return redirect(url_for("login"))

    try:
        with sqlite3.connect(DB_PATH, timeout=10) as conn:  # auto-closes connection
            cursor = conn.cursor()

            # Check if book is available
            cursor.execute("SELECT quantity FROM books WHERE id=?", (book_id,))
            book = cursor.fetchone()

            if book and book[0] > 0:
                issue_date = datetime.now().strftime("%Y-%m-%d")

                # Find member_id (linking user to member table by email)
                cursor.execute("SELECT id FROM members WHERE email=(SELECT email FROM users WHERE id=?)",
                               (session["user_id"],))
                member = cursor.fetchone()

                # If user is not in members table, add them automatically
                if not member:
                    cursor.execute("INSERT INTO members (name,email,membership_date) VALUES (?,?,?)",
                                   (session["user_name"],
                                    (cursor.execute("SELECT email FROM users WHERE id=?",
                                                    (session["user_id"],)).fetchone()[0]),
                                    issue_date))
                    conn.commit()
                    cursor.execute("SELECT last_insert_rowid()")
                    member_id = cursor.fetchone()[0]
                else:
                    member_id = member[0]

                # Insert transaction
                cursor.execute("INSERT INTO transactions (member_id, book_id, issue_date) VALUES (?,?,?)",
                               (member_id, book_id, issue_date))

                # Decrease book quantity
                cursor.execute("UPDATE books SET quantity=quantity-1 WHERE id=?", (book_id,))

                conn.commit()
                flash("Book issued successfully!", "success")
            else:
                flash("Book not available!", "danger")

    except sqlite3.OperationalError as e:
        flash(f"Database error: {e}", "danger")

    return redirect(url_for("user_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)
