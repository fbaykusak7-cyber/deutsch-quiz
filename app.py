from flask import Flask, render_template, request, session, redirect, url_for
import os
import random
import math
import re

app = Flask(__name__)
app.secret_key = "FINAL_ALL_IN_ONE_2026"

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
    if "level" not in session:
        session["level"] = "a1"
    if "xp" not in session:
        session["xp"] = 0
    if "score" not in session:
        session["score"] = 0
    if "total" not in session:
        session["total"] = 0
    if "wrong_words" not in session:
        session["wrong_words"] = []  # list of dicts {de,en}

def reset_stats_only():
    # Skor sıfırlansın, ama wrong_words kaybolmasın
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
    # Her zaman 4 şık üretmeye çalışır, yetmezse tekrar/padding yapar (çökme yok).
    wrong_pool = [w["en"] for w in ALL if w["en"] != correct_en]
    wrong_pool = list(dict.fromkeys(wrong_pool))  # unique preserve order

    options = [correct_en]
    need = 3

    if len(wrong_pool) >= need:
        options += random.sample(wrong_pool, need)
    else:
        options += wrong_pool

    # padding
    while len(options) < 4:
        options.append(correct_en)

    # unique shuffle ama 4'ten az kalırsa tekrar pad
    options = list(dict.fromkeys(options))
    while len(options) < 4:
        options.append(correct_en)

    random.shuffle(options)
    return options[:4]

def get_question(pool):
    if not pool:
        return {"de": "No words", "en": "none"}, ["none", "none", "none", "none"]
    q = random.choice(pool)
    options = build_options(q["en"])
    return q, options

@app.route("/set/<cat>")
def set_category(cat):
    init_session()
    cat = (cat or "").lower()
    if cat not in CATEGORIES:
        cat = "a1"
    session["level"] = cat
    reset_stats_only()
    return redirect(url_for("quiz"))

@app.route("/", methods=["GET", "POST"])
def quiz():
    init_session()

    feedback = ""  # "", "correct", "wrong"

    level = session["level"]
    pool = get_pool(level)

    # kategori boşsa mixed'e düş
    if not pool:
        session["level"] = "mixed"
        reset_stats_only()
        level = "mixed"
        pool = get_pool(level)

    if request.method == "POST":
        selected = request.form.get("answer", "")
        correct = session.get("correct", "")
        german = session.get("current_word", "")

        if selected and correct:
            session["total"] += 1
            if selected == correct:
                session["score"] += 1
                session["xp"] += 10
                feedback = "correct"

                # Wrong modundayken doğru yapınca listeden çıkar
                if level == "wrong":
                    session["wrong_words"] = [w for w in session["wrong_words"] if w["de"] != german]
            else:
                feedback = "wrong"

                # Yanlış yaptıysa wrong_words'a ekle (tekrar ekleme)
                already = any(w["de"] == german for w in session["wrong_words"])
                if not already:
                    session["wrong_words"].append({"de": german, "en": correct})

        # Wrong modunda liste boşaldıysa mixed'e düş
        if level == "wrong" and not session.get("wrong_words", []):
            session["level"] = "mixed"
            reset_stats_only()
            level = "mixed"
            pool = get_pool(level)

    # yeni soru
    level = session["level"]
    pool = get_pool(level)
    q, options = get_question(pool)

    session["correct"] = q["en"]
    session["current_word"] = q["de"]

    level_number = math.floor(session["xp"] / 100) + 1

    return render_template(
        "index.html",
        german=q["de"],
        options=options,
        score=session["score"],
        total=session["total"],
        xp=session["xp"],
        level_number=level_number,
        selected_level=session["level"],
        feedback=feedback,
        wrong_count=len(session.get("wrong_words", []))
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)