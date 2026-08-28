"""
utils/pdf_generator.py
======================
Step 13: ReportLab PDF Document Generator

Generates clean, professional PDF reports for Projects and Sprints.
"""

from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_sprint_report_pdf(project: dict, sprint: dict, metrics: dict, ai_risk: dict = None, recs: list = None, blockers: list = None) -> bytes:
    project = dict(project) if project else {}
    sprint = dict(sprint) if sprint else {}
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    section_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # Title Banner
    story.append(Paragraph(f"SPRINT REPORT: {sprint.get('name', 'Sprint')}", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Project: <b>{project.get('name', '')}</b> | Status: <b>{sprint.get('status', '')}</b> | Dates: {sprint.get('start_date', '')} to {sprint.get('end_date', '')}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=4, spaceAfter=12))

    # Sprint Goal
    if sprint.get('goal'):
        story.append(Paragraph("Sprint Goal:", section_heading))
        story.append(Paragraph(sprint['goal'], body_style))
        story.append(Spacer(1, 10))

    # Metrics Summary Table
    story.append(Paragraph("Sprint Metrics Overview", section_heading))
    m_data = [
        [
            Paragraph(f"<b>Tasks Completed:</b><br/>{metrics.get('completed_tasks', 0)} / {metrics.get('total_tasks', 0)} ({metrics.get('task_pct', 0)}%)", body_style),
            Paragraph(f"<b>Story Points:</b><br/>{metrics.get('completed_sp', 0)} / {metrics.get('total_sp', 0)} ({metrics.get('sp_pct', 0)}%)", body_style),
            Paragraph(f"<b>Recorded Velocity:</b><br/>{metrics.get('velocity', 0)} pts", body_style),
            Paragraph(f"<b>Hours Spent:</b><br/>{metrics.get('actual_hours', 0)}h (Est: {metrics.get('estimated_hours', 0)}h)", body_style)
        ]
    ]
    t_metrics = Table(m_data, colWidths=[135, 135, 135, 135])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 12))

    # AI Evaluation & Risk
    risk_level = ai_risk.get('risk_level') or ai_risk.get('predicted_risk') if ai_risk else 'N/A'
    story.append(Paragraph(f"AI Risk Assessment: <b>{risk_level}</b>", section_heading))
    if recs:
        story.append(Paragraph("<b>AI Scrum Recommendations:</b>", body_style))
        for r in recs[:3]:
            r_title = r.get('title', '')
            r_desc = r.get('description', '')
            story.append(Paragraph(f"• <b>{r_title}:</b> {r_desc}", body_style))
        story.append(Spacer(1, 10))

    # Stand-up Blockers
    if blockers:
        story.append(Paragraph("Daily Stand-up Blockers Identified:", section_heading))
        for b in blockers[:5]:
            story.append(Paragraph(f"• {b}", body_style))
        story.append(Spacer(1, 10))

    doc.build(story)
    pdf_val = buffer.getvalue()
    buffer.close()
    return pdf_val


def generate_project_report_pdf(project: dict, metrics: dict, ai_risk: dict = None, recs: list = None) -> bytes:
    project = dict(project) if project else {}
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'SubTitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    section_heading = ParagraphStyle(
        'SecHeading',
        parent=styles['Heading2'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#1e293b'),
        fontName='Helvetica-Bold',
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # Title Banner
    story.append(Paragraph(f"PROJECT OVERVIEW REPORT: {project.get('name', 'Project')}", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Status: <b>{project.get('status', 'Active')}</b> | Dates: {project.get('start_date', '')} to {project.get('end_date', '')}", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#cbd5e1'), spaceBefore=4, spaceAfter=12))

    # Metrics Summary Table
    story.append(Paragraph("Project Statistics & Progress", section_heading))
    m_data = [
        [
            Paragraph(f"<b>Overall Progress:</b><br/>{metrics.get('progress_pct', 0)}%", body_style),
            Paragraph(f"<b>Team Size:</b><br/>{metrics.get('team_size', 0)} members", body_style),
            Paragraph(f"<b>Total Sprints:</b><br/>{metrics.get('completed_sprints', 0)} / {metrics.get('total_sprints', 0)} done", body_style),
            Paragraph(f"<b>Overdue Tasks:</b><br/>{metrics.get('overdue_tasks', 0)} tasks", body_style)
        ],
        [
            Paragraph(f"<b>Backlog Items:</b><br/>{metrics.get('total_stories', 0)} stories", body_style),
            Paragraph(f"<b>Total Story Points:</b><br/>{metrics.get('total_sp', 0)} pts", body_style),
            Paragraph(f"<b>Tasks Completed:</b><br/>{metrics.get('completed_tasks', 0)} / {metrics.get('total_tasks', 0)}", body_style),
            Paragraph(f"<b>Project Health:</b><br/>{metrics.get('health', 'Healthy')}", body_style)
        ]
    ]
    t_metrics = Table(m_data, colWidths=[135, 135, 135, 135])
    t_metrics.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#e2e8f0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(t_metrics)
    story.append(Spacer(1, 12))

    # AI Evaluation & Recommendations
    risk_level = ai_risk.get('risk_level') or ai_risk.get('predicted_risk') if ai_risk else 'N/A'
    story.append(Paragraph(f"Latest AI Sprint Risk Level: <b>{risk_level}</b>", section_heading))
    if recs:
        story.append(Paragraph("<b>Key Action Items:</b>", body_style))
        for r in recs[:4]:
            r_title = r.get('title', '')
            r_desc = r.get('description', '')
            story.append(Paragraph(f"• <b>{r_title}:</b> {r_desc}", body_style))
        story.append(Spacer(1, 10))

    doc.build(story)
    pdf_val = buffer.getvalue()
    buffer.close()
    return pdf_val
