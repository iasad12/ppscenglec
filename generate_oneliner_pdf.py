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
OUTPUT_PDF = os.path.join(BASE_DIR, "English_Lecturer_One_Liners_Revision_Guide.pdf")

def clean_pdf_text(text):
    if not text:
        return ""
    t = str(text)
    t = t.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    t = t.replace('\ufffd', "'").replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    t = re.sub(r'[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]+', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

class OneLinerNumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(OneLinerNumberedCanvas, self).__init__(*args, **kwargs)
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
            self.setFillColor(colors.HexColor("#0F766E"))
            # Header
            self.drawString(36, 755, "PPSC / FPSC / SPSC / KPPSC - ENGLISH LECTURER ONE-LINER REVISION GUIDE")
            self.drawRightString(576, 755, "Rapid High-Yield Memory Guide (4,894 Statements)")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(36, 748, 576, 748)
            
            # Footer
            self.line(36, 42, 576, 42)
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#475569"))
            self.drawString(36, 30, "Curated by Asad Imran (asadimran.pages.dev) | Solved Past Papers & One-Liners")
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(576, 30, page_text)
            self.restoreState()

def build_oneliner_pdf(json_file=DATA_JSON, output_pdf=OUTPUT_PDF):
    if not os.path.exists(json_file):
        print(f"[!] JSON file not found: {json_file}")
        return

    with open(json_file, "r", encoding="utf-8") as f:
        mcqs = json.load(f)

    print(f"[*] Loaded {len(mcqs)} English Lecturer items for One-Liner compilation...")

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
        textColor=colors.HexColor("#042F2E"),
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
        fontSize=9,
        leading=12.5,
        textColor=colors.HexColor("#065F46"),
        alignment=1
    )

    section_banner_style = ParagraphStyle(
        'SectionBanner',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.white
    )

    q_num_style = ParagraphStyle(
        'QNum',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0D9488"),
        alignment=1
    )

    statement_style = ParagraphStyle(
        'StatementText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0F172A")
    )

    story = []

    # ================= COVER / TITLE SECTION =================
    story.append(Spacer(1, 10))
    story.append(Paragraph("<b>PPSC / FPSC / SPSC / KPPSC</b>", title_style))
    story.append(Spacer(1, 3))
    story.append(Paragraph("<b>ENGLISH LECTURER & SUBJECT SPECIALIST (BS-17)</b>", ParagraphStyle('Sub1', parent=title_style, fontSize=15, leading=19, textColor=colors.HexColor("#0D9488"))))
    story.append(Spacer(1, 3))
    story.append(Paragraph(f"<b>MASTER ONE-LINER REVISION GUIDE ({len(mcqs):,} SOLVED STATEMENTS)</b>", ParagraphStyle('Sub2', parent=title_style, fontSize=11.5, leading=15, textColor=colors.HexColor("#0284C7"))))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Curated & Compiled by <b><a href='https://asadimran.pages.dev/' color='#0F766E'><u>Asad Imran</u> (asadimran.pages.dev)</a></b> | Fast-Track Memory Recall Format", subtitle_style))
    story.append(Spacer(1, 8))

    # Shoutout Banner
    shoutout_data = [[
        Paragraph("<b>Fast-Track Revision Method:</b> Each statement provides the complete question context with the unambiguous correct answer <u><b>boldly underlined</b></u> at the end. Curated from verified past papers (2011–2024), <b>PakMCQs</b>, <b>Sanfoundry</b>, and <b>Dr. Jahanzeb Jahan (Lectureship MCQs)</b>.", shoutout_style)
    ]]
    shoutout_table = Table(shoutout_data, colWidths=[540])
    shoutout_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F0FDFA")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#99F6E4")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    story.append(shoutout_table)
    story.append(Spacer(1, 8))

    # Specs Table
    spec_data = [
        [
            Paragraph("<b>Total Statements</b>", ParagraphStyle('B1', fontName='Helvetica-Bold', fontSize=8.5, alignment=1, textColor=colors.HexColor("#1E293B"))),
            Paragraph("<b>Recommended Pace</b>", ParagraphStyle('B2', fontName='Helvetica-Bold', fontSize=8.5, alignment=1, textColor=colors.HexColor("#1E293B"))),
            Paragraph("<b>PPSC Exam Mark</b>", ParagraphStyle('B3', fontName='Helvetica-Bold', fontSize=8.5, alignment=1, textColor=colors.HexColor("#1E293B"))),
            Paragraph("<b>Target Audience</b>", ParagraphStyle('B4', fontName='Helvetica-Bold', fontSize=8.5, alignment=1, textColor=colors.HexColor("#1E293B")))
        ],
        [
            Paragraph(f"<b>{len(mcqs):,} Facts</b>", ParagraphStyle('V1', fontName='Helvetica-Bold', fontSize=10, alignment=1, textColor=colors.HexColor("#0D9488"))),
            Paragraph("<b>200 Daily</b>", ParagraphStyle('V2', fontName='Helvetica-Bold', fontSize=10, alignment=1, textColor=colors.HexColor("#2563EB"))),
            Paragraph("<b>40% Pass Mark</b>", ParagraphStyle('V3', fontName='Helvetica-Bold', fontSize=10, alignment=1, textColor=colors.HexColor("#16A34A"))),
            Paragraph("<b>Lecturer BS-17</b>", ParagraphStyle('V4', fontName='Helvetica-Bold', fontSize=10, alignment=1, textColor=colors.HexColor("#D97706")))
        ]
    ]
    spec_table = Table(spec_data, colWidths=[135, 135, 135, 135])
    spec_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(spec_table)
    story.append(Spacer(1, 8))

    # Summary Table of Subjects & Counts
    story.append(Paragraph("<b>Table of Contents & Subject Breakdown</b>", ParagraphStyle('H2', fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#0F172A"))))
    story.append(Spacer(1, 3))
    
    summary_rows = [
        [
            Paragraph("<b>Sr.</b>", ParagraphStyle('TH1', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)),
            Paragraph("<b>Topic / Subject Module</b>", ParagraphStyle('TH2', fontName='Helvetica-Bold', fontSize=8, textColor=colors.white)),
            Paragraph("<b>One-Liners Count</b>", ParagraphStyle('TH3', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.white)),
            Paragraph("<b>PPSC Exam Focus</b>", ParagraphStyle('TH4', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.white))
        ]
    ]

    for idx, (subj, s_mcqs) in enumerate(ordered_subjects, 1):
        summary_rows.append([
            Paragraph(str(idx), ParagraphStyle('TD1', fontName='Helvetica', fontSize=7.5)),
            Paragraph(f"<b>{subj}</b>", ParagraphStyle('TD2', fontName='Helvetica', fontSize=7.5, textColor=colors.HexColor("#1E293B"))),
            Paragraph(f"<b>{len(s_mcqs)}</b>", ParagraphStyle('TD3', fontName='Helvetica-Bold', fontSize=7.5, alignment=1, textColor=colors.HexColor("#0D9488"))),
            Paragraph("Core Syllabus", ParagraphStyle('TD4', fontName='Helvetica', fontSize=7.5, alignment=1, textColor=colors.HexColor("#475569")))
        ])

    summary_rows.append([
        Paragraph("Σ", ParagraphStyle('TDTot0', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.HexColor("#042F2E"))),
        Paragraph("<b>TOTAL REVISION STATEMENTS</b>", ParagraphStyle('TDTot1', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor("#042F2E"))),
        Paragraph(f"<b>{len(mcqs):,}</b>", ParagraphStyle('TDTot2', fontName='Helvetica-Bold', fontSize=8, alignment=1, textColor=colors.HexColor("#0D9488"))),
        Paragraph("<b>100% Comprehensive</b>", ParagraphStyle('TDTot3', fontName='Helvetica-Bold', fontSize=7.5, alignment=1, textColor=colors.HexColor("#065F46")))
    ])
        
    summary_table = Table(summary_rows, colWidths=[30, 280, 110, 120])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F766E")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor("#F8FAFC")]),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#F0FDFA")),
        ('LINEABOVE', (0,-1), (-1,-1), 1.2, colors.HexColor("#0D9488")),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8))
    story.append(Paragraph("<i><b>How to use:</b> Read through the statement and test your active recall on the underlined answer. Excellent for the final 15 days before the PPSC / FPSC exam.</i>", ParagraphStyle('Note', fontName='Helvetica-Oblique', fontSize=8, textColor=colors.HexColor("#0F766E"), alignment=1)))
    story.append(PageBreak())

    # ================= SUBJECT SECTIONS =================
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

    for subj_name, s_mcqs in ordered_subjects:
        b_color = colors.HexColor(subject_colors.get(subj_name, "#0F766E"))
        
        banner_table = Table(
            [[Paragraph(f"<b>SECTION: {subj_name.upper()} ({len(s_mcqs)} ONE-LINERS)</b>", section_banner_style)]],
            colWidths=[540]
        )
        banner_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), b_color),
            ('TOPPADDING', (0,0), (-1,-1), 4.5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 4.5),
            ('LEFTPADDING', (0,0), (-1,-1), 10),
        ]))
        story.append(banner_table)
        story.append(Spacer(1, 4))

        # Build One-Liner Table rows
        table_rows = []
        for q in s_mcqs:
            q_text = clean_pdf_text(q.get("question", ""))
            corr_ans = clean_pdf_text(q.get("correct_answer", ""))
            raw_exp = clean_pdf_text(q.get("explanation", ""))
            
            # Format: Question statement — <u><b>Correct Answer</b></u>
            statement_html = f"<b>{q_text}</b> &mdash; <u><font color='#0D9488'><b>{corr_ans}</b></font></u>"
            if raw_exp and len(raw_exp) > 5:
                # Add compact note if explanation exists
                statement_html += f"<br/><font color='#64748B' size='7'><i>Note: {raw_exp[:140]}</i></font>"

            table_rows.append([
                Paragraph(f"<b>{global_q_num}</b>", q_num_style),
                Paragraph(statement_html, statement_style)
            ])
            global_q_num += 1

        chunk_size = 60
        for i in range(0, len(table_rows), chunk_size):
            chunk = table_rows[i:i+chunk_size]
            t = Table(chunk, colWidths=[32, 508])
            t.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 3),
                ('BOTTOMPADDING', (0,0), (-1,-1), 3),
                ('LEFTPADDING', (0,0), (-1,-1), 3),
                ('RIGHTPADDING', (0,0), (-1,-1), 3),
                ('LINEBELOW', (0,0), (-1,-1), 0.35, colors.HexColor("#E2E8F0")),
                ('ROWBACKGROUNDS', (0,0), (-1,-1), [colors.white, colors.HexColor("#F8FAFC")])
            ]))
            story.append(t)

        story.append(Spacer(1, 8))

    print("[*] Compiling One-Liner PDF document...")
    doc.build(story, canvasmaker=OneLinerNumberedCanvas)
    print(f"[+] Successfully generated One-Liner PDF: {output_pdf}")

if __name__ == "__main__":
    build_oneliner_pdf()
