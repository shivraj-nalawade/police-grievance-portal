from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import re

app = Flask(__name__)

# --- Database path ---
BASEDIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASEDIR, "complaints.db")

HIGH_TERMS = [
    # Violence / Murder / Weapons
    "murder", "murdered", "murdering", "homicide", "manslaughter",
    "kill", "killed", "killing", "stab", "stabbing", "stabbed", "knife", "dagger",
    "gun", "firearm", "pistol", "rifle", "shotgun", "revolver", "shoot", "shooting", "shooter",
    "gunfire", "bullet", "cartridge", "explosive", "grenade", "bomb", "explosion", "blast",
    "acid attack", "assassination", "murder attempt", "attempt to murder",
    
    # Terror / Hijack / Large-scale crime
    "terror", "terrorist", "terrorism", "bomb threat", "hijack", "hijacking",
    "massacre", "lynch", "genocide", "hostage", "hostage crisis", "extortion", "blackmail",
    "smuggling", "drug trafficking", "human trafficking", "organ trafficking",
    "illegal arms", "gang war", "shootout", "cartel", "mafia", "underworld",

    # Kidnapping / Abduction
    "kidnap", "kidnapped", "kidnapping", "abduct", "abducted", "abduction", 
    "child abduction", "hostage taking",

    # Sexual violence
    "rape", "raped", "rapist", "sexual assault", "sexual harassment",
    "molestation", "sex abuse", "abuse", "child abuse", "domestic abuse", 
    "harass woman", "forced intercourse", "gangrape", "paedophile", "pedophile",

    # Major threats
    "arson", "set on fire", "burn alive", "threaten", "threatened", "death threat",
    "acid", "honour killing", "contract killing", "suicide bombing", "bombing",
    "murder conspiracy", "violent threat", "bloodshed"
]

MEDIUM_TERMS = [
    # Theft / Property crime
    "theft", "steal", "stolen", "robbery", "robbed", "rob", "robber",
    "snatch", "snatched", "snatcher", "pickpocket", "burglary", "break-in",
    "house break", "car theft", "bike theft", "jewelry theft", "gold theft",
    "shoplifting", "looting", "pilferage", "property stolen", "vandal", "vandalism",
    "damage", "trespass", "trespassing", "illegal entry", "property damage",

    # Fraud / Scams
    "fraud", "fraudulent", "scam", "scammed", "scammer", "cheating",
    "forgery", "fake documents", "fake signature", "fake ID", "cyber fraud", "phishing",
    "online scam", "identity theft", "ATM fraud", "card cloning", "UPI fraud",
    "loan fraud", "investment scam", "insurance scam", "cheque bounce", "embezzlement",
    "tax evasion", "money laundering",

    # Physical violence (not life-threatening)
    "harass", "harassment", "eve teasing", "molest", "assault", "slap",
    "fight", "brawl", "street fight", "neighbour fight", "domestic violence",
    "verbal abuse", "argument", "intoxicated", "drunk", "drinking", "public nuisance",
    "threat", "minor injury", "physical abuse",

    # Accidents / Civil
    "drunk driving", "rash driving", "overspeeding", "road rage",
    "hit and run", "accident", "vehicle accident", "bike accident", "car crash",
    "bus accident", "train accident", "fire accident", "building collapse",
    "missing", "lost", "lost item", "wallet lost", "phone lost", "unconscious",
    "injury", "fall", "workplace accident",

    # Disturbances
    "noise", "loud music", "nuisance", "public nuisance", "disturbance",
    "illegal parking", "parking issue", "road blockage", "protest", "strike",
    "crowd", "mob", "stone pelting", "demonstration", "procession", "unlawful gathering",

    # Other nuisances
    "public drinking", "smoking", "litter", "garbage", "illegal trade",
    "street gambling", "begging", "hawker problem", "illegal hawker", "illegal shop",
    "unauthorized vendor", "illegal encroachment", "spitting", "dirty environment"
]

# --- Regex Pattern Builder ---
def build_pattern(terms):
    escaped = [re.escape(t) for t in terms]
    pattern = r'\b(?:' + '|'.join(escaped) + r')\b'
    return re.compile(pattern, flags=re.IGNORECASE)

HIGH_PATTERN = build_pattern(HIGH_TERMS)
MEDIUM_PATTERN = build_pattern(MEDIUM_TERMS)

# --- Classifier ---
def classify_urgency(text):
    text = (text or "").strip()
    if not text:
        return "Low"
    if HIGH_PATTERN.search(text):
        return "High"
    if MEDIUM_PATTERN.search(text):
        return "Medium"
    return "Low"

# --- Database Init ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact TEXT NOT NULL,
            complaint TEXT NOT NULL,
            urgency TEXT NOT NULL
        )
    """)
    conn.commit()

    # Re-classify old rows
    c.execute("SELECT id, complaint, urgency FROM complaints")
    rows = c.fetchall()
    for row_id, text, old_urg in rows:
        new_urg = classify_urgency(text)
        if new_urg != old_urg:
            c.execute("UPDATE complaints SET urgency=? WHERE id=?", (new_urg, row_id))
    conn.commit()
    conn.close()

# --- Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit_complaint():
    name = request.form.get('name', '').strip()
    contact = request.form.get('contact', '').strip()
    complaint = request.form.get('complaint', '').strip()

    if not (name and contact and complaint):
        return redirect(url_for('index'))

    urgency = classify_urgency(complaint)

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO complaints (name, contact, complaint, urgency) VALUES (?, ?, ?, ?)",
        (name, contact, complaint, urgency)
    )
    conn.commit()
    conn.close()

    return redirect(url_for('view_complaints'))

@app.route('/complaints')
def view_complaints():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, name, contact, complaint, urgency
        FROM complaints
        ORDER BY
            CASE urgency
                WHEN 'High' THEN 1
                WHEN 'Medium' THEN 2
                WHEN 'Low' THEN 3
                ELSE 4
            END,
            id DESC
    """)
    complaints = c.fetchall()
    conn.close()
    return render_template('complaints.html', complaints=complaints)

# --- Run App ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
