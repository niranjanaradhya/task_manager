from flask import Flask, render_template, request, redirect, session
import sqlite3

app = Flask(__name__)
app.secret_key = "secret123"


# ---------- DATABASE ----------
def get_db():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row   # IMPORTANT (access by column name)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        role TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        hours INTEGER,
        status TEXT,
        assigned_to INTEGER,
        FOREIGN KEY (assigned_to) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------- HOME ----------
@app.route('/')
def index():
    return render_template('index.html')


# ---------- SIGNUP ----------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        role = request.form.get('role').strip().lower()

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, password, role)
        )
        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template('signup.html')


# ---------- LOGIN ----------
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = ""

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )
        user = cur.fetchone()
        conn.close()

        if user:
            session.clear()
            session['user_id'] = user['id']
            session['role'] = user['role']

            if user['role'] == 'admin':
                return redirect('/admin_dashboard')
            else:
                return redirect('/employee_dashboard')
        else:
            error = "Invalid credentials"

    return render_template('login.html', error=error)


# ---------- ADMIN DASHBOARD ----------
@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()

    # JOIN to show employee name
    cur.execute("""
        SELECT tasks.*, users.username 
        FROM tasks 
        JOIN users ON tasks.assigned_to = users.id
    """)
    tasks = cur.fetchall()

    conn.close()

    return render_template('admin_dashboard.html', tasks=tasks)

# ---------- DELETE TASK (ADMIN) ----------
@app.route('/delete_task/<int:id>')
def delete_task(id):
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM tasks WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin_dashboard')


# ---------- ASSIGN TASK ----------
@app.route('/assign', methods=['GET', 'POST'])
def assign():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        hours = request.form.get('hours')
        assigned_to = int(request.form.get('assigned_to'))  # FIXED

        cur.execute("""
            INSERT INTO tasks (title, description, hours, status, assigned_to)
            VALUES (?, ?, ?, 'Pending', ?)
        """, (title, description, hours, assigned_to))

        conn.commit()
        conn.close()

        return redirect('/admin_dashboard')

    cur.execute("SELECT id, username FROM users WHERE role='employee'")
    users = cur.fetchall()

    conn.close()

    return render_template('assign.html', users=users)


# ---------- EMPLOYEE DASHBOARD ----------
@app.route('/employee_dashboard')
def employee_dashboard():
    if session.get('role') != 'employee':
        return redirect('/login')

    conn = get_db()
    cur = conn.cursor()

    # IMPORTANT: fetch only logged-in user's tasks
    cur.execute("""
        SELECT * FROM tasks 
        WHERE assigned_to = ?
    """, (session['user_id'],))

    tasks = cur.fetchall()
    conn.close()

    return render_template('employee_dashboard.html', tasks=tasks)


# ---------- UPDATE STATUS ----------
@app.route('/update_status', methods=['POST'])
def update_status():
    task_id = request.form.get('task_id')
    status = request.form.get('status')

    conn = get_db()
    cur = conn.cursor()

    cur.execute(
        "UPDATE tasks SET status=? WHERE id=?",
        (status, task_id)
    )

    conn.commit()
    conn.close()

    return redirect('/employee_dashboard')

# ---------- LOGOUT ----------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


# ---------- RUN ----------
if __name__ == '__main__':
    app.run(debug=True) 