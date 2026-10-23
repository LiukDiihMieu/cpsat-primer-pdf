"""Freeze local mdBook output with local images, fonts and MathJax."""
import asyncio
import base64
from functools import partial
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import shutil
from threading import Thread
from urllib.parse import unquote, urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT/'.cache/upstream'
SITE = UPSTREAM/'.mdbook/book'
SOURCE = ROOT/'build/source'
EXTERNAL_ASSETS = json.loads((ROOT/'external-assets.json').read_text())


def chapter_list():
    """Read chapter order and grouping from upstream SUMMARY.md."""
    chapters = []
    part = None
    for line in (UPSTREAM/'.mdbook/SUMMARY.md').read_text().splitlines():
        if line.startswith('# '):
            part = line[2:].strip()
            if part in {'Summary','The CP-SAT Primer'}:
                part = None
        match = re.match(r'\s*-\s+\[(.+?)\]\((.+?\.md)\)',line)
        if match:
            chapters.append({'title':match[1],'path':match[2].removeprefix('./'),'part':part})
            part = None
    if not chapters:
        raise RuntimeError('No chapters found in upstream SUMMARY.md')
    return chapters


def local_asset(url):
    if url in EXTERNAL_ASSETS:
        spec = EXTERNAL_ASSETS[url]
        asset = ROOT/spec['path']
        if hashlib.sha256(asset.read_bytes()).hexdigest() != spec['sha256']:
            raise RuntimeError(f'External asset checksum mismatch: {asset}')
        return asset
    parsed = urlparse(url)
    path = unquote(parsed.path)
    if parsed.hostname=='raw.githubusercontent.com' and path.startswith('/d-krupke/cpsat-primer/'):
        return UPSTREAM/path.split('/',4)[4]
    if parsed.hostname=='github.com' and path.startswith('/d-krupke/cpsat-primer/blob/'):
        return UPSTREAM/path.split('/',5)[5]
    return None


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):
        pass


async def freeze(base):
    original = (SITE/'print.html').read_text()
    config = '<script type="text/x-mathjax-config">MathJax.Hub.Config({SVG:{useFontCache:false},showMathMenu:false});</script>'
    original = original.replace('<!-- MathJax -->','<!-- MathJax -->'+config)
    original = re.sub(r'https://cdnjs.cloudflare.com/ajax/libs/mathjax/[^/]+/MathJax.js\?config=TeX-AMS-MML_HTMLorMML',
                      '/.cache/mathjax/package/MathJax.js?config=TeX-AMS-MML_SVG',original)
    if 'TeX-AMS-MML_SVG' not in original:
        raise RuntimeError('The upstream MathJax template changed; update prepare.py')
    print_url = base+'/.cache/upstream/.mdbook/book/print.html'
    assets = SOURCE/'assets'
    assets.mkdir(parents=True,exist_ok=True)
    async with async_playwright() as p:
        launch = {'args':['--no-sandbox']}
        if os.environ.get('CHROMIUM_PATH'):
            launch['executable_path'] = os.environ['CHROMIUM_PATH']
        browser = await p.chromium.launch(**launch)
        page = await browser.new_page(viewport={'width':1000,'height':1000})
        await page.add_init_script('window.print=()=>{}')
        unexpected = set()

        async def route_request(route):
            url = route.request.url
            if url==print_url:
                await route.fulfill(body=original,content_type='text/html')
            elif url.startswith(base+'/'):
                await route.continue_()
            elif (asset:=local_asset(url)) is not None and asset.is_file():
                await route.fulfill(path=str(asset))
            else:
                unexpected.add(url)
                await route.abort()

        await page.route('**/*',route_request)
        await page.goto(print_url,wait_until='load',timeout=120000)
        await page.wait_for_function('!!(window.MathJax && MathJax.Hub && MathJax.Hub.Queue)',timeout=60000)
        await page.evaluate('() => new Promise(resolve => MathJax.Hub.Queue(resolve))')
        await page.evaluate('() => document.fonts.ready')
        stats = await page.evaluate('({formulas:document.querySelectorAll(".MathJax_SVG").length,errors:document.querySelectorAll(".MathJax_Error").length})')
        if stats['errors'] or unexpected:
            raise RuntimeError(f'Math errors: {stats["errors"]}; unexpected external resources: {sorted(unexpected)}')
        soup = BeautifulSoup(await page.content(),'html.parser')
        content = soup.select_one('main')
        if content is None:
            raise RuntimeError('No main content found in mdBook output')
        chunks = [[]]
        for node in content.children:
            if getattr(node,'name',None)=='div' and 'break-before' in node.get('style',''):
                chunks.append([])
            else:
                chunks[-1].append(node)
        chapters = chapter_list()
        if len(chunks)!=len(chapters):
            raise RuntimeError(f'Print chapter boundaries changed: {len(chunks)} chunks / {len(chapters)} chapters')
        for chapter,chunk in zip(chapters,chunks):
            headings = [n for n in chunk if getattr(n,'name',None) in {'h1','h2'} and not n.get_text().startswith('Part ')]
            if not headings or not headings[0].get('id'):
                raise RuntimeError(f'No chapter heading: {chapter["path"]}')
            chapter['start_id'] = headings[0]['id']
        (SOURCE/'chapters.json').write_text(json.dumps(chapters,indent=2)+'\n')
        for node in content.select('.img-wrapper,input,script,.MathJax_Preview,.MJX_Assistive_MathML,.buttons'):
            node.decompose()
        for details in content.select('details'):
            details['open'] = ''
        for svg in content.select('.MathJax_SVG svg'):
            if svg.has_attr('viewbox'):
                svg['viewBox'] = svg.attrs.pop('viewbox')
            svg['xmlns'] = 'http://www.w3.org/2000/svg'
            svg['xmlns:xlink'] = 'http://www.w3.org/1999/xlink'
            image = soup.new_tag('img',attrs={'class':'math-svg'})
            image['src'] = 'data:image/svg+xml;base64,'+base64.b64encode(str(svg).encode()).decode()
            image['style'] = f'width:{svg.get("width")};height:{svg.get("height")};{svg.get("style", "")}'
            svg.replace_with(image)

        copied = {}
        def copy_asset(url):
            asset = local_asset(url)
            if asset is None:
                if not url.startswith(base+'/'):
                    raise RuntimeError(f'Asset is not in the pinned checkout: {url}')
                asset = ROOT/unquote(urlparse(url).path).lstrip('/')
            asset = asset.resolve()
            if not asset.is_relative_to(ROOT) or not asset.is_file():
                raise RuntimeError(f'Missing or unexpected asset: {asset}')
            digest = hashlib.sha256(asset.read_bytes()).hexdigest()
            target = assets/(digest[:20]+asset.suffix)
            if not target.exists():
                shutil.copyfile(asset,target)
            copied[str(asset.relative_to(ROOT))] = digest
            return target.as_uri()

        for image in content.select('img[src]'):
            if not image['src'].startswith('data:'):
                image['src'] = copy_asset(urljoin(print_url,image['src']))
        css = []
        for link in soup.select('link[rel=stylesheet]'):
            href = link.get('href','')
            if not (any(key in href for key in ['variables-','general-','fonts-']) or link.get('id')=='mdbook-highlight-css'):
                continue
            url = urljoin(print_url,href)
            text = (ROOT/unquote(urlparse(url).path).lstrip('/')).read_text()
            for match in list(re.finditer(r'url\([\'\"]?([^\)\'\"]+)[\'\"]?\)',text)):
                resource = match[1]
                if not resource.startswith('data:'):
                    text = text.replace(resource,copy_asset(urljoin(url,resource)))
            css.append(text)
        (SOURCE/'official.css').write_text('\n'.join(css))
        (SOURCE/'content.html').write_text(str(content))
        (SOURCE/'print.html').write_text(original)
        (SOURCE/'assets.json').write_text(json.dumps(copied,indent=2)+'\n')
        metadata_path = ROOT/'build/metadata.json'
        metadata = json.loads(metadata_path.read_text())
        metadata.update({'browser_version':browser.version,'rendered_formulas':stats['formulas']})
        metadata_path.write_text(json.dumps(metadata,indent=2)+'\n')
        print(f'Prepared {len(chapters)} chapters and {stats["formulas"]} vector formulas from local source.',flush=True)
        await browser.close()


def main():
    SOURCE.mkdir(parents=True,exist_ok=True)
    server = ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT)))
    Thread(target=server.serve_forever,daemon=True).start()
    try:
        asyncio.run(freeze(f'http://127.0.0.1:{server.server_port}'))
    finally:
        server.shutdown()
        server.server_close()


if __name__=='__main__':
    main()
