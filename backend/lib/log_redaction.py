"""Keep credentials out of HTTP/WebSocket access diagnostics."""
import logging
import re


class CredentialFilter(logging.Filter):
    def filter(self, record):
        message = record.getMessage()
        message = re.sub(r'([?&](?:token|api_key|access_token|refresh_token|secret)=)[^\s&"\']+', r'\1[redacted]', message, flags=re.I)
        message = re.sub(r'(Bearer\s+)[\w.-]+', r'\1[redacted]', message, flags=re.I)
        message = re.sub(r'\beyJ[\w-]+\.[\w-]+\.[\w-]+\b', '[redacted]', message)
        record.msg, record.args = message, ()
        return True
