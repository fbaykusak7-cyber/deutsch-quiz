from flask import Flask, render_template, request, session, jsonify
import os
import random
import math
import re

app = Flask(__name__)
app.secret_key = "AJAX_FINAL_2026"

BASE = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = ["a1", "a2", "hotel", "verb", "pronouns", "mixed", "wrong"]

def clean_line(line: str) -> str:
    line = line.strip()
    line = line.replace("●", "").replace("•", "")
    line = line.replace("–", "-").replace("—", "-")
    line = re.sub(r"\s+", " ", line)
    return line.strip()

def load_txt(filename: str):
    words = []
    path = os.path.join(BASE, filename)
    if not os.path.exists(path):
        return words
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            line = clean_line(raw)
            if "-" not in line:
                continue
            de, en = line.split("-", 1)
            de = de.strip()
            en = en.strip()
            if de and en:
                words.append({"de": de, "en": en})
    return words

A1 = load_txt("a1.txt")
A2 = load_txt("a2.txt")
HOTEL = load_txt("hotel.txt")
VERB = load_txt("verb.txt")
PRON = load_txt("pronouns.txt")
ALL = A1 + A2 + HOTEL + VERB + PRON

def init_session():
    session.setdefault("level", "a1")
    session.setdefault("xp", 0)
    session.setdefault("score", 0)
    session.setdefault("total", 0)
    session.setdefault("wrong_words", [])  # list of {de,en}
    session.setdefault("current_word", "")
    session.setdefault("correct", "")

def reset_stats_only():
    session["xp"] = 0
    session["score"] = 0
    session["total"] = 0

def get_pool(level: str):
    if level == "a1": return A1
    if level == "a2": return A2
    if level == "hotel": return HOTEL
    if level == "verb": return VERB
    if level == "pronouns": return PRON
    if level == "wrong": return session.get("wrong_words", [])
    return ALL  # mixed

def build_options(correct_en: str):
    # Always tries to return 4 options without crashing
    wrong_pool = [w["en"] for w in ALL if w["en"] != correct_en]
    wrong_pool = list(dict.fromkeys(wrong_pool))  # unique

    options = [correct_en]
    if len(wrong_pool) >= 3:
        options += random.sample(wrong_pool, 3)
    else:
        options += wrong_pool

    # pad to 4
    while len(options) < 4:
        options.append(correct_en)

    # ensure length 4
    options = options[:4]
    random.shuffle(options)
    return options

def pick_question():
    level = session["level"]
    pool = get_pool(level)

    # If chosen category empty -> fallback to mixed
    if not pool:
        session["level"] = "mixed"
        pool = get_pool("mixed")

    # If wrong empty -> fallback to mixed
    if session["level"] == "wrong" and not pool:
        session["level"] = "mixed"
        pool = get_pool("mixed")

    q = random.choice(pool) if pool else {"de": "No words", "en": "none"}
    options = build_options(q["en"]) if q["en"] != "none" else ["none", "none", "none", "none"]

    session["current_word"] = q["de"]
    session["correct"] = q["en"]

    return q["de"], options

def payload(feedback: str = ""):
    level_number = math.floor(session["xp"] / 100) + 1
    return {
        "german": session.get("current_word", ""),
        "options": session.get("options", []),  # will fill below
        "score": session["score"],
        "total": session["total"],
        "xp": session["xp"],
        "level_number": level_number,
        "selected_level": session["level"],
        "wrong_count": len(session.get("wrong_words", [])),
        "feedback": feedback,  # "", "correct", "wrong"
    }

@app.route("/", methods=["GET"])
def home():
    init_session()
    # Preload first question for server-render
    german, options = pick_question()
    session["options"] = options
    return render_template(
        "index.html",
        german=german,
        options=options,
        score=session["score"],
        total=session["total"],
        xp=session["xp"],
        level_number=math.floor(session["xp"] / 100) + 1,
        selected_level=session["level"],
        wrong_count=len(session.get("wrong_words", [])),
    )

@app.route("/api/state", methods=["GET"])
def api_state():
    init_session()
    german, options = pick_question()
    session["options"] = options
    data = payload("")
    data["german"] = german
    data["options"] = options
    return jsonify(data)

@app.route("/api/set_category", methods=["POST"])
def api_set_category():
    init_session()
    body = request.get_json(silent=True) or {}
    cat = (body.get("category") or "").lower()
    if cat not in CATEGORIES:
        cat = "a1"

    session["level"] = cat
    reset_stats_only()

    german, options = pick_question()
    session["options"] = options

    data = payload("")
    data["german"] = german
    data["options"] = options
    return jsonify(data)

@app.route("/api/answer", methods=["POST"])
def api_answer():
    init_session()
    body = request.get_json(silent=True) or {}
    selected = body.get("answer", "")
    correct = session.get("correct", "")
    german = session.get("current_word", "")
    level = session["level"]

    feedback = ""

    if selected and correct:
        session["total"] += 1
        if selected == correct:
            session["score"] += 1
            session["xp"] += 10
            feedback = "correct"

            # If in wrong mode, remove when solved
            if level == "wrong":
                session["wrong_words"] = [w for w in session["wrong_words"] if w["de"] != german]
        else:
            feedback = "wrong"
            # add to wrong list if not exists
            if not any(w["de"] == german for w in session["wrong_words"]):
                session["wrong_words"].append({"de": german, "en": correct})

    # If wrong list emptied, fallback to mixed
    if session["level"] == "wrong" and len(session.get("wrong_words", [])) == 0:
        session["level"] = "mixed"
        reset_stats_only()

    # Next question immediately (NO PAGE RELOAD)
    german_next, options_next = pick_question()
    session["options"] = options_next

    data = payload(feedback)
    data["german"] = german_next
    data["options"] = options_next
    return jsonify(data)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)