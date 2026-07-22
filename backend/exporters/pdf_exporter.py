"""PDF 导出"""

import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

# 注册中文字体
pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))


def export_pdf(data: dict) -> bytes:
    """将分析结果导出为 PDF"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()

    # 中文样式
    cn_style = ParagraphStyle('Chinese', parent=styles['Normal'], fontName='STSong-Light', fontSize=10)
    cn_title = ParagraphStyle('CNTitle', parent=styles['Title'], fontName='STSong-Light', fontSize=18)
    cn_heading = ParagraphStyle('CNHeading', parent=styles['Heading2'], fontName='STSong-Light', fontSize=14)

    story = []

    # 标题
    story.append(Paragraph("App Review Analysis Report", cn_title))
    story.append(Spacer(1, 10*mm))

    # 概览
    story.append(Paragraph("Overview", cn_heading))
    reviews = data.get("reviews", [])
    findings = data.get("findings", [])
    requirements = data.get("requirements", [])
    test_cases = data.get("test_cases", [])

    overview_data = [
        ["Metric", "Value"],
        ["Total Reviews", str(len(reviews))],
        ["Findings", str(len(findings))],
        ["Requirements", str(len(requirements))],
        ["Test Cases", str(len(test_cases))],
    ]
    t = Table(overview_data, colWidths=[100, 100])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e2d3d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, -1), 'STSong-Light'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(t)
    story.append(Spacer(1, 8*mm))

    # 发现
    if findings:
        story.append(Paragraph("Findings", cn_heading))
        for f in findings:
            story.append(Paragraph(f"<b>{f.get('topic', '')}</b> [{f.get('severity', '')}]", cn_style))
            story.append(Paragraph(f.get('description', ''), cn_style))
            story.append(Spacer(1, 3*mm))
        story.append(Spacer(1, 5*mm))

    # 需求
    if requirements:
        story.append(Paragraph("Requirements", cn_heading))
        for r in requirements:
            story.append(Paragraph(f"<b>{r.get('req_id', '')}: {r.get('title', '')}</b> [{r.get('priority', '')}]", cn_style))
            story.append(Paragraph(r.get('description', ''), cn_style))
            story.append(Spacer(1, 3*mm))
        story.append(Spacer(1, 5*mm))

    # 测试用例
    if test_cases:
        story.append(Paragraph("Test Cases", cn_heading))
        for tc in test_cases:
            story.append(Paragraph(f"<b>{tc.get('case_id', '')}: {tc.get('title', '')}</b>", cn_style))
            steps = tc.get('steps', [])
            for i, step in enumerate(steps, 1):
                story.append(Paragraph(f"  {i}. {step}", cn_style))
            story.append(Spacer(1, 2*mm))

    doc.build(story)
    return buffer.getvalue()
