import os
import re
import json
import sqlite3
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_JSON = os.path.join(BASE_DIR, "english_lecturer_mcqs.json")
OUTPUT_PDF = os.path.join(BASE_DIR, "English_Lecturer_Past_Papers_Categorized.pdf")

def clean_latin_text(text):
    if not text:
        return ""
    cleaned = re.sub(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+', '', text)
    cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
    cleaned = re.sub(r'&[a-zA-Z0-9#]+;', ' ', cleaned)
    cleaned = re.sub(r'', "'", cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_decorations(self, page_count):
        if self._pageNumber > 1:
            self.saveState()
            self.setFont("Helvetica-Bold", 8)
            self.setFillColor(colors.HexColor("#4338CA"))
            # Header
            self.drawString(36, 755, "PPSC / FPSC / SPSC / KPPSC - ENGLISH LECTURER & SUBJECT SPECIALIST GUIDE")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(36, 748, 576, 748)
            
            # Footer
            self.line(36, 42, 576, 42)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#64748B"))
            self.drawString(36, 30, "Self-Testing Format: Answers & Notes on Right Column | Passing: 40% (Negative Marking: -0.25)")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(576, 30, page_text)
            self.restoreState()

def build_pdf(json_file=DATA_JSON, output_pdf=OUTPUT_PDF):
    if not os.path.exists(json_file):
        print(f"[!] JSON file not found: {json_file}")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        mcqs = json.load(f)

    print(f"[*] Loaded {len(mcqs)} English Lecturer MCQs for PDF compilation...")

    subjects = {}
    for item in mcqs:
        subj = item.get("subject", "English Literature")
        subjects.setdefault(subj, []).append(item)

    subject_order = [
        "Classical & Romantic Poetry",
        "Drama & Theatre",
        "Novels, Fiction & Prose",
        "Modern & Post-Modern Poetry",
        "Linguistics & Phonetics",
        "Literary Theory & Criticism",
        "American & World Literature",
        "History of English Literature",
        "Grammar, Vocabulary & Figures of Speech",
        "General Knowledge & Pakistan Studies"
    ]
    
    ordered_subjects = []
    for s in subject_order:
        if s in subjects:
            ordered_subjects.append((s, subjects[s]))
    for s, list_mcqs in subjects.items():
        if s not in subject_order:
            ordered_subjects.append((s, list_mcqs))

    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=21,
        leading=25,
        textColor=colors.HexColor("#1E1B4B"),
        alignment=1
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
        alignment=1
    )
    
    section_banner_style = ParagraphStyle(
        'SectionBanner',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.white
    )
    
    q_style = ParagraphStyle(
        'QuestionText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor("#1E293B")
    )
    
    opt_style = ParagraphStyle(
        'OptionText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#334155")
    )
    
    ans_badge_style = ParagraphStyle(
        'AnsBadge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=12,
        textColor=colors.HexColor("#065F46"),
        alignment=1
    )
    
    ans_text_style = ParagraphStyle(
        'AnsText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#047857"),
        alignment=1
    )
    
    exp_style = ParagraphStyle(
        'ExpText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#334155"),
        alignment=0
    )

    story = []

    # ================= COVER / TITLE SECTION =================
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>PPSC / FPSC / SPSC / KPPSC</b>", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>ENGLISH LECTURER & SUBJECT SPECIALIST (BS-17)</b>", ParagraphStyle('Sub1', parent=title_style, fontSize=15, leading=19, textColor=colors.HexColor("#4F46E5"))))
    story.append(Spacer(1, 4))
    story.append(Paragraph("<b>MASTER SOLVED PAST PAPERS & CATEGORIZED QUESTION BANK</b>", ParagraphStyle('Sub2', parent=title_style, fontSize=12, leading=16, textColor=colors.HexColor("#0284C7"))))
    story.append(Spacer(1, 6))
    story.append(Paragraph("Categorized Self-Study Guide (Zero-Spoiler Format: Questions on Left, Verified Answers on Right)", subtitle_style))
    story.append(Spacer(1, 12))

    # PPSC Exam Specs Table
    spec_data = [
        [
            Paragraph("<b>Total Exam MCQs</b>", ParagraphStyle('B1', fontName='Helvetica-Bold', fontSize=9, alignment=1, textColor=colors.HexColor("#1E293B"))),
            Paragraph("<b>Negative Marking</b>", ParagraphStyle('B2', fontName='Helvetica-Bold', fontSize=9, alignment=1, textColor=colors.HexColor("#1E293B"))),
            Paragraph("<b>Passing Threshold</b>", ParagraphStyle('B3', fontName='Helvetica-Bold', fontSize=9, alignment=1, textColor=colors.HexColor("#1E293B"))),
            Paragraph("<b>Duration Allowed</b>", ParagraphStyle('B4', fontName='Helvetica-Bold', fontSize=9, alignment=1, textColor=colors.HexColor("#1E293B")))
        ],
        [
            Paragraph("<b>100 Questions</b>", ParagraphStyle('V1', fontName='Helvetica-Bold', fontSize=10.5, alignment=1, textColor=colors.HexColor("#4F46E5"))),
            Paragraph("<b>-0.25 Per Wrong</b>", ParagraphStyle('V2', fontName='Helvetica-Bold', fontSize=10.5, alignment=1, textColor=colors.HexColor("#DC2626"))),
            Paragraph("<b>40% (40 / 100)</b>", ParagraphStyle('V3', fontName='Helvetica-Bold', fontSize=10.5, alignment=1, textColor=colors.HexColor("#16A34A"))),
            Paragraph("<b>90 Minutes</b>", ParagraphStyle('V4', fontName='Helvetica-Bold', fontSize=10.5, alignment=1, textColor=colors.HexColor("#D97706")))
        ]
    ]
    spec_table = Table(spec_data, colWidths=[135, 135, 135, 135])
    spec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(spec_table)
    story.append(Spacer(1, 14))

    # Summary Table of Subjects & Counts
    story.append(Paragraph("<b>Table of Contents & Subject Distribution</b>", ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#0F172A"))))
    story.append(Spacer(1, 5))
    
    summary_rows = [
        [
            Paragraph("<b>Sr.</b>", ParagraphStyle('TH1', fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.white)),
            Paragraph("<b>Topic / Subject Module</b>", ParagraphStyle('TH2', fontName='Helvetica-Bold', fontSize=8.5, textColor=colors.white)),
            Paragraph("<b>MCQs Count</b>", ParagraphStyle('TH3', fontName='Helvetica-Bold', fontSize=8.5, alignment=1, textColor=colors.white)),
            Paragraph("<b>PPSC Weightage</b>", ParagraphStyle('TH4', fontName='Helvetica-Bold', fontSize=8.5, alignment=1, textColor=colors.white))
        ]
    ]
    
    weight_map = {
        "Classical & Romantic Poetry": "15% - 20%",
        "Drama & Theatre": "15% - 20%",
        "Novels, Fiction & Prose": "15% - 20%",
        "Modern & Post-Modern Poetry": "10% - 15%",
        "Linguistics & Phonetics": "10% - 15%",
        "Literary Theory & Criticism": "10% - 15%",
        "American & World Literature": "5% - 10%",
        "History of English Literature": "5% - 10%",
        "Grammar, Vocabulary & Figures of Speech": "10%",
        "General Knowledge & Pakistan Studies": "20% (General Quota)"
    }

    for idx, (subj, s_mcqs) in enumerate(ordered_subjects, 1):
        summary_rows.append([
            Paragraph(str(idx), ParagraphStyle('TD1', fontName='Helvetica', fontSize=8)),
            Paragraph(f"<b>{subj}</b>", ParagraphStyle('TD2', fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#1E293B"))),
            Paragraph(f"<b>{len(s_mcqs)}</b>", ParagraphStyle('TD3', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.HexColor("#4F46E5"))),
            Paragraph(weight_map.get(subj, "10%"), ParagraphStyle('TD4', fontName='Helvetica', fontSize=8, alignment=1, textColor=colors.HexColor("#475569")))
        ])
        
    summary_table = Table(summary_rows, colWidths=[35, 275, 110, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#312E81")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))
    story.append(Paragraph("<i><b>Self-Study Tip:</b> Cover the right-hand column while self-testing. All verified answers and notes are placed exclusively in the right column to prevent cheating.</i>", ParagraphStyle('Note', fontName='Helvetica-Oblique', fontSize=8.5, textColor=colors.HexColor("#4338CA"), alignment=1)))
    story.append(PageBreak())

    # ================= SUBJECT-WISE SECTIONS =================
    global_q_num = 1
    
    subject_colors = {
        "Classical & Romantic Poetry": "#4F46E5",
        "Drama & Theatre": "#7C3AED",
        "Novels, Fiction & Prose": "#0D9488",
        "Modern & Post-Modern Poetry": "#2563EB",
        "Linguistics & Phonetics": "#0284C7",
        "Literary Theory & Criticism": "#9333EA",
        "American & World Literature": "#D97706",
        "History of English Literature": "#475569",
        "Grammar, Vocabulary & Figures of Speech": "#059669",
        "General Knowledge & Pakistan Studies": "#16A34A"
    }

    LEFT_WIDTH = 360
    RIGHT_WIDTH = 180

    for subj_name, s_mcqs in ordered_subjects:
        b_color = colors.HexColor(subject_colors.get(subj_name, "#312E81"))
        
        banner_table = Table(
            [[Paragraph(f"<b>SECTION: {subj_name.upper()} ({len(s_mcqs)} MCQs)</b>", section_banner_style)]],
            colWidths=[540]
        )
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), b_color),
            ('TOPPADDING', (0,0), (-1,-1), 6),
            ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 7))

        for q in s_mcqs:
            q_text = clean_latin_text(q.get("question", ""))
            options = q.get("options", [])
            corr_ans = clean_latin_text(q.get("correct_answer", ""))
            corr_let = q.get("correct_letter", "").strip()
            raw_exp = clean_latin_text(q.get("explanation", ""))
            src_paper = q.get("source_paper", "")
            
            # 1. LEFT COLUMN: Question + Options
            q_elements = []
            q_elements.append(Paragraph(f"<b>Q{global_q_num}. {q_text}</b>", q_style))
            
            if options:
                opt_texts = []
                for opt in options:
                    let = opt.get("letter", "")
                    otxt = clean_latin_text(opt.get("text", "")) or opt.get("text", "")
                    opt_texts.append(f"<b>({let})</b> {otxt}")
                
                if len(opt_texts) == 4:
                    opt_table_data = [
                        [Paragraph(opt_texts[0], opt_style), Paragraph(opt_texts[1], opt_style)],
                        [Paragraph(opt_texts[2], opt_style), Paragraph(opt_texts[3], opt_style)]
                    ]
                    opt_table = Table(opt_table_data, colWidths=[175, 175])
                    opt_table.setStyle(TableStyle([
                        ('TOPPADDING', (0,0), (-1,-1), 1),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
                        ('LEFTPADDING', (0,0), (-1,-1), 0),
                        ('RIGHTPADDING', (0,0), (-1,-1), 0),
                    ]))
                    q_elements.append(Spacer(1, 2))
                    q_elements.append(opt_table)
                else:
                    for ot in opt_texts:
                        q_elements.append(Paragraph(ot, opt_style))

            # 2. RIGHT COLUMN: Answer Badge + Answer Text + Explanation Note
            ans_elements = []
            if corr_let:
                ans_elements.append(Paragraph(f"<b>[{corr_let}]</b>", ans_badge_style))
            if corr_ans:
                ans_elements.append(Paragraph(f"<b>{corr_ans}</b>", ans_text_style))
            else:
                ans_elements.append(Paragraph("<b>Answered</b>", ans_text_style))
                
            if raw_exp and len(raw_exp) > 4:
                exp_snippet = raw_exp[:180] + ("..." if len(raw_exp) > 180 else "")
                ans_elements.append(Spacer(1, 2))
                ans_elements.append(Paragraph(f"<b>Note:</b> {exp_snippet}", exp_style))
            elif src_paper and "PPSC" in src_paper or "SPSC" in src_paper:
                ans_elements.append(Spacer(1, 2))
                ans_elements.append(Paragraph(f"<i>{src_paper}</i>", exp_style))

            row_table = Table(
                [[q_elements, ans_elements]],
                colWidths=[LEFT_WIDTH, RIGHT_WIDTH]
            )
            row_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (0,0), colors.HexColor("#FFFFFF")),
                ('BACKGROUND', (1,0), (1,0), colors.HexColor("#F0FDF4")),
                ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
                ('LINEBEFORE', (1,0), (1,0), 0.75, colors.HexColor("#86EFAC")),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING', (0,0), (0,0), 6),
                ('RIGHTPADDING', (0,0), (0,0), 6),
                ('LEFTPADDING', (1,0), (1,0), 6),
                ('RIGHTPADDING', (1,0), (1,0), 6),
            ]))

            story.append(KeepTogether([row_table, Spacer(1, 3)]))
            global_q_num += 1

        story.append(Spacer(1, 10))

    print("[*] Rebuilding English Lecturer PDF with right-column answers...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] Successfully generated PDF: {output_pdf}")
    print(f"[+] Total questions formatted: {global_q_num - 1}")

if __name__ == "__main__":
    build_pdf()
