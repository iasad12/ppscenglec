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

def clean_pdf_text(text):
    if not text:
        return ""
    t = str(text)
    t = t.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    t = t.replace('\ufffd', "'").replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

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
            self.drawRightString(576, 755, "Sourced from PakMCQs.com & Solved Past Papers")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(36, 748, 576, 748)
            
            # Footer
            self.line(36, 42, 576, 42)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(36, 30, "Curated by Asad Imran (asadimran.pages.dev) | Sourced from PakMCQs.com | Passing: 40% (-0.25 Neg.)")
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
        "Famous Playwright, Poet and Others",
        "Ages, Era, Period",
        "Literary Theory and Criticism",
        "Language and Linguistics",
        "American Literature",
        "Medieval Literature and Culture",
        "Cultural & Literary English Renaissance",
        "Cultural & Literary 18th-19th Centuries",
        "Cultural & Literary in Modernity",
        "English Romantic Poetry",
        "Modern Poetry and Poetics",
        "The Gothic Novel",
        "The Victorian Novel",
        "Restoration & 18th-Century Drama",
        "Introduction to Literary Studies",
        "Introduction to Literary Theory",
        "Miscellaneous Literature MCQs",
        "English Grammar & Vocabulary",
        "Pakistan Current Affairs & GK",
        "Islamic Studies",
        "Everyday Science & Math",
        "PPSC / SPSC Solved Past Papers (2011-2024)"
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
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#1E1B4B"),
        alignment=1
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        alignment=1
    )
    
    shoutout_style = ParagraphStyle(
        'ShoutoutText',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#065F46"),
        alignment=1
    )

    section_banner_style = ParagraphStyle(
        'SectionBanner',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=14.5,
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
    
    contrib_style = ParagraphStyle(
        'ContribText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#64748B"),
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
    story.append(Spacer(1, 8))
    story.append(Paragraph("<b>PPSC / FPSC / SPSC / KPPSC</b>", title_style))
    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>ENGLISH LECTURER & SUBJECT SPECIALIST (BS-17)</b>", ParagraphStyle('Sub1', parent=title_style, fontSize=15, leading=19, textColor=colors.HexColor("#4F46E5"))))
    story.append(Spacer(1, 3))
    story.append(Paragraph(f"<b>MASTER SOLVED PAST PAPERS &amp; CATEGORIZED QUESTION BANK ({len(mcqs):,} MCQs)</b>", ParagraphStyle('Sub2', parent=title_style, fontSize=11.5, leading=15, textColor=colors.HexColor("#0284C7"))))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Curated &amp; Compiled by <b><a href='https://asadimran.pages.dev/' color='#4338CA'><u>Asad Imran</u> (asadimran.pages.dev)</a></b> | Zero-Spoiler Two-Column Format", subtitle_style))
    story.append(Spacer(1, 8))

    # Shoutout Banner for PakMCQs, Sanfoundry, and Contributors
    shoutout_data = [[
        Paragraph("<b>Special Acknowledgement &amp; Shoutout:</b> Core MCQs and community contributions graciously sourced from <b>PakMCQs (pakmcqs.com)</b>, <b>Sanfoundry</b>, and <b>Dr. Jahanzeb Jahan (Lectureship MCQs)</b>, along with verified solved past papers compiled by Kashif Ali (Success Times Academy) and PPSC/SPSC Examination Boards.", shoutout_style)
    ]]
    shoutout_table = Table(shoutout_data, colWidths=[540])
    shoutout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#ECFDF5")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#A7F3D0")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(shoutout_table)
    story.append(Spacer(1, 10))

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
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(spec_table)
    story.append(Spacer(1, 10))

    # Summary Table of Subjects & Counts
    story.append(Paragraph("<b>Table of Contents &amp; Subject Distribution</b>", ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=10.5, textColor=colors.HexColor("#0F172A"))))
    story.append(Spacer(1, 4))
    
    summary_rows = [
        [
            Paragraph("<b>Sr.</b>", ParagraphStyle('TH1', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)),
            Paragraph("<b>Topic / Subject Module</b>", ParagraphStyle('TH2', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)),
            Paragraph("<b>MCQs Count</b>", ParagraphStyle('TH3', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.white)),
            Paragraph("<b>PPSC Weightage</b>", ParagraphStyle('TH4', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.white))
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
            Paragraph(str(idx), ParagraphStyle('TD1', fontName='Helvetica', fontSize=7.5)),
            Paragraph(f"<b>{subj}</b>", ParagraphStyle('TD2', fontName='Helvetica', fontSize=7.5, textColor=colors.HexColor("#1E293B"))),
            Paragraph(f"<b>{len(s_mcqs)}</b>", ParagraphStyle('TD3', fontName='Helvetica-Bold', fontSize=7.5, alignment=1, textColor=colors.HexColor("#4F46E5"))),
            Paragraph(weight_map.get(subj, "10%"), ParagraphStyle('TD4', fontName='Helvetica', fontSize=7.5, alignment=1, textColor=colors.HexColor("#475569")))
        ])

    # Total row
    summary_rows.append([
        Paragraph("Σ", ParagraphStyle('TDTot0', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.HexColor("#1E1B4B"))),
        Paragraph("<b>TOTAL VERIFIED QUESTION BANK</b>", ParagraphStyle('TDTot1', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor("#1E1B4B"))),
        Paragraph(f"<b>{len(mcqs):,}</b>", ParagraphStyle('TDTot2', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.HexColor("#4F46E5"))),
        Paragraph("<b>100% Comprehensive</b>", ParagraphStyle('TDTot3', fontName='Helvetica-Bold', fontSize=7.5, alignment=1, textColor=colors.HexColor("#065F46")))
    ])
        
    summary_table = Table(summary_rows, colWidths=[30, 280, 110, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#312E81")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor("#F8FAFC")]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#EEF2FF")),
        ('LINEABOVE', (0,-1), (-1,-1), 1.2, colors.HexColor("#4F46E5")),
        ('TOPPADDING', (0,0), (-1,-1), 3.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3.5),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 10))
    story.append(Paragraph("<i><b>Self-Study Tip:</b> Cover the right-hand column while self-testing. All verified answers, contributor credits, and notes are placed exclusively in the right column to prevent cheating.</i>", ParagraphStyle('Note', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor("#4338CA"), alignment=1)))
    story.append(PageBreak())

    # ================= SUBJECT-WISE SECTIONS =================
    global_q_num = 1
    
    subject_colors = {
        "Famous Playwright, Poet and Others": "#4F46E5",
        "Ages, Era, Period": "#7C3AED",
        "Literary Theory and Criticism": "#9333EA",
        "Language and Linguistics": "#0284C7",
        "American Literature": "#D97706",
        "Medieval Literature and Culture": "#475569",
        "Cultural & Literary English Renaissance": "#2563EB",
        "Cultural & Literary 18th-19th Centuries": "#0D9488",
        "Cultural & Literary in Modernity": "#3B82F6",
        "English Romantic Poetry": "#E11D48",
        "Modern Poetry and Poetics": "#8B5CF6",
        "The Gothic Novel": "#334155",
        "The Victorian Novel": "#059669",
        "Restoration & 18th-Century Drama": "#B45309",
        "Introduction to Literary Studies": "#6366F1",
        "Introduction to Literary Theory": "#A855F7",
        "Miscellaneous Literature MCQs": "#64748B",
        "English Grammar & Vocabulary": "#10B981",
        "Pakistan Current Affairs & GK": "#16A34A",
        "Islamic Studies": "#047857",
        "Everyday Science & Math": "#0284C7",
        "PPSC / SPSC Solved Past Papers (2011-2024)": "#DC2626"
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
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 6))

        for q in s_mcqs:
            q_text = clean_pdf_text(q.get("question", ""))
            options = q.get("options", [])
            corr_ans = clean_pdf_text(q.get("correct_answer", ""))
            corr_let = q.get("correct_letter", "").strip()
            raw_exp = clean_pdf_text(q.get("explanation", ""))
            submitted_by = clean_pdf_text(q.get("submitted_by", ""))
            src_paper = clean_pdf_text(q.get("source_paper", ""))
            
            # 1. LEFT COLUMN: Question + Options
            q_elements = []
            q_elements.append(Paragraph(f"<b>Q{global_q_num}. {q_text}</b>", q_style))
            
            if options:
                opt_texts = []
                for opt in options:
                    let = opt.get("letter", "")
                    otxt = clean_pdf_text(opt.get("text", ""))
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

            # 2. RIGHT COLUMN: Answer Badge + Answer Text + Contributor + Explanation Note
            ans_elements = []
            if corr_let:
                ans_elements.append(Paragraph(f"<b>[{corr_let}]</b>", ans_badge_style))
            if corr_ans:
                ans_elements.append(Paragraph(f"<b>{corr_ans}</b>", ans_text_style))
            else:
                ans_elements.append(Paragraph("<b>Answered</b>", ans_text_style))
                
            # Always render contributor / submission credit
            if src_paper and ("PPSC" in src_paper or "SPSC" in src_paper or "KPPSC" in src_paper):
                contrib_label = f"Source: {src_paper}"
            elif submitted_by:
                contrib_label = f"Submitted by: {submitted_by}"
            else:
                contrib_label = "Submitted by: PakMCQs Contributor"

            ans_elements.append(Spacer(1, 1.5))
            ans_elements.append(Paragraph(f"<i>{contrib_label}</i>", contrib_style))

            if raw_exp and len(raw_exp) > 4:
                exp_snippet = raw_exp[:180] + ("..." if len(raw_exp) > 180 else "")
                ans_elements.append(Spacer(1, 2))
                ans_elements.append(Paragraph(f"<b>Note:</b> {exp_snippet}", exp_style))

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
                ('TOPPADDING', (0,0), (-1,-1), 4.5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
                ('LEFTPADDING', (0,0), (0,0), 6),
                ('RIGHTPADDING', (0,0), (0,0), 6),
                ('LEFTPADDING', (1,0), (1,0), 6),
                ('RIGHTPADDING', (1,0), (1,0), 6),
            ]))

            story.append(KeepTogether([row_table, Spacer(1, 2.5)]))
            global_q_num += 1

        story.append(Spacer(1, 8))

    print("[*] Rebuilding English Lecturer PDF with clean text and contributor attribution...")
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[+] Successfully generated PDF: {output_pdf}")
    print(f"[+] Total questions formatted: {global_q_num - 1}")

if __name__ == "__main__":
    build_pdf()
