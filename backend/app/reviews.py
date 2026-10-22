from .main import *
from .projects import retrieve, requirements



# Engineering Review v1: transparent rules-based screening, never an engineering approval.
REVIEW_FIELDS = [
    ('voltage','Voltage / distribution', r'\b\d+(?:\.\d+)?\s*(?:kV|VDC|VAC|V(?:\s*AC|\s*DC)?)\b', 'Record nominal distribution voltage and AC/DC designation.'),
    ('capacity','Power capacity', r'\b\d+(?:\.\d+)?\s*(?:MW|kW|MVA|kVA)\b', 'Record project or equipment power ratings.'),
    ('storage','Energy storage', r'\b\d+(?:\.\d+)?\s*(?:MWh|kWh)\b|\b(?:BESS|battery storage|energy storage)\b', 'Check whether energy storage is in scope and, if so, its ratings.'),
    ('frequency','AC frequency', r'\b(?:50|60)\s*Hz\b', 'Check frequency if AC power equipment is in scope.'),
    ('protection','Protection / safety', r'\b(?:breaker|circuit protection|short.circuit|grounding|earthing|arc.flash|protective relay|fault current)\b', 'Confirm protective design information is available for engineering review.'),
    ('drawings','Drawings / SLD', r'\b(?:single.line diagram|\bSLD\b|one.line diagram|electrical schematic|drawing number)\b', 'Check for electrical diagram references and revisions.'),
    ('interconnection','Grid / utility', r'\b(?:interconnection|point of common coupling|\bPCC\b|utility service|grid connection)\b', 'Identify grid interface or utility requirements where applicable.'),
    ('commissioning','Testing / commissioning', r'\b(?:commissioning|acceptance test|factory acceptance|\bFAT\b|site acceptance|\bSAT\b)\b', 'Identify validation or commissioning requirements.'),
]

@app.get('/projects/{project_id}/engineering-review')
def engineering_review(project_id: str, user=Depends(current_user)):
    with db() as conn:
        if not conn.execute('SELECT 1 FROM projects WHERE id=? AND owner_id=?', (project_id, user['id'])).fetchone():
            raise HTTPException(404, 'Project not found')
        rows = conn.execute('SELECT d.id AS document_id, d.filename, c.page_number, c.content ' +
            'FROM chunks c JOIN documents d ON c.document_id=d.id ' +
            'WHERE d.project_id=? ORDER BY d.created_at,c.page_number,c.id', (project_id,)).fetchall()
    items=[]
    for code, label, pattern, guidance in REVIEW_FIELDS:
        regex=re.compile(pattern,re.I)
        found=[]
        for row in rows:
            for m in regex.finditer(row['content']):
                nearby=row['content'][max(0,m.start()-100): min(len(row['content']),m.end()+120)]
                nearby=' '.join(nearby.split())
                candidate={'value':m.group(0),'filename':row['filename'],'page':row['page_number'], 'excerpt':nearby}
                if not any(x['value']==candidate['value'] and x['filename']==candidate['filename'] and x['page']==candidate['page'] for x in found):
                    found.append(candidate)
                if len(found)>=5:break
            if len(found)>=5:break
        items.append({'id':code,'label':label,'status':'evidence_found' if found else 'not_found',
            'evidence':found, 'guidance':guidance})
    return {'project_id':project_id,'document_count':len(set(row['document_id'] for row in rows)),
            'checks':items,'evidence_count':sum(bool(x['evidence']) for x in items),
            'disclaimer':'Automated text screening only. Missing mentions are not proof of missing design requirements. Evidence is unverified and must be checked against original documents by qualified engineers.'}


# Conservative text-based comparison of explicitly named engineering quantities.
# This is a candidate discrepancy scanner, NOT design verification or electrical engineering approval.
COMPARE_FIELDS = [
 ('design_capacity','Design power capacity',r'(?:nominal\s+)?(?:electrical\s+)?design\s+capacity\s*(?:is|:|of)?\s*(\d+(?:\.\d+)?)\s*(MW|kW)\b', {'kw':1,'mw':1000}, 'kW'),
 ('peak_it_load','Peak IT load',r'(?:peak\s+IT\s+(?:demand|load))\s*(?:is|:|of)?\s*(\d+(?:\.\d+)?)\s*(MW|kW)\b', {'kw':1,'mw':1000}, 'kW'),
 ('dc_bus_voltage','DC bus voltage',r'(?:DC\s+bus(?:\s+voltage)?|bus\s+voltage|DC\s+distribution\s+voltage)\s*(?:is\s+set\s+to|is\s+rated\s+at|rated\s+at|of|is|:|at)?\s*(\d+(?:\.\d+)?)\s*(kVDC|VDC|kV\s*DC|V\s*DC|kV|V)\b', {'vdc':1,'kvdc':1000,'v':1,'kv':1000}, 'VDC'),
 ('battery_capacity','Battery usable energy',r'(?:usable\s+energy\s+capacity|battery\s+(?:energy\s+)?capacity)\s*(?:of|is|:)?\s*(\d+(?:\.\d+)?)\s*(kWh|MWh)\b', {'kwh':1,'mwh':1000}, 'kWh'),
 ('ac_frequency','AC frequency',r'(?:AC\s+frequency|system\s+frequency|grid\s+frequency)\s*(?:of|is|:)?\s*(\d+(?:\.\d+)?)\s*(Hz)\b', {'hz':1}, 'Hz'),
 ('transformer_rating','Main transformer rating',r'(?:main\s+)?transformer\s+(?:rating|capacity)\s*(?:of|is|:)?\s*(\d+(?:\.\d+)?)\s*(kVA|MVA)\b', {'kva':1,'mva':1000}, 'kVA'),
]

def compare_specifications(rows):
    """Find candidate differences in named fields; preserve intra-document ambiguity."""
    groups=[]
    for field,label,pattern,units,canonical in COMPARE_FIELDS:
        rx=re.compile(pattern,re.I)
        matches=[]
        for row in rows:
            content=row['content']
            hits=list(rx.finditer(content))
            if field=='dc_bus_voltage':
                # Common alternative: "800 VDC bus", "800 VDC DC bus" or "800 VDC bus voltage".
                # Reject an isolated voltage unless accompanied by a bus designation.
                reverse=re.compile(r'\b(\d+(?:\.\d+)?)\s*(kVDC|VDC|kV\s*DC|V\s*DC)\s+(?:DC\s+)?bus(?:\s+voltage)?\b',re.I)
                hits+=list(reverse.finditer(content))
            for m in hits:
                # A historical comparison is evidence, not the current revision's rating.
                nearby=content[max(0,m.start()-100):m.start()].lower()
                if re.search(r'(?:previously documented|previous revision|formerly specified|prior design)\s*$|revision\s+a(?:\s+nominal\s+electrical)?\s*$',nearby):
                    continue
                raw=float(m.group(1));unit=re.sub(r'\s+','',m.group(2).lower())
                if unit not in units: continue
                normalized=round(raw*units[unit],6)
                item={'document_id':row['document_id'],'filename':row['filename'],'page':row['page_number'],
                      'value':m.group(0),'normalized_value':normalized,'normalized_unit':canonical,
                      'excerpt':' '.join(content[max(0,m.start()-85):min(len(content),m.end()+110)].split())}
                if not any(x['document_id']==item['document_id'] and x['page']==item['page'] and x['normalized_value']==normalized for x in matches):
                    matches.append(item)
        bydoc={}
        for x in matches: bydoc.setdefault(x['document_id'],set()).add(x['normalized_value'])
        # A document containing two distinct values is ambiguous, and must not be
        # treated as one unambiguous requirement or used to assert a resolved conflict.
        ambiguities=[did for did,values in bydoc.items() if len(values)>1]
        singles=[next(iter(values)) for values in bydoc.values() if len(values)==1]
        cross_diff=len(set(singles))>1
        status=('possible_conflict' if cross_diff else
                'internal_ambiguity' if ambiguities else
                'consistent_evidence' if len(bydoc)>1 else 'insufficient_comparison')
        note=('Different unambiguous values appear across documents; confirm scope and revision.' if cross_diff else
              'Multiple values were detected within the same document. Check their roles before comparing.' if ambiguities else
              'Same named value found in multiple documents; this does not prove full consistency.' if len(bydoc)>1 else
              'Only one document has a match for this field; cross-document comparison is incomplete.')
        groups.append({'id':field,'label':label,'status':status,'document_count':len(bydoc),
                       'evidence':matches[:20],'note':note,'ambiguous_document_count':len(ambiguities)})
    return groups

@app.get('/projects/{project_id}/conflicts')
def project_conflicts(project_id: str, user=Depends(current_user)):
    with db() as conn:
        if not conn.execute('SELECT 1 FROM projects WHERE id=? AND owner_id=?', (project_id,user['id'])).fetchone():
            raise HTTPException(404, 'Project not found')
        rows=conn.execute("SELECT d.id AS document_id,d.filename,c.page_number,c.content FROM chunks c JOIN documents d ON c.document_id=d.id WHERE d.project_id=? ORDER BY d.created_at,c.page_number,c.id",(project_id,)).fetchall()
    groups=compare_specifications(rows)
    count=len(set(r['document_id'] for r in rows))
    return {'project_id':project_id,'document_count':count,'possible_conflicts':sum(g['status']=='possible_conflict' for g in groups),
            'checks':groups,'disclaimer':'Candidate discrepancies from extracted text only. Requires at least two documents for comparison; not a design or code compliance check. Confirm field roles, revision dates, and context with qualified engineers.'}


@app.get('/projects/{project_id}/engineering-report.pdf')
def engineering_report_pdf(project_id: str, user=Depends(current_user)):
    """Download a private, evidence-based screening report (not a design approval)."""
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.units import inch
    from reportlab.lib.pagesizes import A4
    from xml.sax.saxutils import escape

    with db() as conn:
        project=conn.execute('SELECT name FROM projects WHERE id=? AND owner_id=?',(project_id,user['id'])).fetchone()
        if not project: raise HTTPException(404, 'Project not found')
        docs=conn.execute('SELECT filename FROM documents WHERE project_id=? ORDER BY created_at, id',(project_id,)).fetchall()
    screening=engineering_review(project_id,user)
    comparison=project_conflicts(project_id,user)
    stream=io.BytesIO()
    doc=SimpleDocTemplate(stream,pagesize=A4,rightMargin=43,leftMargin=43,topMargin=48,bottomMargin=48,title='EngiFlow AI Engineering Review')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportTitleX',parent=styles['Title'],fontSize=19,leading=24,textColor=colors.HexColor('#32235d'),spaceAfter=10))
    styles.add(ParagraphStyle(name='SectionX',parent=styles['Heading2'],fontSize=12,leading=16,textColor=colors.HexColor('#47378c'),spaceBefore=11,spaceAfter=5))
    styles.add(ParagraphStyle(name='BodyX',parent=styles['BodyText'],fontSize=9,leading=12,spaceAfter=4))
    styles.add(ParagraphStyle(name='SmallX',parent=styles['BodyText'],fontSize=8,leading=10,textColor=colors.HexColor('#555b6f'),spaceAfter=3))
    def para(t,style='BodyX'): return Paragraph(escape(str(t)),styles[style])
    story=[Paragraph('EngiFlow AI | Engineering Review',styles['ReportTitleX']),para('Project: '+project['name']),para('Generated (UTC): '+datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')),para(f'Documents: {len(docs)} | Screening topics with evidence: {screening["evidence_count"]}/{len(screening["checks"])} | Candidate discrepancies: {comparison["possible_conflicts"]}')]
    story += [para('This is automated text screening, not an engineering design review, safety validation, or compliance approval. Every finding requires source verification and qualified engineering judgment.','SmallX'),Paragraph('Input documents',styles['SectionX'])]
    for d in docs: story.append(para('- '+d['filename'],'SmallX'))
    if not docs: story.append(para('No uploaded documents found.'))
    story.append(Paragraph('Specification evidence screening',styles['SectionX']))
    for item in screening['checks']:
        pieces=[para(item['label']+' — '+('Evidence located' if item['evidence'] else 'No textual evidence located'))]
        for e in item['evidence'][:2]: pieces.append(para(f'{e["value"]} | {e["filename"]} | page {e["page"]}', 'SmallX'))
        if not item['evidence']: pieces.append(para(item['guidance'],'SmallX'))
        story.append(KeepTogether(pieces))
    story.append(Paragraph('Cross-document specification comparison',styles['SectionX']))
    if len(docs)<2: story.append(para('Insufficient documents for a cross-document comparison.'))
    for item in comparison['checks']:
        state={'possible_conflict':'REVIEW DIFFERENCE','internal_ambiguity':'CHECK AMBIGUOUS VALUES',
               'consistent_evidence':'MATCHING EVIDENCE','insufficient_comparison':'INSUFFICIENT COMPARISON'}[item['status']]
        story.append(para(item['label']+' — '+state))
        story.append(para(item['note'],'SmallX'))
        if item['evidence']:
            head=[para('Value','SmallX'),para('Source document','SmallX'),para('Page','SmallX')]
            data=[head]
            for e in item['evidence'][:10]:
                data.append([para(f'{e["normalized_value"]:g} {e["normalized_unit"]}','SmallX'),
                             para(e['filename'],'SmallX'),para(str(e['page']),'SmallX')])
            table=Table(data,colWidths=[82,355,55],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eeebfa')),
                ('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),0.6,colors.HexColor('#cabff3')),
                ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f8f7fc')]),
                ('BOTTOMPADDING',(0,0),(-1,-1),4),('TOPPADDING',(0,0),(-1,-1),4)]))
            story.append(table)
        story.append(Spacer(1,5))
    story.append(KeepTogether([Paragraph('Follow-up actions',styles['SectionX']),para('1. Confirm that compared values describe the same equipment, engineering role, scope, and design revision.'),para('2. Validate extracted values against the original documents and applicable drawings.'),para('3. Have a qualified engineer resolve any true conflicts and document decisions.'),para('4. Treat topics without text evidence as open questions, not confirmed omissions.')]))
    def footer(canvas,document):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#777788'))
        canvas.drawString(43,30,'EngiFlow AI | Prototype automated screening | Not for engineering approval')
        canvas.drawRightString(A4[0]-43,30,f'Page {document.page}');canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    stream.seek(0)
    return StreamingResponse(stream,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="engiflow-engineering-review.pdf"','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
