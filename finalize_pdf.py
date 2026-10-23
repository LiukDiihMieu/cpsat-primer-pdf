"""Add consistent document-information and XMP metadata without changing pages."""
from datetime import datetime, timezone
import json
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject
from pypdf.xmp import XmpInformation

ROOT = Path(__file__).resolve().parent


def main():
    path = ROOT/'output/pdf/cpsat-primer-letter.pdf'
    provenance = json.loads((ROOT/'build/metadata.json').read_text())
    reader = PdfReader(path)
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    title = 'The CP-SAT Primer - Unofficial Letter PDF Edition'
    author = 'Dominik Krupke'
    subject = "Using and Understanding Google OR-Tools' CP-SAT Solver. Unofficial Letter PDF edition."
    keywords = ['CP-SAT','OR-Tools','constraint programming','combinatorial optimization']
    source = 'https://github.com/d-krupke/cpsat-primer/commit/'+provenance['upstream_commit']
    created = datetime.fromisoformat(provenance['built_at']).astimezone(timezone.utc)
    pdf_date = created.strftime('D:%Y%m%d%H%M%SZ')
    writer.add_metadata({
        '/Title':title,'/Author':author,'/Subject':subject,
        '/Keywords':', '.join(keywords),'/Creator':'cpsat-primer-pdf',
        '/CreationDate':pdf_date,'/ModDate':pdf_date,'/Source':source,
    })
    writer.root_object[NameObject('/Lang')] = TextStringObject('en')
    xmp = XmpInformation.create()
    xmp.dc_title = {'x-default':title}
    xmp.dc_creator = [author]
    xmp.dc_description = {'x-default':subject}
    xmp.dc_subject = keywords
    xmp.dc_language = ['en']
    xmp.dc_source = source
    xmp.dc_rights = {'x-default':'CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/), subject to existing third-party exceptions; see NOTICE.md.'}
    xmp.xmp_creator_tool = 'cpsat-primer-pdf'
    xmp.xmp_create_date = created
    xmp.xmp_modify_date = created
    xmp.pdf_keywords = ', '.join(keywords)
    xmp.pdf_producer = reader.metadata.producer
    writer.xmp_metadata = xmp
    temporary = path.with_suffix('.tmp.pdf')
    writer.write(temporary)
    temporary.replace(path)
    verified = PdfReader(path)
    assert verified.metadata.title == title
    assert verified.xmp_metadata.dc_creator == [author]
    assert verified.xmp_metadata.dc_source == source
    assert len(verified.pages) == len(reader.pages)
    print('Document properties and XMP metadata verified.',flush=True)


if __name__=='__main__':
    main()
