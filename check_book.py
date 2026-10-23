"""Audit source retention, navigation, page numbers and text bounds."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from bs4 import BeautifulSoup
from pypdf import PdfReader
import pymupdf
from PIL import Image, ImageDraw

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--review', action='store_true', help='Render every page into review contact sheets')
args = parser.parse_args()
ROOT = Path(__file__).resolve().parent
PDF = ROOT/'output/pdf/cpsat-primer-letter.pdf'
QA = ROOT/'build/review'
QA.mkdir(parents=True,exist_ok=True)
source = BeautifulSoup((ROOT/'build/source/content.html').read_text(),'html.parser')
book = BeautifulSoup((ROOT/'build/source/book.html').read_text(),'html.parser')
assert Counter(t.get_text() for t in source.select('pre')) == Counter(t.get_text() for t in book.select('pre'))
for selector in ['img.math-svg','img:not(.math-svg)','table','details']:
    assert len(source.select(selector)) == len(book.select(selector)), selector
lost = Counter(t.get_text() for t in source.select('p')) - Counter(t.get_text() for t in book.select('p,figcaption'))
for text in lost:
    normalized = ' '.join(text.split())
    assert normalized.startswith('The CP-SAT Primer is maintained by') or normalized.startswith('If you find the primer helpful, consider leaving'), text
reader = PdfReader(PDF)
assert reader.outline
assert reader.metadata.title and reader.metadata.author and reader.metadata.subject
assert reader.xmp_metadata is not None
assert reader.xmp_metadata.dc_title['x-default'] == reader.metadata.title
assert reader.xmp_metadata.dc_creator == [reader.metadata.author]
assert reader.xmp_metadata.dc_source == reader.metadata['/Source']
destinations = reader.named_destinations
internal = external = 0
for page in reader.pages:
    for ref in page.get('/Annots',[]):
        a = ref.get_object()
        if isinstance(a.get('/Dest'),str):
            assert a['/Dest'] in destinations, a['/Dest']
            internal += 1
        elif a.get('/A',{}).get('/S') == '/URI':
            uri = a['/A']['/URI']
            assert not uri.startswith('file:'), uri
            external += 1
doc = pymupdf.open(PDF)
outside = []
short = []
numbering = []
page_counts = []
for i,page in enumerate(doc):
    assert tuple(round(v) for v in page.rect[2:]) == (612,792)
    text = page.get_text()
    page_counts.append(len(text))
    if i and not re.search(r'\b'+str(i+1)+r'\s*$',text):
        numbering.append(i+1)
    if i>5 and len(text)<300:
        short.append(i+1)
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines',[]):
            x0,y0,x1,y1=line['bbox']
            if x0<60 or x1>552 or y0<18 or y1>777:
                outside.append({'page':i+1,'box':line['bbox'],'text':''.join(s['text']for s in line['spans'])[:110]})
toc = book.select('.full-toc a[href]')
toc_pages = {}
printed_toc_checked = 0
for a in toc:
    name=a['href'][1:]
    assert name in destinations, name
    toc_pages[a.get_text(' ',strip=True)] = reader.get_destination_page_number(destinations[name])+1
    if 'toc-part' in a.parent.get('class',[]):
        continue
    found = False
    for page_index in range(reader.get_destination_page_number(destinations['contents']), reader.get_destination_page_number(destinations[book.select_one('.chapter-title')['id']])):
        for ref in reader.pages[page_index].get('/Annots',[]):
            annotation = ref.get_object()
            if annotation.get('/Dest') != name:
                continue
            x0,y0,x1,y1 = map(float,annotation['/Rect'])
            clip = pymupdf.Rect(x0,792-max(y0,y1),x1,792-min(y0,y1))
            words = doc[page_index].get_text('words',clip=clip)
            if words and words[-1][4] == str(toc_pages[a.get_text(' ',strip=True)]):
                found = True
                break
        if found:
            break
    assert found, f'Printed TOC page number could not be verified: {name}'
    printed_toc_checked += 1
report = {'pages':len(doc),'bookmarks':len(doc.get_toc()),'bookmark_depth':max(t[0]for t in doc.get_toc()),
          'internal_links':internal,'external_links':external,'toc_entries':len(toc),
          'toc_pages':toc_pages,'printed_toc_page_numbers_checked':printed_toc_checked,'numbering_issues':numbering,'text_outside_margins':outside,
          'short_pages':short,'source_content_retained':True}
(QA/'audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items()if k!='toc_pages'},indent=2),flush=True)
geometry = json.loads((ROOT/'build/geometry.json').read_text())
geometry_issues = [box for box in geometry if box['page']>1 and (
    box['x']<85 or box['x']+box['width']>731 or box['y']<80 or box['y']+box['height']>981)]
report['geometry_issues'] = geometry_issues
(QA/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
errors = [line for line in (ROOT/'build/build.log').read_text().splitlines() if line.startswith('ERROR:')]
if numbering or outside or geometry_issues or errors:
    raise RuntimeError(f'PDF audit failed: page numbers={numbering}, text bounds={outside[:3]}, graphics bounds={geometry_issues[:3]}, render errors={errors[:3]}')
if not args.review:
    raise SystemExit(0)
# Every page appears in a numbered contact sheet; flagged pages get larger renders.
for base in range(0,len(doc),20):
    canvas=Image.new('RGB',(4*320,5*435),'#b0b0b0')
    for offset in range(min(20,len(doc)-base)):
        page=doc[base+offset]
        pix=page.get_pixmap(matrix=pymupdf.Matrix(.5,.5))
        im=Image.frombytes('RGB',(pix.width,pix.height),pix.samples)
        x=(offset%4)*320+7;y=(offset//4)*435+22
        canvas.paste(im,(x,y))
        ImageDraw.Draw(canvas).text((x,y-17),str(base+offset+1),fill='black')
    canvas.save(QA/f'contact-{base+1:03}.png')
selected = set(short) | {item['page']for item in outside} | {1,2,3,4,5,6}
selected |= {t[2]for t in doc.get_toc()if t[0]<=2}
for n in sorted(selected):
    doc[n-1].get_pixmap(matrix=pymupdf.Matrix(1.1,1.1)).save(QA/f'page-{n:03}.png')
