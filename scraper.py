import os
import re
import sys
import json
import time
import sqlite3
import urllib.request
import ssl
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(BASE_DIR, "english_lecturer_mcqs.json")
DB_PATH = os.path.join(BASE_DIR, "english_lecturer.db")

SSL_CTX = ssl.create_default_context()
SSL_CTX.set_ciphers('DEFAULT@SECLEVEL=1')
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
}

# ALL 19 PAKMCQS ENGLISH LITERATURE SUBCATEGORIES + MAIN + GK
ALL_CATEGORIES = [
    # 1. All 19 Table Subcategories
    ("https://pakmcqs.com/category/english-literature-mcqs/famous-playwright-poet-and-others", 97, "Drama & Theatre"),
    ("https://pakmcqs.com/category/english-literature-mcqs/ages-era-period", 55, "History of English Literature"),
    ("https://pakmcqs.com/category/english-literature-mcqs/american-literature", 34, "American & World Literature"),
    ("https://pakmcqs.com/category/english-literature-mcqs/miscellaneous-literature-mcqs", 33, "English Literature"),
    ("https://pakmcqs.com/category/english-literature-mcqs/literary-theory-and-criticism", 23, "Literary Theory & Criticism"),
    ("https://pakmcqs.com/category/english-literature-mcqs/language-and-linguistics", 22, "Linguistics & Phonetics"),
    ("https://pakmcqs.com/category/english-literature-mcqs/medieval-literature-and-culture", 20, "History of English Literature"),
    ("https://pakmcqs.com/category/english-literature-mcqs/introduction-to-literary-studies", 10, "English Literature"),
    ("https://pakmcqs.com/category/english-literature-mcqs/introduction-to-literary-theory", 10, "Literary Theory & Criticism"),
    ("https://pakmcqs.com/category/english-literature-mcqs/cultural-and-literary-english-renaissance", 10, "History of English Literature"),
    ("https://pakmcqs.com/category/english-literature-mcqs/cultural-and-literary-18th-19th-centuries", 10, "History of English Literature"),
    ("https://pakmcqs.com/category/english-literature-mcqs/cultural-and-literary-in-modernity", 10, "History of English Literature"),
    ("https://pakmcqs.com/category/english-literature-mcqs/the-gothic-novel", 10, "Novels, Fiction & Prose"),
    ("https://pakmcqs.com/category/english-literature-mcqs/english-romantic-poetry", 10, "Classical & Romantic Poetry"),
    ("https://pakmcqs.com/category/english-literature-mcqs/modern-poetry-and-poetics", 10, "Modern & Post-Modern Poetry"),
    ("https://pakmcqs.com/category/english-literature-mcqs/african-american-literature", 10, "American & World Literature"),
    ("https://pakmcqs.com/category/english-literature-mcqs/the-victorian-novel", 1, "Novels, Fiction & Prose"),
    ("https://pakmcqs.com/category/english-literature-mcqs/restoration-eighteenth-century-drama", 1, "Drama & Theatre"),
    ("https://pakmcqs.com/category/english-literature-mcqs/medieval-women-writers", 1, "History of English Literature"),

    # 2. Main Comprehensive English Literature Category (374 pages)
    ("https://pakmcqs.com/category/english-literature-mcqs", 150, "English Literature"),

    # 3. English Grammar & Vocabulary
    ("https://pakmcqs.com/category/english-mcqs", 30, "Grammar, Vocabulary & Figures of Speech"),

    # 4. 20% PPSC General Ability Quota
    ("https://pakmcqs.com/category/pakistan-current-affairs-mcqs", 20, "General Knowledge & Pakistan Studies"),
    ("https://pakmcqs.com/category/islamic-studies-mcqs", 15, "General Knowledge & Pakistan Studies"),
    ("https://pakmcqs.com/category/everyday-science-mcqs", 15, "General Knowledge & Pakistan Studies")
]

def classify_literature_subject(question_text, explanation_text="", source_cat=""):
    combined = f"{question_text} {explanation_text} {source_cat}".lower()
    
    # 1. Linguistics & Phonetics
    ling_keywords = [
        "linguistic", "phoneme", "allophone", "phonology", "phonetics", "morpheme", "morphology", "syntax", "syntactic",
        "semantics", "pragmatics", "sociolinguistic", "chomsky", "saussure", "langue", "parole", "competence", "performance",
        "diphthong", "plosive", "fricative", "bilabial", "velar", "nasal", "vocal cord", "articulation", "idiolect", "dialect",
        "pidgin", "creole", "isogloss", "lingua franca", "diglossia", "speech act", "semiotic", "synchronic", "diachronic",
        "minimal pair", "syllable", "stress", "intonation", "consonant", "vowel"
    ]
    if any(k in combined for k in ling_keywords):
        return "Linguistics & Phonetics"
        
    # 2. Literary Theory & Criticism
    crit_keywords = [
        "criticism", "literary theory", "poetics", "aristotle", "catharsis", "hamartia", "anagnorisis", "peripeteia",
        "mimesis", "longinus", "sublime", "sir philip sidney", "apology for poetry", "dryden", "essay on dramatic poesy",
        "dr. johnson", "preface to shakespeare", "biographia literaria", "fancy and imagination", "preface to lyrical ballads",
        "matthew arnold", "touchstone method", "t.s. eliot", "objective correlative", "dissociation of sensibility", "unified sensibility",
        "tradition and the individual talent", "structuralism", "post-structuralism", "deconstruction", "derrida", "foucault",
        "post-colonial", "orientalism", "edward said", "feminism", "marxist criticism", "new criticism", "close reading",
        "pathetic fallacy", "intentional fallacy", "affective fallacy"
    ]
    if any(k in combined for k in crit_keywords):
        return "Literary Theory & Criticism"
        
    # 3. Drama & Theatre
    drama_keywords = [
        "drama", "play", "theatre", "tragedy", "comedy", "tragicomedy", "farce", "melodrama", "chorus", "soliloquy", "aside",
        "shakespeare", "hamlet", "macbeth", "king lear", "othello", "tempest", "twelfth night", "as you like it",
        "merchant of venice", "romeo and juliet", "midsummer night", "julius caesar", "marlowe", "dr. faustus", "tamburlaine",
        "jew of malta", "ben jonson", "every man in his humour", "volpone", "alchemist", "john webster", "duchess of malfi",
        "white devil", "g.b. shaw", "pygmalion", "man and superman", "arms and the man", "saint joan", "henrik ibsen", "doll's house",
        "ghosts", "hedda gabler", "samuel beckett", "waiting for godot", "endgame", "theatre of the absurd", "arthur miller",
        "death of a salesman", "crucible", "harold pinter", "caretaker", "birthday party", "homecoming", "sophocles", "oedipus"
    ]
    if any(k in combined for k in drama_keywords):
        return "Drama & Theatre"
        
    # 4. Classical & Romantic Poetry
    poetry_keywords = [
        "poet", "poem", "stanza", "sonnet", "ode", "elegy", "epic", "ballad", "heroic couplet", "blank verse", "rhyme", "meter",
        "chaucer", "canterbury tales", "spenser", "faerie queene", "milton", "paradise lost", "paradise regained", "samson agonistes",
        "john donne", "metaphysical", "holy sonnets", "flea", "valediction", "alexander pope", "rape of the lock", "dunciad",
        "william blake", "songs of innocence", "songs of experience", "wordsworth", "prelude", "tintern abbey", "daffodils",
        "coleridge", "rime of the ancient mariner", "kubla khan", "christabel", "keats", "ode to a nightingale", "ode on a grecian urn",
        "hyperion", "endymion", "p.b. shelley", "adomais", "adonais", "ode to the west wind", "to a skylark", "prometheus unbound",
        "lord byron", "don juan", "childe harold"
    ]
    if any(k in combined for k in poetry_keywords):
        return "Classical & Romantic Poetry"
        
    # 5. Modern & Post-Modern Poetry
    mod_poetry_keywords = [
        "w.b. yeats", "sailing to byzantium", "second coming", "easter 1916", "wild swans at coole", "t.s. eliot", "waste land",
        "love song of j. alfred prufrock", "four quartets", "ash wednesday", "philip larkin", "whitsun weddings", "church going",
        "ted hughes", "hawk roosting", "crow", "sylvia plath", "daddy", "lady lazarus", "ariel", "robert frost", "stopping by woods",
        "road not taken", "mending wall", "birches", "seamus heaney", "w.h. auden", "in memory of w.b. yeats", "shield of achilles",
        "ezra pound", "imagism", "canto", "modernist poetry"
    ]
    if any(k in combined for k in mod_poetry_keywords):
        return "Modern & Post-Modern Poetry"

    # 6. Novels, Fiction & Prose
    novel_keywords = [
        "novel", "novelist", "prose", "picaresque", "gothic", "epistolary", "francis bacon", "bacon's essays", "jonathan swift",
        "gulliver's travels", "tale of a tub", "modest proposal", "henry fielding", "tom jones", "joseph andrews", "jane austen",
        "pride and prejudice", "sense and sensibility", "emma", "mansfield park", "persuasion", "northanger abbey", "charlotte bronte",
        "jane eyre", "emily bronte", "wuthering heights", "charles dickens", "great expectations", "oliver twist", "david copperfield",
        "tale of two cities", "bleak house", "hard times", "george eliot", "middlemarch", "mill on the floss", "silas marner",
        "adam bede", "thomas hardy", "tess of the d'urbervilles", "jude the obscure", "mayor of casterbridge", "return of the native",
        "virginia woolf", "mrs dalloway", "to the lighthouse", "orlando", "stream of consciousness", "james joyce", "ulysses",
        "portrait of the artist", "dubliners", "george orwell", "animal farm", "nineteen eighty-four", "1984", "e.m. forster", "passage to india"
    ]
    if any(k in combined for k in novel_keywords):
        return "Novels, Fiction & Prose"
        
    # 7. American & World Literature
    american_keywords = [
        "american literature", "hemingway", "old man and the sea", "farewell to arms", "for whom the bell tolls", "william faulkner",
        "sound and the fury", "as i lay dying", "f. scott fitzgerald", "great gatsby", "herman melville", "moby dick", "mark twain",
        "huckleberry finn", "tom sawyer", "nathaniel hawthorne", "scarlet letter", "edgar allan poe", "raven", "walt whitman",
        "leaves of grass", "emily dickinson", "chinua achebe", "things fall apart", "wole soyinka", "salman rushdie", "midnight's children",
        "arundhati roy", "god of small things", "bapsi sidhwa", "ice-candy man", "kamila shamsie", "mohsin hamid", "relicant fundamentalist"
    ]
    if any(k in combined for k in american_keywords):
        return "American & World Literature"
        
    # 8. Grammar, Figures of Speech & Vocabulary
    grammar_keywords = [
        "synonym", "antonym", "figure of speech", "metaphor", "simile", "personification", "hyperbole", "oxymoron", "irony",
        "alliteration", "assonance", "consonance", "onomatopoeia", "synecdoche", "metonymy", "pun", "idiom", "preposition",
        "passive voice", "active voice", "spelling", "analogy", "clause", "phrase", "parts of speech", "sentence"
    ]
    if any(k in combined for k in grammar_keywords):
        return "Grammar, Vocabulary & Figures of Speech"
        
    # 9. General Knowledge & Pakistan Studies (20% quota)
    gk_keywords = [
        "pakistan", "constitution", "islamabad", "lahore", "karachi", "quaid", "allama iqbal", "prophet", "quran", "surah",
        "namaz", "salat", "hajj", "zakat", "atmosphere", "nitrogen", "oxygen", "solar system", "planet", "capital of", "currency of",
        "president", "prime minister", "current affairs", "unsc", "who", "united nations"
    ]
    if any(k in combined for k in gk_keywords):
        return "General Knowledge & Pakistan Studies"
        
    return "English Literature"

def fetch_pakmcqs_page(url, page_num=1, default_cat="English Literature"):
    p_url = f"{url}/page/{page_num}" if page_num > 1 else url
    req = urllib.request.Request(p_url, headers=HEADERS)
    
    try:
        with urllib.request.urlopen(req, context=SSL_CTX, timeout=8) as r:
            html = r.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            articles = soup.find_all('article') or soup.find_all('div', class_='post')
            items = []
            
            for art in articles:
                title_el = art.find('h2') or art.find('h3') or art.find('a', class_='post-title')
                if not title_el:
                    continue
                q_text = title_el.get_text(strip=True)
                q_text = re.sub(r'^\d+[\.\)]\s*', '', q_text).strip()
                
                excerpt = art.find('div', class_='excerpt') or art
                
                options = []
                correct_answer = ""
                correct_letter = ""
                
                strong_texts = [s.get_text(strip=True) for s in excerpt.find_all('strong')]
                
                p_tags = excerpt.find_all('p')
                opt_block = ""
                for p in p_tags:
                    t = p.get_text(separator="\n", strip=True)
                    if any(re.search(r'^[A-D]\.', line.strip()) for line in t.split('\n')):
                        opt_block = t
                        break
                        
                if not opt_block:
                    opt_block = excerpt.get_text(separator="\n", strip=True)
                    
                lines = [l.strip() for l in opt_block.split('\n') if l.strip()]
                
                for line in lines:
                    m = re.match(r'^([A-E])[\.\)]\s*(.+)$', line)
                    if m:
                        let = m.group(1).upper()
                        opt_val = m.group(2).strip()
                        is_corr = False
                        for st in strong_texts:
                            if opt_val.lower() in st.lower() or f"{let}." in st or f"{let})" in st:
                                is_corr = True
                                break
                        options.append({
                            "letter": let,
                            "text": opt_val,
                            "is_correct": is_corr
                        })
                        if is_corr:
                            correct_answer = opt_val
                            correct_letter = let
                            
                if options and not correct_answer:
                    for opt in options:
                        if any(opt["text"].lower() in st.lower() for st in strong_texts if "submitted" not in st.lower()):
                            opt["is_correct"] = True
                            correct_answer = opt["text"]
                            correct_letter = opt["letter"]
                            break
                            
                if not options or len(options) < 2:
                    continue
                    
                if not correct_answer:
                    options[0]["is_correct"] = True
                    correct_answer = options[0]["text"]
                    correct_letter = options[0]["letter"]
                    
                subject = classify_literature_subject(q_text, "", default_cat)
                
                items.append({
                    "id": abs(hash(q_text)) % 10000000,
                    "question": q_text,
                    "options": options,
                    "correct_answer": correct_answer,
                    "correct_letter": correct_letter,
                    "explanation": "",
                    "subject": subject,
                    "source_paper": "PakMCQs English Literature",
                    "source_url": p_url
                })
                
            return items
    except Exception:
        return []

def scrape_and_compile():
    print("[*] Starting Full PPSC English Literature Harvester (All 19 Categories)...", flush=True)
    all_mcqs = {}
    
    # Load existing if available to preserve
    if os.path.exists(DATA_JSON):
        try:
            with open(DATA_JSON, "r", encoding="utf-8") as f:
                existing = json.load(f)
                for q in existing:
                    all_mcqs[q["question"].strip().lower()] = q
            print(f"[+] Loaded {len(all_mcqs)} existing MCQs.", flush=True)
        except Exception:
            pass
            
    tasks = []
    for cat_url, max_p, default_subj in ALL_CATEGORIES:
        for p in range(1, max_p + 1):
            tasks.append((cat_url, p, default_subj))
            
    print(f"[*] Fetching {len(tasks)} category pages with 10 workers...", flush=True)
    
    completed = 0
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_pakmcqs_page, url, p, subj): (url, p) for url, p, subj in tasks}
        for f in as_completed(futures):
            completed += 1
            if completed % 25 == 0 or completed == len(tasks):
                print(f"[*] Processed {completed}/{len(tasks)} pages... ({len(all_mcqs)} unique MCQs in master bank)", flush=True)
            try:
                page_items = f.result()
                for item in page_items:
                    k = item["question"].strip().lower()
                    if k not in all_mcqs:
                        all_mcqs[k] = item
            except Exception:
                pass
                
    results = list(all_mcqs.values())
    print(f"\n[+] Full Scraping Complete! Total Consolidated Unique MCQs: {len(results)}", flush=True)
    
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"[+] Saved JSON dataset to: {DATA_JSON}", flush=True)
    
    init_db(results)

def init_db(mcqs):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY,
        question TEXT NOT NULL,
        options_json TEXT,
        correct_answer TEXT,
        correct_letter TEXT,
        explanation TEXT,
        subject TEXT,
        source_paper TEXT,
        source_url TEXT
    )
    """)
    c.execute("DELETE FROM questions")
    
    rows = []
    for idx, q in enumerate(mcqs, 1):
        rows.append((
            q.get("id") or idx,
            q["question"],
            json.dumps(q.get("options", []), ensure_ascii=False),
            q.get("correct_answer", ""),
            q.get("correct_letter", ""),
            q.get("explanation", ""),
            q.get("subject", "English Literature"),
            q.get("source_paper", ""),
            q.get("source_url", "")
        ))
        
    c.executemany("""
    INSERT INTO questions (id, question, options_json, correct_answer, correct_letter, explanation, subject, source_paper, source_url)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    
    conn.commit()
    conn.close()
    print(f"[+] Synced {len(rows)} questions to SQLite database: {DB_PATH}", flush=True)

if __name__ == "__main__":
    scrape_and_compile()
