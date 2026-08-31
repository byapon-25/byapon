import sqlite3

DB = "byapon.db"

con = sqlite3.connect(DB)

con.executescript("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    class_name TEXT,
    batch TEXT,
    guardian TEXT,
    password TEXT NOT NULL,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    phone TEXT,
    subject TEXT,
    qualification TEXT,
    salary REAL DEFAULT 0,
    password TEXT NOT NULL,
    active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    attendance_date TEXT NOT NULL,
    status TEXT NOT NULL,
    UNIQUE(student_id, attendance_date)
);

CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    subject TEXT NOT NULL,
    exam_date TEXT NOT NULL,
    full_marks REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exam_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    mark REAL DEFAULT 0,
    UNIQUE(exam_id, student_id)
);

CREATE TABLE IF NOT EXISTS fees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    fee_month TEXT NOT NULL,
    amount REAL DEFAULT 0,
    paid_amount REAL DEFAULT 0,
    payment_date TEXT,
    status TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_date TEXT NOT NULL,
    tx_type TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS routines (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_name TEXT,
    batch TEXT,
    subject TEXT,
    teacher TEXT,
    start_time TEXT,
    end_time TEXT
);

CREATE TABLE IF NOT EXISTS teacher_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    batch TEXT NOT NULL,
    subject TEXT NOT NULL,
    active INTEGER DEFAULT 1,
    UNIQUE(teacher_id,batch,subject)
);

CREATE TABLE IF NOT EXISTS coaching_days (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    day_date TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL,
    note TEXT
);

CREATE TABLE IF NOT EXISTS teacher_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    class_date TEXT NOT NULL,
    batch TEXT NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL
);

INSERT OR IGNORE INTO users(username,password,role)
VALUES ('admin','admin123','admin');
""")

con.commit()
con.close()

print("================================")
print("BYAPON DATABASE READY")
print("Admin ID: admin")
print("Admin Password: admin123")
print("================================")
