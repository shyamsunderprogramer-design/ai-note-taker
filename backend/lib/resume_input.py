"""Extract resume text without running analysis or saving the uploaded file."""
import io
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree

MAX_BYTES = 5 * 1024 * 1024
MAX_TEXT = MAX_BYTES


def extract_resume(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if not content or len(content) > MAX_BYTES:
        raise ValueError('Choose a nonempty resume file up to 5 MB.')
    try:
        if extension == '.pdf':
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as reader:
                if len(reader.pages) > 30:
                    raise ValueError('Please use a resume with at most 30 pages.')
                text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        elif extension == '.docx':
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                info = archive.getinfo('word/document.xml')
                if info.file_size > MAX_BYTES:
                    raise ValueError('The document is too large after extraction.')
                root = ElementTree.fromstring(archive.read(info))
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text = '\n'.join(''.join(p.itertext()) for p in root.findall('.//w:p', ns))
        elif extension == '.doc':
            tool = shutil.which('textutil')
            if not tool:
                raise ValueError('Legacy DOC conversion is unavailable here. Save as DOCX, PDF, or text and upload again.')
            result = subprocess.run([tool, '-convert', 'txt', '-format', 'doc', '-stdin', '-stdout'],
                                    input=content, capture_output=True, timeout=15, check=True)
            text = result.stdout.decode('utf-8')
        elif extension in {'.txt', '.text', '.md', '.json'}:
            text = content.decode('utf-8-sig')
            if extension == '.json':
                text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        else:
            raise ValueError('Supported formats: PDF, DOC, DOCX, TXT, JSON, and Markdown.')
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError('Could not read this file. Export it as DOCX or UTF-8 text and try again.') from exc
    text = text.replace('\x00', '').strip()
    if len(text) < 20:
        raise ValueError('No readable resume text found. For scanned PDFs, export a searchable PDF or upload text.')
    if len(text) > MAX_TEXT:
        raise ValueError('Extracted document exceeds 5 MB. Please upload a smaller document.')
    return text
