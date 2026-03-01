from flask import Flask, render_template, request, session, redirect, url_for
import os
import random
import math
import re

app = Flask(__name__)
app.secret_key = "final_production_version"

BASE = os.path.dirname(os.path.abspath(__file__))

CATEGORIES = ["a1","a2","hotel","verb","pronouns","mixed","wrong"]

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

def get_question(pool):
    correct = random.choice(pool)
    wrong_pool = [w["en"] for w in ALL if w["en"]!=correct["en"]]
    options = random.sample(wrong_pool,3) + [correct["en"]]
    random.shuffle(options)
    return correct,options

@app.route("/set/<cat>")
def set_category(cat):
    cat = cat.lower()
    if cat not in CATEGORIES:
        cat="a1"
    session["level"]=cat
    reset_stats()
    return redirect(url_for("quiz"))

@app.route("/",methods=["GET","POST"])
def quiz():

    if "level" not in session:
        session["level"]="a1"
        session["wrong_words"]=[]
        reset_stats()

    level=session["level"]
    pool=get_pool(level)

    if not pool:
        return "No words in this category."

    feedback=""

    if request.method=="POST":
        selected=request.form.get("answer")
        correct=session.get("correct")
        german=session.get("current_word")

        if selected:
            session["total"]+=1

            if selected==correct:
                session["score"]+=1
                session["xp"]+=10
                feedback="correct"

                if level=="wrong":
                    session["wrong_words"]=[
                        w for w in session["wrong_words"]
                        if w["de"]!=german
                    ]
            else:
                feedback="wrong"
                if not any(w["de"]==german for w in session["wrong_words"]):
                    session["wrong_words"].append({"de":german,"en":correct})

    q,options=get_question(pool)
    session["correct"]=q["en"]
    session["current_word"]=q["de"]

    level_number=math.floor(session["xp"]/100)+1

    return render_template("index.html",
        german=q["de"],
        options=options,
        score=session["score"],
        total=session["total"],
        xp=session["xp"],
        level_number=level_number,
        selected_level=session["level"],
        feedback=feedback
    )

if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)