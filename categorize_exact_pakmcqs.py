import os
import json
import re
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(BASE_DIR, "english_lecturer_mcqs.json")
DB_PATH = os.path.join(BASE_DIR, "english_lecturer.db")

PAKMCQS_CATEGORY_MAP = [
    # (slug/keyword, Declared Category Name)
    ("famous-playwright-poet-and-others", "Famous Playwright, Poet and Others"),
    ("ages-era-period", "Ages, Era, Period"),
    ("american-literature", "American Literature"),
    ("literary-theory-and-criticism", "Literary Theory and Criticism"),
    ("introduction-to-literary-studies", "Introduction to Literary Studies"),
    ("introduction-to-literary-theory", "Introduction to Literary Theory"),
    ("cultural-and-literary-english-renaissance", "Cultural & Literary English Renaissance"),
    ("cultural-and-literary-18th-19th-centuries", "Cultural & Literary 18th-19th Centuries"),
    ("cultural-and-literary-in-modernity", "Cultural & Literary in Modernity"),
    ("medieval-literature-and-culture", "Medieval Literature and Culture"),
    ("medieval-women-writers", "Medieval Women Writers"),
    ("the-gothic-novel", "The Gothic Novel"),
    ("english-romantic-poetry", "English Romantic Poetry"),
    ("modern-poetry-and-poetics", "Modern Poetry and Poetics"),
    ("the-victorian-novel", "The Victorian Novel"),
    ("african-american-literature", "African-American Literature"),
    ("restoration-eighteenth-century-drama", "Restoration & 18th-Century Drama"),
    ("language-and-linguistics", "Language and Linguistics"),
    ("miscellaneous-literature-mcqs", "Miscellaneous Literature MCQs"),
    ("english-mcqs", "English Grammar & Vocabulary"),
    ("pakistan-current-affairs", "Pakistan Current Affairs & GK"),
    ("islamic-studies", "Islamic Studies"),
    ("everyday-science", "Everyday Science & Math")
]

def map_exact_pakmcqs_category(q):
    source_url = q.get("source_url", "").lower()
    source_paper = q.get("source_paper", "").lower()
    q_text = q.get("question", "").lower()
    exp_text = q.get("explanation", "").lower()

    if "past paper" in source_paper or "ppsc" in source_paper or "spsc" in source_paper or "kppsc" in source_paper:
        return "PPSC / SPSC Solved Past Papers (2011-2024)"

    for slug, cat_name in PAKMCQS_CATEGORY_MAP:
        if slug in source_url:
            return cat_name

    # Content-based classification into exact PakMCQs subcategories for general pages
    if any(k in q_text for k in ["linguistic", "phoneme", "phonology", "phonetics", "morpheme", "syntax", "semantics", "pragmatics", "saussure", "chomsky", "pidgin", "creole", "consonant", "vowel", "diglossia", "speech act"]):
        return "Language and Linguistics"
        
    if any(k in q_text for k in ["poetics", "criticism", "catharsis", "hamartia", "aristotle", "longinus", "dryden", "preface to lyrical ballads", "touchstone method", "objective correlative", "structuralism", "deconstruction", "orientalism", "edward said", "pathetic fallacy"]):
        return "Literary Theory and Criticism"

    if any(k in q_text for k in ["shakespeare", "marlowe", "ben jonson", "webster", "g.b. shaw", "ibsen", "beckett", "milton", "donne", "chaucer", "pope", "wordsworth", "keats", "shelley", "byron", "tennyson", "browning"]):
        return "Famous Playwright, Poet and Others"

    if any(k in q_text for k in ["hemingway", "faulkner", "fitzgerald", "dickinson", "frost", "whitman", "melville", "mark twain", "edgar allan poe", "american"]):
        return "American Literature"

    if any(k in q_text for k in ["gothic", "castle of otranto", "frankenstein", "dracula", "radcliffe"]):
        return "The Gothic Novel"

    if any(k in q_text for k in ["victorian", "dickens", "george eliot", "hardy", "thackeray", "trollope"]):
        return "The Victorian Novel"

    if any(k in q_text for k in ["romantic", "wordsworth", "coleridge", "keats", "shelley", "byron", "lyrical ballads"]):
        return "English Romantic Poetry"

    if any(k in q_text for k in ["modern poetry", "t.s. eliot", "yeats", "larkin", "sylvia plath", "ted hughes", "auden", "ezra pound", "imagism"]):
        return "Modern Poetry and Poetics"

    if any(k in q_text for k in ["renaissance", "elizabethan", "spenser", "sidney", "university wits"]):
        return "Cultural & Literary English Renaissance"

    if any(k in q_text for k in ["medieval", "beowulf", "middle english", "piers plowman", "gawain", "norman conquest", "anglo-saxon"]):
        return "Medieval Literature and Culture"

    if any(k in q_text for k in ["restoration", "congreve", "wycherley", "dryden", "comedy of manners"]):
        return "Restoration & 18th-Century Drama"

    if any(k in q_text for k in ["age", "period", "century", "augustan", "jacobean", "caroline"]):
        return "Ages, Era, Period"

    if any(k in q_text for k in ["synonym", "antonym", "preposition", "passive voice", "active voice", "idiom", "analogy"]):
        return "English Grammar & Vocabulary"

    if any(k in q_text for k in ["pakistan", "islam", "prophet", "quran", "science", "capital of", "president"]):
        return "General Knowledge & Pakistan Studies"

    return "Miscellaneous Literature MCQs"

def run_categorization():
    with open(DATA_JSON, "r", encoding="utf-8") as f:
        mcqs = json.load(f)

    category_counts = {}
    updated_mcqs = []

    for q in mcqs:
        exact_cat = map_exact_pakmcqs_category(q)
        q["subject"] = exact_cat
        category_counts[exact_cat] = category_counts.get(exact_cat, 0) + 1
        updated_mcqs.append(q)

    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(updated_mcqs, f, ensure_ascii=False, indent=2)

    print("=== EXACT PAKMCQS CATEGORY DISTRIBUTION ===")
    for cat, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {cat}: {count} MCQs")

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
    for idx, q in enumerate(updated_mcqs, 1):
        rows.append((
            q.get("id") or idx,
            q["question"],
            json.dumps(q.get("options", []), ensure_ascii=False),
            q.get("correct_answer", ""),
            q.get("correct_letter", ""),
            q.get("explanation", ""),
            q.get("submitted_by", "PakMCQs Community Contributor"),
            q.get("subject", "Miscellaneous Literature MCQs"),
            q.get("source_paper", "PakMCQs (pakmcqs.com)"),
            q.get("source_url", "")
        ))
    c.executemany("""
    INSERT INTO questions (id, question, options_json, correct_answer, correct_letter, explanation, submitted_by, subject, source_paper, source_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    conn.commit()
    conn.close()
    print(f"\n[+] Successfully updated {len(rows)} questions in SQLite database with exact PakMCQs categories.")

if __name__ == "__main__":
    run_categorization()
