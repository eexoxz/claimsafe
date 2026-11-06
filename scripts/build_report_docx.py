"""Build the formal report from Markdown and the sanitised reference styles.

PDF export is deliberately through the saved DOCX, rather than a second layout engine.
Run --export-pdf on Windows with Microsoft Word installed, or export the DOCX in Word.
"""
from __future__ import annotations

import argparse
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]
ASSETS = REPO / 'docs/report-assets'
SOURCE = REPO / 'docs/REPORT_DRAFT.md'
TEMPLATE = ASSETS / 'report-template.docx'


def set_font(style, size=12, bold=False):
    style.font.name = 'Times New Roman'
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    props = style.element.get_or_add_rPr()
    fonts = props.find(qn('w:rFonts'))
    if fonts is not None:
        for k in ('asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme'):
            fonts.attrib.pop(qn('w:'+k),None)
        for k in ('ascii','hAnsi','eastAsia','cs'):
            fonts.set(qn('w:'+k),'Times New Roman')
    color = props.find(qn('w:color'))
    if color is not None:
        color.attrib.pop(qn('w:themeColor'),None)


def field(p, instruction, cached=''):
    run = p.add_run()
    begin = OxmlElement('w:fldChar'); begin.set(qn('w:fldCharType'),'begin')
    code = OxmlElement('w:instrText'); code.set(qn('xml:space'),'preserve')
    code.text = ' ' + instruction + ' '
    separate = OxmlElement('w:fldChar'); separate.set(qn('w:fldCharType'),'separate')
    value = OxmlElement('w:t'); value.text = cached
    end = OxmlElement('w:fldChar'); end.set(qn('w:fldCharType'),'end')
    for node in (begin,code,separate,value,end):
        run._r.append(node)


def page_numbers(section, fmt, start=1):
    section.footer.is_linked_to_previous = False
    p = section.footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1
    field(p,'PAGE')
    for run in p.runs:
        run.font.name = 'Times New Roman'; run.font.size = Pt(12)
    pg = section._sectPr.find(qn('w:pgNumType'))
    if pg is None:
        pg = OxmlElement('w:pgNumType'); section._sectPr.append(pg)
    pg.set(qn('w:fmt'),fmt); pg.set(qn('w:start'),str(start))


def diagrams():
    font_dir = Path('C:/Windows/Fonts')
    def font(size, bold=False):
        candidate = font_dir / ('timesbd.ttf' if bold else 'times.ttf')
        if candidate.exists():
            return ImageFont.truetype(str(candidate),size)
        return ImageFont.load_default(size=size)
    def canvas(height):
        im = Image.new('RGB',(1800,height),'white')
        return im,ImageDraw.Draw(im)
    def box(draw,xy,title,lines):
        draw.rectangle(xy,fill='#f6f6f6',outline='black',width=3)
        x1,y1,x2,y2=xy
        draw.text(((x1+x2)/2,y1+30),title,fill='black',font=font(38,True),anchor='mt')
        for n,line in enumerate(lines):
            draw.text(((x1+x2)/2,y1+90+43*n),line,fill='black',font=font(32),anchor='mt')
    def arrow(draw,start,end):
        draw.line((start,end),fill='black',width=4)
        x,y=end; sx,sy=start
        if abs(x-sx)>abs(y-sy):
            direction=1 if x>sx else -1
            draw.polygon([(x,y),(x-20*direction,y-12),(x-20*direction,y+12)],fill='black')
        else:
            direction=1 if y>sy else -1
            draw.polygon([(x,y),(x-12,y-20*direction),(x+12,y-20*direction)],fill='black')
    im,d=canvas(1000)
    nodes=[
        ((30,145,350,405),'Browser',['Students and staff','Untrusted requests']),
        ((480,145,800,405),'Caddy',['TLS termination','Static files']),
        ((930,145,1290,405),'Application',['Waitress and Django','Proxy authentication']),
        ((1420,145,1780,405),'SQLite database',['Encrypted private fields','Claims and audit events']),
        ((480,555,800,780),'Local CA',['Certificate and key','Explicit client trust']),
        ((930,555,1290,780),'Private keys',['Protected profile files','Field and proxy keys']),
    ]
    arrows=[((350,265),(480,265)),((800,265),(930,265)),((1290,265),(1420,265)),((640,555),(640,405)),((1110,555),(1110,405))]
    labels=[((1100,48),'Protected loopback profile',29),((415,205),'HTTPS',26),((415,335),'8443',26),((865,205),'Loopback',26),((865,335),'HTTP 9010',24),((1355,335),'ORM',28),((900,870),'Database and keys are outside the static web root.',32),((900,925),'HTTPS ends at Caddy; internal HTTP stays on loopback.',32)]
    d.rectangle((430,85,1795,820),outline='#777777',width=2)
    for xy,title,lines in nodes: box(d,xy,title,lines)
    for start,end in arrows: arrow(d,start,end)
    for xy,label,size in labels: d.text(xy,label,font=font(size),anchor='mm',fill='black')
    im.save(ASSETS/'architecture.png',dpi=(300,300))
    # Retain a vector source from the same graph used for the report raster.
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1000" viewBox="0 0 1800 1000">',
         '<rect width="1800" height="1000" fill="white"/>',
         '<defs><marker id="arrow" viewBox="0 0 10 10" refX="10" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M 0 0 L 10 5 L 0 10 z"/></marker></defs>',
         '<g font-family="Times New Roman,serif" fill="black" text-anchor="middle">',
         '<rect x="430" y="85" width="1365" height="735" fill="none" stroke="#777" stroke-width="2"/>']
    for (x1,y1,x2,y2),title,lines in nodes:
        svg.append(f'<rect x="{x1}" y="{y1}" width="{x2-x1}" height="{y2-y1}" fill="#f6f6f6" stroke="black" stroke-width="3"/>')
        svg.append(f'<text x="{(x1+x2)/2}" y="{y1+66}" font-size="38" font-weight="bold">{escape(title)}</text>')
        for n,line in enumerate(lines): svg.append(f'<text x="{(x1+x2)/2}" y="{y1+120+43*n}" font-size="32">{escape(line)}</text>')
    for (x1,y1),(x2,y2) in arrows: svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="black" stroke-width="4" marker-end="url(#arrow)"/>')
    for (x,y),label,size in labels: svg.append(f'<text x="{x}" y="{y+size/3}" font-size="{size}">{escape(label)}</text>')
    svg.append('</g></svg>')
    (ASSETS/'architecture.svg').write_text('\n'.join(svg),encoding='utf-8')
    im,d=canvas(820)
    d.text((65,35),'CLAIM',font=font(38,True),fill='black')
    for xy,title in [((100,130,520,290),'Pending'),((690,130,1110,290),'Approved'),((1280,130,1700,290),'Collected'),((100,360,520,510),'Rejected')]:
        box(d,xy,title,[])
    arrow(d,(520,210),(690,210)); arrow(d,(1110,210),(1280,210)); arrow(d,(310,290),(310,360))
    d.text((605,158),'Review',font=font(29),anchor='mm',fill='black')
    d.text((1195,150),'Valid code',font=font(29),anchor='mm',fill='black')
    d.text((1195,315),'Officer confirms',font=font(28),anchor='mm',fill='black')
    d.text((1195,350),'handover',font=font(28),anchor='mm',fill='black')
    d.text((350,328),'Not approved',font=font(28),fill='black')
    d.text((65,570),'ITEM',font=font(38,True),fill='black')
    for xy,title in [((100,640,520,795),'Available'),((690,640,1110,795),'Reserved'),((1280,640,1700,795),'Returned')]:
        box(d,xy,title,[])
    arrow(d,(520,720),(690,720)); arrow(d,(1110,720),(1280,720))
    im.save(ASSETS/'workflow.png',dpi=(300,300))


def hyperlink(p,url):
    rel = p.part.relate_to(url,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',is_external=True)
    link = OxmlElement('w:hyperlink'); link.set(qn('r:id'),rel)
    run = OxmlElement('w:r'); props = OxmlElement('w:rPr')
    color = OxmlElement('w:color'); color.set(qn('w:val'),'000000'); props.append(color)
    run.append(props); text=OxmlElement('w:t'); text.text=url; run.append(text)
    link.append(run); p._p.append(link)


def paragraph(doc,text,style='Normal'):
    p=doc.add_paragraph(style=style)
    # References keep proper URL hyperlinks and may wrap naturally in Word.
    pieces=re.split(r'(https?://\S+)',text)
    for piece in pieces:
        if piece.startswith(('https://','http://')):
            hyperlink(p,piece)
        else:
            p.add_run(piece)
    return p


def caption(doc,text):
    match=re.match(r'(Figure|Table) (\d+) (.*)',text)
    if not match:
        raise ValueError(text)
    kind,number,title=match.groups()
    p=doc.add_paragraph(style='Caption')
    p.add_run(kind+' '); field(p,f'SEQ {kind} \\* ARABIC',number); p.add_run(' '+title)
    return p


def table(doc,rows):
    t=doc.add_table(rows=len(rows),cols=len(rows[0]))
    t.alignment=WD_TABLE_ALIGNMENT.CENTER; t.autofit=False
    widths={4:[2.0,.8,1.65,1.82],3:[1.85,.7,3.72],2:[2.65,3.62]}[len(rows[0])]
    if rows[0] == ['Category', 'Evidence', 'Remaining boundary']:
        widths = [1.85, 2.05, 2.37]
    for col,width in zip(t.columns,widths):
        col.width=Inches(width)
    borders=OxmlElement('w:tblBorders')
    for side in ['top','left','bottom','right','insideH','insideV']:
        b=OxmlElement('w:'+side)
        for key,val in [('val','single'),('sz','4'),('color','D9D9D9')]:
            b.set(qn('w:'+key),val)
        borders.append(b)
    t._tbl.tblPr.append(borders)
    for r,row in enumerate(rows):
        trpr=t.rows[r]._tr.get_or_add_trPr()
        cant=OxmlElement('w:cantSplit'); trpr.append(cant)
        if r==0:
            repeat=OxmlElement('w:tblHeader'); trpr.append(repeat)
        for c,value in enumerate(row):
            cell=t.cell(r,c); cell.width=Inches(widths[c])
            cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p=cell.paragraphs[0]; p.style='Report Table'
            if c==1 and (len(row)==4 or rows[0][1]=='Priority'):
                p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            run=p.add_run(value); run.bold=r==0
            margins=OxmlElement('w:tcMar')
            for side in ['top','bottom','left','right']:
                v=OxmlElement('w:'+side); v.set(qn('w:w'),'100'); v.set(qn('w:type'),'dxa'); margins.append(v)
            cell._tc.get_or_add_tcPr().append(margins)
            if r==0:
                shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'EEEEEE'); cell._tc.get_or_add_tcPr().append(shade)
    # A small paragraph after a table separates it from the following narrative.
    after=doc.add_paragraph(); after.paragraph_format.space_after=Pt(0); after.paragraph_format.line_spacing=1
    after.paragraph_format.space_before=Pt(0); after.add_run().font.size=Pt(3)
    return t


def build(output_dir):
    output_dir.mkdir(parents=True,exist_ok=True)
    text=SOURCE.read_text(encoding='utf-8')
    if not all((ASSETS / name).is_file() for name in ['architecture.png', 'workflow.png']):
        diagrams()
    d=Document(TEMPLATE)
    normal=d.styles['Normal']; set_font(normal)
    pf=normal.paragraph_format
    pf.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY; pf.line_spacing=1.5
    pf.space_before=Pt(0); pf.space_after=Pt(12)
    pf.first_line_indent=Pt(0); pf.left_indent=Pt(0); pf.right_indent=Pt(0)
    pf.widow_control=True; pf.keep_with_next=False; pf.keep_together=False
    for name in ['Heading 1','Heading 2','Heading 3']:
        s=d.styles[name]; set_font(s,12,True)
        s.paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
        s.paragraph_format.line_spacing=1.5; s.paragraph_format.keep_with_next=True
        s.paragraph_format.space_after=Pt(6)
        s.paragraph_format.space_before=Pt(12 if name=='Heading 1' else 6)
    set_font(d.styles['Title'],14,True)
    d.styles['Title'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for name,size,bold in [('Report Front',12,False),('Report Subtitle',16,True),('Report Reference',11,False),('Report Table',10.5,False),('Report Code',9,False),('Front Heading',12,True),('Appendix Heading',12,True)]:
        if name not in d.styles:
            s=d.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
        else:
            s=d.styles[name]
        s.base_style=normal; set_font(s,size,bold)
        s.paragraph_format.line_spacing=1.5
    for name in ['Report Front','Report Subtitle']:
        d.styles[name].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
    d.styles['Report Table'].paragraph_format.line_spacing=1.15
    d.styles['Report Table'].paragraph_format.space_after=Pt(0)
    d.styles['Report Table'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
    d.styles['Report Reference'].paragraph_format.line_spacing=1.15
    d.styles['Report Reference'].paragraph_format.left_indent=Inches(.3)
    d.styles['Report Reference'].paragraph_format.first_line_indent=Inches(-.3)
    d.styles['Report Reference'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
    d.styles['Report Code'].font.name='Consolas'
    d.styles['Report Code'].paragraph_format.line_spacing=1.15
    d.styles['Report Code'].paragraph_format.space_after=Pt(0)
    d.styles['Report Code'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.LEFT
    d.styles['Front Heading'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
    d.styles['Front Heading'].paragraph_format.keep_with_next=True
    set_font(d.styles['Caption'],10.5)
    d.styles['Caption'].paragraph_format.alignment=WD_ALIGN_PARAGRAPH.CENTER
    d.styles['Caption'].paragraph_format.line_spacing=1.15
    d.styles['Caption'].paragraph_format.space_after=Pt(12)
    d.styles['Caption'].paragraph_format.keep_with_next=False
    for name in ['toc 1','toc 2','table of figures']:
        if name not in d.styles:
            d.styles.add_style(name,WD_STYLE_TYPE.PARAGRAPH)
        set_font(d.styles[name],11)
        d.styles[name].paragraph_format.line_spacing=1
        d.styles[name].paragraph_format.space_after=Pt(4)
    d.core_properties.title='ClaimSafe Secure Campus Lost Property Claim and Collection System'
    d.core_properties.author='Ooi Ee Sheng'
    d.core_properties.subject='Security 6000CMD and 6005CEM coursework report'
    d.core_properties.last_modified_by=''
    settings=d.settings.element
    update=OxmlElement('w:updateFields'); update.set(qn('w:val'),'true'); settings.append(update)

    cover=paragraph(d,'ClaimSafe Secure Campus Lost Property Claim and Collection System','Title')
    cover.paragraph_format.space_before=Pt(90)
    cover.paragraph_format.space_after=Pt(48)
    paragraph(d,'Security 6000CMD and 6005CEM','Report Front')
    paragraph(d,'Secure Application Development and Implementation','Report Front')
    p=paragraph(d,'Ooi Ee Sheng','Report Front'); p.paragraph_format.space_before=Pt(36)
    paragraph(d,'Coventry Student ID 15384832','Report Front')
    report_date=next(line for line in text.splitlines() if re.fullmatch(r'\d{1,2} [A-Za-z]+ \d{4}',line))
    p=paragraph(d,report_date,'Report Front'); p.paragraph_format.space_before=Pt(36)
    prelim=d.add_section(WD_SECTION_START.NEW_PAGE); page_numbers(prelim,'lowerRoman')
    body_heading='## 1.0 Introduction and System Overview'
    paragraph(d,'TABLE OF CONTENTS','Front Heading')
    field(d.add_paragraph(),'TOC \\o "1-2" \\h \\z \\u')
    d.add_page_break(); paragraph(d,'LIST OF FIGURES','Front Heading')
    field(d.add_paragraph(),'TOC \\h \\z \\c "Figure"')
    p=paragraph(d,'LIST OF TABLES','Front Heading'); p.paragraph_format.space_before=Pt(24)
    field(d.add_paragraph(),'TOC \\h \\z \\c "Table"')
    body=d.add_section(WD_SECTION_START.NEW_PAGE); page_numbers(body,'decimal')
    lines=(body_heading+text.split(body_heading,1)[1]).splitlines()
    i=0; first=True; reference_mode=False
    while i<len(lines):
        line=lines[i].strip()
        if not line:
            i+=1; continue
        if line.startswith('## '):
            title=line[3:]
            p=d.add_paragraph(title,'Heading 1')
            p.paragraph_format.page_break_before = not first
            first=False; reference_mode=title=='6.0 References'
            i+=1; continue
        if line.startswith('### '):
            style='Heading 2' if re.match(r'### \d+\.\d+ ',line) else 'Appendix Heading'
            p=d.add_paragraph(line[4:],style)
            p.paragraph_format.keep_with_next=True
            i+=1; continue
        if line.startswith('!['):
            match=re.fullmatch(r'!\[(.*?)\]\((.*?)\)',line)
            label,location=match.groups(); image_path=ASSETS/Path(location).name
            p=d.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next=True; p.paragraph_format.space_after=Pt(4)
            p.paragraph_format.line_spacing=1
            run=p.add_run(); shape=run.add_picture(str(image_path),width=Inches(6.27))
            shape._inline.docPr.set('descr',label)
            caption(d,label); i+=1; continue
        if re.fullmatch(r'Table \d+ [^.]+',line):
            p=caption(d,line); p.paragraph_format.keep_with_next=True
            i+=1; continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                row=[v.strip() for v in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',v) for v in row):
                    rows.append(row)
                i+=1
            table(d,rows); continue
        if line.startswith('```'):
            i+=1
            while i<len(lines) and not lines[i].startswith('```'):
                p=d.add_paragraph(lines[i],'Report Code'); p.paragraph_format.keep_with_next=True
                i+=1
            if d.paragraphs:
                d.paragraphs[-1].paragraph_format.keep_with_next=False
            i+=1; continue
        block=[line]; i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','![','```','Table ')):
            block.append(lines[i].strip()); i+=1
        paragraph(d,' '.join(block),'Report Reference' if reference_mode else 'Normal')
    final=output_dir/'ClaimSafe_Report_Draft.docx'
    d.save(final)
    shutil.copyfile(SOURCE,output_dir/'ClaimSafe_Report_Draft.md')
    if (output_dir/'report-assets').resolve()!=ASSETS.resolve():
        shutil.copytree(ASSETS,output_dir/'report-assets',dirs_exist_ok=True)
    main=text.split(body_heading,1)[1].split('## 6.0 References',1)[0]
    print(json.dumps({'docx':str(final),'main_words':len(re.findall(r"\b[\w]+(?:['’-][\w]+)*\b",main))}))
    return final


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=REPO/'.local/report')
    parser.add_argument('--export-pdf',action='store_true',help='Update fields and export using installed Microsoft Word on Windows')
    args=parser.parse_args()
    final=build(args.output_dir.resolve())
    if args.export_pdf:
        subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(REPO/'scripts/export_report.ps1'),'-DocumentPath',str(final),'-PdfPath',str(final.with_suffix('.pdf'))],check=True)


if __name__=='__main__':
    main()
