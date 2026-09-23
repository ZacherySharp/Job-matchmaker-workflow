"""
Renders tailored resume JSON files as professional PDFs using reportlab.
Reads all .json files from .tmp/tailored/ and outputs matching .pdf files.
"""

import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).parent.parent
TAILORED_DIR = ROOT / ".tmp" / "tailored"

# --- Colour palette ---
DARK = colors.HexColor("#1a1a2e")
ACCENT = colors.HexColor("#16213e")
RULE = colors.HexColor("#0f3460")
LIGHT_GRAY = colors.HexColor("#f5f5f5")


def make_styles():
    base = getSampleStyleSheet()
    return {
        "name": ParagraphStyle(
            "name", fontName="Helvetica-Bold", fontSize=20, textColor=DARK,
            spaceAfter=2, leading=24,
        ),
        "contact": ParagraphStyle(
            "contact", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#555555"),
            spaceAfter=6, leading=12,
        ),
        "section": ParagraphStyle(
            "section", fontName="Helvetica-Bold", fontSize=11, textColor=RULE,
            spaceBefore=10, spaceAfter=2, leading=14,
        ),
        "summary": ParagraphStyle(
            "summary", fontName="Helvetica", fontSize=9.5, textColor=DARK,
            spaceAfter=4, leading=14,
        ),
        "job_title": ParagraphStyle(
            "job_title", fontName="Helvetica-Bold", fontSize=9.5, textColor=DARK,
            spaceAfter=1, leading=12,
        ),
        "job_org": ParagraphStyle(
            "job_org", fontName="Helvetica-Oblique", fontSize=9, textColor=colors.HexColor("#444444"),
            spaceAfter=2, leading=11,
        ),
        "bullet": ParagraphStyle(
            "bullet", fontName="Helvetica", fontSize=9, textColor=DARK,
            leftIndent=12, spaceAfter=2, leading=12, bulletIndent=4,
        ),
        "skill_label": ParagraphStyle(
            "skill_label", fontName="Helvetica-Bold", fontSize=9, textColor=DARK,
            spaceAfter=1, leading=11,
        ),
        "skill_value": ParagraphStyle(
            "skill_value", fontName="Helvetica", fontSize=9, textColor=DARK,
            spaceAfter=3, leading=11,
        ),
        "cert": ParagraphStyle(
            "cert", fontName="Helvetica", fontSize=9, textColor=DARK,
            leftIndent=12, spaceAfter=2, leading=11, bulletIndent=4,
        ),
    }


def rule():
    return HRFlowable(width="100%", thickness=1, color=RULE, spaceAfter=4, spaceBefore=2)


def section_header(title: str, styles: dict):
    return [Paragraph(title.upper(), styles["section"]), rule()]


def build_story(data: dict, styles: dict) -> list:
    story = []

    # Header
    story.append(Paragraph(data.get("name", "Saqiv Williams"), styles["name"]))
    contact_parts = [
        data.get("phone", ""),
        data.get("email", ""),
        data.get("linkedin", ""),
        data.get("location", ""),
    ]
    story.append(Paragraph(" | ".join(p for p in contact_parts if p), styles["contact"]))
    story.append(Spacer(1, 4))

    # Summary
    if data.get("summary"):
        story += section_header("Professional Summary", styles)
        story.append(Paragraph(data["summary"], styles["summary"]))

    # Education
    edu_list = data.get("education", [])
    if edu_list:
        story += section_header("Education", styles)
        for edu in edu_list:
            title_line = f"<b>{edu.get('institution', '')}</b>"
            degree_line = f"{edu.get('degree', '')}  <font color='#666666'>{edu.get('dates', '')}</font>"
            story.append(Paragraph(title_line, styles["job_title"]))
            story.append(Paragraph(degree_line, styles["job_org"]))
            for detail in edu.get("details", []):
                story.append(Paragraph(f"• {detail}", styles["bullet"]))
            story.append(Spacer(1, 4))

    # Experience
    exp_list = data.get("experience", [])
    if exp_list:
        story += section_header("Experience", styles)
        for exp in exp_list:
            title_line = f"<b>{exp.get('title', '')}</b>"
            org_line = f"{exp.get('organization', '')}  <font color='#666666'>{exp.get('dates', '')}</font>"
            story.append(Paragraph(title_line, styles["job_title"]))
            story.append(Paragraph(org_line, styles["job_org"]))
            for bullet in exp.get("bullets", []):
                story.append(Paragraph(f"• {bullet}", styles["bullet"]))
            story.append(Spacer(1, 4))

    # Skills
    skills = data.get("skills", {})
    if skills:
        story += section_header("Skills", styles)
        if skills.get("technical"):
            story.append(Paragraph("<b>Technical:</b>", styles["skill_label"]))
            story.append(Paragraph(", ".join(skills["technical"]), styles["skill_value"]))
        if skills.get("soft"):
            story.append(Paragraph("<b>Interpersonal:</b>", styles["skill_label"]))
            story.append(Paragraph(", ".join(skills["soft"]), styles["skill_value"]))

    # Certifications
    certs = data.get("certifications", [])
    if certs:
        story += section_header("Certifications & Courses", styles)
        for cert in certs:
            story.append(Paragraph(f"• {cert}", styles["cert"]))
        story.append(Spacer(1, 4))

    # Achievements
    achievements = data.get("achievements", [])
    if achievements:
        story += section_header("Achievements & Activities", styles)
        for ach in achievements:
            story.append(Paragraph(f"• {ach}", styles["cert"]))

    return story


def render_pdf(json_path: Path) -> Path:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    job_id = data.get("_job_id", json_path.stem)
    pdf_path = json_path.parent / f"{job_id}.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
    )

    styles = make_styles()
    story = build_story(data, styles)
    doc.build(story)
    return pdf_path


def main() -> list[Path]:
    json_files = list(TAILORED_DIR.glob("*.json"))
    if not json_files:
        print(f"No tailored JSON files found in {TAILORED_DIR}")
        return []

    print(f"Generating PDFs for {len(json_files)} resumes...")
    pdfs = []
    for jf in json_files:
        try:
            pdf_path = render_pdf(jf)
            print(f"  Created: {pdf_path.name}")
            pdfs.append(pdf_path)
        except Exception as e:
            print(f"  Failed {jf.name}: {e}")

    print(f"\nGenerated {len(pdfs)} PDFs in {TAILORED_DIR}")
    return pdfs


if __name__ == "__main__":
    main()
