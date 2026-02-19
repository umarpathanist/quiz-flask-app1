from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import psycopg2
import json
import os

app = Flask(__name__)
app.secret_key = "super-secret-key"

# =========================
# DATABASE CONFIG (LOCAL)
# =========================
DB_CONFIG = {
    "host": "127.0.0.1",
    "database": "quizdb",
    "user": "postgres",
    "password": "Umar123",
    "port": 5432
}

# =========================
# DATABASE CONNECTION
# =========================
def get_conn():
    db_url = os.getenv("DATABASE_URL")

    if db_url:
        return psycopg2.connect(db_url)

    return psycopg2.connect(
        host=DB_CONFIG["host"],
        database=DB_CONFIG["database"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        port=DB_CONFIG["port"]
    )

# =========================
# LOAD QUESTIONS
# =========================
QUESTIONS_FILE = os.path.join(app.root_path, "questions.json")

def load_questions():
    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# =========================
# DATABASE FUNCTIONS
# =========================
def save_result_db(name, amount, status, correct, wrong, answers):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO results (name, amount, status, correct, wrong, answers)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        name,
        amount,
        status,
        correct,
        wrong,
        json.dumps(answers)
    ))

    conn.commit()
    cur.close()
    conn.close()


def load_results_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, amount, status, correct, wrong, answers
        FROM results
        ORDER BY amount DESC
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = []
    for r in rows:
        results.append({
            "id": r[0],
            "name": r[1],
            "amount": r[2],
            "status": r[3],
            "correct": r[4],
            "wrong": r[5],
            "answers": r[6]
        })

    return results

# =========================
# HOME
# =========================
@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        name = request.form.get("name", "").strip()

        if not name.replace(" ", "").isalpha():
            return render_template("index.html",
                                   error="Name must contain only letters.")

        if len(name) < 3:
            return render_template("index.html",
                                   error="Minimum 3 characters required.")

        session["student_name"] = name
        return redirect(url_for("quiz"))

    return render_template("index.html")

# =========================
# QUIZ
# =========================
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "student_name" not in session:
        return redirect(url_for("home"))

    questions = load_questions()

    session.setdefault("correct_count", 0)
    session.setdefault("wrong_count", 0)
    session.setdefault("answer_log", [])

    feedback = None
    show_next = False
    correct_option_text = None  # ⭐ FIX

    if request.method == "GET":
        q_index = 0
        current_prize = 0
        session["correct_count"] = 0
        session["wrong_count"] = 0
        session["answer_log"] = []

    else:
        q_index = int(request.form["q_index"])
        current_prize = int(request.form["current_prize"])

        if "answer" in request.form:
            selected = int(request.form["answer"])
            question = questions[q_index]
            correct = question["correct_option"]

            if selected == correct:
                feedback = "correct"
                current_prize += 500
                session["correct_count"] += 1
            else:
                feedback = "wrong"
                correct_option_text = question["options"][correct - 1]  # ⭐ FIX
                current_prize -= 250
                session["wrong_count"] += 1

            session["answer_log"].append({
                "question": question["question"],
                "options": question["options"],
                "correct_answer": question["options"][correct - 1],
                "user_answer": question["options"][selected - 1],
                "is_correct": selected == correct
            })

            show_next = True

        else:
            q_index += 1

            if q_index >= len(questions):
                name = session["student_name"]
                correct = session["correct_count"]
                wrong = session["wrong_count"]
                answers = session["answer_log"]

                save_result_db(
                    name,
                    current_prize,
                    "finished",
                    correct,
                    wrong,
                    answers
                )

                results = load_results_db()
                session["last_attempt_idx"] = results[-1]["id"]  # ⭐ FIX

                total = len(questions)
                percent = (correct / total) * 100
                is_winner = percent >= 70

                return render_template(
                    "result.html",
                    name=name,
                    amount=current_prize,
                    percentage=round(percent, 2),
                    is_winner=is_winner
                )

    question = questions[q_index]

    return render_template(
        "quiz.html",
        name=session["student_name"],
        q_index=q_index,
        current_prize=current_prize,
        question_text=question["question"],
        options=question["options"],
        feedback=feedback,
        correct_option=correct_option_text,  # ⭐ FIX
        show_next=show_next
    )

# =========================
# LEADERBOARD
# =========================
@app.route("/leaderboard")
def leaderboard():
    results = load_results_db()

    return render_template(
        "leaderboard.html",
        results=results,
        user=session.get("student_name"),
        last_attempt_idx=session.get("last_attempt_idx")
    )

# =========================
# REVIEW (CORRECT USER)
# =========================
@app.route("/review/<int:result_id>")
def review(result_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, amount, status, correct, wrong, answers
        FROM results
        WHERE id = %s
    """, (result_id,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return redirect(url_for("leaderboard"))

    attempt = {
        "id": row[0],
        "name": row[1],
        "amount": row[2],
        "status": row[3],
        "correct": row[4],
        "wrong": row[5],
        "answers": row[6]
    }

    return render_template("review.html", attempt=attempt)

# =========================
# API
# =========================
@app.route("/api/results")
def api_results():
    return jsonify(load_results_db())

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(debug=True)
