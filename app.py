from flask import Flask,render_template,request,redirect,url_for,session,flash
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

app=Flask(__name__)
app.secret_key="byapon-secret-2026"
DB="byapon.db"

def db():
 c=sqlite3.connect(DB)
 c.row_factory=sqlite3.Row
 return c

def init_db():
    con = db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL
    );
    """)
    con.execute(
        "INSERT OR IGNORE INTO users(username,password,role) VALUES(?,?,?)",
        ("admin","admin123","admin")
    )
    con.commit()
    con.close()

def _admin_ok():
    return session.get("role") == "admin"


def admin_required():
 return session.get("role")=="admin"


@app.route("/admin/change-password", methods=["GET","POST"])
def admin_change_password():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not new or len(new) < 6:
            flash("New password must be at least 6 characters.", "danger")
            return render_template("admin_change_password.html")

        if new != confirm:
            flash("New passwords do not match.", "danger")
            return render_template("admin_change_password.html")

        con = db()
        user = con.execute(
            "SELECT * FROM users WHERE id=? AND role='admin'",
            (session.get("user_id"),)
        ).fetchone()

        valid = False
        if user:
            try:
                valid = check_password_hash(user["password"], current)
            except Exception:
                valid = (user["password"] == current)

        if not valid:
            con.close()
            flash("Current password is incorrect.", "danger")
            return render_template("admin_change_password.html")

        con.execute(
            "UPDATE users SET password=? WHERE id=? AND role='admin'",
            (generate_password_hash(new), session.get("user_id"))
        )
        con.commit()
        con.close()

        flash("Admin password changed successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("admin_change_password.html")


@app.route("/")
def home():
 return render_template("home.html")

@app.route("/login",methods=["GET","POST"])
def login():
    role=request.args.get("role") or request.form.get("role") or "admin"

    if request.method=="POST":
        username=request.form.get("username","").strip()
        password=request.form.get("password","")
        con=db()
        user=None

        if role=="admin":
            user=con.execute(
                "SELECT * FROM users WHERE username=? AND role='admin'",
                (username,)
            ).fetchone()

            if user:
                try:
                    if not check_password_hash(user["password"],password):
                        user=None
                except Exception:
                    if user["password"] != password:
                        user=None

        elif role=="teacher":
            # First: normal teacher_id login
            user=con.execute(
                "SELECT id,teacher_id AS username,password FROM teachers "
                "WHERE teacher_id=? AND active=1",
                (username,)
            ).fetchone()

            # Second: allow teacher account from users table
            if not user:
                u=con.execute(
                    "SELECT * FROM users WHERE username=? AND role='teacher'",
                    (username,)
                ).fetchone()

                if u:
                    teacher=con.execute(
                        "SELECT id,teacher_id,password FROM teachers "
                        "WHERE id=? AND active=1",
                        (u["id"],)
                    ).fetchone()

                    if teacher:
                        user=teacher

            # Third: numeric teacher database ID
            if not user and username.isdigit():
                user=con.execute(
                    "SELECT id,teacher_id AS username,password FROM teachers "
                    "WHERE id=? AND active=1",
                    (int(username),)
                ).fetchone()

            if user:
                try:
                    if not check_password_hash(user["password"],password):
                        user=None
                except Exception:
                    if user["password"] != password:
                        user=None

        elif role=="student":
            user=con.execute(
                "SELECT id,student_id AS username,password FROM students "
                "WHERE student_id=? AND active=1",
                (username,)
            ).fetchone()

            if user:
                try:
                    if not check_password_hash(user["password"],password):
                        user=None
                except Exception:
                    if user["password"] != password:
                        user=None

        con.close()

        if user:
            session["user_id"]=user["id"]
            session["username"]=user["username"]
            session["role"]=role
            return redirect(url_for("dashboard"))

        flash("Invalid ID or password.","danger")

    return render_template("login.html",role=role)

@app.route("/dashboard")
def dashboard():
 if not session.get("role"):
  return redirect(url_for("home"))
 if session["role"]=="admin":
  return render_template("admin_dashboard.html")
 if session["role"]=="teacher":
  return teacher_panel()
 return render_template("student_dashboard.html")

@app.route("/logout")
def logout():
 session.clear()
 return redirect(url_for("home"))

@app.route("/students", methods=["GET","POST"])
def students():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    if request.method == "POST":
        try:
            con.execute("""
                INSERT INTO students
                (student_id,name,phone,class_name,batch,guardian,password)
                VALUES (?,?,?,?,?,?,?)
            """, (
                request.form["student_id"].strip(),
                request.form["name"].strip(),
                request.form.get("phone","").strip(),
                request.form.get("class_name","").strip(),
                request.form.get("batch","").strip(),
                request.form.get("guardian","").strip(),
                request.form["password"]
            ))
            con.commit()
            flash("Student added successfully.","success")
        except sqlite3.IntegrityError:
            con.rollback()
            flash("Student ID already exists.","danger")

        con.close()
        return redirect(url_for("students"))

    rows = con.execute(
        "SELECT * FROM students ORDER BY id DESC"
    ).fetchall()

    con.close()
    return render_template("students.html", students=rows)


@app.route("/students/<int:sid>/delete", methods=["POST"])
def delete_student(sid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()
    con.execute("DELETE FROM students WHERE id=?", (sid,))
    con.commit()
    con.close()

    flash("Student deleted successfully.","success")
    return redirect(url_for("students"))


@app.route("/students/<int:sid>/edit", methods=["GET","POST"])
def edit_student(sid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()
    student = con.execute(
        "SELECT * FROM students WHERE id=?", (sid,)
    ).fetchone()

    if not student:
        con.close()
        flash("Student not found.","danger")
        return redirect(url_for("students"))

    if request.method == "POST":
        try:
            con.execute("""
                UPDATE students SET
                student_id=?,
                name=?,
                phone=?,
                class_name=?,
                batch=?,
                guardian=?,
                password=?,
                active=?
                WHERE id=?
            """, (
                request.form["student_id"].strip(),
                request.form["name"].strip(),
                request.form.get("phone","").strip(),
                request.form.get("class_name","").strip(),
                request.form.get("batch","").strip(),
                request.form.get("guardian","").strip(),
                request.form["password"],
                int(request.form.get("active",1)),
                sid
            ))

            con.commit()
            flash("Student updated successfully.","success")

        except sqlite3.IntegrityError:
            con.rollback()
            flash("Student ID already exists.","danger")

        con.close()
        return redirect(url_for("students"))

    con.close()
    return render_template("edit_student.html", student=student)


@app.route("/teachers", methods=["GET","POST"])
def teachers():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    if request.method == "POST":
        try:
            con.execute("""
                INSERT INTO teachers
                (teacher_id,name,phone,subject,qualification,salary,password)
                VALUES (?,?,?,?,?,?,?)
            """, (
                request.form["teacher_id"].strip(),
                request.form["name"].strip(),
                request.form.get("phone","").strip(),
                request.form.get("subject","").strip(),
                request.form.get("qualification","").strip(),
                float(request.form.get("salary") or 0),
                request.form["password"]
            ))
            con.commit()
            flash("Teacher added successfully.","success")

        except sqlite3.IntegrityError:
            con.rollback()
            flash("Teacher ID already exists.","danger")

        except (ValueError,TypeError):
            con.rollback()
            flash("Invalid teacher information.","danger")

        con.close()
        return redirect(url_for("teachers"))

    rows = con.execute(
        "SELECT * FROM teachers ORDER BY id DESC"
    ).fetchall()

    con.close()

    return render_template("teachers.html", teachers=rows)


@app.route("/teachers/<int:tid>/edit", methods=["GET","POST"])
def edit_teacher(tid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    teacher = con.execute(
        "SELECT * FROM teachers WHERE id=?",
        (tid,)
    ).fetchone()

    if not teacher:
        con.close()
        flash("Teacher not found.","danger")
        return redirect(url_for("teachers"))

    if request.method == "POST":
        try:
            con.execute("""
                UPDATE teachers SET
                teacher_id=?,
                name=?,
                phone=?,
                subject=?,
                qualification=?,
                salary=?,
                password=?,
                active=?
                WHERE id=?
            """, (
                request.form["teacher_id"].strip(),
                request.form["name"].strip(),
                request.form.get("phone","").strip(),
                request.form.get("subject","").strip(),
                request.form.get("qualification","").strip(),
                float(request.form.get("salary") or 0),
                request.form["password"],
                int(request.form.get("active",1)),
                tid
            ))

            con.commit()
            flash("Teacher updated successfully.","success")

        except sqlite3.IntegrityError:
            con.rollback()
            flash("Teacher ID already exists.","danger")

        except (ValueError,TypeError):
            con.rollback()
            flash("Invalid teacher information.","danger")

        con.close()
        return redirect(url_for("teachers"))

    con.close()

    return render_template(
        "edit_teacher.html",
        teacher=teacher
    )


@app.route("/teachers/<int:tid>/delete", methods=["POST"])
def delete_teacher(tid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()
    con.execute("DELETE FROM teachers WHERE id=?", (tid,))
    con.commit()
    con.close()

    flash("Teacher deleted successfully.","success")
    return redirect(url_for("teachers"))


@app.route("/teachers/<int:tid>/reset-password", methods=["POST"])
def reset_teacher_password(tid):

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    new_password=request.form.get("new_password","").strip()

    if len(new_password) < 4:
        flash("Password must contain at least 4 characters.","danger")
        return redirect(url_for("teachers"))

    con=db()

    teacher=con.execute(
        "SELECT id FROM teachers WHERE id=?",
        (tid,)
    ).fetchone()

    if not teacher:
        con.close()
        flash("Teacher not found.","danger")
        return redirect(url_for("teachers"))

    con.execute(
        "UPDATE teachers SET password=? WHERE id=?",
        (generate_password_hash(new_password),tid)
    )

    con.commit()
    con.close()

    flash("Teacher password changed successfully.","success")
    return redirect(url_for("teachers"))


@app.route("/attendance", methods=["GET","POST"])
def attendance():
    if session.get("role") not in ("admin", "teacher"):
        return redirect(url_for("dashboard"))

    con = db()
    selected_date = request.values.get(
        "date"
    ) or __import__("datetime").date.today().isoformat()

    if request.method == "POST":
        for key,value in request.form.items():
            if key.startswith("status_"):
                sid = int(key.split("_")[1])

                con.execute("""
                    INSERT INTO attendance
                    (student_id,attendance_date,status)
                    VALUES (?,?,?)
                    ON CONFLICT(student_id,attendance_date)
                    DO UPDATE SET status=excluded.status
                """,(sid,selected_date,value))

        con.commit()
        flash("Attendance saved successfully.","success")

    students = con.execute("""
        SELECT s.*,
               a.id AS attendance_id,
               COALESCE(a.status,'Absent') AS attendance_status
        FROM students s
        LEFT JOIN attendance a
        ON a.student_id=s.id
        AND a.attendance_date=?
        WHERE s.active=1
        ORDER BY s.class_name,s.batch,s.name
    """,(selected_date,)).fetchall()

    con.close()

    return render_template(
        "attendance.html",
        students=students,
        selected_date=selected_date
    )


@app.route("/student/attendance")
def student_attendance():
    if session.get("role") != "student":
        return redirect(url_for("dashboard"))

    sid = session["user_id"]

    con = db()

    student = con.execute(
        "SELECT * FROM students WHERE id=?",
        (sid,)
    ).fetchone()

    records = con.execute("""
        SELECT attendance_date,status
        FROM attendance
        WHERE student_id=?
        ORDER BY attendance_date DESC
    """,(sid,)).fetchall()

    con.close()

    return render_template(
        "student_attendance.html",
        student=student,
        records=records
    )



@app.route("/teacher/attendance/print")
def teacher_attendance_print():
    if session.get("role") != "teacher":
        return redirect(url_for("dashboard"))

    selected_date = request.args.get("date") or __import__("datetime").date.today().isoformat()

    con = db()

    teacher = con.execute(
        "SELECT * FROM teachers WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    records = con.execute("""
        SELECT
            s.student_id,
            s.name,
            s.class_name,
            s.batch,
            COALESCE(a.status,'Absent') AS attendance_status
        FROM students s
        LEFT JOIN attendance a
            ON a.student_id=s.id
            AND a.attendance_date=?
        WHERE s.active=1
        ORDER BY s.class_name,s.batch,s.name
    """,(selected_date,)).fetchall()

    con.close()

    return render_template(
        "teacher_attendance_print.html",
        teacher=teacher,
        records=records,
        selected_date=selected_date
    )

@app.route("/student/attendance/print")
def student_attendance_print():
    if session.get("role") != "student":
        return redirect(url_for("dashboard"))

    sid = session["user_id"]

    con = db()

    student = con.execute(
        "SELECT * FROM students WHERE id=?",
        (sid,)
    ).fetchone()

    records = con.execute("""
        SELECT attendance_date,status
        FROM attendance
        WHERE student_id=?
        ORDER BY attendance_date
    """,(sid,)).fetchall()

    con.close()

    return render_template(
        "student_attendance_print.html",
        student=student,
        records=records
    )



@app.route("/attendance/<int:aid>/delete", methods=["POST"])
def delete_attendance(aid):
    if session.get("role") not in ("admin", "teacher"):
        return redirect(url_for("dashboard"))

    con = db()
    try:
        row = con.execute(
            "SELECT id FROM attendance WHERE id=?",
            (aid,)
        ).fetchone()

        if not row:
            flash("Attendance record not found.", "danger")
            return redirect(url_for("attendance"))

        con.execute("DELETE FROM attendance WHERE id=?", (aid,))
        con.commit()
        flash("Attendance deleted successfully.", "success")

    except Exception as e:
        con.rollback()
        flash("Could not delete attendance record.", "danger")
        print("ATTENDANCE DELETE ERROR:", e)

    finally:
        con.close()

    return redirect(url_for("attendance"))

@app.route("/exams", methods=["GET","POST"])
def exams():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    if request.method == "POST":
        title = request.form.get("title","").strip()
        subject = request.form.get("subject","").strip()
        exam_date = request.form.get("exam_date","")
        full_marks = float(request.form.get("full_marks") or 0)

        con.execute("""
            INSERT INTO exams(title,subject,exam_date,full_marks)
            VALUES(?,?,?,?)
        """,(title,subject,exam_date,full_marks))

        con.commit()
        flash("Exam created successfully.","success")

    exams_list = con.execute(
        "SELECT * FROM exams ORDER BY exam_date DESC,id DESC"
    ).fetchall()

    con.close()

    return render_template(
        "exams.html",
        exams=exams_list
    )


@app.route("/exams/<int:eid>/marks", methods=["GET","POST"])
def exam_marks(eid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    exam = con.execute(
        "SELECT * FROM exams WHERE id=?",
        (eid,)
    ).fetchone()

    if not exam:
        con.close()
        flash("Exam not found.","danger")
        return redirect(url_for("exams"))

    if request.method == "POST":

        for key,value in request.form.items():

            if key.startswith("mark_"):

                sid = int(key.split("_")[1])

                try:
                    mark = float(value or 0)
                except ValueError:
                    mark = 0

                existing = con.execute("""
                    SELECT id FROM marks
                    WHERE exam_id=? AND student_id=?
                """,(eid,sid)).fetchone()

                if existing:

                    con.execute("""
                        UPDATE marks
                        SET mark=?
                        WHERE exam_id=? AND student_id=?
                    """,(mark,eid,sid))

                else:

                    con.execute("""
                        INSERT INTO marks(exam_id,student_id,mark)
                        VALUES(?,?,?)
                    """,(eid,sid,mark))

        con.commit()
        flash("Marks saved successfully.","success")

    students = con.execute("""
        SELECT s.id,
               s.student_id,
               s.name,
               s.class_name,
               s.batch,
               COALESCE(m.mark,0) AS mark
        FROM students s
        LEFT JOIN marks m
        ON m.student_id=s.id
        AND m.exam_id=?
        WHERE s.active=1
        ORDER BY s.class_name,s.batch,s.name
    """,(eid,)).fetchall()

    con.close()

    return render_template(
        "exam_marks.html",
        exam=exam,
        students=students
    )


@app.route("/student/marksheet")
def student_marksheet():

    if session.get("role") != "student":
        return redirect(url_for("dashboard"))

    sid = session["user_id"]

    con = db()

    student = con.execute(
        "SELECT * FROM students WHERE id=?",
        (sid,)
    ).fetchone()

    marks = con.execute("""
        SELECT e.title,
               e.subject,
               e.exam_date,
               e.full_marks,
               m.mark
        FROM marks m
        JOIN exams e ON e.id=m.exam_id
        WHERE m.student_id=?
        ORDER BY e.exam_date DESC,e.id DESC
    """,(sid,)).fetchall()

    con.close()

    return render_template(
        "student_marksheet.html",
        student=student,
        marks=marks
    )


@app.route("/student/marksheet/print")
def student_marksheet_print():

    if session.get("role") != "student":
        return redirect(url_for("dashboard"))

    sid = session["user_id"]

    con = db()

    student = con.execute(
        "SELECT * FROM students WHERE id=?",
        (sid,)
    ).fetchone()

    marks = con.execute("""
        SELECT e.title,
               e.subject,
               e.exam_date,
               e.full_marks,
               m.mark
        FROM marks m
        JOIN exams e ON e.id=m.exam_id
        WHERE m.student_id=?
        ORDER BY e.exam_date
    """,(sid,)).fetchall()

    con.close()

    return render_template(
        "student_marksheet_print.html",
        student=student,
        marks=marks
    )


@app.route("/finance", methods=["GET","POST"])
def finance():

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    if request.method == "POST":

        try:
            con.execute("""
                INSERT INTO transactions
                (tx_date,tx_type,category,amount,note)
                VALUES (?,?,?,?,?)
            """,(
                request.form["tx_date"],
                request.form["tx_type"],
                request.form["category"],
                float(request.form["amount"]),
                request.form.get("note","")
            ))

            con.commit()
            flash("Transaction added successfully.","success")

        except (ValueError,TypeError):

            con.rollback()
            flash("Invalid transaction information.","danger")

    transactions = con.execute("""
        SELECT *
        FROM transactions
        ORDER BY tx_date DESC,id DESC
    """).fetchall()

    income = con.execute("""
        SELECT COALESCE(SUM(amount),0) AS total
        FROM transactions
        WHERE tx_type='Income'
    """).fetchone()["total"]

    expense = con.execute("""
        SELECT COALESCE(SUM(amount),0) AS total
        FROM transactions
        WHERE tx_type='Expense'
    """).fetchone()["total"]

    con.close()

    return render_template(
        "finance.html",
        transactions=transactions,
        income=income,
        expense=expense
    )


@app.route("/finance/<int:tid>/edit",methods=["GET","POST"])
def edit_transaction(tid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    con=db()
    transaction=con.execute("SELECT * FROM transactions WHERE id=?",(tid,)).fetchone()
    if not transaction:
        con.close()
        flash("Transaction not found.","danger")
        return redirect(url_for("finance"))
    if request.method=="POST":
        try:
            con.execute("""UPDATE transactions SET tx_date=?,tx_type=?,category=?,amount=?,note=? WHERE id=?""",
            (request.form["tx_date"],request.form["tx_type"],request.form["category"],
             float(request.form["amount"]),request.form.get("note",""),tid))
            con.commit()
            con.close()
            flash("Finance record updated successfully.","success")
            return redirect(url_for("finance"))
        except (ValueError,TypeError):
            con.rollback()
            flash("Invalid information.","danger")
    con.close()
    return render_template("edit_transaction.html",transaction=transaction)

@app.post("/finance/<int:tid>/delete")
def delete_transaction(tid):

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    con.execute(
        "DELETE FROM transactions WHERE id=?",
        (tid,)
    )

    con.commit()
    con.close()

    flash("Transaction deleted.","success")

    return redirect(url_for("finance"))


@app.route("/fees/<int:fid>/edit",methods=["GET","POST"])
def edit_fee(fid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    con=db()
    fee=con.execute("SELECT * FROM fees WHERE id=?",(fid,)).fetchone()
    if not fee:
        con.close()
        flash("Fee record not found.","danger")
        return redirect(url_for("fees"))
    students=con.execute("SELECT id,student_id,name FROM students WHERE active=1 ORDER BY name").fetchall()
    if request.method=="POST":
        amount=float(request.form.get("amount") or 0)
        paid=float(request.form.get("paid_amount") or 0)
        status="Paid" if paid>=amount else ("Partial" if paid>0 else "Unpaid")
        con.execute("""UPDATE fees SET student_id=?,fee_month=?,amount=?,paid_amount=?,payment_date=?,status=?,note=? WHERE id=?""",
        (int(request.form["student_id"]),request.form["fee_month"],amount,paid,request.form.get("payment_date"),status,request.form.get("note",""),fid))
        con.commit()
        con.close()
        flash("Fee record updated successfully.","success")
        return redirect(url_for("fees"))
    con.close()
    return render_template("edit_fee.html",fee=fee,students=students)

@app.post("/fees/<int:fid>/delete")
def delete_fee_record(fid):

    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    con.execute(
        "DELETE FROM fees WHERE id=?",
        (fid,)
    )

    con.commit()
    con.close()

    flash("Fee record deleted.","success")

    return redirect(url_for("fees"))


@app.route("/student/profile")
def student_profile():

    if session.get("role") != "student":
        return redirect(url_for("dashboard"))

    con = db()

    student = con.execute(
        "SELECT * FROM students WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    con.close()

    if not student:
        flash("Student profile not found.","danger")
        return redirect(url_for("logout"))

    return render_template(
        "student_profile.html",
        student=student
    )


@app.route("/student/fees")
def student_fees():

    if session.get("role") != "student":
        return redirect(url_for("dashboard"))

    con = db()

    student = con.execute(
        "SELECT * FROM students WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    fees = con.execute("""
        SELECT fee_month,
               amount,
               paid_amount,
               payment_date,
               status,
               note
        FROM fees
        WHERE student_id=?
        ORDER BY fee_month DESC
    """,(session["user_id"],)).fetchall()

    con.close()

    return render_template(
        "student_fees.html",
        student=student,
        fees=fees
    )


@app.route("/teacher")
def teacher_panel():
    if session.get("role") != "teacher":
        return redirect(url_for("dashboard"))

    con=db()

    teacher=con.execute(
        "SELECT * FROM teachers WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    assignments=con.execute("""
        SELECT *
        FROM teacher_assignments
        WHERE teacher_id=? AND active=1
        ORDER BY id DESC
    """,(session["user_id"],)).fetchall()

    class_count=con.execute("""
        SELECT COUNT(*)
        FROM teacher_classes
        WHERE teacher_id=?
    """,(session["user_id"],)).fetchone()[0]

    con.close()

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher,
        assignments=assignments,
        class_count=class_count
    )

@app.route("/teacher/classes", methods=["GET","POST"])
def teacher_classes():

    if session.get("role") not in ("teacher", "admin"):
        return redirect(url_for("dashboard"))

    con = db()

    teacher = con.execute(
        "SELECT * FROM teachers WHERE id=?",
        (session["user_id"],)
    ).fetchone()

    if request.method == "POST":

        class_date = request.form.get("class_date","")
        batch = request.form.get("batch","").strip()
        subject = request.form.get("subject","").strip()
        topic = request.form.get("topic","").strip()

        if class_date and batch and subject and topic:

            con.execute("""
                INSERT INTO teacher_classes
                (teacher_id,class_date,batch,subject,topic)
                VALUES (?,?,?,?,?)
            """, (
                session["user_id"],
                class_date,
                batch,
                subject,
                topic
            ))

            con.commit()
            flash("Class record added successfully.","success")

        else:
            flash("Please fill in all fields.","danger")

        con.close()

        return redirect(url_for("teacher_classes"))

    classes = con.execute("""
        SELECT *
        FROM teacher_classes
        WHERE teacher_id=?
        ORDER BY class_date DESC,id DESC
    """,(session["user_id"],)).fetchall()

    con.close()

    return render_template(
        "teacher_classes.html",
        teacher=teacher,
        classes=classes
    )


@app.route("/teacher/classes/<int:cid>/edit", methods=["GET","POST"])
def edit_teacher_class(cid):

    if session.get("role") != "teacher":
        return redirect(url_for("dashboard"))

    con=db()

    class_record=con.execute("""
        SELECT *
        FROM teacher_classes
        WHERE id=? AND teacher_id=?
    """,(cid,session["user_id"])).fetchone()

    if not class_record:
        con.close()
        flash("Class record not found.","danger")
        return redirect(url_for("teacher_classes"))

    if request.method=="POST":

        class_date=request.form.get("class_date","").strip()
        batch=request.form.get("batch","").strip()
        subject=request.form.get("subject","").strip()
        topic=request.form.get("topic","").strip()

        if not all([class_date,batch,subject,topic]):
            con.close()
            flash("Please fill in all fields.","danger")
            return redirect(url_for("edit_teacher_class",cid=cid))

        con.execute("""
            UPDATE teacher_classes
            SET class_date=?,batch=?,subject=?,topic=?
            WHERE id=? AND teacher_id=?
        """,(class_date,batch,subject,topic,cid,session["user_id"]))

        con.commit()
        con.close()

        flash("Class record updated successfully.","success")
        return redirect(url_for("teacher_classes"))

    con.close()

    return render_template(
        "edit_teacher_class.html",
        class_record=class_record
    )


@app.route("/teacher/classes/<int:cid>/delete", methods=["POST"])
def delete_teacher_class(cid):

    if session.get("role") != "teacher":
        return redirect(url_for("dashboard"))

    con = db()

    con.execute("""
        DELETE FROM teacher_classes
        WHERE id=? AND teacher_id=?
    """,(cid,session["user_id"]))

    con.commit()
    con.close()

    flash("Class record deleted.","success")

    return redirect(url_for("teacher_classes"))



# Create teacher class table if it does not already exist
con = db()

con.execute("""
CREATE TABLE IF NOT EXISTS teacher_classes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    class_date TEXT NOT NULL,
    batch TEXT NOT NULL,
    subject TEXT NOT NULL,
    topic TEXT NOT NULL
)
""")

con.commit()
con.close()



# ===== COMPLETE MODULE ROUTES =====

# ===== COMPLETE MODULE ROUTES =====

@app.route("/fees", methods=["GET","POST"])
def fees():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    if request.method == "POST":
        try:
            student_id = int(request.form["student_id"])
            fee_month = request.form["fee_month"].strip()
            amount = float(request.form.get("amount") or 0)
            paid_amount = float(request.form.get("paid_amount") or 0)
            payment_date = request.form.get("payment_date","")
            note = request.form.get("note","").strip()

            if paid_amount >= amount:
                status = "Paid"
            elif paid_amount > 0:
                status = "Partial"
            else:
                status = "Unpaid"

            con.execute("""
                INSERT INTO fees
                (student_id,fee_month,amount,paid_amount,payment_date,status,note)
                VALUES (?,?,?,?,?,?,?)
            """,(
                student_id,fee_month,amount,paid_amount,
                payment_date,status,note
            ))

            con.commit()
            flash("Fee record added successfully.","success")

        except (ValueError,TypeError,sqlite3.IntegrityError):
            con.rollback()
            flash("Invalid fee information.","danger")

        con.close()
        return redirect(url_for("fees"))

    rows = con.execute("""
        SELECT f.*,s.student_id AS student_code,s.name AS student_name
        FROM fees f
        LEFT JOIN students s ON s.id=f.student_id
        ORDER BY f.fee_month DESC,f.id DESC
    """).fetchall()

    students = con.execute("""
        SELECT id,student_id,name
        FROM students
        WHERE active=1
        ORDER BY name
    """).fetchall()

    con.close()

    return render_template(
        "fees.html",
        fees=rows,
        students=students
    )


@app.route("/attendance/<int:aid>/edit", methods=["GET","POST"])
def edit_attendance(aid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con=db()
    record=con.execute("""
        SELECT a.*, s.student_id AS student_code, s.name
        FROM attendance a
        LEFT JOIN students s ON s.id=a.student_id
        WHERE a.id=?
    """,(aid,)).fetchone()

    if not record:
        con.close()
        flash("Attendance record not found.","danger")
        return redirect(url_for("attendance"))

    if request.method=="POST":
        con.execute("""
            UPDATE attendance
            SET attendance_date=?, status=?
            WHERE id=?
        """,(
            request.form.get("attendance_date","").strip(),
            request.form.get("status","Absent").strip(),
            aid
        ))
        con.commit()
        con.close()
        flash("Attendance updated successfully.","success")
        return redirect(url_for("attendance"))

    con.close()
    return render_template("edit_attendance.html", record=record)


@app.route("/exams/<int:eid>/edit", methods=["GET","POST"])
def edit_exam(eid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con=db()
    exam=con.execute(
        "SELECT * FROM exams WHERE id=?",(eid,)
    ).fetchone()

    if not exam:
        con.close()
        flash("Exam not found.","danger")
        return redirect(url_for("exams"))

    if request.method=="POST":
        try:
            title=request.form.get("title","").strip()
            subject=request.form.get("subject","").strip()
            exam_date=request.form.get("exam_date","").strip()
            full_marks=float(request.form.get("full_marks") or 0)

            if not title or not subject or not exam_date or full_marks<=0:
                raise ValueError

            con.execute("""
                UPDATE exams
                SET title=?, subject=?, exam_date=?, full_marks=?
                WHERE id=?
            """,(title,subject,exam_date,full_marks,eid))
            con.commit()
            con.close()

            flash("Exam updated successfully.","success")
            return redirect(url_for("exams"))

        except (ValueError,TypeError):
            con.rollback()
            flash("Invalid exam information.","danger")

    con.close()
    return render_template("edit_exam.html",exam=exam)

@app.route("/exams/<int:eid>/delete", methods=["POST"])
def delete_exam(eid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    con.execute("DELETE FROM marks WHERE exam_id=?",(eid,))
    con.execute("DELETE FROM exams WHERE id=?",(eid,))

    con.commit()
    con.close()

    flash("Exam deleted successfully.","success")
    return redirect(url_for("exams"))


@app.route("/routine", methods=["GET","POST"])
def routine():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    if request.method == "POST":
        try:
            con.execute("""
                INSERT INTO routines
                (day_name,batch,subject,teacher,start_time,end_time)
                VALUES (?,?,?,?,?,?)
            """,(
                request.form.get("day_name","").strip(),
                request.form.get("batch","").strip(),
                request.form.get("subject","").strip(),
                request.form.get("teacher","").strip(),
                request.form.get("start_time",""),
                request.form.get("end_time","")
            ))

            con.commit()
            flash("Routine added successfully.","success")

        except sqlite3.IntegrityError:
            con.rollback()
            flash("Could not add routine.","danger")

        con.close()
        return redirect(url_for("routine"))

    routines = con.execute("""
        SELECT * FROM routines
        ORDER BY
        CASE day_name
            WHEN 'Saturday' THEN 1
            WHEN 'Sunday' THEN 2
            WHEN 'Monday' THEN 3
            WHEN 'Tuesday' THEN 4
            WHEN 'Wednesday' THEN 5
            WHEN 'Thursday' THEN 6
            WHEN 'Friday' THEN 7
            ELSE 8
        END,start_time,id
    """).fetchall()

    con.close()

    return render_template(
        "routine.html",
        routines=routines
    )


@app.route("/routine/<int:rid>/edit", methods=["GET","POST"])
def edit_routine(rid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))
    con=db()
    row=con.execute("SELECT * FROM routines WHERE id=?",(rid,)).fetchone()
    if not row:
        con.close()
        flash("Routine not found.","danger")
        return redirect(url_for("routine"))
    if request.method=="POST":
        con.execute("""UPDATE routines SET day_name=?,batch=?,subject=?,teacher=?,start_time=?,end_time=? WHERE id=?""",
        (request.form.get("day_name",""),request.form.get("batch",""),
         request.form.get("subject",""),request.form.get("teacher",""),
         request.form.get("start_time",""),request.form.get("end_time",""),rid))
        con.commit()
        con.close()
        flash("Routine updated successfully.","success")
        return redirect(url_for("routine"))
    con.close()
    return render_template("edit_routine.html",row=row)

@app.route("/routine/<int:rid>/delete", methods=["POST"])
def delete_routine(rid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()
    con.execute("DELETE FROM routines WHERE id=?",(rid,))
    con.commit()
    con.close()

    flash("Routine deleted successfully.","success")
    return redirect(url_for("routine"))


@app.route("/calendar", methods=["GET","POST"])
def calendar():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    if request.method == "POST":
        try:
            con.execute("""
                INSERT INTO coaching_days(day_date,status,note)
                VALUES(?,?,?)
            """,(
                request.form.get("day_date",""),
                request.form.get("status","Open"),
                request.form.get("note","").strip()
            ))

            con.commit()
            flash("Calendar entry saved successfully.","success")

        except sqlite3.IntegrityError:
            con.rollback()
            flash("Could not save calendar entry.","danger")

        con.close()
        return redirect(url_for("calendar"))

    days = con.execute("""
        SELECT * FROM coaching_days
        ORDER BY day_date DESC,id DESC
    """).fetchall()

    con.close()

    return render_template(
        "calendar.html",
        days=days,
        coaching_days=days
    )


@app.route("/teacher-assignments", methods=["GET","POST"])
def teacher_assignments():
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()

    if request.method == "POST":
        try:
            con.execute("""
                INSERT INTO teacher_assignments
                (teacher_id,batch,subject,active)
                VALUES (?,?,?,1)
            """,(
                int(request.form["teacher_id"]),
                request.form.get("batch","").strip(),
                request.form.get("subject","").strip()
            ))

            con.commit()
            flash("Teacher assignment added successfully.","success")

        except (ValueError,TypeError,sqlite3.IntegrityError):
            con.rollback()
            flash("Invalid teacher assignment.","danger")

        con.close()
        return redirect(url_for("teacher_assignments"))

    assignments = con.execute("""
        SELECT ta.*,
               t.teacher_id,
               t.name AS teacher_name
        FROM teacher_assignments ta
        LEFT JOIN teachers t ON t.id=ta.teacher_id
        ORDER BY ta.id DESC
    """).fetchall()

    teachers = con.execute("""
        SELECT id,teacher_id,name,subject
        FROM teachers
        WHERE active=1
        ORDER BY name
    """).fetchall()

    con.close()

    return render_template(
        "teacher_assignments.html",
        assignments=assignments,
        teachers=teachers
    )


@app.post("/teacher-assignments/<int:aid>/delete")
def delete_teacher_assignment(aid):
    if session.get("role") != "admin":
        return redirect(url_for("dashboard"))

    con = db()
    con.execute(
        "DELETE FROM teacher_assignments WHERE id=?",(aid,)
    )
    con.commit()
    con.close()

    flash("Teacher assignment deleted successfully.","success")
    return redirect(url_for("teacher_assignments"))


if __name__=="__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
# ================================
# MISSING ADMIN ROUTES
# ================================

