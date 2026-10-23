#!/usr/bin/env python3
"""Fetch a revision, run the official mdBook build, typeset and audit the PDF."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / '.cache'
BUILD = ROOT / 'build'
UPSTREAM = CACHE / 'upstream'


def run(*args, cwd=ROOT, **kwargs):
    return subprocess.run(args, cwd=cwd, check=True, **kwargs)


def git_output(*args):
    return run('git', '-C', str(UPSTREAM), *args, capture_output=True, text=True).stdout.strip()


def file_digest(paths):
    digest = hashlib.sha256()
    for path in sorted(paths):
        if not path.is_file():
            continue
        digest.update(path.relative_to(ROOT).as_posix().encode() + b'\0')
        digest.update(path.read_bytes())
        digest.update(b'\0')
    return digest.hexdigest()


def pipeline_digest():
    paths = [*ROOT.glob('*.py'),*ROOT.glob('*.css'),ROOT/'requirements.txt',ROOT/'tools.json',
             ROOT/'NOTICE.md',ROOT/'external-assets.json',*list((ROOT/'LICENSES').glob('*')),
             *list((ROOT/'assets/external').glob('*'))]
    return file_digest(paths)


def install_tool(name, spec):
    destination = CACHE / ('bin' if name == 'mdbook' else 'mathjax')
    marker = destination / f'.{name}-{spec["version"]}'
    if marker.exists():
        return
    archive = CACHE / f'{name}-{spec["version"]}.tar.gz'
    if not archive.exists():
        request = urllib.request.Request(spec['url'], headers={'User-Agent': 'cpsat-primer-pdf'})
        with urllib.request.urlopen(request, timeout=90) as response:
            archive.write_bytes(response.read())
    if hashlib.sha256(archive.read_bytes()).hexdigest() != spec['sha256']:
        archive.unlink()
        raise RuntimeError(f'{name}: archive checksum mismatch')
    destination.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive) as tar:
        tar.extractall(destination, filter='data')
    marker.touch()


def package_release():
    out = ROOT/'output/pdf'
    metadata = json.loads((BUILD/'metadata.json').read_text())
    (out/'build-info.json').write_text(json.dumps(metadata,indent=2)+'\n')
    shutil.copyfile(BUILD/'review/audit.json',out/'audit.json')
    with zipfile.ZipFile(out/'licenses.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted((ROOT/'LICENSES').iterdir()):
            if path.is_file() and not path.name.startswith('.'):
                archive.write(path,path.name)
    shutil.copyfile(ROOT/'NOTICE.md',out/'NOTICE.md')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ref', help='Upstream branch, tag, or commit; defaults to upstream.json')
    parser.add_argument('--resolve-only', action='store_true', help='Fetch and write provenance without building')
    parser.add_argument('--reuse-source', action='store_true', help='Use the revision in build/metadata.json')
    parser.add_argument('--review', action='store_true', help='Render numbered page contact sheets')
    args = parser.parse_args()
    CACHE.mkdir(exist_ok=True)
    BUILD.mkdir(exist_ok=True)
    config = json.loads((ROOT / 'upstream.json').read_text())
    reference = (json.loads((BUILD/'metadata.json').read_text())['upstream_commit']
                 if args.reuse_source else args.ref or config['revision'])
    if reference.startswith('-'):
        parser.error('An upstream reference cannot start with a dash')
    if not (UPSTREAM / '.git').exists():
        run('git', 'clone', '--no-checkout', '--depth', '1', config['repository'], str(UPSTREAM))
    # This is an ignored, disposable checkout, never a user's upstream working tree.
    run('git', '-C', str(UPSTREAM), 'fetch', '--depth', '1', 'origin', reference)
    run('git', '-C', str(UPSTREAM), 'checkout', '--detach', '--force', 'FETCH_HEAD')
    commit = git_output('rev-parse', 'HEAD')
    tracked = git_output('ls-files', 'chapters', 'images', '.scripts', '.mdbook/SUMMARY.md', '.mdbook/book.toml', 'LICENSE')
    content_paths = [UPSTREAM/path for path in tracked.splitlines()]
    content_digest = file_digest(content_paths)
    pipeline_hash = pipeline_digest()
    tools = json.loads((ROOT/'tools.json').read_text())
    metadata = {
        'upstream_repository':config['repository'],'upstream_commit':commit,
        'upstream_commit_date':git_output('show','-s','--format=%cs','HEAD'),
        'content_sha256':content_digest,'pipeline_sha256':pipeline_hash,
        'built_at':datetime.now(timezone.utc).isoformat(),
        'release_tag':f'pdf-{content_digest[:12]}-{pipeline_hash[:12]}',
        'tools':{name:spec['version'] for name,spec in tools.items()},
    }
    (BUILD/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as stream:
            stream.write(f'release_tag={metadata["release_tag"]}\nupstream_commit={commit}\n')
    print(json.dumps(metadata,indent=2),flush=True)
    if args.resolve_only:
        return
    for name,spec in tools.items():
        install_tool(name,spec)
    run(sys.executable,str(UPSTREAM/'.scripts/build.py'))
    run(str(CACHE/'bin/mdbook'),'build',str(UPSTREAM/'.mdbook'))
    for script in ['prepare.py','build_book.py','finalize_pdf.py']:
        run(sys.executable,str(ROOT/script))
    command = [sys.executable,str(ROOT/'check_book.py')]
    if args.review:
        command.append('--review')
    run(*command)
    package_release()
    out = ROOT/'output/pdf'
    print(f'Build and audit passed: {out / "cpsat-primer-letter.pdf"}',flush=True)


if __name__ == '__main__':
    main()
