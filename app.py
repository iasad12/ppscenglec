import os
import re
import json
import sqlite3
import random
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory, make_response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "english_lecturer.db")
PDF_PATH = os.path.join(BASE_DIR, "English_Lecturer_Past_Papers_Categorized.pdf")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"), static_folder=os.path.join(BASE_DIR, "static"))

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/sw.js")
def service_worker():
    response = make_response(send_from_directory(os.path.join(BASE_DIR, "static"), "sw.js"))
    response.headers["Content-Type"] = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    return response

@app.route("/manifest.json")
def manifest():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "manifest.json")

@app.route("/download-pdf")
def download_pdf():
    if os.path.exists(PDF_PATH):
        return send_file(PDF_PATH, as_attachment=True, download_name="English_Lecturer_Past_Papers_Categorized.pdf")
    return jsonify({"error": "PDF not generated yet"}), 404

@app.route("/api/stats")
def api_stats():
    if not os.path.exists(DB_PATH):
        return jsonify({"total_questions": 0, "subjects": []})
        
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT COUNT(*) FROM questions")
    total_questions = c.fetchone()[0]
    
    c.execute("SELECT subject, COUNT(*) as count FROM questions GROUP BY subject ORDER BY count DESC")
    subjects = [{"subject": row["subject"], "count": row["count"]} for row in c.fetchall()]
    
    conn.close()
    return jsonify({
        "total_questions": total_questions,
        "subjects": subjects
    })

@app.route("/api/subjects")
def api_subjects():
    if not os.path.exists(DB_PATH):
        return jsonify([])
        
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT subject, COUNT(*) as count FROM questions GROUP BY subject ORDER BY count DESC")
    subjects = [{"subject": row["subject"], "count": row["count"]} for row in c.fetchall()]
    conn.close()
    return jsonify(subjects)

@app.route("/api/mock-test")
def api_mock_test():
    if not os.path.exists(DB_PATH):
        return jsonify({"error": "Database not initialized"}), 500
        
    conn = get_db()
    c = conn.cursor()
    
    # Official PPSC Lecturer English Blueprint Distribution across exact PakMCQs categories (100 MCQs: 80 English + 20 GK)
    distribution = [
        ("Famous Playwright, Poet and Others", 22),
        ("Ages, Era, Period", 10),
        ("Literary Theory and Criticism", 8),
        ("Language and Linguistics", 8),
        ("American Literature", 6),
        ("Medieval Literature and Culture", 5),
        ("English Romantic Poetry", 4),
        ("Modern Poetry and Poetics", 4),
        ("The Gothic Novel", 3),
        ("Cultural & Literary English Renaissance", 3),
        ("Cultural & Literary 18th-19th Centuries", 3),
        ("PPSC / SPSC Solved Past Papers (2011-2024)", 4),
        ("Miscellaneous Literature MCQs", 5),
        ("English Grammar & Vocabulary", 5),
        ("Pakistan Current Affairs & GK", 4),
        ("Islamic Studies", 3),
        ("Everyday Science & Math", 3)
    ]
    
    selected_questions = []
    
    for subject, count in distribution:
        c.execute("""
            SELECT id, question, options_json, correct_answer, correct_letter, explanation, submitted_by, subject, source_paper
            FROM questions
            WHERE subject = ?
            ORDER BY RANDOM()
            LIMIT ?
        """, (subject, count))
        rows = c.fetchall()
        for r in rows:
            selected_questions.append({
                "id": r["id"],
                "question": r["question"],
                "options": json.loads(r["options_json"]),
                "correct_answer": r["correct_answer"],
                "correct_letter": r["correct_letter"],
                "explanation": r["explanation"],
                "submitted_by": r["submitted_by"],
                "subject": r["subject"],
                "source_paper": r["source_paper"]
            })
            
    # Fill remaining if needed to make exactly 100
    if len(selected_questions) < 100:
        needed = 100 - len(selected_questions)
        existing_ids = tuple(q["id"] for q in selected_questions) or (-1,)
        placeholders = ",".join("?" * len(existing_ids))
        c.execute(f"""
            SELECT id, question, options_json, correct_answer, correct_letter, explanation, submitted_by, subject, source_paper
            FROM questions
            WHERE id NOT IN ({placeholders})
            ORDER BY RANDOM()
            LIMIT ?
        """, (*existing_ids, needed))
        for r in c.fetchall():
            selected_questions.append({
                "id": r["id"],
                "question": r["question"],
                "options": json.loads(r["options_json"]),
                "correct_answer": r["correct_answer"],
                "correct_letter": r["correct_letter"],
                "explanation": r["explanation"],
                "submitted_by": r["submitted_by"],
                "subject": r["subject"],
                "source_paper": r["source_paper"]
            })
            
    random.shuffle(selected_questions)
    selected_questions = selected_questions[:100]
    conn.close()
    
    return jsonify({
        "test_type": "PPSC / FPSC English Lecturer Full Mock Exam (100 MCQs)",
        "duration_minutes": 90,
        "passing_marks": 40.0,
        "negative_marking_rate": 0.25,
        "total_questions": len(selected_questions),
        "questions": selected_questions
    })

@app.route("/api/practice")
def api_practice():
    subject = request.args.get("subject", "all")
    limit = int(request.args.get("limit", 25))
    
    conn = get_db()
    c = conn.cursor()
    
    if subject == "all":
        c.execute("""
            SELECT id, question, options_json, correct_answer, correct_letter, explanation, submitted_by, subject, source_paper
            FROM questions
            ORDER BY RANDOM()
            LIMIT ?
        """, (limit,))
    else:
        c.execute("""
            SELECT id, question, options_json, correct_answer, correct_letter, explanation, submitted_by, subject, source_paper
            FROM questions
            WHERE subject = ?
            ORDER BY RANDOM()
            LIMIT ?
        """, (subject, limit))
        
    rows = c.fetchall()
    questions = []
    for r in rows:
        questions.append({
            "id": r["id"],
            "question": r["question"],
            "options": json.loads(r["options_json"]),
            "correct_answer": r["correct_answer"],
            "correct_letter": r["correct_letter"],
            "explanation": r["explanation"],
            "submitted_by": r["submitted_by"],
            "subject": r["subject"],
            "source_paper": r["source_paper"]
        })
        
    conn.close()
    return jsonify({
        "subject": subject,
        "total_questions": len(questions),
        "questions": questions
    })

@app.route("/api/search")
def api_search():
    query = request.args.get("q", "").strip()
    subject = request.args.get("subject", "all")
    page = int(request.args.get("page", 1))
    per_page = 20
    offset = (page - 1) * per_page
    
    conn = get_db()
    c = conn.cursor()
    
    sql = "SELECT id, question, options_json, correct_answer, correct_letter, explanation, submitted_by, subject, source_paper FROM questions WHERE 1=1"
    params = []
    
    if query:
        sql += " AND (question LIKE ? OR explanation LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])
        
    if subject and subject != "all":
        sql += " AND subject = ?"
        params.append(subject)
        
    count_sql = "SELECT COUNT(*) FROM (" + sql + ")"
    c.execute(count_sql, params)
    total_count = c.fetchone()[0]
    
    sql += " LIMIT ? OFFSET ?"
    params.extend([per_page, offset])
    c.execute(sql, params)
    
    questions = []
    for r in c.fetchall():
        questions.append({
            "id": r["id"],
            "question": r["question"],
            "options": json.loads(r["options_json"]),
            "correct_answer": r["correct_answer"],
            "correct_letter": r["correct_letter"],
            "explanation": r["explanation"],
            "submitted_by": r["submitted_by"],
            "subject": r["subject"],
            "source_paper": r["source_paper"]
        })
        
    conn.close()
    return jsonify({
        "total": total_count,
        "page": page,
        "per_page": per_page,
        "questions": questions
    })

@app.route("/api/submit-test", methods=["POST"])
def api_submit_test():
    data = request.json or {}
    test_type = data.get("test_type", "PPSC English Lecturer Mock Exam")
    subject = data.get("subject", "Comprehensive Literature")
    total_questions = int(data.get("total_questions", 100))
    time_taken = int(data.get("time_taken_seconds", 0))
    answers = data.get("answers", {})
    question_ids = data.get("question_ids", [])
    
    if not question_ids:
        return jsonify({"error": "No question IDs provided"}), 400
        
    conn = get_db()
    c = conn.cursor()
    
    placeholders = ",".join("?" * len(question_ids))
    c.execute(f"""
        SELECT id, question, options_json, correct_answer, correct_letter, explanation, subject, source_paper
        FROM questions
        WHERE id IN ({placeholders})
    """, question_ids)
    
    rows = {r["id"]: dict(r) for r in c.fetchall()}
    conn.close()
    
    correct_count = 0
    incorrect_count = 0
    unattempted_count = 0
    detailed_review = []
    subject_stats = {}
    
    for q_id in question_ids:
        q_info = rows.get(q_id)
        if not q_info:
            continue
            
        user_ans = answers.get(str(q_id)) or answers.get(q_id) or ""
        correct_ans = q_info["correct_answer"]
        
        is_attempted = bool(user_ans and user_ans.strip())
        is_correct = (user_ans.strip().lower() == correct_ans.strip().lower()) if is_attempted else False
        
        if is_correct:
            correct_count += 1
        elif is_attempted:
            incorrect_count += 1
        else:
            unattempted_count += 1
            
        subj = q_info["subject"]
        if subj not in subject_stats:
            subject_stats[subj] = {"total": 0, "correct": 0, "incorrect": 0, "unattempted": 0}
        subject_stats[subj]["total"] += 1
        if is_correct:
            subject_stats[subj]["correct"] += 1
        elif is_attempted:
            subject_stats[subj]["incorrect"] += 1
        else:
            subject_stats[subj]["unattempted"] += 1
            
        detailed_review.append({
            "id": q_id,
            "question": q_info["question"],
            "options": json.loads(q_info["options_json"]),
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "correct_letter": q_info["correct_letter"],
            "is_attempted": is_attempted,
            "is_correct": is_correct,
            "explanation": q_info["explanation"],
            "subject": subj
        })
        
    # PPSC Negative Marking Formula:
    # Score = (Correct * 1.0) - (Incorrect * 0.25)
    negative_deduction = round(incorrect_count * 0.25, 2)
    raw_score = correct_count * 1.0
    net_score = round(max(0.0, raw_score - negative_deduction), 2)
    
    percentage = round((net_score / total_questions * 100), 2) if total_questions > 0 else 0
    passed = 1 if net_score >= 40.0 else 0
    
    return jsonify({
        "net_score": net_score,
        "raw_score": raw_score,
        "negative_deduction": negative_deduction,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "unattempted_count": unattempted_count,
        "total_questions": total_questions,
        "percentage": percentage,
        "passed": bool(passed),
        "passing_threshold": 40.0,
        "negative_rate": 0.25,
        "time_taken_seconds": time_taken,
        "subject_stats": subject_stats,
        "detailed_review": detailed_review
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)
