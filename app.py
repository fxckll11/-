from flask import Flask, render_template, request, session, redirect
import random, json, re, datetime, time

app = Flask(__name__)
app.secret_key = "secret123"


# ================= HELPERS =================
def norm(t):
    return re.sub(r"[^\w\s]", "", t.lower().strip())


def load_words(level):
    with open(f"words/{level}.json", encoding="utf-8") as f:
        return json.load(f)


def load_grammar(level):
    with open(f"templates/grammar/{level}.json", encoding="utf-8") as f:
        return json.load(f)


# ================= DAILY =================
def init_daily():
    today = str(datetime.date.today())

    if session.get("daily_date") != today:
        session["daily_date"] = today
        session["daily"] = {"q1": False, "q2": False, "q3": False}


# ================= HOME =================
@app.route("/")
def index():

    init_daily()

    progress = session.get("progress", {
        "translation_done": 0,
        "grammar_done": 0
    })

    return render_template(
        "index.html",
        progress=progress,
        level=session.get("level", "A1"),
        daily=session.get("daily")
    )


# ================= START =================
@app.route("/start/<level>")
def start(level):
    session["level"] = level
    return render_template("mode.html", level=level)


# ================= MODE =================
@app.route("/mode/<mode>")
def mode(mode):

    level = session.get("level", "A1")

    session["mode"] = mode
    session["i"] = 0
    session["score"] = 0
    session["results"] = []

    session.setdefault("progress", {
        "translation_done": 0,
        "grammar_done": 0
    })

    tasks = []

    try:

        # ================= TRANSLATION =================
        if mode == "translation":

            words = load_words(level)
            keys = list(words.keys())

            if len(keys) < 10:
                keys = keys * 2

            random.shuffle(keys)

            selected = keys[:10]
            half = 5

            # ===== 5 TEST =====
            for w in selected[:half]:

                correct = words[w]["translations"][0]

                wrong_pool = [k for k in keys if k in words and k != w]
                wrong = random.sample(wrong_pool, min(3, len(wrong_pool)))

                options = [words[x]["translations"][0] for x in wrong]

                if correct not in options:
                    options[0] = correct

                random.shuffle(options)

                tasks.append({
                    "type": "choice",
                    "question": f"Translate: {w}",
                    "answer": correct,
                    "options": options
                })

            # ===== 5 INPUT =====
            for w in selected[half:]:

                correct = words[w]["translations"][0]

                tasks.append({
                    "type": "input",
                    "question": f"Translate: {w}",
                    "answer": correct
                })

        # ================= GRAMMAR =================
        elif mode == "grammar":

            data = load_grammar(level)

            if len(data) < 10:
                data = data * 2

            selected = random.sample(data, 10)
            half = 5

            # ===== 5 TEST =====
            for t in selected[:half]:

                tasks.append({
                    "type": "choice",
                    "question": t.get("question", ""),
                    "answer": t.get("answer", ""),
                    "options": t.get("options", [
                        t.get("answer", "is"),
                        "is",
                        "are",
                        "was"
                    ])
                })

            # ===== 5 INPUT =====
            for t in selected[half:]:

                tasks.append({
                    "type": "input",
                    "question": t.get("question", ""),
                    "answer": t.get("answer", "")
                })

        else:
            return redirect("/")

        session["tasks"] = tasks
        return redirect("/task")

    except Exception as e:
        print("MODE ERROR:", e)
        return redirect("/")


# ================= TASK =================
@app.route("/task", methods=["GET", "POST"])
def task():

    tasks = session.get("tasks", [])
    i = session.get("i", 0)

    if i >= len(tasks):
        return redirect("/result")

    task = tasks[i]

    if request.method == "POST":

        ans = request.form.get("answer", "")
        correct = task["answer"]

        ok = False

        if task["type"] == "input":
            if norm(ans) == norm(correct):
                session["score"] += 1
                ok = True
        else:
            if ans == correct:
                session["score"] += 1
                ok = True

        session["results"].append({
            "question": task["question"],
            "user": ans,
            "correct": correct,
            "ok": ok
        })

        session["i"] += 1
        return redirect("/task")

    return render_template("task.html", task=task, num=i + 1)


# ================= RESULT =================
@app.route("/result")
def result():

    init_daily()

    level = session.get("level", "A1")
    score = session.get("score", 0)
    mode = session.get("mode")

    progress = session.get("progress")

    xp_gain = score * 10
    daily = session.get("daily")

    if mode == "grammar":
        daily["q1"] = True
        xp_gain = int(xp_gain * 1.5)

    if mode == "translation":
        daily["q2"] = True
        xp_gain = int(xp_gain * 2)

    if session.get("i", 0) >= 10:
        daily["q3"] = True
        xp_gain += 50

    session["daily"] = daily

    if progress["translation_done"] >= 25 and progress["grammar_done"] >= 25:

        levels = ["A1","A2","B1","B2","C1","C2"]

        idx = levels.index(level)
        if idx < len(levels) - 1:
            session["level"] = levels[idx + 1]

            session["progress"] = {
                "translation_done": 0,
                "grammar_done": 0
            }

    return render_template(
        "result.html",
        score=score,
        results=session.get("results", []),
        level=session.get("level"),
        progress=session.get("progress"),
        xp=xp_gain,
        daily=daily
    )


# ================= STUDY =================
@app.route("/study")
def study():
    data = {}
    for lvl in ["A1","A2","B1","B2","C1","C2"]:
        data[lvl] = load_words(lvl)
    return render_template("study.html", words=data)


# ================= RULES =================
@app.route("/rules")
def rules():
    return render_template("rules.html")


# ================= RUN =================
if __name__ == "__main__":
    app.run(debug=True)