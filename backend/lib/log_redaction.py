"""Keep credentials out of HTTP/WebSocket access diagnostics."""
import logging
import re


class CredentialFilter(logging.Filter):
    def filter(self, record):
        # Uvicorn's AccessFormatter unpacks five arguments after filters run.
        # Redact each string while preserving that structured record.
        def redact(value):
            if not isinstance(value, str):
                return value
            value = re.sub(r'([?&](?:token|api_key|access_token|refresh_token|secret)=)[^\s&"\']+', r'\1[redacted]', value, flags=re.I)
            value = re.sub(r'(Bearer\s+)[\w.-]+', r'\1[redacted]', value, flags=re.I)
            return re.sub(r'\beyJ[\w-]+\.[\w-]+\.[\w-]+\b', '[redacted]', value)

        record.msg = redact(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(redact(value) for value in record.args)
        elif isinstance(record.args, dict):
            record.args = {key: redact(value) for key, value in record.args.items()}
        return True
