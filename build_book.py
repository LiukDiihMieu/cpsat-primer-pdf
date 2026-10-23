"""Build the complete Letter reading edition from frozen official HTML."""
from collections import Counter
from copy import copy
import html
import json
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup
from weasyprint import HTML

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output/pdf'
OUT.mkdir(parents=True, exist_ok=True)
BUILD = ROOT/'build'
(BUILD/'review').mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=BUILD/'build.log', filemode='w', level=logging.WARNING)
source_path = ROOT/'build/source/content.html'
source = BeautifulSoup(source_path.read_text(), 'html.parser')
main = source.select_one('main')
chapter_metadata = json.loads((BUILD/'source/chapters.json').read_text())
chapters = [(c['start_id'], c['title'], c['part']) for c in chapter_metadata]
metadata = json.loads((BUILD/'metadata.json').read_text())

doc = BeautifulSoup('<!doctype html><html lang="en" class="light"><head><meta charset="utf-8"><title>The CP-SAT Primer - Unofficial Letter PDF Edition</title><meta name="author" content="Dominik Krupke and contributors"></head><body><main></main></body></html>', 'html.parser')
for name in ['build/source/official.css', 'print.css', 'book.css']:
    doc.head.append(doc.new_tag('link', rel='stylesheet', href=(ROOT/name).as_uri()))
body = doc.select_one('main')
cover = copy(main.select_one('img'))
cover_section = doc.new_tag('section', attrs={'class':'cover'})
cover_section.append(cover)
body.append(cover_section)
commit = metadata['upstream_commit']
built_date = metadata['built_at'][:10]
front = f'''<section class="edition"><h1>The CP-SAT Primer</h1>
<p class="subtitle">Using and Understanding Google OR-Tools' CP-SAT Solver<br>Unofficial Letter PDF edition</p>
<p>By Dominik Krupke, with contributions from Leon Lan, Michael Perk, and <a href="https://github.com/d-krupke/cpsat-primer/graphs/contributors">other contributors</a>.</p>
<p>Original: <a href="https://d-krupke.github.io/cpsat-primer/">The CP-SAT Primer website</a><br>
Source: <a href="https://github.com/d-krupke/cpsat-primer">d-krupke/cpsat-primer</a></p>
<p>The original work and this reading edition are distributed under <a href="https://creativecommons.org/licenses/by/4.0/">Creative Commons Attribution 4.0 International (CC BY 4.0)</a>. Existing third-party notices remain applicable.</p>
<p>Unofficial PDF edition, reformatted for print. Not endorsed by the original author or the OR-Tools team.</p>
<p class="small">Based on upstream revision <a href="https://github.com/d-krupke/cpsat-primer/commit/{commit}">{commit[:12]}</a> · Built {built_date}</p></section>'''
body.append(BeautifulSoup(front, 'html.parser'))
toc = doc.new_tag('nav', attrs={'class':'toc full-toc'})
toc_title = doc.new_tag('h1', id='contents')
toc_title.string = 'Contents'
toc.append(toc_title)
body.append(toc)
chapter_sections = []
excluded = Counter()
for index, (start_id, title, part) in enumerate(chapters):
    start = source.find(id=start_id)
    stop = source.find(id=chapters[index+1][0]) if index+1 < len(chapters) else None
    assert start and start.parent == main, start_id
    section = doc.new_tag('section', attrs={'class':'chapter'})
    if part:
        part_id = re.sub(r'[^a-z0-9]+', '-', part.lower()).strip('-')
        h = doc.new_tag('h1', id=part_id, attrs={'class':'part-title'})
        h.string = part
        section.append(h)
        p = doc.new_tag('p', attrs={'class':'toc-part'})
        a = doc.new_tag('a', href='#'+part_id)
        a.string = part
        p.append(a)
        toc.append(p)
    heading = doc.new_tag('h2', id=start_id, attrs={'class':'chapter-title'})
    if index == 0:
        heading['style'] = 'bookmark-level:1'
    heading.string = title
    section.append(heading)
    node = start.next_sibling
    while node and node != stop:
        if not (getattr(node,'name',None) == 'h1' and node.get_text().startswith('Part ')):
            section.append(copy(node))
        node = node.next_sibling
    # Part headings belong to the following chapter, rather than the previous one.
    for h in section.select('h1:not(.part-title)'):
        anchor = doc.new_tag('span', id=h.get('id', ''))
        h.replace_with(anchor)
    # mdBook inserts a title before a chapter that already has its own title.
    # A second title before any prose is mdBook's redundant chapter heading.
    for candidate in list(section.children)[list(section.children).index(heading)+1:]:
        if not getattr(candidate, 'name', None):
            continue
        if candidate.name == 'h2':
            candidate.replace_with(doc.new_tag('span', id=candidate.get('id','')))
            break
        if candidate.get_text(strip=True) or candidate.find('img'):
            break
    if index == 0:
        img = section.select_one('label.checkbox-label')
        if img:
            img.decompose()  # The original cover appears once, as the first PDF page.
    if chapter_metadata[index]['path'] == 'declarative_modeling.md':
        section['class'].append('companion')
    for p in list(section.select('p')):
        text = p.get_text(' ',strip=True)
        if text.startswith('The CP-SAT Primer is maintained by') or text.startswith('If you find the primer helpful, consider leaving'):
            previous = p.find_previous_sibling()
            if previous and previous.name == 'hr':
                previous.decompose()
            excluded[text] += 1
            p.decompose()
    # Remove empty mdBook page-break divs; chapter containers now control pagination.
    for div in section.select('div[style]'):
        if 'break-before' in div['style'] and not div.get_text(strip=True) and not div.find('img'):
            div.decompose()
    content_headings = [h for h in section.select('h2,h3,h4,h5,h6') if h != heading]
    in_section = False
    for h in content_headings:
        original_level = int(h.name[1])
        if original_level == 2:
            in_section = True
        level = original_level + (1 if in_section else 0)
        h.name = 'h'+str(min(level,6))
    # Section-level TOC entries follow the chapter's own hierarchy.
    link = doc.new_tag('a', href='#'+start_id, attrs={'class':'toc-chapter'})
    link.string = title
    toc.append(link)
    for h in ([] if index == 0 else section.select('h3')):
        if not h.get('id'):
            continue
        a = doc.new_tag('a', href='#'+h['id'], attrs={'class':'toc-section'})
        a.string = h.get_text(' ', strip=True)
        toc.append(a)
    chapter_sections.append(section)
    body.append(section)

# Named anchors are widespread in the original book; preserve them as PDF IDs.
existing_ids = {t['id'] for t in doc.select('[id]')}
for anchor in doc.select('a[name]'):
    if not anchor.get('id') and anchor['name'] not in existing_ids:
        anchor['id'] = anchor['name']
        existing_ids.add(anchor['name'])
    elif not anchor.get('id'):
        del anchor['name']
for img in doc.select('img.math-svg'):
    img['style'] = img.get('style','') + ';font-size:92%'
for h in doc.select('.chapter h2,.chapter h3,.chapter h4,.chapter h5,.chapter h6'):
    if h.select_one('.MathJax_SVG'):
        label_node = copy(h)
        for span in label_node.select('.MathJax_SVG'):
            mathml = BeautifulSoup(html.unescape(span.get('data-mathml','')), 'html.parser')
            span.replace_with(mathml.get_text())
        label = label_node.get_text(' ',strip=True).replace('\\','\\\\').replace("'","\\'")
        h['style'] = h.get('style','') + f";bookmark-label:'{label}'"
for table in doc.select('table'):
    if table.find('th') and len(table.select('tr')) > 1:
        table['class'] = table.get('class',[]) + ['data-table']
        headers = [th.get_text(' ',strip=True) for th in table.select('th')]
        if headers and 'Workers' in headers[0] and len(headers) == 5:
            table['class'].append('workers-table')
            columns = doc.new_tag('colgroup')
            for width in [8,25,27,25,15]:
                columns.append(doc.new_tag('col',style=f'width:{width}%'))
            table.insert(0,columns)
    else:
        table['class'] = table.get('class',[]) + ['callout']
# Keep an illustration and its following caption together where possible.
for img in list(doc.select('img:not(.math-svg)')):
    if img.parent and img.parent.name == 'section':
        next_p = img.find_next_sibling()
        if next_p and next_p.name == 'p' and next_p.find('strong'):
            figure = doc.new_tag('figure')
            img.insert_before(figure)
            figure.append(img.extract())
            caption = doc.new_tag('figcaption')
            for child in list(next_p.contents):
                caption.append(child.extract())
            next_p.decompose()
            figure.append(caption)

ids = {t['id'] for t in doc.select('[id]')}
missing = Counter()
for a in doc.select('a[href]'):
    href = a['href']
    if href.startswith('#') and href[1:] not in ids:
        missing[href] += 1
        a['href'] = 'https://d-krupke.github.io/cpsat-primer/print.html' + href
    elif href.startswith('file:'):
        raise ValueError(f'Unexpected local file hyperlink: {href}')

duplicates = [i for i,n in Counter(t['id'] for t in doc.select('[id]')).items() if n>1]
if duplicates:
    raise ValueError(f'Duplicate IDs: {duplicates}')
html_path = ROOT/'build/source/book.html'
html_path.write_text(str(doc))
print(f'Prepared {len(chapters)} chapters; {len(toc.select(".toc-section"))} section entries; missing source anchors: {dict(missing)}', flush=True)
from weasyprint.urls import URLFetcher

rendered = HTML(
    filename=str(html_path),
    url_fetcher=URLFetcher(allowed_protocols={'file','data'}, fail_on_errors=True),
).render()

geometry = []
for page_number,page in enumerate(rendered.pages,1):
    for box in page._page_box.descendants():
        element = getattr(box,'element',None)
        if element is None or element.tag not in {'img','pre','table'}:
            continue
        if type(box).__name__ in {'TextBox','LineBox'}:
            continue
        geometry.append({'page':page_number,'tag':element.tag,'class':element.get('class',''),
                         'alt':element.get('alt',''),'x':box.position_x,'y':box.position_y,
                         'width':box.width,'height':box.height})
(ROOT/'build/geometry.json').write_text(json.dumps(geometry))
pdf_path = OUT/'cpsat-primer-letter.pdf'
rendered.write_pdf(pdf_path)
report = {'pdf':str(pdf_path),'pages':len(rendered.pages),'chapters':len(chapters),
          'toc_sections':len(toc.select('.toc-section')), 'missing_source_anchors':dict(missing),
          'upstream_commit':commit,'consolidated_attribution_paragraphs':sum(excluded.values())}
(ROOT/'build/build-report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report), flush=True)
if missing:
    raise RuntimeError(f'Unresolved internal book links: {dict(missing)}')
