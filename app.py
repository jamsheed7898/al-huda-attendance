
import os, sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, jsonify

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE_THIS_SECRET_KEY")
DB = os.path.join(os.path.dirname(__file__), "attendance.db")

# CHANGE THESE BEFORE PUBLIC DEPLOYMENT.
MASTER_PIN = os.environ.get("MASTER_PIN", "9999")
CLASS_PINS = {str(i): os.environ.get(f"CLASS_{i}_PIN", f"{1000+i}") for i in range(1,13)}

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c=db()
    c.execute("""CREATE TABLE IF NOT EXISTS students(
        id INTEGER PRIMARY KEY AUTOINCREMENT, class TEXT NOT NULL,
        roll TEXT UNIQUE NOT NULL, name TEXT NOT NULL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS attendance(
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT NOT NULL,
        roll TEXT NOT NULL, status TEXT NOT NULL,
        UNIQUE(date,roll))""")
    c.commit()
    if c.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
        from seed_students import STUDENTS
        c.executemany("INSERT INTO students(class,roll,name) VALUES(?,?,?)", STUDENTS)
        c.commit()
    c.close()

def role_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("role"): return redirect(url_for("home"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def home():
    c=db()
    classes=[r["class"] for r in c.execute("SELECT DISTINCT class FROM students ORDER BY CAST(class AS INTEGER)")]
    c.close()
    return render_template("index.html", classes=classes)

@app.post("/login")
def login():
    pin=request.form.get("pin","").strip()
    if pin == MASTER_PIN:
        session["role"]="admin"; session["class"]=None
        return redirect(url_for("admin"))
    for cl,p in CLASS_PINS.items():
        if pin == p:
            session["role"]="teacher"; session["class"]=cl
            return redirect(url_for("teacher"))
    return redirect(url_for("home", error="Invalid PIN"))

@app.get("/logout")
def logout():
    session.clear(); return redirect(url_for("home"))

@app.get("/parent")
def parent():
    cl=request.args.get("class","")
    roll=request.args.get("roll","")
    c=db()
    students=c.execute("SELECT roll,name,class FROM students WHERE class=? ORDER BY name",(cl,)).fetchall()
    history=[]
    student=None
    if roll:
        student=c.execute("SELECT roll,name,class FROM students WHERE roll=? AND class=?",(roll,cl)).fetchone()
        if student:
            history=c.execute("""SELECT date,status FROM attendance WHERE roll=?
                ORDER BY date DESC""",(roll,)).fetchall()
    c.close()
    return render_template("parent.html", classes=classes_list(), selected_class=cl,
                           students=students, selected_roll=roll, student=student, history=history)

def classes_list():
    c=db(); x=[r["class"] for r in c.execute("SELECT DISTINCT class FROM students ORDER BY CAST(class AS INTEGER)")]; c.close(); return x

@app.get("/teacher")
@role_required
def teacher():
    if session.get("role")!="teacher": return redirect(url_for("admin"))
    cl=session["class"]; date=request.args.get("date","")
    c=db()
    students=c.execute("SELECT roll,name,class FROM students WHERE class=? ORDER BY name",(cl,)).fetchall()
    statuses={r["roll"]:r["status"] for r in c.execute("SELECT roll,status FROM attendance WHERE date=?",(date,))}
    c.close()
    return render_template("teacher.html", class_name=cl, students=students, statuses=statuses, date=date)

@app.post("/teacher/save")
@role_required
def teacher_save():
    if session.get("role")!="teacher": return redirect(url_for("admin"))
    cl=session["class"]; date=request.form["date"]; c=db()
    for s in c.execute("SELECT roll FROM students WHERE class=?",(cl,)).fetchall():
        st=request.form.get("status_"+s["roll"])
        if st in ("P","A","L"):
            c.execute("""INSERT INTO attendance(date,roll,status) VALUES(?,?,?)
                ON CONFLICT(date,roll) DO UPDATE SET status=excluded.status""",(date,s["roll"],st))
    c.commit(); c.close()
    return redirect(url_for("teacher",date=date))

@app.get("/admin")
@role_required
def admin():
    if session.get("role")!="admin": return redirect(url_for("teacher"))
    cl=request.args.get("class","1"); date=request.args.get("date","")
    c=db()
    students=c.execute("SELECT roll,name,class FROM students WHERE class=? ORDER BY name",(cl,)).fetchall()
    statuses={r["roll"]:r["status"] for r in c.execute("SELECT roll,status FROM attendance WHERE date=?",(date,))}
    reports=c.execute("""SELECT a.date,s.class,
      SUM(a.status='P') p,SUM(a.status='A') absent,SUM(a.status='L') leave
      FROM attendance a JOIN students s ON s.roll=a.roll
      GROUP BY a.date,s.class ORDER BY a.date DESC, CAST(s.class AS INTEGER)""").fetchall()
    c.close()
    return render_template("admin.html", classes=classes_list(), selected_class=cl,
        students=students,statuses=statuses,date=date,reports=reports)

@app.post("/admin/save")
@role_required
def admin_save():
    if session.get("role")!="admin": return redirect(url_for("home"))
    cl=request.form["class"]; date=request.form["date"]; c=db()
    for s in c.execute("SELECT roll FROM students WHERE class=?",(cl,)).fetchall():
        st=request.form.get("status_"+s["roll"])
        if st in ("P","A","L"):
            c.execute("""INSERT INTO attendance(date,roll,status) VALUES(?,?,?)
                ON CONFLICT(date,roll) DO UPDATE SET status=excluded.status""",(date,s["roll"],st))
    c.commit(); c.close()
    return redirect(url_for("admin", **{"class": cl, "date": date}))

@app.get("/api/students")
def api_students():
    cl=request.args.get("class",""); c=db()
    rows=c.execute("SELECT roll,name,class FROM students WHERE class=? ORDER BY name",(cl,)).fetchall()
    c.close(); return jsonify([dict(r) for r in rows])

init_db()
if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT",5000)))
