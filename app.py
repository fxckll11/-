from flask import Flask, render_template, request, session, redirect
import random, json, re, datetime

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


LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2"]


# ================= INIT DAILY =================
def init_daily():
    today = str(datetime.date.today())

    if session.get("daily_date") != today:
        session["daily_date"] = today
        session["daily"] = {"q1": False, "q2": False, "q3": False}
        session["level_lock"] = False
        session["study_start"] = None


# ================= HOME =================
@app.route("/")
def index():
    init_daily()

    progress = session.get("progress") or {"grammar": 0, "translation": 0}

    grammar = progress["grammar"]
    translation = progress["translation"]

    percent = int(((grammar + translation) / 50) * 100)

    return render_template(
        "index.html",
        level=session.get("level", "A1"),
        percent=percent,
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

    tasks = []

    if mode == "translation":

        words = load_words(level)
        keys = list(words.keys())
        random.shuffle(keys)

        for w in keys[:5]:
            correct = words[w]["translations"][0]

            options = [correct]
            while len(options) < 4:
                val = words[random.choice(keys)]["translations"][0]
                if val not in options:
                    options.append(val)

            random.shuffle(options)

            tasks.append({
                "type": "choice",
                "question": f"Translate: {w}",
                "answer": correct,
                "options": options
            })

        for w in keys[5:10]:
            tasks.append({
                "type": "input",
                "question": f"Translate: {w}",
                "answer": words[w]["translations"][0]
            })

    else:

        data = load_grammar(level)
        random.shuffle(data)

        for t in data[:5]:
            tasks.append({
                "type": "choice",
                "question": t["question"],
                "answer": t["answer"],
                "options": t["options"]
            })

        for t in data[5:10]:
            tasks.append({
                "type": "input",
                "question": t["question"],
                "answer": t["answer"]
            })

    session["tasks"] = tasks
    return redirect("/task")


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
            ok = norm(ans) == norm(correct)
        else:
            ok = ans == correct

        if ok:
            session["score"] += 1

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

    progress = session.get("progress") or {"grammar": 0, "translation": 0}

    grammar = int(progress["grammar"])
    translation = int(progress["translation"])

    level = session.get("level", "A1")
    if level not in LEVELS:
        level = "A1"
        session["level"] = level

    score = session.get("score", 0)

    # ================= XP =================
    xp = score * 10

    mode = session.get("mode")

    # ================= UPDATE PROGRESS =================
    if score == 10:

        if mode == "grammar":
            grammar += 1

        if mode == "translation":
            translation += 1

    session["progress"] = {
        "grammar": grammar,
        "translation": translation
    }

    # ================= DAILY QUEST =================
    daily = session.get("daily", {"q1": False, "q2": False, "q3": False})

    start = session.get("study_start")
    if start:
        elapsed = datetime.datetime.now().timestamp() - start
        if elapsed >= 600:
            daily["q3"] = True

    session["daily"] = daily

    # ================= SAFE LEVEL UP =================
    current_index = LEVELS.index(level)

    if not session.get("level_lock", False):

        if grammar >= 25 and translation >= 25:

            if current_index < len(LEVELS) - 1:

                session["level"] = LEVELS[current_index + 1]

                session["progress"] = {
                    "grammar": 0,
                    "translation": 0
                }

                session["level_lock"] = True

    return render_template(
        "result.html",
        score=score,
        xp=xp,
        results=session.get("results"),
        level=session.get("level"),
        progress=session.get("progress"),
        daily=session.get("daily")
    )


# ================= STUDY =================
@app.route("/study")
def study():
    data = {lvl: load_words(lvl) for lvl in LEVELS}
    return render_template("study.html", words=data)


# ================= RULES =================
@app.route("/rules")
def rules():
    return render_template("rules.html")


if __name__ == "__main__":
    app.run(debug=True)
