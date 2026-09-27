import os
from datetime import date, datetime, timedelta
from functools import wraps

import mysql.connector
from mysql.connector import Error
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "college-library-super5-secret-key")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Test12345")
DB_NAME = os.getenv("DB_NAME", "library_management")
DB_PORT = int(os.getenv("DB_PORT", "3306"))

DEMO_USERS = {
    "admin": {"password": "admin123", "role": "Admin", "name": "Anjali Kumari"},
    "librarian": {"password": "lib123", "role": "Librarian", "name": "Library Librarian"},
    "staff": {"password": "staff123", "role": "Staff", "name": "Library Staff"},
    "student": {"password": "student123", "role": "Student", "name": "Student User"},
    "faculty": {"password": "faculty123", "role": "Faculty", "name": "Faculty User"},
}

BOOK_SEED = [
    ("B001", "Head First Python", "Paul Barry", "Programming", 788),
    ("B002", "Learn Python The Hard Way", "Zed Shaw", "Python", 650),
    ("B003", "Python Programming", "John Zelle", "Python", 720),
    ("B004", "Secret Python", "Rashly", "Python", 550),
    ("B005", "Python Cookbook", "David Beazley", "Python", 850),
    ("B006", "Into Machine Learning", "Andrew Ng", "Machine Learning", 920),
    ("B007", "Fluent Python", "Luciano Ramalho", "Python", 980),
    ("B008", "Programming Python", "Mark Lutz", "Python", 1100),
    ("B009", "The Algorithm", "Panos Louridas", "Algorithms", 700),
    ("B010", "The Technic Python", "Mike Dawson", "Python", 620),
    ("B011", "Machine Learning", "Sebastian Raschka", "Machine Learning", 950),
    ("B012", "My Python", "N. Rao", "Python", 580),
    ("B013", "Joss Elif Guru", "Joss", "Programming", 600),
    ("B014", "Elite Jungle Python", "David Amos", "Python", 720),
    ("B015", "Jungli Python", "Mark Summerfield", "Python", 680),
    ("B016", "Mumbai Python", "Amit Sharma", "Python", 590),
    ("B017", "Python Crash Course", "Eric Matthes", "Python", 850),
    ("B018", "Head First Java", "Kathy Sierra", "Java", 900),
    ("B019", "Let Us C", "Yashavant Kanetkar", "C Programming", 550),
    ("B020", "Programming in C++", "Bjarne Stroustrup", "C++", 980),
    ("B021", "Data Structures", "Schaum", "Data Structure", 750),
    ("B022", "Computer Networks", "Tanenbaum", "Networking", 890),
    ("B023", "Database Management", "Ramez Elmasri", "DBMS", 850),
    ("B024", "Web Technology", "Jeffrey Jackson", "Web", 780),
    ("B025", "Operating System", "Silberschatz", "Operating System", 950),
    ("B026", "Software Engineering", "Ian Sommerville", "Software Engineering", 1000),
    ("B027", "Advanced Java", "Herbert Schildt", "Java", 870),
    ("B028", "Artificial Intelligence", "Stuart Russell", "AI", 1200),
    ("B029", "Cloud Computing", "Thomas Erl", "Cloud", 1050),
    ("B030", "Discrete Mathematics", "Kenneth Rosen", "Mathematics", 800),
]


def server_connection(use_db=True):
    kwargs = dict(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, port=DB_PORT)
    if use_db:
        kwargs["database"] = DB_NAME
    return mysql.connector.connect(**kwargs)


def ensure_database():
    conn = server_connection(False)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}`")
    conn.commit()
    cur.close()
    conn.close()


def add_column_if_missing(cur, table, column, definition):
    cur.execute(f"SHOW COLUMNS FROM `{table}` LIKE %s", (column,))
    if cur.fetchone() is None:
        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}")


def setup_database():
    ensure_database()
    conn = server_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS books (
            book_id VARCHAR(30) PRIMARY KEY,
            title VARCHAR(200) NOT NULL,
            author VARCHAR(150),
            category VARCHAR(100),
            price DECIMAL(10,2) DEFAULT 0,
            status VARCHAR(30) DEFAULT 'Available'
        )
    """)
    book_cols = {
        "quantity_total": "INT DEFAULT 1",
        "quantity_available": "INT DEFAULT 1",
        "isbn": "VARCHAR(30)",
        "publisher": "VARCHAR(150)",
        "edition": "VARCHAR(50)",
        "publish_year": "INT NULL",
        "rack": "VARCHAR(50)",
        "shelf": "VARCHAR(50)",
        "archived": "TINYINT(1) DEFAULT 0",
    }
    for col, definition in book_cols.items():
        add_column_if_missing(cur, "books", col, definition)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS members (
            prn_no VARCHAR(50) PRIMARY KEY,
            member_type VARCHAR(50), id_no VARCHAR(50), first_name VARCHAR(100), last_name VARCHAR(100),
            address1 VARCHAR(200), address2 VARCHAR(200), postcode VARCHAR(30), mobile VARCHAR(40),
            email VARCHAR(150), class_name VARCHAR(100)
        )
    """)
    for col, definition in {"email": "VARCHAR(150)", "class_name": "VARCHAR(100)"}.items():
        add_column_if_missing(cur, "members", col, definition)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id INT AUTO_INCREMENT PRIMARY KEY,
            prn_no VARCHAR(50), book_id VARCHAR(30), book_title VARCHAR(200), author VARCHAR(150),
            date_borrowed DATE, date_due DATE, return_date DATE NULL,
            days_allowed INT DEFAULT 14, late_return_fine DECIMAL(10,2) DEFAULT 0,
            date_overdue VARCHAR(30), status VARCHAR(30) DEFAULT 'Issued',
            condition_on_return VARCHAR(30) DEFAULT 'Good'
        )
    """)
    for col, definition in {
        "return_date": "DATE NULL", "days_allowed": "INT DEFAULT 14",
        "late_return_fine": "DECIMAL(10,2) DEFAULT 0", "date_overdue": "VARCHAR(30)",
        "condition_on_return": "VARCHAR(30) DEFAULT 'Good'",
    }.items():
        add_column_if_missing(cur, "transactions", col, definition)

    create_sql = {
        "suppliers": """
            CREATE TABLE IF NOT EXISTS suppliers (
                supplier_id INT AUTO_INCREMENT PRIMARY KEY, name VARCHAR(150) NOT NULL,
                contact VARCHAR(100), email VARCHAR(150), address VARCHAR(250), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "purchases": """
            CREATE TABLE IF NOT EXISTS purchases (
                purchase_id INT AUTO_INCREMENT PRIMARY KEY, book_id VARCHAR(30), supplier_id INT, invoice_no VARCHAR(80),
                quantity INT DEFAULT 1, unit_price DECIMAL(10,2) DEFAULT 0, purchase_date DATE, total_cost DECIMAL(12,2) DEFAULT 0,
                notes VARCHAR(250), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "accession_register": """
            CREATE TABLE IF NOT EXISTS accession_register (
                accession_id INT AUTO_INCREMENT PRIMARY KEY, accession_no VARCHAR(80) UNIQUE, book_id VARCHAR(30), isbn VARCHAR(30),
                edition VARCHAR(50), publisher VARCHAR(150), purchase_date DATE, price DECIMAL(10,2), rack VARCHAR(50), shelf VARCHAR(50),
                condition_status VARCHAR(30) DEFAULT 'Good', branch VARCHAR(100) DEFAULT 'Main Library'
            )""",
        "inventory_audit": """
            CREATE TABLE IF NOT EXISTS inventory_audit (
                audit_id INT AUTO_INCREMENT PRIMARY KEY, audit_date DATE, book_id VARCHAR(30), system_qty INT, physical_qty INT,
                missing_qty INT DEFAULT 0, damaged_qty INT DEFAULT 0, remarks VARCHAR(250), verified_by VARCHAR(100)
            )""",
        "transfers": """
            CREATE TABLE IF NOT EXISTS transfers (
                transfer_id INT AUTO_INCREMENT PRIMARY KEY, book_id VARCHAR(30), from_branch VARCHAR(100), to_branch VARCHAR(100),
                from_rack VARCHAR(50), to_rack VARCHAR(50), quantity INT DEFAULT 1, transfer_date DATE, remarks VARCHAR(250), transferred_by VARCHAR(100)
            )""",
        "circulation_rules": """
            CREATE TABLE IF NOT EXISTS circulation_rules (
                rule_id INT AUTO_INCREMENT PRIMARY KEY, member_type VARCHAR(50) UNIQUE, max_books INT DEFAULT 3,
                issue_days INT DEFAULT 14, fine_per_day DECIMAL(10,2) DEFAULT 50
            )""",
        "fine_waivers": """
            CREATE TABLE IF NOT EXISTS fine_waivers (
                waiver_id INT AUTO_INCREMENT PRIMARY KEY, transaction_id INT, original_fine DECIMAL(10,2), waiver_amount DECIMAL(10,2),
                final_fine DECIMAL(10,2), reason VARCHAR(250), approved_by VARCHAR(100), status VARCHAR(30) DEFAULT 'Pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "staff_shifts": """
            CREATE TABLE IF NOT EXISTS staff_shifts (
                shift_id INT AUTO_INCREMENT PRIMARY KEY, staff_name VARCHAR(120), shift_date DATE, entry_time TIME, exit_time TIME,
                status VARCHAR(30) DEFAULT 'Present', notes VARCHAR(250)
            )""",
        "permissions": """
            CREATE TABLE IF NOT EXISTS permissions (
                permission_id INT AUTO_INCREMENT PRIMARY KEY, role_name VARCHAR(50) UNIQUE,
                can_add_book TINYINT(1) DEFAULT 1, can_delete_book TINYINT(1) DEFAULT 0,
                can_issue TINYINT(1) DEFAULT 1, can_return TINYINT(1) DEFAULT 1, can_reports TINYINT(1) DEFAULT 1,
                can_backup TINYINT(1) DEFAULT 0
            )""",
        "approval_requests": """
            CREATE TABLE IF NOT EXISTS approval_requests (
                request_id INT AUTO_INCREMENT PRIMARY KEY, request_type VARCHAR(80), reference_id VARCHAR(80), requested_by VARCHAR(100),
                reason VARCHAR(250), status VARCHAR(30) DEFAULT 'Pending', approved_by VARCHAR(100), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "classes": """
            CREATE TABLE IF NOT EXISTS classes (
                class_id INT AUTO_INCREMENT PRIMARY KEY, class_name VARCHAR(100) UNIQUE, course VARCHAR(100), year_name VARCHAR(50), section_name VARCHAR(50)
            )""",
        "reading_badges": """
            CREATE TABLE IF NOT EXISTS reading_badges (
                badge_id INT AUTO_INCREMENT PRIMARY KEY, prn_no VARCHAR(50), badge_name VARCHAR(80), awarded_on DATE,
                UNIQUE KEY uq_badge (prn_no, badge_name)
            )""",
        "digital_resources": """
            CREATE TABLE IF NOT EXISTS digital_resources (
                resource_id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(200), resource_type VARCHAR(50), publisher VARCHAR(150),
                resource_url VARCHAR(500), notes VARCHAR(250), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "book_editions": """
            CREATE TABLE IF NOT EXISTS book_editions (
                edition_id INT AUTO_INCREMENT PRIMARY KEY, book_id VARCHAR(30), edition VARCHAR(50), isbn VARCHAR(30), publisher VARCHAR(150),
                publish_year INT NULL, price DECIMAL(10,2), copies INT DEFAULT 1
            )""",
        "reviews": """
            CREATE TABLE IF NOT EXISTS reviews (
                review_id INT AUTO_INCREMENT PRIMARY KEY, book_id VARCHAR(30), prn_no VARCHAR(50), rating INT, review_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "wishlist": """
            CREATE TABLE IF NOT EXISTS wishlist (
                wishlist_id INT AUTO_INCREMENT PRIMARY KEY, prn_no VARCHAR(50), book_id VARCHAR(30), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_wish (prn_no, book_id)
            )""",
        "announcements": """
            CREATE TABLE IF NOT EXISTS announcements (
                announcement_id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(200), message TEXT, priority VARCHAR(30) DEFAULT 'Normal',
                created_by VARCHAR(100), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "activity_log": """
            CREATE TABLE IF NOT EXISTS activity_log (
                activity_id INT AUTO_INCREMENT PRIMARY KEY, action VARCHAR(100), details VARCHAR(500), actor VARCHAR(100), activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "study_seats": """
            CREATE TABLE IF NOT EXISTS study_seats (
                seat_id INT AUTO_INCREMENT PRIMARY KEY, seat_code VARCHAR(30) UNIQUE, floor_name VARCHAR(50), zone_name VARCHAR(80), status VARCHAR(30) DEFAULT 'Available'
            )""",
        "seat_bookings": """
            CREATE TABLE IF NOT EXISTS seat_bookings (
                booking_id INT AUTO_INCREMENT PRIMARY KEY, seat_id INT, prn_no VARCHAR(50), booking_date DATE, start_time TIME, end_time TIME,
                status VARCHAR(30) DEFAULT 'Booked', checked_in_at DATETIME NULL, checked_out_at DATETIME NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "study_rooms": """
            CREATE TABLE IF NOT EXISTS study_rooms (
                room_id INT AUTO_INCREMENT PRIMARY KEY, room_name VARCHAR(80) UNIQUE, floor_name VARCHAR(50), capacity INT DEFAULT 4, status VARCHAR(30) DEFAULT 'Available'
            )""",
        "room_bookings": """
            CREATE TABLE IF NOT EXISTS room_bookings (
                room_booking_id INT AUTO_INCREMENT PRIMARY KEY, room_id INT, prn_no VARCHAR(50), booking_date DATE, start_time TIME, end_time TIME,
                purpose VARCHAR(250), status VARCHAR(30) DEFAULT 'Booked', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "library_visits": """
            CREATE TABLE IF NOT EXISTS library_visits (
                visit_id INT AUTO_INCREMENT PRIMARY KEY, prn_no VARCHAR(50), entry_time DATETIME DEFAULT CURRENT_TIMESTAMP, exit_time DATETIME NULL,
                method VARCHAR(30) DEFAULT 'QR', notes VARCHAR(250)
            )""",
        "donations": """
            CREATE TABLE IF NOT EXISTS donations (
                donation_id INT AUTO_INCREMENT PRIMARY KEY, donor_name VARCHAR(150), donor_contact VARCHAR(100), book_title VARCHAR(200),
                author VARCHAR(150), isbn VARCHAR(30), quantity INT DEFAULT 1, condition_status VARCHAR(30) DEFAULT 'Good',
                donated_on DATE, status VARCHAR(30) DEFAULT 'Pending', approved_by VARCHAR(100), remarks VARCHAR(250)
            )""",
        "interlibrary_loans": """
            CREATE TABLE IF NOT EXISTS interlibrary_loans (
                loan_id INT AUTO_INCREMENT PRIMARY KEY, book_id VARCHAR(30), from_branch VARCHAR(100), to_branch VARCHAR(100),
                requested_by VARCHAR(100), request_date DATE, due_date DATE NULL, status VARCHAR(30) DEFAULT 'Requested', remarks VARCHAR(250)
            )""",
        "helpdesk_tickets": """
            CREATE TABLE IF NOT EXISTS helpdesk_tickets (
                ticket_id INT AUTO_INCREMENT PRIMARY KEY, prn_no VARCHAR(50), subject VARCHAR(200), category VARCHAR(80), description TEXT,
                status VARCHAR(30) DEFAULT 'Open', assigned_to VARCHAR(100), response TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME NULL
            )""",
        "book_requests": """
            CREATE TABLE IF NOT EXISTS book_requests (
                request_id INT AUTO_INCREMENT PRIMARY KEY, prn_no VARCHAR(50), title VARCHAR(200), author VARCHAR(150), reason VARCHAR(250),
                votes INT DEFAULT 0, status VARCHAR(30) DEFAULT 'Requested', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "fine_disputes": """
            CREATE TABLE IF NOT EXISTS fine_disputes (
                dispute_id INT AUTO_INCREMENT PRIMARY KEY, transaction_id INT, prn_no VARCHAR(50), amount DECIMAL(10,2), reason VARCHAR(250),
                status VARCHAR(30) DEFAULT 'Pending', reviewed_by VARCHAR(100), review_note VARCHAR(250), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "library_events": """
            CREATE TABLE IF NOT EXISTS library_events (
                event_id INT AUTO_INCREMENT PRIMARY KEY, title VARCHAR(200), event_date DATE, start_time TIME, end_time TIME,
                venue VARCHAR(150), description VARCHAR(500), seats INT DEFAULT 50, created_by VARCHAR(100), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
        "event_registrations": """
            CREATE TABLE IF NOT EXISTS event_registrations (
                registration_id INT AUTO_INCREMENT PRIMARY KEY, event_id INT, prn_no VARCHAR(50), registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_event_reg (event_id, prn_no)
            )""",
        "book_clubs": """
            CREATE TABLE IF NOT EXISTS book_clubs (
                club_id INT AUTO_INCREMENT PRIMARY KEY, club_name VARCHAR(120) UNIQUE, current_book_id VARCHAR(30) NULL,
                meeting_day VARCHAR(30), description VARCHAR(500), created_by VARCHAR(100)
            )""",
        "club_members": """
            CREATE TABLE IF NOT EXISTS club_members (
                club_member_id INT AUTO_INCREMENT PRIMARY KEY, club_id INT, prn_no VARCHAR(50), joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_club_member (club_id, prn_no)
            )""",
        "reading_plans": """
            CREATE TABLE IF NOT EXISTS reading_plans (
                plan_id INT AUTO_INCREMENT PRIMARY KEY, prn_no VARCHAR(50), month_name VARCHAR(20), year_no INT, target_books INT DEFAULT 5,
                completed_books INT DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_read_plan (prn_no, month_name, year_no)
            )""",
        "login_audit": """
            CREATE TABLE IF NOT EXISTS login_audit (
                login_id INT AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100), role_name VARCHAR(50), success TINYINT(1), ip_address VARCHAR(80),
                login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
    }
    for sql in create_sql.values():
        cur.execute(sql)

    cur.execute("SELECT COUNT(*) FROM books")
    if cur.fetchone()[0] == 0:
        cur.executemany("""INSERT INTO books (book_id,title,author,category,price,status,quantity_total,quantity_available)
                          VALUES (%s,%s,%s,%s,%s,'Available',1,1)""", BOOK_SEED)

    # Fix quantity totals for existing legacy rows where needed.
    cur.execute("UPDATE books SET quantity_total=1 WHERE quantity_total IS NULL OR quantity_total<1")
    cur.execute("UPDATE books SET quantity_available=1 WHERE quantity_available IS NULL")

    defaults = [
        ("Student", 3, 14, 50), ("Faculty", 10, 30, 20), ("Teacher", 10, 30, 20), ("Staff", 5, 20, 30)
    ]
    cur.executemany("""INSERT INTO circulation_rules (member_type,max_books,issue_days,fine_per_day)
                       VALUES (%s,%s,%s,%s) ON DUPLICATE KEY UPDATE max_books=VALUES(max_books), issue_days=VALUES(issue_days), fine_per_day=VALUES(fine_per_day)""", defaults)
    roles = [
        ("Admin",1,1,1,1,1,1),("Librarian",1,0,1,1,1,0),("Staff",1,0,1,1,1,0),("Student",0,0,1,0,0,0),("Faculty",0,0,1,1,1,0)
    ]
    cur.executemany("""INSERT INTO permissions (role_name,can_add_book,can_delete_book,can_issue,can_return,can_reports,can_backup)
                       VALUES (%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE
                       can_add_book=VALUES(can_add_book), can_delete_book=VALUES(can_delete_book), can_issue=VALUES(can_issue),
                       can_return=VALUES(can_return), can_reports=VALUES(can_reports), can_backup=VALUES(can_backup)""", roles)
    cur.execute("SELECT COUNT(*) FROM study_seats")
    if cur.fetchone()[0] == 0:
        seat_rows=[]
        for floor, prefix in [("Ground Floor","G"),("First Floor","F"),("Second Floor","S")]:
            for i in range(1,7):
                seat_rows.append((f"{prefix}{i:02d}", floor, "Reading Zone", "Available"))
        cur.executemany("INSERT INTO study_seats(seat_code,floor_name,zone_name,status) VALUES(%s,%s,%s,%s)", seat_rows)
    cur.execute("SELECT COUNT(*) FROM study_rooms")
    if cur.fetchone()[0] == 0:
        cur.executemany("INSERT INTO study_rooms(room_name,floor_name,capacity,status) VALUES(%s,%s,%s,%s)", [
            ("Discussion Room 1","First Floor",6,"Available"),("Discussion Room 2","First Floor",8,"Available"),("Research Room","Second Floor",4,"Available")
        ])
    conn.commit()
    cur.close()
    conn.close()


def db_query(sql, params=(), fetch=True):
    conn = server_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall() if fetch else None
    if not fetch:
        conn.commit()
    cur.close(); conn.close()
    return rows


def db_exec(sql, params=()):
    conn = server_connection()
    cur = conn.cursor()
    cur.execute(sql, params)
    last = cur.lastrowid
    conn.commit()
    cur.close(); conn.close()
    return last


def log_action(action, details):
    try:
        actor = session.get("full_name") or session.get("username") or "System"
        db_exec("INSERT INTO activity_log(action,details,actor) VALUES(%s,%s,%s)", (action, details, actor))
    except Exception:
        pass


def logged_in(*allowed_roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not session.get("logged_in"):
                return redirect(url_for("login", next=request.path))
            if allowed_roles and session.get("role") not in allowed_roles:
                flash("You do not have permission for this page.", "error")
                return redirect(url_for("dashboard"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator


@app.context_processor
def context_data():
    return {
        "username": session.get("username", "Guest"),
        "full_name": session.get("full_name", ""),
        "role": session.get("role", ""),
        "dark_mode": session.get("dark_mode", False),
        "today": date.today(),
        "library_name": "College Library",
        "app_title": "College Library Portal",
    }


@app.route("/manifest.json")
def manifest():
    return send_from_directory(os.path.join(app.static_folder), "manifest.json", mimetype="application/manifest+json")

@app.route("/sw.js")
def service_worker():
    return send_from_directory(os.path.join(app.static_folder), "sw.js", mimetype="application/javascript")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = DEMO_USERS.get(username)
        if user and user["password"] == password:
            session.clear()
            session.update(logged_in=True, username=username, role=user["role"], full_name=user["name"])
            log_action("Login", f"{username} logged in")
            try:
                db_exec("INSERT INTO login_audit(username,role_name,success,ip_address) VALUES(%s,%s,1,%s)", (username,user["role"],request.remote_addr))
            except Exception:
                pass
            return redirect(request.args.get("next") or url_for("dashboard"))
        try:
            db_exec("INSERT INTO login_audit(username,role_name,success,ip_address) VALUES(%s,%s,0,%s)", (username,"Unknown",request.remote_addr))
        except Exception:
            pass
        flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    log_action("Logout", f"{session.get('username','User')} logged out")
    session.clear()
    return redirect(url_for("login"))


@app.route("/toggle-theme", methods=["POST"])
@logged_in()
def toggle_theme():
    session["dark_mode"] = not session.get("dark_mode", False)
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/")
def home():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))
    latest = db_query("SELECT title,message,priority FROM announcements ORDER BY announcement_id DESC LIMIT 5")
    popular = db_query("SELECT book_id,book_title,COUNT(*) cnt FROM transactions GROUP BY book_id,book_title ORDER BY cnt DESC LIMIT 6")
    new_books = db_query("SELECT book_id,title,author,category,status FROM books WHERE archived=0 ORDER BY book_id DESC LIMIT 6")
    return render_template("public_home.html", latest=latest, popular=popular, new_books=new_books)


@app.route("/dashboard")
@logged_in()
def dashboard():
    total_books = db_query("SELECT COALESCE(SUM(quantity_total),COUNT(*)) AS n FROM books WHERE archived=0")[0]["n"]
    available = db_query("SELECT COALESCE(SUM(quantity_available),0) AS n FROM books WHERE archived=0")[0]["n"]
    issued = db_query("SELECT COUNT(*) AS n FROM transactions WHERE status='Issued'")[0]["n"]
    members = db_query("SELECT COUNT(*) AS n FROM members")[0]["n"]
    overdue = db_query("SELECT COUNT(*) AS n FROM transactions WHERE status='Issued' AND date_due < CURDATE()")[0]["n"]
    fine = db_query("SELECT COALESCE(SUM(late_return_fine),0) AS n FROM transactions")[0]["n"]
    categories = db_query("SELECT COALESCE(category,'Other') category, COUNT(*) n FROM books WHERE archived=0 GROUP BY category ORDER BY n DESC LIMIT 8")
    popular = db_query("""SELECT book_id,book_title,COUNT(*) cnt FROM transactions GROUP BY book_id,book_title ORDER BY cnt DESC LIMIT 5""")
    notices = db_query("SELECT title,message,priority FROM announcements ORDER BY announcement_id DESC LIMIT 5")
    return render_template("dashboard.html", stats={"books":total_books,"available":available,"issued":issued,"members":members,"overdue":overdue,"fine":fine}, categories=categories, popular=popular, notices=notices)


@app.route("/books", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff")
def books():
    if request.method == "POST":
        action = request.form.get("action")
        book_id = request.form.get("book_id","...").strip()
        if action == "add":
            try:
                db_exec("""INSERT INTO books(book_id,title,author,category,price,status,quantity_total,quantity_available,isbn,publisher,edition,publish_year,rack,shelf)
                           VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (book_id,request.form.get("title"),request.form.get("author"),request.form.get("category"),request.form.get("price") or 0,
                         "Available",request.form.get("quantity_total") or 1,request.form.get("quantity_total") or 1,request.form.get("isbn"),request.form.get("publisher"),
                         request.form.get("edition"),request.form.get("publish_year") or None,request.form.get("rack"),request.form.get("shelf")))
                log_action("Add Book", f"{book_id} added")
                flash("Book added successfully.","success")
            except Error as e:
                flash(f"Could not add book: {e}","error")
        elif action == "update":
            db_exec("""UPDATE books SET title=%s,author=%s,category=%s,price=%s,quantity_total=%s,quantity_available=LEAST(quantity_available + GREATEST(%s-quantity_total,0),%s),isbn=%s,publisher=%s,edition=%s,publish_year=%s,rack=%s,shelf=%s WHERE book_id=%s""",
                    (request.form.get("title"),request.form.get("author"),request.form.get("category"),request.form.get("price") or 0,
                     request.form.get("quantity_total") or 1,request.form.get("quantity_total") or 1,request.form.get("quantity_total") or 1,
                     request.form.get("isbn"),request.form.get("publisher"),request.form.get("edition"),request.form.get("publish_year") or None,
                     request.form.get("rack"),request.form.get("shelf"),book_id))
            log_action("Update Book", f"{book_id} updated")
            flash("Book updated.","success")
        elif action == "archive":
            db_exec("UPDATE books SET archived=1, status='Archived' WHERE book_id=%s", (book_id,))
            log_action("Archive Book", f"{book_id} archived")
            flash("Book archived.","success")
    rows = db_query("SELECT * FROM books WHERE archived=0 ORDER BY book_id")
    return render_template("books.html", books=rows)


@app.route("/members", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff")
def members():
    if request.method == "POST":
        db_exec("""INSERT INTO members(prn_no,member_type,id_no,first_name,last_name,address1,address2,postcode,mobile,email,class_name)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE member_type=VALUES(member_type),id_no=VALUES(id_no),first_name=VALUES(first_name),last_name=VALUES(last_name),
                   address1=VALUES(address1),address2=VALUES(address2),postcode=VALUES(postcode),mobile=VALUES(mobile),email=VALUES(email),class_name=VALUES(class_name)""",
                (request.form.get("prn_no"),request.form.get("member_type"),request.form.get("id_no"),request.form.get("first_name"),request.form.get("last_name"),
                 request.form.get("address1"),request.form.get("address2"),request.form.get("postcode"),request.form.get("mobile"),request.form.get("email"),request.form.get("class_name")))
        log_action("Member Save", f"{request.form.get('prn_no')} saved")
        flash("Member saved.","success")
    rows = db_query("SELECT * FROM members ORDER BY prn_no")
    classes = db_query("SELECT * FROM classes ORDER BY class_name")
    return render_template("members.html", members=rows, classes=classes)


@app.route("/issue", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff","Faculty")
def issue_book():
    if request.method == "POST":
        prn = request.form.get("prn_no")
        book_id = request.form.get("book_id")
        member = db_query("SELECT * FROM members WHERE prn_no=%s", (prn,))
        book = db_query("SELECT * FROM books WHERE book_id=%s AND archived=0", (book_id,))
        if not member or not book or book[0].get("quantity_available",1) <= 0:
            flash("Member/book invalid or no copy is available.","error")
        else:
            mtype = member[0].get("member_type") or "Student"
            rule = db_query("SELECT * FROM circulation_rules WHERE member_type=%s", (mtype,))
            rule = rule[0] if rule else db_query("SELECT * FROM circulation_rules WHERE member_type='Student'")[0]
            active = db_query("SELECT COUNT(*) n FROM transactions WHERE prn_no=%s AND status='Issued'", (prn,))[0]["n"]
            if active >= rule["max_books"]:
                flash(f"Issue limit reached. Maximum {rule['max_books']} active books allowed.","error")
            else:
                issue_date = date.today()
                due = issue_date + timedelta(days=int(rule["issue_days"]))
                b = book[0]
                db_exec("""INSERT INTO transactions(prn_no,book_id,book_title,author,date_borrowed,date_due,days_allowed,status)
                           VALUES(%s,%s,%s,%s,%s,%s,%s,'Issued')""", (prn,book_id,b["title"],b["author"],issue_date,due,rule["issue_days"]))
                db_exec("UPDATE books SET quantity_available=GREATEST(quantity_available-1,0), status=IF(quantity_available-1>0,'Available','Issued') WHERE book_id=%s", (book_id,))
                log_action("Issue Book", f"{book_id} issued to {prn}")
                flash(f"Book issued. Due date: {due}","success")
    members_rows = db_query("SELECT prn_no,TRIM(CONCAT(COALESCE(first_name,''),' ',COALESCE(last_name,''))) name FROM members ORDER BY prn_no")
    books_rows = db_query("SELECT book_id,title,quantity_available FROM books WHERE archived=0 AND quantity_available>0 ORDER BY book_id")
    return render_template("issue.html", members=members_rows, books=books_rows)


@app.route("/return", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff","Faculty")
def return_book():
    if request.method == "POST":
        tx_id = request.form.get("transaction_id")
        tx = db_query("SELECT * FROM transactions WHERE transaction_id=%s AND status='Issued'", (tx_id,))
        if tx:
            tx = tx[0]
            rule = db_query("SELECT * FROM circulation_rules WHERE member_type=(SELECT member_type FROM members WHERE prn_no=%s)", (tx["prn_no"],))
            fine_day = float(rule[0]["fine_per_day"]) if rule else 50.0
            late_days = max((date.today() - tx["date_due"]).days, 0)
            fine = late_days * fine_day
            condition = request.form.get("condition", "Good")
            db_exec("UPDATE transactions SET return_date=CURDATE(),late_return_fine=%s,date_overdue=%s,status='Returned',condition_on_return=%s WHERE transaction_id=%s",
                    (fine, str(late_days) if late_days else "0", condition, tx_id))
            db_exec("UPDATE books SET quantity_available=quantity_available+1,status='Available' WHERE book_id=%s", (tx["book_id"],))
            if condition in ("Lost", "Damaged"):
                db_exec("UPDATE books SET status=%s WHERE book_id=%s", (condition, tx["book_id"]))
            log_action("Return Book", f"Transaction {tx_id} returned; fine ₹{fine:.2f}; condition {condition}")
            flash(f"Book returned. Fine: ₹{fine:.2f}","success")
    rows = db_query("SELECT * FROM transactions WHERE status='Issued' ORDER BY date_due")
    return render_template("return.html", transactions=rows)


@app.route("/catalogue")
@logged_in()
def catalogue():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "All")
    params = []
    sql = "SELECT * FROM books WHERE archived=0"
    if q:
        like = f"%{q}%"
        sql += " AND (book_id LIKE %s OR title LIKE %s OR author LIKE %s OR isbn LIKE %s OR publisher LIKE %s)"
        params += [like]*5
    if cat != "All":
        sql += " AND category=%s"; params.append(cat)
    sql += " ORDER BY title"
    rows = db_query(sql, tuple(params))
    cats = [r["category"] for r in db_query("SELECT DISTINCT category FROM books WHERE category IS NOT NULL ORDER BY category")]
    return render_template("catalogue.html", books=rows, categories=cats, q=q, category=cat)


@app.route("/acquisition")
@logged_in("Admin","Librarian","Staff")
def acquisition():
    suppliers = db_query("SELECT * FROM suppliers ORDER BY supplier_id DESC")
    purchases = db_query("""SELECT p.*,s.name supplier_name FROM purchases p LEFT JOIN suppliers s ON p.supplier_id=s.supplier_id ORDER BY p.purchase_id DESC""")
    books_rows = db_query("SELECT book_id,title FROM books WHERE archived=0 ORDER BY book_id")
    return render_template("acquisition.html", suppliers=suppliers, purchases=purchases, books=books_rows)


@app.post("/supplier/add")
@logged_in("Admin","Librarian","Staff")
def add_supplier():
    db_exec("INSERT INTO suppliers(name,contact,email,address) VALUES(%s,%s,%s,%s)", (request.form.get("name"),request.form.get("contact"),request.form.get("email"),request.form.get("address")))
    log_action("Add Supplier", request.form.get("name","")); flash("Supplier added.","success")
    return redirect(url_for("acquisition"))


@app.post("/purchase/add")
@logged_in("Admin","Librarian","Staff")
def add_purchase():
    qty = int(request.form.get("quantity") or 1)
    unit = float(request.form.get("unit_price") or 0)
    pid = db_exec("""INSERT INTO purchases(book_id,supplier_id,invoice_no,quantity,unit_price,purchase_date,total_cost,notes)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s)""", (request.form.get("book_id"),request.form.get("supplier_id") or None,request.form.get("invoice_no"),qty,unit,request.form.get("purchase_date") or date.today(),qty*unit,request.form.get("notes")))
    db_exec("UPDATE books SET quantity_total=quantity_total+%s, quantity_available=quantity_available+%s,status='Available' WHERE book_id=%s", (qty,qty,request.form.get("book_id")))
    log_action("Purchase", f"Purchase {pid} added"); flash("Purchase recorded and stock updated.","success")
    return redirect(url_for("acquisition"))


@app.route("/accession", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff")
def accession():
    if request.method == "POST":
        db_exec("""INSERT INTO accession_register(accession_no,book_id,isbn,edition,publisher,purchase_date,price,rack,shelf,condition_status,branch)
                   VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                (request.form.get("accession_no"),request.form.get("book_id"),request.form.get("isbn"),request.form.get("edition"),request.form.get("publisher"),
                 request.form.get("purchase_date") or date.today(),request.form.get("price") or 0,request.form.get("rack"),request.form.get("shelf"),request.form.get("condition_status"),request.form.get("branch")))
        log_action("Accession Entry", request.form.get("accession_no","")); flash("Accession record saved.","success")
    rows = db_query("SELECT * FROM accession_register ORDER BY accession_id DESC")
    books_rows = db_query("SELECT book_id,title FROM books WHERE archived=0 ORDER BY book_id")
    return render_template("accession.html", rows=rows, books=books_rows)


@app.route("/inventory-audit", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff")
def inventory_audit():
    if request.method == "POST":
        system_qty = int(request.form.get("system_qty") or 0)
        physical = int(request.form.get("physical_qty") or 0)
        damaged = int(request.form.get("damaged_qty") or 0)
        missing = max(system_qty - physical, 0)
        db_exec("INSERT INTO inventory_audit(audit_date,book_id,system_qty,physical_qty,missing_qty,damaged_qty,remarks,verified_by) VALUES(CURDATE(),%s,%s,%s,%s,%s,%s,%s)",
                (request.form.get("book_id"),system_qty,physical,missing,damaged,request.form.get("remarks"),session.get("full_name")))
        log_action("Inventory Audit", request.form.get("book_id","")); flash("Inventory audit saved.","success")
    rows = db_query("SELECT * FROM inventory_audit ORDER BY audit_id DESC")
    books_rows = db_query("SELECT book_id,title,quantity_total FROM books WHERE archived=0 ORDER BY book_id")
    return render_template("inventory.html", audits=rows, books=books_rows)


@app.route("/transfers", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff")
def transfers():
    if request.method == "POST":
        db_exec("INSERT INTO transfers(book_id,from_branch,to_branch,from_rack,to_rack,quantity,transfer_date,remarks,transferred_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (request.form.get("book_id"),request.form.get("from_branch"),request.form.get("to_branch"),request.form.get("from_rack"),request.form.get("to_rack"),request.form.get("quantity") or 1,request.form.get("transfer_date") or date.today(),request.form.get("remarks"),session.get("full_name")))
        db_exec("UPDATE books SET rack=%s,shelf=%s WHERE book_id=%s", (request.form.get("to_rack"),request.form.get("to_shelf"),request.form.get("book_id")))
        log_action("Book Transfer", request.form.get("book_id","")); flash("Transfer recorded.","success")
    rows = db_query("SELECT * FROM transfers ORDER BY transfer_id DESC")
    books_rows = db_query("SELECT book_id,title,rack,shelf FROM books WHERE archived=0 ORDER BY book_id")
    return render_template("transfers.html", rows=rows, books=books_rows)


@app.route("/circulation-rules", methods=["GET","POST"])
@logged_in("Admin","Librarian")
def circulation_rules():
    if request.method == "POST":
        db_exec("""INSERT INTO circulation_rules(member_type,max_books,issue_days,fine_per_day) VALUES(%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE max_books=VALUES(max_books),issue_days=VALUES(issue_days),fine_per_day=VALUES(fine_per_day)""",
                (request.form.get("member_type"),request.form.get("max_books") or 3,request.form.get("issue_days") or 14,request.form.get("fine_per_day") or 50))
        flash("Circulation rule saved.","success")
    rows = db_query("SELECT * FROM circulation_rules ORDER BY member_type")
    return render_template("rules.html", rules=rows)


@app.route("/fine-waiver", methods=["GET","POST"])
@logged_in("Admin")
def fine_waiver():
    if request.method == "POST":
        original = float(request.form.get("original_fine") or 0)
        waiver = min(float(request.form.get("waiver_amount") or 0), original)
        db_exec("INSERT INTO fine_waivers(transaction_id,original_fine,waiver_amount,final_fine,reason,approved_by,status) VALUES(%s,%s,%s,%s,%s,%s,'Approved')",
                (request.form.get("transaction_id"),original,waiver,original-waiver,request.form.get("reason"),session.get("full_name")))
        flash("Fine waiver recorded.","success")
    rows = db_query("SELECT * FROM fine_waivers ORDER BY waiver_id DESC")
    txs = db_query("SELECT transaction_id,prn_no,book_title,late_return_fine FROM transactions WHERE late_return_fine>0 ORDER BY transaction_id DESC")
    return render_template("waiver.html", waivers=rows, transactions=txs)


@app.route("/staff-shifts", methods=["GET","POST"])
@logged_in("Admin","Librarian")
def staff_shifts():
    if request.method == "POST":
        db_exec("INSERT INTO staff_shifts(staff_name,shift_date,entry_time,exit_time,status,notes) VALUES(%s,%s,%s,%s,%s,%s)",
                (request.form.get("staff_name"),request.form.get("shift_date") or date.today(),request.form.get("entry_time"),request.form.get("exit_time"),request.form.get("status","Present"),request.form.get("notes")))
        flash("Shift record saved.","success")
    rows = db_query("SELECT * FROM staff_shifts ORDER BY shift_id DESC")
    return render_template("shifts.html", rows=rows)


@app.route("/permissions", methods=["GET","POST"])
@logged_in("Admin")
def permissions():
    if request.method == "POST":
        role = request.form.get("role_name")
        vals = [request.form.get(k)=="on" for k in ["can_add_book","can_delete_book","can_issue","can_return","can_reports","can_backup"]]
        db_exec("""UPDATE permissions SET can_add_book=%s,can_delete_book=%s,can_issue=%s,can_return=%s,can_reports=%s,can_backup=%s WHERE role_name=%s""", (*vals,role))
        flash("Permissions updated.","success")
    rows = db_query("SELECT * FROM permissions ORDER BY permission_id")
    return render_template("permissions.html", rows=rows)


@app.route("/approvals", methods=["GET","POST"])
@logged_in("Admin","Librarian")
def approvals():
    if request.method == "POST":
        request_id = request.form.get("request_id")
        status = request.form.get("status", "Approved")
        db_exec("UPDATE approval_requests SET status=%s,approved_by=%s WHERE request_id=%s", (status,session.get("full_name"),request_id))
        log_action("Approval", f"Request {request_id}: {status}")
        flash("Approval updated.","success")
    rows = db_query("SELECT * FROM approval_requests ORDER BY request_id DESC")
    return render_template("approvals.html", rows=rows)


@app.post("/approval-request")
@logged_in("Staff","Librarian","Faculty")
def approval_request():
    db_exec("INSERT INTO approval_requests(request_type,reference_id,requested_by,reason) VALUES(%s,%s,%s,%s)", (request.form.get("request_type"),request.form.get("reference_id"),session.get("full_name"),request.form.get("reason")))
    flash("Approval request submitted.","success")
    return redirect(url_for("approvals"))


@app.route("/classes", methods=["GET","POST"])
@logged_in("Admin","Librarian")
def classes():
    if request.method == "POST":
        db_exec("INSERT INTO classes(class_name,course,year_name,section_name) VALUES(%s,%s,%s,%s) ON DUPLICATE KEY UPDATE course=VALUES(course),year_name=VALUES(year_name),section_name=VALUES(section_name)",
                (request.form.get("class_name"),request.form.get("course"),request.form.get("year_name"),request.form.get("section_name")))
        flash("Class saved.","success")
    rows = db_query("SELECT * FROM classes ORDER BY class_name")
    return render_template("classes.html", rows=rows)


@app.route("/reading-achievements")
@logged_in()
def reading_achievements():
    readers = db_query("SELECT prn_no,COUNT(*) cnt FROM transactions WHERE status='Returned' GROUP BY prn_no ORDER BY cnt DESC LIMIT 15")
    badges = db_query("SELECT * FROM reading_badges ORDER BY awarded_on DESC")
    # award badges based on returned-book counts
    for r in readers:
        count = int(r["cnt"])
        candidates = [("Bronze Reader",10),("Silver Reader",25),("Gold Reader",50),("Library Champion",100)]
        for badge, threshold in candidates:
            if count >= threshold:
                try:
                    db_exec("INSERT IGNORE INTO reading_badges(prn_no,badge_name,awarded_on) VALUES(%s,%s,CURDATE())", (r["prn_no"],badge))
                except Exception:
                    pass
    badges = db_query("SELECT * FROM reading_badges ORDER BY awarded_on DESC")
    return render_template("achievements.html", readers=readers, badges=badges)


@app.route("/resources", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff")
def resources():
    if request.method == "POST":
        db_exec("INSERT INTO digital_resources(title,resource_type,publisher,resource_url,notes) VALUES(%s,%s,%s,%s,%s)", (request.form.get("title"),request.form.get("resource_type"),request.form.get("publisher"),request.form.get("resource_url"),request.form.get("notes")))
        flash("Digital resource added.","success")
    rows = db_query("SELECT * FROM digital_resources ORDER BY resource_id DESC")
    return render_template("resources.html", rows=rows)


@app.route("/editions", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff")
def editions():
    if request.method == "POST":
        db_exec("INSERT INTO book_editions(book_id,edition,isbn,publisher,publish_year,price,copies) VALUES(%s,%s,%s,%s,%s,%s,%s)",
                (request.form.get("book_id"),request.form.get("edition"),request.form.get("isbn"),request.form.get("publisher"),request.form.get("publish_year") or None,request.form.get("price") or 0,request.form.get("copies") or 1))
        flash("Edition saved.","success")
    rows = db_query("SELECT * FROM book_editions ORDER BY edition_id DESC")
    books_rows = db_query("SELECT book_id,title FROM books WHERE archived=0 ORDER BY book_id")
    return render_template("editions.html", rows=rows, books=books_rows)


@app.route("/advanced-search")
@logged_in()
def advanced_search():
    q = request.args.get("q","").strip(); isbn = request.args.get("isbn","").strip(); publisher = request.args.get("publisher","").strip(); rack = request.args.get("rack","").strip(); status = request.args.get("status","All")
    sql = "SELECT * FROM books WHERE 1=1"; params=[]
    if q:
        sql += " AND (title LIKE %s OR author LIKE %s OR category LIKE %s OR book_id LIKE %s)"; params += [f"%{q}%"]*4
    if isbn: sql += " AND isbn LIKE %s"; params.append(f"%{isbn}%")
    if publisher: sql += " AND publisher LIKE %s"; params.append(f"%{publisher}%")
    if rack: sql += " AND rack LIKE %s"; params.append(f"%{rack}%")
    if status != "All": sql += " AND status=%s"; params.append(status)
    rows = db_query(sql + " ORDER BY title", tuple(params))
    return render_template("advanced_search.html", rows=rows)


@app.route("/demand")
@logged_in("Admin","Librarian","Staff")
def demand():
    rows = db_query("""SELECT b.book_id,b.title,b.quantity_total,b.quantity_available,COALESCE(t.issue_count,0) issue_count
                       FROM books b LEFT JOIN (SELECT book_id,COUNT(*) issue_count FROM transactions GROUP BY book_id) t ON b.book_id=t.book_id
                       WHERE b.archived=0 ORDER BY issue_count DESC""")
    recommendations=[]
    for r in rows:
        total=max(int(r["quantity_total"] or 1),1); avail=int(r["quantity_available"] or 0); issues=int(r["issue_count"] or 0)
        if (issues >= 5 and avail <= 2) or (issues >= 10 and avail <= max(3,total//3)):
            recommendations.append({**r,"recommended_purchase":max(2, issues//4 + 1)})
    return render_template("demand.html", rows=rows, recommendations=recommendations)


@app.route("/faculty")
@logged_in("Faculty")
def faculty_portal():
    name=session.get("full_name")
    rows=db_query("SELECT * FROM transactions WHERE status='Issued' ORDER BY date_due")
    return render_template("faculty.html", name=name, transactions=rows)



# ---------------- SUPER5 NEW CAMPUS FEATURES ----------------
@app.route("/seat-booking", methods=["GET","POST"])
@logged_in()
def seat_booking():
    msg = None
    if request.method == "POST":
        seat_id = request.form.get("seat_id")
        booking_date = request.form.get("booking_date") or str(date.today())
        start = request.form.get("start_time") or "10:00"
        end = request.form.get("end_time") or "12:00"
        prn = session.get("prn_no") or request.form.get("prn_no") or (session.get("full_name") or session.get("username"))
        clashes = db_query("""SELECT booking_id FROM seat_bookings WHERE seat_id=%s AND booking_date=%s AND status IN ('Booked','Checked-In')
                              AND NOT (end_time<=%s OR start_time>=%s)""", (seat_id,booking_date,start,end))
        if clashes:
            flash("Seat is already booked for that time.","error")
        else:
            db_exec("INSERT INTO seat_bookings(seat_id,prn_no,booking_date,start_time,end_time) VALUES(%s,%s,%s,%s,%s)",(seat_id,prn,booking_date,start,end))
            log_action("Seat Booking", f"Seat {seat_id} booked by {prn}")
            flash("Study seat booked successfully.","success")
    seats=db_query("SELECT * FROM study_seats ORDER BY floor_name,seat_code")
    mine=db_query("""SELECT sb.*,ss.seat_code,ss.floor_name FROM seat_bookings sb JOIN study_seats ss ON ss.seat_id=sb.seat_id
                     WHERE sb.prn_no=%s ORDER BY booking_date DESC,start_time DESC LIMIT 20""",(session.get("prn_no") or session.get("full_name") or session.get("username"),))
    return render_template("seat_booking.html",seats=seats,mine=mine,today=date.today())

@app.route("/seat-checkin/<int:booking_id>")
@logged_in()
def seat_checkin(booking_id):
    db_exec("UPDATE seat_bookings SET status='Checked-In',checked_in_at=NOW() WHERE booking_id=%s",(booking_id,))
    flash("Seat check-in recorded.","success")
    return redirect(url_for("seat_booking"))

@app.route("/seat-checkout/<int:booking_id>")
@logged_in()
def seat_checkout(booking_id):
    db_exec("UPDATE seat_bookings SET status='Completed',checked_out_at=NOW() WHERE booking_id=%s",(booking_id,))
    flash("Seat check-out recorded.","success")
    return redirect(url_for("seat_booking"))

@app.route("/room-booking", methods=["GET","POST"])
@logged_in()
def room_booking():
    if request.method == "POST":
        room_id=request.form.get("room_id"); booking_date=request.form.get("booking_date") or str(date.today()); start=request.form.get("start_time") or "11:00"; end=request.form.get("end_time") or "12:00"
        prn=session.get("prn_no") or request.form.get("prn_no") or (session.get("full_name") or session.get("username"))
        if db_query("""SELECT room_booking_id FROM room_bookings WHERE room_id=%s AND booking_date=%s AND status='Booked'
                       AND NOT (end_time<=%s OR start_time>=%s)""",(room_id,booking_date,start,end)):
            flash("Room is already booked for that time.","error")
        else:
            db_exec("INSERT INTO room_bookings(room_id,prn_no,booking_date,start_time,end_time,purpose) VALUES(%s,%s,%s,%s,%s,%s)",(room_id,prn,booking_date,start,end,request.form.get("purpose")))
            flash("Study room booked.","success")
    rooms=db_query("SELECT * FROM study_rooms ORDER BY room_id")
    mine=db_query("SELECT rb.*,sr.room_name,sr.capacity FROM room_bookings rb JOIN study_rooms sr ON sr.room_id=rb.room_id WHERE rb.prn_no=%s ORDER BY booking_date DESC,start_time DESC LIMIT 20",(session.get("prn_no") or session.get("full_name") or session.get("username"),))
    return render_template("room_booking.html",rooms=rooms,mine=mine,today=date.today())

@app.route("/library-entry", methods=["GET","POST"])
@logged_in()
def library_entry():
    prn=request.form.get("prn_no") if request.method=="POST" else (session.get("prn_no") or "")
    if request.method=="POST":
        if not prn: flash("Enter PRN.","error")
        else:
            open_visit=db_query("SELECT visit_id FROM library_visits WHERE prn_no=%s AND exit_time IS NULL ORDER BY visit_id DESC LIMIT 1",(prn,))
            if open_visit:
                db_exec("UPDATE library_visits SET exit_time=NOW() WHERE visit_id=%s",(open_visit[0]["visit_id"],))
                flash("Library exit recorded.","success")
            else:
                db_exec("INSERT INTO library_visits(prn_no,method) VALUES(%s,%s)",(prn,request.form.get("method","QR")))
                flash("Library entry recorded.","success")
    recent=db_query("SELECT * FROM library_visits ORDER BY visit_id DESC LIMIT 30")
    return render_template("library_entry.html",recent=recent,prn=prn)

@app.route("/donations", methods=["GET","POST"])
@logged_in("Admin","Librarian","Staff")
def donations():
    if request.method=="POST":
        db_exec("INSERT INTO donations(donor_name,donor_contact,book_title,author,isbn,quantity,condition_status,donated_on,remarks) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (request.form.get("donor_name"),request.form.get("donor_contact"),request.form.get("book_title"),request.form.get("author"),request.form.get("isbn"),request.form.get("quantity") or 1,request.form.get("condition_status","Good"),request.form.get("donated_on") or date.today(),request.form.get("remarks")))
        flash("Donation request saved.","success")
    rows=db_query("SELECT * FROM donations ORDER BY donation_id DESC")
    return render_template("donations.html",rows=rows)

@app.route("/donations/<int:donation_id>/<status>")
@logged_in("Admin","Librarian")
def donation_status(donation_id,status):
    if status not in ("Approved","Rejected"): status="Pending"
    db_exec("UPDATE donations SET status=%s,approved_by=%s WHERE donation_id=%s",(status,session.get("full_name"),donation_id))
    flash(f"Donation marked {status}.","success")
    return redirect(url_for("donations"))

@app.route("/loan-requests", methods=["GET","POST"])
@logged_in()
def loan_requests():
    if request.method=="POST":
        db_exec("INSERT INTO interlibrary_loans(book_id,from_branch,to_branch,requested_by,request_date,remarks) VALUES(%s,%s,%s,%s,CURDATE(),%s)",(request.form.get("book_id"),request.form.get("from_branch"),request.form.get("to_branch"),session.get("full_name") or session.get("username"),request.form.get("remarks")))
        flash("Inter-library loan request submitted.","success")
    rows=db_query("SELECT * FROM interlibrary_loans ORDER BY loan_id DESC")
    books_rows=db_query("SELECT book_id,title FROM books WHERE archived=0 ORDER BY book_id")
    return render_template("loan_requests.html",rows=rows,books=books_rows)

@app.route("/help-desk", methods=["GET","POST"])
@logged_in()
def help_desk():
    if request.method=="POST":
        db_exec("INSERT INTO helpdesk_tickets(prn_no,subject,category,description) VALUES(%s,%s,%s,%s)",(session.get("prn_no") or request.form.get("prn_no") or session.get("username"),request.form.get("subject"),request.form.get("category"),request.form.get("description")))
        flash("Help-desk ticket submitted.","success")
    if session.get("role") in ("Admin","Librarian","Staff"):
        rows=db_query("SELECT * FROM helpdesk_tickets ORDER BY ticket_id DESC")
    else:
        rows=db_query("SELECT * FROM helpdesk_tickets WHERE prn_no=%s ORDER BY ticket_id DESC",(session.get("prn_no") or session.get("username"),))
    return render_template("help_desk.html",rows=rows)

@app.route("/help-desk/<int:ticket_id>", methods=["POST"])
@logged_in("Admin","Librarian","Staff")
def help_desk_update(ticket_id):
    status=request.form.get("status","In Progress")
    db_exec("UPDATE helpdesk_tickets SET status=%s,assigned_to=%s,response=%s,resolved_at=IF(%s='Resolved',NOW(),resolved_at) WHERE ticket_id=%s",(status,session.get("full_name"),request.form.get("response"),status,ticket_id))
    flash("Ticket updated.","success")
    return redirect(url_for("help_desk"))

@app.route("/book-requests", methods=["GET","POST"])
@logged_in()
def book_requests():
    if request.method=="POST":
        db_exec("INSERT INTO book_requests(prn_no,title,author,reason) VALUES(%s,%s,%s,%s)",(session.get("prn_no") or session.get("username"),request.form.get("title"),request.form.get("author"),request.form.get("reason")))
        flash("Book request submitted.","success")
    rows=db_query("SELECT * FROM book_requests ORDER BY votes DESC,request_id DESC")
    return render_template("book_requests.html",rows=rows)

@app.route("/book-request/<int:request_id>/vote", methods=["POST"])
@logged_in()
def vote_book_request(request_id):
    db_exec("UPDATE book_requests SET votes=votes+1 WHERE request_id=%s",(request_id,))
    flash("Vote recorded.","success")
    return redirect(url_for("book_requests"))

@app.route("/fine-disputes", methods=["GET","POST"])
@logged_in()
def fine_disputes():
    if request.method=="POST":
        tx=request.form.get("transaction_id"); row=db_query("SELECT prn_no,late_return_fine FROM transactions WHERE transaction_id=%s",(tx,))
        if row:
            db_exec("INSERT INTO fine_disputes(transaction_id,prn_no,amount,reason) VALUES(%s,%s,%s,%s)",(tx,row[0]["prn_no"],row[0]["late_return_fine"] or 0,request.form.get("reason")))
            flash("Fine dispute submitted.","success")
    if session.get("role") in ("Admin","Librarian","Staff"):
        rows=db_query("SELECT * FROM fine_disputes ORDER BY dispute_id DESC")
    else:
        rows=db_query("SELECT * FROM fine_disputes WHERE prn_no=%s ORDER BY dispute_id DESC",(session.get("prn_no") or session.get("username"),))
    txs=db_query("SELECT transaction_id,book_title,late_return_fine FROM transactions WHERE late_return_fine>0 ORDER BY transaction_id DESC LIMIT 50")
    return render_template("fine_disputes.html",rows=rows,transactions=txs)

@app.route("/fine-disputes/<int:dispute_id>", methods=["POST"])
@logged_in("Admin","Librarian")
def fine_dispute_review(dispute_id):
    status=request.form.get("status","Approved")
    if status not in ("Approved","Rejected"): status="Pending"
    db_exec("UPDATE fine_disputes SET status=%s,reviewed_by=%s,review_note=%s WHERE dispute_id=%s",(status,session.get("full_name"),request.form.get("review_note"),dispute_id))
    flash("Fine dispute reviewed.","success")
    return redirect(url_for("fine_disputes"))

@app.route("/events", methods=["GET","POST"])
@logged_in()
def events():
    if request.method=="POST" and session.get("role") in ("Admin","Librarian","Staff"):
        db_exec("INSERT INTO library_events(title,event_date,start_time,end_time,venue,description,seats,created_by) VALUES(%s,%s,%s,%s,%s,%s,%s,%s)",(request.form.get("title"),request.form.get("event_date"),request.form.get("start_time"),request.form.get("end_time"),request.form.get("venue"),request.form.get("description"),request.form.get("seats") or 50,session.get("full_name")))
        flash("Event created.","success")
    rows=db_query("SELECT e.*,COUNT(er.registration_id) registered FROM library_events e LEFT JOIN event_registrations er ON er.event_id=e.event_id GROUP BY e.event_id ORDER BY e.event_date,e.start_time")
    return render_template("events.html",rows=rows,can_post=session.get("role") in ("Admin","Librarian","Staff"))

@app.route("/events/<int:event_id>/register", methods=["POST"])
@logged_in()
def event_register(event_id):
    prn=session.get("prn_no") or session.get("username")
    try:
        db_exec("INSERT INTO event_registrations(event_id,prn_no) VALUES(%s,%s)",(event_id,prn))
        flash("Event registration successful.","success")
    except Exception:
        flash("Already registered or registration unavailable.","error")
    return redirect(url_for("events"))

@app.route("/book-clubs", methods=["GET","POST"])
@logged_in()
def book_clubs():
    if request.method=="POST" and session.get("role") in ("Admin","Librarian","Staff"):
        db_exec("INSERT INTO book_clubs(club_name,current_book_id,meeting_day,description,created_by) VALUES(%s,%s,%s,%s,%s)",(request.form.get("club_name"),request.form.get("current_book_id") or None,request.form.get("meeting_day"),request.form.get("description"),session.get("full_name")))
        flash("Book club created.","success")
    rows=db_query("SELECT bc.*,b.title current_title,(SELECT COUNT(*) FROM club_members cm WHERE cm.club_id=bc.club_id) member_count FROM book_clubs bc LEFT JOIN books b ON b.book_id=bc.current_book_id ORDER BY club_id DESC")
    books_rows=db_query("SELECT book_id,title FROM books WHERE archived=0 ORDER BY title")
    return render_template("book_clubs.html",rows=rows,books=books_rows,can_post=session.get("role") in ("Admin","Librarian","Staff"))

@app.route("/book-clubs/<int:club_id>/join", methods=["POST"])
@logged_in()
def join_club(club_id):
    prn=session.get("prn_no") or session.get("username")
    try:
        db_exec("INSERT INTO club_members(club_id,prn_no) VALUES(%s,%s)",(club_id,prn)); flash("Joined book club.","success")
    except Exception:
        flash("Already a member.","error")
    return redirect(url_for("book_clubs"))

@app.route("/reading-plan", methods=["GET","POST"])
@logged_in()
def reading_plan():
    prn=session.get("prn_no") or session.get("username"); now=datetime.now()
    if request.method=="POST":
        db_exec("INSERT INTO reading_plans(prn_no,month_name,year_no,target_books,completed_books) VALUES(%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE target_books=VALUES(target_books)",(prn,request.form.get("month_name") or now.strftime("%B"),request.form.get("year_no") or now.year,request.form.get("target_books") or 5,request.form.get("completed_books") or 0))
        flash("Reading plan saved.","success")
    plans=db_query("SELECT * FROM reading_plans WHERE prn_no=%s ORDER BY year_no DESC,plan_id DESC",(prn,))
    returned=db_query("SELECT COUNT(*) cnt FROM transactions WHERE prn_no=%s AND status='Returned'",(prn,))[0]["cnt"]
    return render_template("reading_plan.html",plans=plans,returned=returned,month=datetime.now().strftime("%B"),year=datetime.now().year)

@app.route("/similar/<book_id>")
@logged_in()
def similar_books(book_id):
    base=db_query("SELECT category,author,title FROM books WHERE book_id=%s",(book_id,))
    rows=[]
    if base:
        category=base[0]["category"]; author=base[0]["author"]
        rows=db_query("SELECT * FROM books WHERE archived=0 AND book_id<>%s AND (category=%s OR author=%s) ORDER BY CASE WHEN category=%s THEN 0 ELSE 1 END,title LIMIT 12",(book_id,category,author,category))
    return render_template("similar.html",base=base[0] if base else None,rows=rows)

@app.route("/data-quality")
@logged_in("Admin","Librarian","Staff")
def data_quality():
    checks=[
        ("Books missing ISBN", "SELECT COUNT(*) n FROM books WHERE archived=0 AND (isbn IS NULL OR isbn='')"),
        ("Books missing rack", "SELECT COUNT(*) n FROM books WHERE archived=0 AND (rack IS NULL OR rack='')"),
        ("Members missing mobile", "SELECT COUNT(*) n FROM members WHERE mobile IS NULL OR mobile=''"),
        ("Members missing email", "SELECT COUNT(*) n FROM members WHERE email IS NULL OR email=''"),
        ("Books with zero available copies", "SELECT COUNT(*) n FROM books WHERE archived=0 AND quantity_available=0"),
    ]
    rows=[{"label":label,"n":db_query(sql)[0]["n"]} for label,sql in checks]
    return render_template("data_quality.html",rows=rows)

@app.route("/heatmap")
@logged_in("Admin","Librarian","Staff")
def heatmap():
    rows=db_query("SELECT HOUR(activity_time) hour,COUNT(*) cnt FROM activity_log GROUP BY HOUR(activity_time) ORDER BY hour")
    return render_template("heatmap.html",rows=rows)

@app.route("/security")
@logged_in("Admin")
def security():
    rows=db_query("SELECT * FROM login_audit ORDER BY login_id DESC LIMIT 100")
    return render_template("security.html",rows=rows)

@app.route("/certificate/<prn_no>")
@logged_in()
def certificate(prn_no):
    member=db_query("SELECT * FROM members WHERE prn_no=%s",(prn_no,))
    count=db_query("SELECT COUNT(*) cnt FROM transactions WHERE prn_no=%s AND status='Returned'",(prn_no,))[0]["cnt"]
    return render_template("certificate.html",member=member[0] if member else None,count=count)

@app.route("/assistant", methods=["GET","POST"])
@logged_in()
def assistant():
    q=request.form.get("question","").strip()
    answer=[]
    if q:
        low=q.lower()
        if "available" in low or "book" in low:
            term=q.replace("available","").replace("books","").strip()
            rows=db_query("SELECT book_id,title,author FROM books WHERE archived=0 AND quantity_available>0 AND (title LIKE %s OR author LIKE %s OR category LIKE %s) LIMIT 10",(f"%{term}%",f"%{term}%",f"%{term}%"))
            answer=[f"{r['book_id']} — {r['title']} — {r['author']}" for r in rows] or ["No matching available books found."]
        elif "overdue" in low:
            rows=db_query("SELECT transaction_id,prn_no,book_title,date_due FROM transactions WHERE status='Issued' AND date_due<CURDATE() ORDER BY date_due")
            answer=[f"Txn {r['transaction_id']}: {r['book_title']} — {r['prn_no']} — due {r['date_due']}" for r in rows] or ["No overdue books right now."]
        elif "fine" in low:
            total=db_query("SELECT COALESCE(SUM(late_return_fine),0) n FROM transactions")[0]["n"]
            answer=[f"Total recorded fine: ₹{float(total or 0):.0f}"]
        elif "member" in low:
            n=db_query("SELECT COUNT(*) n FROM members")[0]["n"]; answer=[f"Total registered members: {n}"]
        else:
            answer=["Try asking: available Python books, overdue books, total fine, or total members."]
    return render_template("assistant.html",question=q,answer=answer)

@app.route("/install-info")
@logged_in()
def install_info():
    return render_template("install_info.html")

@app.route("/activity")
@logged_in()
def activity():
    rows = db_query("SELECT * FROM activity_log ORDER BY activity_id DESC LIMIT 200")
    return render_template("activity.html", rows=rows)


@app.route("/reports")
@logged_in("Admin","Librarian","Staff","Faculty")
def reports():
    counts = {
        "books": db_query("SELECT COUNT(*) n FROM books WHERE archived=0")[0]["n"],
        "members": db_query("SELECT COUNT(*) n FROM members")[0]["n"],
        "issued": db_query("SELECT COUNT(*) n FROM transactions WHERE status='Issued'")[0]["n"],
        "returned": db_query("SELECT COUNT(*) n FROM transactions WHERE status='Returned'")[0]["n"],
        "fine": db_query("SELECT COALESCE(SUM(late_return_fine),0) n FROM transactions")[0]["n"],
        "purchases": db_query("SELECT COALESCE(SUM(total_cost),0) n FROM purchases")[0]["n"],
    }
    return render_template("reports.html", counts=counts)


@app.route("/scan")
@logged_in()
def scan():
    return render_template("scan.html")


@app.route("/intelligence")
@logged_in()
def intelligence():
    popular=db_query("SELECT book_id,book_title,COUNT(*) cnt FROM transactions GROUP BY book_id,book_title ORDER BY cnt DESC LIMIT 10")
    top_readers=db_query("SELECT prn_no,COUNT(*) cnt FROM transactions WHERE status='Returned' GROUP BY prn_no ORDER BY cnt DESC LIMIT 10")
    demand_rows=db_query("SELECT category,COUNT(*) cnt FROM books WHERE archived=0 GROUP BY category ORDER BY cnt DESC LIMIT 10")
    return render_template("intelligence.html",popular=popular,top_readers=top_readers,categories=demand_rows)


@app.route("/announcements", methods=["GET","POST"])
@logged_in()
def announcements():
    if request.method == "POST" and session.get("role") in ("Admin","Librarian","Staff"):
        db_exec("INSERT INTO announcements(title,message,priority,created_by) VALUES(%s,%s,%s,%s)", (request.form.get("title"),request.form.get("message"),request.form.get("priority"),session.get("full_name")))
        flash("Announcement published.","success")
    rows=db_query("SELECT * FROM announcements ORDER BY announcement_id DESC")
    return render_template("announcements.html",rows=rows,can_post=session.get("role") in ("Admin","Librarian","Staff"))


@app.route("/digital-library")
@logged_in()
def digital_library():
    return render_template("digital_library.html", resources=db_query("SELECT * FROM digital_resources ORDER BY resource_id DESC"))


@app.route("/rack-finder")
@logged_in()
def rack_finder():
    q=request.args.get("q","")
    rows=db_query("SELECT book_id,title,author,category,rack,shelf,quantity_available,status FROM books WHERE archived=0 AND (book_id LIKE %s OR title LIKE %s OR author LIKE %s) ORDER BY title", (f"%{q}%",f"%{q}%",f"%{q}%"))
    return render_template("rack_finder.html",rows=rows,q=q)


@app.route("/library-data")
@logged_in("Admin","Librarian","Staff")
def library_data():
    rows=db_query("""SELECT b.book_id,b.title,b.author,b.category,b.price,b.quantity_total,b.quantity_available,b.rack,b.shelf,b.status,
                    t.prn_no,t.date_borrowed,t.date_due,t.return_date,t.late_return_fine,t.condition_on_return
                    FROM books b LEFT JOIN (SELECT * FROM transactions WHERE transaction_id IN (SELECT MAX(transaction_id) FROM transactions GROUP BY book_id)) t
                    ON b.book_id=t.book_id WHERE b.archived=0 ORDER BY b.book_id""")
    return render_template("library_data.html",rows=rows)


@app.route("/member-card/<prn_no>")
@logged_in()
def member_card(prn_no):
    row=db_query("SELECT * FROM members WHERE prn_no=%s",(prn_no,))
    return render_template("member_card.html",member=row[0] if row else None)


@app.route("/member-profile/<prn_no>")
@logged_in()
def member_profile(prn_no):
    member=db_query("SELECT * FROM members WHERE prn_no=%s",(prn_no,))
    history=db_query("SELECT * FROM transactions WHERE prn_no=%s ORDER BY transaction_id DESC",(prn_no,))
    return render_template("member_profile.html",member=member[0] if member else None,history=history)


@app.route("/e-library/<book_id>/file")
@logged_in()
def elibrary_file(book_id):
    return "PDF viewer placeholder: upload a PDF file in your preferred media storage and link it through Digital Resources.", 200


@app.errorhandler(Exception)
def handle_error(exc):
    if app.debug:
        raise exc
    return render_template("error.html", error=str(exc)), 500


try:
    setup_database()
    print("College Library portal database setup complete.")
except Exception as startup_error:
    print("DATABASE SETUP ERROR:", startup_error)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
