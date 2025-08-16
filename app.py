from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
import re

app = Flask(__name__)

# Database path (absolute, predictable)
BASEDIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASEDIR, "complaints.db")

# --- Keyword lists (expanded) ---
HIGH_TERMS = [
    "murder", "murdered", "kill", "killed", "killing", "stab", "stabbing", "stabbed", "knife",
    "gun", "firearm", "shoot", "shooting", "shooter", "gunfire", "bomb", "explosion", "blast",
    "terror", "terrorist", "hostage", "abduct", "abduction", "kidnap", "kidnapping",
    "rape", "sexual assault", "sexual harassment", "sexual-offense", "molestation", "weapon",
    "arson", "set on fire", "attack", "attacked", "threaten", "threat", "threatened",
    "hijack", "hijacking", "massacre", "lynch"
]

MEDIUM_TERMS = [
    "theft", "steal", "stolen", "robbery", "robbed", "rob", "snatch", "snatched", "snatching",
    "pickpocket", "vandal", "vandalism", "vandalised", "vandalized", "damage", "vandalise",
    "fraud", "scam", "scammed", "harass", "harassment", "molest", "assault", "fight", "brawl",
    "intoxicated", "drunk", "drinking", "drunk driving", "hit and run", "accident", "missing",
    "lost", "lost item", "parking", "noise", "loud music", "nuisance", "protest", "block road",
    "public drinking", "smoking", "litter", "garbage", "illegal parking", "trespass", "disturbance",
    "begging", "petty theft", "snatcher", "suspicious person"
]

# Build regex patterns using word boundaries to avoid partial matches
def build_pattern(terms):
    # Escape terms so special characters are safe; join with |
    escaped = [re.escape(t) for t in terms]
    # \b ensures word boundaries (works with multi-word terms too)
    pattern = r'\b(?:' + '|'.join(escaped) + r')\b'
    return re.compile(pattern, flags=re.IGNORECASE)

HIGH_PATTERN = build_pattern(HIGH_TERMS)
MEDIUM_PATTERN = build_pattern(MEDIUM_TERMS)

# --- Database initialization and re-classification of existing rows ---
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

    # Re-classify existing rows (so older entries get updated with new keyword lists)
    c.execute("SELECT id, complaint, urgency FROM complaints")
    rows = c.fetchall()
    updated = 0
    for r in rows:
        row_id, text, old_urg = r
        new_urg = classify_urgency(text)
        if new_urg != old_urg:
            c.execute("UPDATE complaints SET urgency=? WHERE id=?", (new_urg, row_id))
            updated += 1

    if updated:
        conn.commit()
    conn.close()
    if updated:
        print(f"[init_db] Re-classified {updated} existing complaint(s) using updated keywords.")

# --- Classifier using regex patterns ---
def classify_urgency(text):
    text = (text or "").strip()
    if not text:
        return "Low"
    # High priority checks first
    if HIGH_PATTERN.search(text):
        return "High"
    if MEDIUM_PATTERN.search(text):
        return "Medium"
    return "Low"

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

# --- Start ---
if __name__ == '__main__':
    init_db()
    app.run(debug=True)
