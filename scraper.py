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
    ("https://pakmcqs.com/category/english-literature-mcqs", 150, "English Literature"),
    ("https://pakmcqs.com/category/english-mcqs", 30, "Grammar, Vocabulary & Figures of Speech"),
    ("https://pakmcqs.com/category/pakistan-current-affairs-mcqs", 20, "General Knowledge & Pakistan Studies"),
    ("https://pakmcqs.com/category/islamic-studies-mcqs", 15, "General Knowledge & Pakistan Studies"),
    ("https://pakmcqs.com/category/everyday-science-mcqs", 15, "General Knowledge & Pakistan Studies")
]

def clean_text_formatting(text):
    if not text:
        return ""
    t = str(text)
    t = t.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    t = t.replace('\ufffd', "'").replace('', "'")
    t = re.sub(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+', '', t)
    t = re.sub(r'<[^>]+>', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

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
                raw_q = title_el.get_text(strip=True)
                raw_q = re.sub(r'^\d+[\.\)]\s*', '', raw_q).strip()
                q_text = clean_text_formatting(raw_q)
                
                excerpt = art.find('div', class_='excerpt') or art
                
                # Extract Contributor / Submitted by
                submitted_by = ""
                sub_p = excerpt.find(lambda e: e.name == 'p' and 'Submitted' in e.get_text())
                if sub_p:
                    st_name = sub_p.find('strong')
                    if st_name:
                        submitted_by = clean_text_formatting(st_name.get_text(strip=True))
                    else:
                        submitted_by = clean_text_formatting(sub_p.get_text(strip=True).replace('Submitted by:', '').strip())
                if not submitted_by:
                    submitted_by = "PakMCQs Community Contributor"
                
                options = []
                correct_answer = ""
                correct_letter = ""
                
                strong_texts = [clean_text_formatting(s.get_text(strip=True)) for s in excerpt.find_all('strong')]
                
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
                        opt_val = clean_text_formatting(m.group(2).strip())
                        is_corr = False
                        for st in strong_texts:
                            if (opt_val.lower() in st.lower() or f"{let}." in st or f"{let})" in st) and "submitted" not in st.lower():
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
                    "submitted_by": submitted_by,
                    "subject": subject,
                    "source_paper": "PakMCQs (pakmcqs.com)",
                    "source_url": p_url
                })
                
            return items
    except Exception:
        return []

# Solved past papers extracted from the user's PDF (2011-2024)
PDF_PAST_PAPERS_MCQS = [
    # SPSC 2023
    {"question": "An auxiliary language which arises to fulfil certain limited communication needs among people who have no common language is known as?", "options": [{"letter": "A", "text": "Lingua Franca", "is_correct": False}, {"letter": "B", "text": "Creole", "is_correct": False}, {"letter": "C", "text": "Pidgin", "is_correct": True}, {"letter": "D", "text": "None of these", "is_correct": False}], "correct_answer": "Pidgin", "correct_letter": "C", "explanation": "A pidgin is a simplified language developed for communication between groups with no common tongue.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Linguistics & Phonetics", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "'Speech Act Theory' was developed by?", "options": [{"letter": "A", "text": "William Labov", "is_correct": False}, {"letter": "B", "text": "Piaget", "is_correct": False}, {"letter": "C", "text": "J.L. Austin", "is_correct": True}, {"letter": "D", "text": "None of these", "is_correct": False}], "correct_answer": "J.L. Austin", "correct_letter": "C", "explanation": "J.L. Austin introduced Speech Act Theory in 'How to Do Things with Words' (1962).", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Linguistics & Phonetics", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "The term 'Diglossia' was introduced into linguistics by?", "options": [{"letter": "A", "text": "William Labov", "is_correct": False}, {"letter": "B", "text": "Baker", "is_correct": False}, {"letter": "C", "text": "Charles Ferguson", "is_correct": True}, {"letter": "D", "text": "None of these", "is_correct": False}], "correct_answer": "Charles Ferguson", "correct_letter": "C", "explanation": "Charles Ferguson introduced Diglossia in 1959.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Linguistics & Phonetics", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Which among the following is an example of an acronym?", "options": [{"letter": "A", "text": "Smog", "is_correct": False}, {"letter": "B", "text": "UNESCO", "is_correct": True}, {"letter": "C", "text": "Buzz", "is_correct": False}, {"letter": "D", "text": "Edit", "is_correct": False}], "correct_answer": "UNESCO", "correct_letter": "B", "explanation": "UNESCO is an acronym pronounced as a single word from initial letters.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Linguistics & Phonetics", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Consonants articulated by raising the back of the tongue towards the soft palate are called?", "options": [{"letter": "A", "text": "Post-alveolar", "is_correct": False}, {"letter": "B", "text": "Alveolar", "is_correct": False}, {"letter": "C", "text": "Palatal", "is_correct": False}, {"letter": "D", "text": "Velar", "is_correct": True}], "correct_answer": "Velar", "correct_letter": "D", "explanation": "Velar consonants (/k/, /g/, /ŋ/) are produced at the velum (soft palate).", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Linguistics & Phonetics", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Which is the famous elegy written by Shelley on the death of John Keats?", "options": [{"letter": "A", "text": "In Memoriam", "is_correct": False}, {"letter": "B", "text": "Lycidas", "is_correct": False}, {"letter": "C", "text": "Adonais", "is_correct": True}, {"letter": "D", "text": "Thyrsis", "is_correct": False}], "correct_answer": "Adonais", "correct_letter": "C", "explanation": "Adonais (1821) is a pastoral elegy written by P.B. Shelley mourning the death of John Keats.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Classical & Romantic Poetry", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Aristotle classified plot in Poetics into 'Simple and Complex' on the basis of?", "options": [{"letter": "A", "text": "Hamartia & Catharsis", "is_correct": False}, {"letter": "B", "text": "Anagnorisis & Peripeteia", "is_correct": True}, {"letter": "C", "text": "Sublimity & Decorum", "is_correct": False}, {"letter": "D", "text": "All of these", "is_correct": False}], "correct_answer": "Anagnorisis & Peripeteia", "correct_letter": "B", "explanation": "Aristotle defined complex plots by the inclusion of reversal (peripeteia) and recognition (anagnorisis).", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Literary Theory & Criticism", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "What is the name of Wordsworth's spiritual and autobiographical long poem?", "options": [{"letter": "A", "text": "The Canterbury Tales", "is_correct": False}, {"letter": "B", "text": "Don Juan", "is_correct": False}, {"letter": "C", "text": "Daffodils", "is_correct": False}, {"letter": "D", "text": "The Prelude", "is_correct": True}], "correct_answer": "The Prelude", "correct_letter": "D", "explanation": "The Prelude, or Growth of a Poet's Mind, is William Wordsworth's epic autobiographical poem in blank verse.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Classical & Romantic Poetry", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "What period in English Literature is called the 'Augustan Age'?", "options": [{"letter": "A", "text": "Early 16th Century", "is_correct": False}, {"letter": "B", "text": "17th Century", "is_correct": False}, {"letter": "C", "text": "18th Century", "is_correct": True}, {"letter": "D", "text": "15th Century", "is_correct": False}], "correct_answer": "18th Century", "correct_letter": "C", "explanation": "The Augustan Age refers to the early 18th-century neo-classical literary period.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "History of English Literature", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Which of the following is NOT a play written by William Shakespeare?", "options": [{"letter": "A", "text": "The Tempest", "is_correct": False}, {"letter": "B", "text": "Pygmalion", "is_correct": True}, {"letter": "C", "text": "The Merchant of Venice", "is_correct": False}, {"letter": "D", "text": "King Lear", "is_correct": False}], "correct_answer": "Pygmalion", "correct_letter": "B", "explanation": "Pygmalion (1913) was written by George Bernard Shaw.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Drama & Theatre", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Who is the villain and antagonist in Shakespeare's Hamlet?", "options": [{"letter": "A", "text": "Horatio", "is_correct": False}, {"letter": "B", "text": "Iago", "is_correct": False}, {"letter": "C", "text": "Claudius", "is_correct": True}, {"letter": "D", "text": "Polonius", "is_correct": False}], "correct_answer": "Claudius", "correct_letter": "C", "explanation": "King Claudius is the villain in Hamlet who poisoned King Hamlet.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Drama & Theatre", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "The phrase 'Pathetic Fallacy' was coined by?", "options": [{"letter": "A", "text": "John Milton", "is_correct": False}, {"letter": "B", "text": "S.T. Coleridge", "is_correct": False}, {"letter": "C", "text": "Thomas Carlyle", "is_correct": False}, {"letter": "D", "text": "John Ruskin", "is_correct": True}], "correct_answer": "John Ruskin", "correct_letter": "D", "explanation": "John Ruskin coined 'Pathetic Fallacy' in Modern Painters (1856).", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Literary Theory & Criticism", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Which era is called the 'Golden Period' of English Literature?", "options": [{"letter": "A", "text": "Elizabethan Age", "is_correct": True}, {"letter": "B", "text": "Victorian Age", "is_correct": False}, {"letter": "C", "text": "Early 18th Century", "is_correct": False}, {"letter": "D", "text": "None of these", "is_correct": False}], "correct_answer": "Elizabethan Age", "correct_letter": "A", "explanation": "The Elizabethan Age (1558–1603) is the Golden Age of English literature.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "History of English Literature", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Which of the following is the 19th-century Victorian woman novelist whose real name was Mary Ann Evans?", "options": [{"letter": "A", "text": "Emily Dickinson", "is_correct": False}, {"letter": "B", "text": "Ezra Pound", "is_correct": False}, {"letter": "C", "text": "Virginia Woolf", "is_correct": False}, {"letter": "D", "text": "George Eliot", "is_correct": True}], "correct_answer": "George Eliot", "correct_letter": "D", "explanation": "George Eliot was the pen name of Mary Ann Evans.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Novels, Fiction & Prose", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "'Elia' is the famous pen name of which of the following essayists?", "options": [{"letter": "A", "text": "Francis Bacon", "is_correct": False}, {"letter": "B", "text": "Charles Lamb", "is_correct": True}, {"letter": "C", "text": "Thomas Hardy", "is_correct": False}, {"letter": "D", "text": "None of these", "is_correct": False}], "correct_answer": "Charles Lamb", "correct_letter": "B", "explanation": "Charles Lamb wrote 'Essays of Elia' (1823).", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Novels, Fiction & Prose", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "After whose death in 1843 did William Wordsworth become the Poet Laureate of England?", "options": [{"letter": "A", "text": "Robert Southey", "is_correct": True}, {"letter": "B", "text": "Walter Scott", "is_correct": False}, {"letter": "C", "text": "S.T. Coleridge", "is_correct": False}, {"letter": "D", "text": "John Dryden", "is_correct": False}], "correct_answer": "Robert Southey", "correct_letter": "A", "explanation": "Wordsworth succeeded Robert Southey as Poet Laureate in 1843.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Classical & Romantic Poetry", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "'Sweet are the uses of adversity' is a famous line from which play of Shakespeare?", "options": [{"letter": "A", "text": "The Merchant of Venice", "is_correct": False}, {"letter": "B", "text": "Romeo and Juliet", "is_correct": False}, {"letter": "C", "text": "Twelfth Night", "is_correct": False}, {"letter": "D", "text": "As You Like It", "is_correct": True}], "correct_answer": "As You Like It", "correct_letter": "D", "explanation": "Spoken by Duke Senior in Act II, Scene 1 of As You Like It.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Drama & Theatre", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Which was the first published novel of Charles Dickens?", "options": [{"letter": "A", "text": "Great Expectations", "is_correct": False}, {"letter": "B", "text": "Hard Times", "is_correct": False}, {"letter": "C", "text": "The Pickwick Papers", "is_correct": True}, {"letter": "D", "text": "Oliver Twist", "is_correct": False}], "correct_answer": "The Pickwick Papers", "correct_letter": "C", "explanation": "The Pickwick Papers (1836-1837) was Dickens's first novel.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Novels, Fiction & Prose", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    {"question": "Who is the philosophical author of 'Symposium'?", "options": [{"letter": "A", "text": "Aristotle", "is_correct": False}, {"letter": "B", "text": "Dante", "is_correct": False}, {"letter": "C", "text": "Longinus", "is_correct": False}, {"letter": "D", "text": "Plato", "is_correct": True}], "correct_answer": "Plato", "correct_letter": "D", "explanation": "Symposium is a philosophical dialogue by Plato.", "submitted_by": "Kashif Ali (Success Times Academy)", "subject": "Literary Theory & Criticism", "source_paper": "SPSC Subject Specialist English (BS-17) 2023"},
    # PPSC 2011, 2015, 2017, 2020, 2022
    {"question": "'Because I Could Not Stop For Death' was written by which American poet?", "options": [{"letter": "A", "text": "William Shakespeare", "is_correct": False}, {"letter": "B", "text": "Sylvia Plath", "is_correct": False}, {"letter": "C", "text": "Edgar Allan Poe", "is_correct": False}, {"letter": "D", "text": "Emily Dickinson", "is_correct": True}], "correct_answer": "Emily Dickinson", "correct_letter": "D", "explanation": "Emily Dickinson composed this famous poem personifying Death.", "submitted_by": "PPSC Past Paper 2011", "subject": "American & World Literature", "source_paper": "PPSC English Lecturer (BS-17) 2011"},
    {"question": "A far-fetched, intricate and startling metaphor characteristic of metaphysical poetry is called a:", "options": [{"letter": "A", "text": "Conceit", "is_correct": True}, {"letter": "B", "text": "Hyperbole", "is_correct": False}, {"letter": "C", "text": "Illusion", "is_correct": False}, {"letter": "D", "text": "Analogy", "is_correct": False}], "correct_answer": "Conceit", "correct_letter": "A", "explanation": "A metaphysical conceit is an elaborate and unusual comparison.", "submitted_by": "PPSC Past Paper 2011", "subject": "Classical & Romantic Poetry", "source_paper": "PPSC English Lecturer (BS-17) 2011"},
    {"question": "The dramatic monologue 'Ulysses' was composed by:", "options": [{"letter": "A", "text": "Robert Browning", "is_correct": False}, {"letter": "B", "text": "Arthur Hallam", "is_correct": False}, {"letter": "C", "text": "Alfred Lord Tennyson", "is_correct": True}, {"letter": "D", "text": "Matthew Arnold", "is_correct": False}], "correct_answer": "Alfred Lord Tennyson", "correct_letter": "C", "explanation": "Alfred Lord Tennyson wrote 'Ulysses' in blank verse in 1833.", "submitted_by": "PPSC Past Paper 2011", "subject": "Classical & Romantic Poetry", "source_paper": "PPSC English Lecturer (BS-17) 2011"},
    {"question": "The Norman Conquest of England took place in which year?", "options": [{"letter": "A", "text": "1065", "is_correct": False}, {"letter": "B", "text": "1067", "is_correct": False}, {"letter": "C", "text": "1066", "is_correct": True}, {"letter": "D", "text": "956", "is_correct": False}], "correct_answer": "1066", "correct_letter": "C", "explanation": "William the Conqueror defeated King Harold at the Battle of Hastings in 1066.", "submitted_by": "PPSC Past Paper 2011", "subject": "History of English Literature", "source_paper": "PPSC English Lecturer (BS-17) 2011"},
    {"question": "'War between flesh and spirit' is a central theme in which novel of Thomas Hardy?", "options": [{"letter": "A", "text": "Far from the Madding Crowd", "is_correct": False}, {"letter": "B", "text": "Jude the Obscure", "is_correct": True}, {"letter": "C", "text": "The Mayor of Casterbridge", "is_correct": False}, {"letter": "D", "text": "The Return of the Native", "is_correct": False}], "correct_answer": "Jude the Obscure", "correct_letter": "B", "explanation": "Jude the Obscure (1895) deals with a deadly war between flesh and spirit.", "submitted_by": "PPSC Past Paper 2011", "subject": "Novels, Fiction & Prose", "source_paper": "PPSC English Lecturer (BS-17) 2011"},
    {"question": "In Rhetoric, the ethical appeal and character that a speaker projects to persuade an audience is called:", "options": [{"letter": "A", "text": "Ethos", "is_correct": True}, {"letter": "B", "text": "Pathos", "is_correct": False}, {"letter": "C", "text": "Logos", "is_correct": False}, {"letter": "D", "text": "Kairos", "is_correct": False}], "correct_answer": "Ethos", "correct_letter": "A", "explanation": "Ethos is Aristotle's term for persuasion through character and credibility.", "submitted_by": "PPSC Past Paper 2015", "subject": "Literary Theory & Criticism", "source_paper": "PPSC English Lecturer (BS-17) 2015"},
    {"question": "In drama, a brief remark made by an actor intended for the audience and presumed not to be heard by the other characters on stage is an:", "options": [{"letter": "A", "text": "Aside", "is_correct": True}, {"letter": "B", "text": "Soliloquy", "is_correct": False}, {"letter": "C", "text": "Monologue", "is_correct": False}, {"letter": "D", "text": "Apostrophe", "is_correct": False}], "correct_answer": "Aside", "correct_letter": "A", "explanation": "An aside is delivered to the audience while other characters are present on stage.", "submitted_by": "PPSC Past Paper 2015", "subject": "Drama & Theatre", "source_paper": "PPSC English Lecturer (BS-17) 2015"},
    {"question": "Which of the following describes the central theme of Milton's Paradise Lost?", "options": [{"letter": "A", "text": "To justify the ways of God to men", "is_correct": True}, {"letter": "B", "text": "The cunningness of Satan", "is_correct": False}, {"letter": "C", "text": "Human weakness", "is_correct": False}, {"letter": "D", "text": "God's absolute authority", "is_correct": False}], "correct_answer": "To justify the ways of God to men", "correct_letter": "A", "explanation": "Milton states his purpose in Book I: 'And justify the ways of God to men.'", "submitted_by": "PPSC Past Paper 2015", "subject": "Classical & Romantic Poetry", "source_paper": "PPSC English Lecturer (BS-17) 2015"},
    {"question": "T.S. Eliot was awarded the Nobel Prize in Literature in which year?", "options": [{"letter": "A", "text": "1948", "is_correct": True}, {"letter": "B", "text": "1947", "is_correct": False}, {"letter": "C", "text": "1946", "is_correct": False}, {"letter": "D", "text": "1956", "is_correct": False}], "correct_answer": "1948", "correct_letter": "A", "explanation": "T.S. Eliot received the Nobel Prize in Literature in 1948.", "submitted_by": "PPSC Past Paper 2015", "subject": "Modern & Post-Modern Poetry", "source_paper": "PPSC English Lecturer (BS-17) 2015"},
    {"question": "In Oedipus Rex by Sophocles, whose murder must be avenged to end the plague devastating Thebes?", "options": [{"letter": "A", "text": "Creon", "is_correct": False}, {"letter": "B", "text": "Polybus", "is_correct": False}, {"letter": "C", "text": "King Laius", "is_correct": True}, {"letter": "D", "text": "Polynices", "is_correct": False}], "correct_answer": "King Laius", "correct_letter": "C", "explanation": "The Delphic oracle requires avenging the murder of former King Laius.", "submitted_by": "PPSC Past Paper 2017", "subject": "Drama & Theatre", "source_paper": "PPSC English Lecturer (BS-17) 2017"},
    {"question": "In Heart of Darkness by Joseph Conrad, aboard which vessel and place does Kurtz utter 'The horror! The horror!' before dying?", "options": [{"letter": "A", "text": "At the Inner Station", "is_correct": False}, {"letter": "B", "text": "In Brussels", "is_correct": False}, {"letter": "C", "text": "Aboard Marlow's steamer on the Congo River", "is_correct": True}, {"letter": "D", "text": "In the jungle", "is_correct": False}], "correct_answer": "Aboard Marlow's steamer on the Congo River", "correct_letter": "C", "explanation": "Kurtz dies aboard Marlow's steamship cabin while traveling down the Congo River.", "submitted_by": "PPSC Past Paper 2017", "subject": "Novels, Fiction & Prose", "source_paper": "PPSC English Lecturer (BS-17) 2017"},
    {"question": "In Shakespeare's Othello, how does Iago metaphorically describe jealousy to Othello?", "options": [{"letter": "A", "text": "Downfall of many men", "is_correct": False}, {"letter": "B", "text": "The scourge of the weak", "is_correct": False}, {"letter": "C", "text": "The green-eyed monster", "is_correct": True}, {"letter": "D", "text": "The poison of the heart", "is_correct": False}], "correct_answer": "The green-eyed monster", "correct_letter": "C", "explanation": "Iago warns: 'O, beware, my lord, of jealousy; / It is the green-eyed monster.'", "submitted_by": "PPSC Past Paper 2017", "subject": "Drama & Theatre", "source_paper": "PPSC English Lecturer (BS-17) 2017"},
    {"question": "What kind of government is depicted in Salem in Arthur Miller's The Crucible?", "options": [{"letter": "A", "text": "Democracy", "is_correct": False}, {"letter": "B", "text": "Theocracy", "is_correct": True}, {"letter": "C", "text": "Monarchy", "is_correct": False}, {"letter": "D", "text": "Kleptocracy", "is_correct": False}], "correct_answer": "Theocracy", "correct_letter": "B", "explanation": "Salem in 1692 is governed as a strict theocracy combining religious law with civil courts.", "submitted_by": "PPSC Past Paper 2017", "subject": "Drama & Theatre", "source_paper": "PPSC English Lecturer (BS-17) 2017"},
    {"question": "Most of the novels of Indian English novelist R.K. Narayan are set in the fictional South Indian town of:", "options": [{"letter": "A", "text": "Madras", "is_correct": False}, {"letter": "B", "text": "Malgudi", "is_correct": True}, {"letter": "C", "text": "Trivandrum", "is_correct": False}, {"letter": "D", "text": "Mano Majra", "is_correct": False}], "correct_answer": "Malgudi", "correct_letter": "B", "explanation": "R.K. Narayan set his novels in the fictional town of Malgudi.", "submitted_by": "PPSC Past Paper 2020", "subject": "American & World Literature", "source_paper": "PPSC English Lecturer (BS-17) 2020"},
    {"question": "How many total plays did William Shakespeare officially write in the First Folio canon?", "options": [{"letter": "A", "text": "36", "is_correct": False}, {"letter": "B", "text": "37", "is_correct": True}, {"letter": "C", "text": "38", "is_correct": False}, {"letter": "D", "text": "39", "is_correct": False}], "correct_answer": "37", "correct_letter": "B", "explanation": "Shakespeare wrote 37 plays in the traditional canon.", "submitted_by": "PPSC Past Paper 2020", "subject": "Drama & Theatre", "source_paper": "PPSC English Lecturer (BS-17) 2020"},
    {"question": "In which novel of D.H. Lawrence is the protagonist's relationship with his mother analyzed through the 'Oedipus Complex'?", "options": [{"letter": "A", "text": "Lady Chatterley's Lover", "is_correct": False}, {"letter": "B", "text": "Sons and Lovers", "is_correct": True}, {"letter": "C", "text": "The Trespasser", "is_correct": False}, {"letter": "D", "text": "The Rainbow", "is_correct": False}], "correct_answer": "Sons and Lovers", "correct_letter": "B", "explanation": "Sons and Lovers (1913) portrays Paul Morel's Oedipal entanglement with his mother.", "submitted_by": "PPSC Past Paper 2020", "subject": "Novels, Fiction & Prose", "source_paper": "PPSC English Lecturer (BS-17) 2020"},
    {"question": "Who was the leading Irish modernist poet who composed 'The Second Coming' and 'Sailing to Byzantium'?", "options": [{"letter": "A", "text": "T.S. Eliot", "is_correct": False}, {"letter": "B", "text": "W.B. Yeats", "is_correct": True}, {"letter": "C", "text": "Ezra Pound", "is_correct": False}, {"letter": "D", "text": "W.H. Auden", "is_correct": False}], "correct_answer": "W.B. Yeats", "correct_letter": "B", "explanation": "W.B. Yeats was the leader of the Irish Literary Revival.", "submitted_by": "PPSC Past Paper 2022", "subject": "Modern & Post-Modern Poetry", "source_paper": "PPSC English Lecturer (BS-17) 2022"},
    {"question": "The book 'Orientalism' (1978), which laid the foundation of post-colonial studies, was authored by:", "options": [{"letter": "A", "text": "Frantz Fanon", "is_correct": False}, {"letter": "B", "text": "Edward Said", "is_correct": True}, {"letter": "C", "text": "Homi Bhabha", "is_correct": False}, {"letter": "D", "text": "Gayatri Spivak", "is_correct": False}], "correct_answer": "Edward Said", "correct_letter": "B", "explanation": "Edward Said's 'Orientalism' founded post-colonial critical theory.", "submitted_by": "PPSC Past Paper 2022", "subject": "Literary Theory & Criticism", "source_paper": "PPSC English Lecturer (BS-17) 2022"}
]

def clean_and_normalize_existing():
    if not os.path.exists(DATA_JSON):
        return
    with open(DATA_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    cleaned_list = []
    seen = set()
    for q in data:
        q_text = clean_text_formatting(q.get("question", ""))
        key = q_text.lower().strip()
        if key in seen or not q_text:
            continue
        seen.add(key)
        
        # Clean options
        opts = []
        for o in q.get("options", []):
            opts.append({
                "letter": o.get("letter", ""),
                "text": clean_text_formatting(o.get("text", "")),
                "is_correct": o.get("is_correct", False)
            })
            
        submitted_by = q.get("submitted_by") or "PakMCQs Community Contributor"
        src_paper = q.get("source_paper") or "PakMCQs (pakmcqs.com)"
        
        cleaned_list.append({
            "id": q.get("id") or (abs(hash(q_text)) % 10000000),
            "question": q_text,
            "options": opts,
            "correct_answer": clean_text_formatting(q.get("correct_answer", "")),
            "correct_letter": q.get("correct_letter", "").strip(),
            "explanation": clean_text_formatting(q.get("explanation", "")),
            "submitted_by": clean_text_formatting(submitted_by),
            "subject": q.get("subject", "English Literature"),
            "source_paper": src_paper,
            "source_url": q.get("source_url", "https://pakmcqs.com")
        })
        
    # Inject past papers if missing
    for pq in PDF_PAST_PAPERS_MCQS:
        k = clean_text_formatting(pq["question"]).lower().strip()
        if k not in seen:
            seen.add(k)
            cleaned_list.insert(0, pq)
            
    with open(DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(cleaned_list, f, ensure_ascii=False, indent=2)
    print(f"[+] Cleaned and normalized {len(cleaned_list)} MCQs in {DATA_JSON}", flush=True)
    init_db(cleaned_list)

def init_db(mcqs):
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
    for idx, q in enumerate(mcqs, 1):
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
    print(f"[+] Synced {len(rows)} questions to SQLite database: {DB_PATH}", flush=True)

if __name__ == "__main__":
    clean_and_normalize_existing()
