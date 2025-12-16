from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import json
import os

app = Flask(__name__)
app.secret_key = "super-secret-key"   # needed for session

# Questions format:
# [question, option1, option2, option3, option4, correct_option_index]
questions = [
    ["Who is Shah Rukh Khan?", "WWE Wrestler", "Plumber", "Actor", "Astronaut", 3],
    ["What is the capital of France?", "Berlin", "Paris", "Rome", "London", 2],
    ["Which planet is known as the Red Planet?", "Earth", "Venus", "Mars", "Jupiter", 3],
    ["What is the largest mammal?", "Shark", "Blue Whale", "Elephant", "Giraffe", 2],
    ["Who wrote 'Romeo and Juliet'?", "William Shakespeare", "Jane Austen", "Charles Dickens", "Homer", 1],
    ["What is the square root of 64?", "8", "10", "6", "12", 1],
    ["Which country is known as the Land of the Rising Sun?", "India", "South Korea", "Japan", "China", 3],
    ["Who painted the Mona Lisa?", "Claude Monet", "Pablo Picasso", "Leonardo da Vinci", "Vincent van Gogh", 3],
    ["What is the fastest land animal?", "Horse", "Lion", "Cheetah", "Elephant", 3],
    ["Which ocean is the largest?", "Indian Ocean", "Pacific Ocean", "Atlantic Ocean", "Arctic Ocean", 2],
    ["What is the smallest country in the world?", "San Marino", "Vatican City", "Monaco", "Liechtenstein", 2]
]

prizes = [100000,100000,100000,100000,100000,100000,100000,100000,100000,100000,100000]

# Path to JSON file to store results
RESULTS_FILE = os.path.join(app.root_path, "results.json")


def load_results():
    """Load all saved results from results.json (returns list)."""
    if not os.path.exists(RESULTS_FILE):
        return []
    with open(RESULTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def save_result(name, amount, status, correct, wrong):
    results = load_results()
    results.append({
        "name": name,
        "amount": amount,
        "status": status,
        "correct": correct,
        "wrong": wrong
    })
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        student_name = request.form.get("name", "").strip()

        # ✅ Server-side validation
        if not student_name.replace(" ", "").isalpha():
            return render_template(
                "index.html",
                error="Name must contain only letters and spaces."
            )

        if len(student_name) < 3 or len(student_name) > 20:
            return render_template(
                "index.html",
                error="Name must be between 3 and 20 characters."
            )

        session["student_name"] = student_name
        return redirect(url_for("quiz"))

    return render_template("index.html")


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if "student_name" not in session:
        return redirect(url_for("home"))

    student_name = session["student_name"]

    # ✅ SAFETY INITIALIZATION
    if "answer_log" not in session:
        session["answer_log"] = []

    if "correct_count" not in session:
        session["correct_count"] = 0

    if "wrong_count" not in session:
        session["wrong_count"] = 0


    # initialize defaults
    feedback = None
    correct_option = None
    show_next = False

    if request.method == "GET":
        q_index = 0
        current_prize = 0
        session["correct_count"] = 0
        session["wrong_count"] = 0
        session["answer_log"] = []

    else:
        q_index = int(request.form["q_index"])
        current_prize = int(request.form["current_prize"])

        # 🔹 If this POST is for checking answer
        if "answer" in request.form:
            selected = int(request.form["answer"])
            correct = questions[q_index][5]

            if selected == correct:
                feedback = "correct"
                current_prize += prizes[q_index]
                session["correct_count"] += 1
            else:
                feedback = "wrong"
                correct_option = questions[q_index][correct]
                session["wrong_count"] += 1

                # ✅ Save question review info (ADD HERE)
            session["answer_log"].append({
                "question": questions[q_index][0],
                "options": questions[q_index][1:5],
                "correct_answer": questions[q_index][questions[q_index][5]],
                "user_answer": questions[q_index][selected],
                "is_correct": selected == correct
            })



            show_next = True   # show Next button
            # ❗ DO NOT increment q_index here

        # 🔹 If this POST is for next question
        else:
            q_index += 1

            if q_index >= len(questions):
                save_result(
                    student_name,
                    current_prize,
                    "finished",
                    session["correct_count"],
                    session["wrong_count"],
                    session["answer_log"]
                )
                session["last_attempt_idx"] = len(load_results()) -1

                return render_template(
                    "result.html",
                    name=student_name,
                    message="Quiz Completed 🎉",
                    amount=current_prize,
                    results_count=len(load_results())
                )

    question = questions[q_index]

    return render_template(
        "quiz.html",
        name=student_name,
        q_index=q_index,
        current_prize=current_prize,
        question_text=question[0],
        option_a=question[1],
        option_b=question[2],
        option_c=question[3],
        option_d=question[4],
        feedback=feedback,
        correct_option=correct_option,
        show_next=show_next,
        questions = questions
    )

def save_result(name, amount, status, correct, wrong, answers):
    results = load_results()
    results.append({
        "name": name,
        "amount": amount,
        "status": status,
        "correct": correct,
        "wrong": wrong,
        "answers": answers
    })
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)


@app.route("/results")
def all_results():
    """Return all students' results in JSON format."""
    results = load_results()
    return jsonify(results)


@app.route("/leaderboard")
def leaderboard():
    results = load_results()
    results = sorted(results, key=lambda x: x["amount"], reverse=True)

    return render_template(
    "leaderboard.html",
    results=results,
    user=session.get("student_name"),
    last_attempt_idx=session.get("last_attempt_idx")
)


@app.route("/review/<int:idx>")
def review(idx):
    results = load_results()

    # safety check
    if idx < 0 or idx >= len(results):
        return redirect(url_for("leaderboard"))

    attempt = results[idx]

    return render_template(
        "review.html",
        attempt=attempt
    )




if __name__ == "__main__":
    app.run(debug=True)
