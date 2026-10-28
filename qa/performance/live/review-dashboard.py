#!/usr/bin/env python3
"""Serve saved QA reports locally: python3 qa/performance/live/review-dashboard.py."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PAGE = Path(__file__).with_name('review-dashboard.html')


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        route = unquote(urlsplit(self.path).path)
        if route in ('/', '/fix-watch.html'):
            body, content_type = PAGE.read_bytes(), 'text/html; charset=utf-8'
        elif route == '/api/reports':
            paths = sorted(ROOT.glob('*.md')) + sorted((ROOT / 'results/2026-09-27-remediation').rglob('*'))
            paths += [ROOT / 'results/2026-09-27-remediation-plan.json', ROOT / 'results/2026-09-27-final-app-review.json']
            body = json.dumps([str(p.relative_to(ROOT)) for p in paths if p.is_file() and p.suffix in ('.md', '.json', '.log')]).encode()
            content_type = 'application/json'
        elif route.startswith('/reports/'):
            path = (ROOT / route[len('/reports/'):]).resolve()
            allowed = path.is_relative_to(ROOT) and path.suffix in ('.md', '.json', '.log')
            if not allowed or not path.is_file():
                self.send_error(404)
                return
            body, content_type = path.read_bytes(), 'text/plain; charset=utf-8'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    print('ANT review dashboard: http://127.0.0.1:8047/', flush=True)
    ThreadingHTTPServer(('127.0.0.1', 8047), Handler).serve_forever()
