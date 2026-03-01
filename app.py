from flask import Flask, render_template, request, session, jsonify
import os
import random
import math
import re

app = Flask(__name__)
app.secret_key = "AJAX_FINAL_2026"

BASE = os.path.dirname(os.path.abspath(__file__))
CATEGORIES = ["a1", "a2", "hotel", "verb", "pronouns", "mixed", "wrong"]

def clean_line(line):
    line = line.strip()
    line = line.replace("●","").replace("•","")
    line = line.replace("–","-").replace("—","-")
    line = re.sub(r"\s+"," ",line)
    return line.strip()

def load_txt(filename):
    words = []
    path = os.path.join(BASE, filename)
    if not os.path.exists(path):
        return words

    with open(path,"r",encoding="utf-8",errors="ignore") as f:
        for raw in f:
            line = clean_line(raw)
            if "-" not in line:
                continue
            de,en = line.split("-",1)
            de = de.strip()
            en = en.strip()
            if de and en:
                words.append({"de":de,"en":en})
    return words

A1 = load_txt("a1.txt")
A2 = load_txt("a2.txt")
HOTEL = load_txt("hotel.txt")
VERB = load_txt("verb.txt")
PRON = load_txt("pronouns.txt")

ALL = A1 + A2 + HOTEL + VERB + PRON

def init_session():
    session.setdefault("level","a1")
    session.setdefault("xp",0)
    session.setdefault("score",0)
    session.setdefault("total",0)
    session.setdefault("wrong_words",[])

def reset_stats():
    session["xp"]=0
    session["score"]=0
    session["total"]=0

def get_pool(level):
    if level=="a1": return A1
    if level=="a2": return A2
    if level=="hotel": return HOTEL
    if level=="verb": return VERB
    if level=="pronouns": return PRON
    if level=="wrong": return session.get("wrong_words",[])
    return ALL

def build_options(correct):
    wrong_pool=[w["en"] for w in ALL if w["en"]!=correct]
    options=[correct]

    if len(wrong_pool)>=3:
        options+=random.sample(wrong_pool,3)
    else:
        options+=wrong_pool

    while len(options)<4:
        options.append(correct)

    random.shuffle(options)
    return options[:4]

def next_question():
    level=session["level"]
    pool=get_pool(level)

    if not pool:
        session["level"]="mixed"
        pool=get_pool("mixed")

    q=random.choice(pool)
    session["correct"]=q["en"]
    session["current_word"]=q["de"]
    options=build_options(q["en"])
    return q["de"],options

@app.route("/", methods=["GET","POST"])
def home():
    init_session()

    german,options=next_question()

    return render_template(
        "index.html",
        german=german,
        options=options,
        score=session["score"],
        total=session["total"],
        xp=session["xp"],
        level_number=math.floor(session["xp"]/100)+1,
        selected_level=session["level"],
        wrong_count=len(session.get("wrong_words",[]))
    )

@app.route("/api/set_category", methods=["POST"])
def api_set_category():
    init_session()
    data=request.get_json() or {}
    cat=data.get("category","a1").lower()

    if cat not in CATEGORIES:
        cat="a1"

    session["level"]=cat
    reset_stats()

    german,options=next_question()

    return jsonify({
        "german":german,
        "options":options,
        "score":session["score"],
        "total":session["total"],
        "xp":session["xp"],
        "level_number":math.floor(session["xp"]/100)+1,
        "selected_level":session["level"],
        "wrong_count":len(session.get("wrong_words",[])),
        "feedback":""
    })

@app.route("/api/answer", methods=["POST"])
def api_answer():
    init_session()
    data=request.get_json() or {}
    selected=data.get("answer","")
    correct=session.get("correct","")
    german=session.get("current_word","")
    level=session["level"]

    feedback=""

    session["total"]+=1

    if selected==correct:
        session["score"]+=1
        session["xp"]+=10
        feedback="correct"

        if level=="wrong":
            session["wrong_words"]=[w for w in session["wrong_words"] if w["de"]!=german]
    else:
        feedback="wrong"
        if not any(w["de"]==german for w in session["wrong_words"]):
            session["wrong_words"].append({"de":german,"en":correct})

    german_next,options_next=next_question()

    return jsonify({
        "german":german_next,
        "options":options_next,
        "score":session["score"],
        "total":session["total"],
        "xp":session["xp"],
        "level_number":math.floor(session["xp"]/100)+1,
        "selected_level":session["level"],
        "wrong_count":len(session.get("wrong_words",[])),
        "feedback":feedback
    })

if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)