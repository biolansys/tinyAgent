from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

root = Path('.').resolve()
skip = {'.git', '__pycache__', '.pytest_cache', '.venv', 'venv', 'node_modules'}

def list_dirs(base: Path, depth=0, max_depth=2):
    if depth > max_depth:
        return []
    rows = []
    try:
        children = sorted([p for p in base.iterdir() if p.is_dir() and p.name not in skip], key=lambda p: p.name.lower())
    except Exception:
        return rows
    for child in children:
        rows.append((depth, child.name))
        rows.extend(list_dirs(child, depth + 1, max_depth=max_depth))
    return rows

rows = [(0, root.name)] + list_dirs(root, 1, 2)

img_w, img_h = 1800, max(1200, 40 + len(rows) * 30)
img = Image.new('RGB', (img_w, img_h), '#f6fbff')
draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype('arial.ttf', 20)
    font_bold = ImageFont.truetype('arialbd.ttf', 24)
except Exception:
    font = ImageFont.load_default()
    font_bold = font

draw.rectangle((0, 0, img_w, 90), fill='#0b3d91')
draw.text((30, 28), 'Repository Hierarchy (depth <= 2)', fill='white', font=font_bold)

y = 120
for depth, name in rows:
    x = 40 + depth * 60
    if depth > 0:
        draw.line((x - 30, y + 10, x - 8, y + 10), fill='#4a6fa5', width=2)
    box_color = ['#dbeafe', '#e0f2fe', '#ecfccb', '#fef3c7'][min(depth, 3)]
    draw.rounded_rectangle((x, y, x + 620, y + 24), radius=6, fill=box_color, outline='#93c5fd', width=1)
    draw.text((x + 10, y + 4), name, fill='#0f172a', font=font)
    y += 30

img_path = root / 'repository_hierarchy.png'
img.save(img_path)

pdf_path = root / 'project_presentation_plan_beautified.pdf'
doc = SimpleDocTemplate(str(pdf_path), pagesize=A4, leftMargin=1.6*cm, rightMargin=1.6*cm, topMargin=1.4*cm, bottomMargin=1.4*cm)
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='TitleBlue', parent=styles['Title'], textColor=colors.HexColor('#0b3d91'), fontSize=24, leading=28, spaceAfter=10))
styles.add(ParagraphStyle(name='H2Blue', parent=styles['Heading2'], textColor=colors.HexColor('#1d4ed8'), fontSize=14, leading=18, spaceBefore=8, spaceAfter=4))
styles.add(ParagraphStyle(name='Body', parent=styles['BodyText'], fontSize=10.5, leading=14, textColor=colors.HexColor('#0f172a')))

story = []
story.append(Paragraph('OpenRouter Agent Project Structure', styles['TitleBlue']))
story.append(Paragraph('Presentation Summary', styles['H2Blue']))
story.append(Paragraph('Local AI coding agent with multi-provider routing, strong project isolation, plugin extensibility, and safety-oriented tool execution.', styles['Body']))
story.append(Spacer(1, 8))

bullets = [
    'Purpose: AI-assisted coding runtime for isolated projects under workspace/.',
    'Core modules: CLI dispatcher, runtime planner/executor/reviewer, tools, providers, plugins.',
    'Safety model: scoped paths, command validation, confirmations, dry-run, scoped worker patches.',
    'Operations: backups, logs, snapshots, project sessions, memory, checkpoints.',
]

data = [[Paragraph('- ' + b, styles['Body'])] for b in bullets]
table = Table(data, colWidths=[17.5*cm])
table.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#eef6ff')),
    ('BOX', (0,0), (-1,-1), 0.8, colors.HexColor('#93c5fd')),
    ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#bfdbfe')),
    ('LEFTPADDING', (0,0), (-1,-1), 8),
    ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ('TOPPADDING', (0,0), (-1,-1), 5),
    ('BOTTOMPADDING', (0,0), (-1,-1), 5),
]))
story.append(table)
story.append(Spacer(1, 12))
story.append(Paragraph('Directory / Subdirectory Hierarchy Diagram', styles['H2Blue']))
rlimg = RLImage(str(img_path), width=17.5*cm, height=17.5*cm * (img_h / img_w))
story.append(rlimg)
doc.build(story)
print(str(img_path))
print(str(pdf_path))
