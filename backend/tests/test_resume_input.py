import io
import zipfile
import pytest
from lib.resume_input import extract_resume


@pytest.mark.parametrize('extension', ['txt', 'md', 'text'])
def test_text_formats(extension):
    text = 'Alex built a Python inventory system at Acme.'
    assert extract_resume('resume.' + extension, text.encode()) == text


def test_json_and_invalid_json():
    assert 'Python' in extract_resume('resume.json', b'{"name":"Alex","skills":["Python"]}')
    with pytest.raises(ValueError):
        extract_resume('resume.json', b'not valid json')


def test_docx_includes_table_content():
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w') as archive:
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Alex: Python engineer.</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Acme inventory project.</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
    text = extract_resume('resume.docx', out.getvalue())
    assert 'Python' in text and 'Acme' in text


@pytest.mark.parametrize('name,content', [('resume.pdf', b'broken PDF'), ('resume.exe', b'x'*30), ('resume.txt', b'')])
def test_rejects_unreadable_or_unsupported_files(name, content):
    with pytest.raises(ValueError):
        extract_resume(name, content)


def test_doc_uses_native_converter(monkeypatch):
    from lib import resume_input
    from types import SimpleNamespace
    monkeypatch.setattr(resume_input.shutil, 'which', lambda _: '/usr/bin/textutil')
    def convert(args, **kwargs):
        assert args[-2:] == ['-stdin', '-stdout']
        assert kwargs['input'] == b'legacy document'
        return SimpleNamespace(stdout=b'Alex built the inventory service at Acme.')
    monkeypatch.setattr(resume_input.subprocess, 'run', convert)
    assert 'Acme' in extract_resume('resume.doc', b'legacy document')


def test_pdf_text_extraction():
    stream = b'BT /F1 12 Tf 50 700 Td (Alex built Python services at Acme.) Tj ET'
    objects = [b'<< /Type /Catalog /Pages 2 0 R >>',
               b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
               b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',
               b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
               b'<< /Length ' + str(len(stream)).encode() + b' >>\nstream\n' + stream + b'\nendstream']
    pdf = b'%PDF-1.4\n'
    offsets = []
    for i, obj in enumerate(objects, 1):
        offsets.append(len(pdf))
        pdf += f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n'
    xref = len(pdf)
    pdf += b'xref\n0 6\n0000000000 65535 f \n'
    pdf += b''.join(f'{offset:010d} 00000 n \n'.encode() for offset in offsets)
    pdf += f'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF'.encode()
    assert 'Python services at Acme' in extract_resume('resume.pdf', pdf)


def test_upload_endpoint(monkeypatch):
    from pathlib import Path
    for relative in ['core', 'modules/ai']:
        monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / relative))
    from routes.interview import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    app = FastAPI()
    app.include_router(router)
    with TestClient(app) as client:
        response = client.post('/resume/context', files={'file': ('resume.md', b'Alex built Python services at Acme.', 'text/markdown')})
        assert response.status_code == 200
        assert 'Acme' in response.json()['text']
        response = client.post('/resume/context', files={'file': ('resume.exe', b'Unsupported resume file content.', 'application/octet-stream')})
        assert response.status_code == 422


def test_long_resume_is_retained_in_full():
    text = 'Python engineer with project experience.\n' * 600 + 'Final project: Kubernetes migration.'
    assert len(text) > 12000
    assert extract_resume('resume.md', text.encode()) == text
