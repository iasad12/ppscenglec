import os
import json
import re
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(BASE_DIR, "english_lecturer_mcqs.json")
DB_PATH = os.path.join(BASE_DIR, "english_lecturer.db")

def un_mangle(text):
    if not text:
        return ""
    t = str(text)
    
    # 1. Un-mangle single character quoting
    for _ in range(6):
        t = re.sub(r'[\'"]([a-zA-Z0-9_\-\?\.,:;!\(\)\/])[\'"]', r'\1', t)

    # 2. Clean isolated leading or trailing quotes on words
    t = re.sub(r"([a-zA-Z0-9]{2,})'(\s|$|\?|\.|\,)", r"\1\2", t)
    t = re.sub(r"(\s|^|\()'(?=[a-zA-Z0-9]{2,})", r"\1", t)
    t = re.sub(r"([a-zA-Z0-9]{2,})\"(\s|$|\?|\.|\,)", r"\1\2", t)
    t = re.sub(r"(\s|^|\()\"(?=[a-zA-Z0-9]{2,})", r"\1", t)

    # 3. Clean multiple quotes
    t = re.sub(r"'+", "'", t)
    t = re.sub(r'"+', '"', t)
    t = t.replace(" '", " ").replace("' ", " ")
    
    # 4. Strip non-latin artifacts
    t = re.sub(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def clean_dataset():
    with open(DATA_JSON, "r", encoding="utf-8") as f:
        mcqs = json.load(f)

    cleaned = []
    seen = set()

    for q in mcqs:
        q_text = un_mangle(q.get("question", ""))
        key = q_text.lower().strip()
        if not q_text or key in seen:
            continue
        seen.add(key)

        opts = []
        for o in q.get("options", []):
            opts.append({
                "letter": o.get("letter", ""),
                "text": un_mangle(o.get("text", "")),
                "is_correct": o.get("is_correct", False)
            })

        sub = un_mangle(q.get("submitted_by", ""))
        if not sub or sub == '"""' or "PakMCQs" in sub:
            sub = "PakMCQs Community Contributor"

        src = un_mangle(q.get("source_paper", ""))
        if not src:
            src = "PakMCQs (pakmcqs.com)"

        cleaned.append({
            "id": q.get("id") or (abs(hash(q_text)) % 10000000),
            "question": q_text,
            "options": opts,
            "correct_answer": un_mangle(q.get("correct_answer", "")),
            "correct_letter": q.get("correct_letter", "").strip(),
            "explanation": un_mangle(q.get("explanation", "")),
            "submitted_by": sub,
            "subject": q.get("subject", "English Literature"),
            "source_paper": src,
            "source_url": q.get("source_url", "https://pakmcqs.com")
        })

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False, indent=2)

    print(f"[+] Total cleaned MCQs: {len(cleaned)}")

    # Update SQLite database
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS questions")
    c.execute("""
    CREATE TABLE questions (
        id INTEGER PRIMARY KEY,
        question TEXT NOT NULL,
        options_json TEXT,
        correct_answer TEXT,
        correct_letter TEXT,
        explanation TEXT,
        submitted_by TEXT,
        subject TEXT,
        source_paper TEXT,
        source_url TEXT
    )
    """)
    rows = []
    for idx, q in enumerate(cleaned, 1):
        rows.append((
            q.get("id") or idx,
            q["question"],
            json.dumps(q.get("options", []), ensure_ascii=False),
            q.get("correct_answer", ""),
            q.get("correct_letter", ""),
            q.get("explanation", ""),
            q.get("submitted_by", "PakMCQs Community Contributor"),
            q.get("subject", "English Literature"),
            q.get("source_paper", "PakMCQs (pakmcqs.com)"),
            q.get("source_url", "")
        ))
    c.executemany("""
    INSERT INTO questions (id, question, options_json, correct_answer, correct_letter, explanation, submitted_by, subject, source_paper, source_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    print(f"[+] Synced {len(rows)} clean questions to SQLite: {DB_PATH}")

if __name__ == "__main__":
    clean_dataset()
