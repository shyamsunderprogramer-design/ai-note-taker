"""Serve actual web pages with clean URLs and an explicit isolated API endpoint."""
import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import io
import json
from pathlib import Path
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument('--port', type=int, default=8048)
parser.add_argument('--api', default='http://127.0.0.1:8049')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1] / 'apps' / 'web'

class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        path = Path(self.translate_path(self.path))
        if path.is_dir():
            path = path / 'index.html'
        elif not path.suffix:
            path = path.with_suffix('.html')
        if path.is_file() and path.suffix == '.html' and path.resolve().is_relative_to(root):
            html = path.read_text()
            html = html.replace('<head>', '<head><script>window.__API_URL__=' + json.dumps(args.api) + ';</script>', 1)
            body = html.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            return io.BytesIO(body)
        return super().send_head()

ThreadingHTTPServer(('127.0.0.1', args.port), partial(Handler, directory=str(root))).serve_forever()
