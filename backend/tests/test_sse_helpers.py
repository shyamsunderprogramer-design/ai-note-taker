"""
Test suite for backend/lib/sse_helpers.py
Covers the 7 SSE event formatters: make_meta, make_content, make_done,
make_error, make_vision, make_vision_done.

Every helper returns a string formatted as:
    event: <type>\ndata: <json>\n\n

The wire format matters — clients parse on the literal "event: "
and "data: " prefixes plus the trailing blank line.

Run with: python -m pytest backend/tests/test_sse_helpers.py -v
"""

import json
import os
import sys

import pytest

# Add backend/ to sys.path so `from lib.sse_helpers import ...` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from lib.sse_helpers import (  # noqa: E402
    make_meta,
    make_content,
    make_done,
    make_error,
    make_vision,
    make_vision_done,
)


class TestMakeMeta:
    """make_meta: identifies the model + provider at stream start."""

    def test_event_type_is_meta(self):
        out = make_meta("gpt-oss:20b", "ollama")
        assert out.startswith("event: meta\n")  # nosec B101

    def test_data_payload_is_valid_json(self):
        out = make_meta("gpt-oss:20b", "ollama")
        # Extract the data line
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        payload = json.loads(data_line[6:])  # strip "data: "
        assert payload["type"] == "meta"  # nosec B101
        assert payload["model"] == "gpt-oss:20b"  # nosec B101
        assert payload["provider"] == "ollama"  # nosec B101

    def test_ends_with_double_newline(self):
        # SSE spec: events are terminated by a blank line
        out = make_meta("m", "p")
        assert out.endswith("\n\n")  # nosec B101

    def test_special_chars_in_provider_preserved(self):
        out = make_meta("m", "provider with spaces")
        assert "provider with spaces" in out  # nosec B101


class TestMakeContent:
    """make_content: text chunk in the stream."""

    def test_event_type_is_chunk(self):
        out = make_content("hello world")
        assert out.startswith("event: chunk\n")  # nosec B101

    def test_data_carries_content(self):
        out = make_content("hello world")
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        payload = json.loads(data_line[6:])
        assert payload["type"] == "chunk"  # nosec B101
        assert payload["content"] == "hello world"  # nosec B101

    def test_empty_content_still_emits_event(self):
        out = make_content("")
        # An empty content is still a valid SSE event
        assert out.startswith("event: chunk\n")  # nosec B101

    def test_newlines_in_content_escaped(self):
        # The content contains a literal \n; the SSE format must escape
        # it so clients don't break on multi-line data fields.
        out = make_content("line1\nline2")
        # The raw \n should NOT appear inside the data payload —
        # only the \n\n terminator at the end is allowed
        data_section = out.split("data: ")[1]
        # Strip the trailing \n\n terminator
        payload_str = data_section.rstrip("\n")
        # Re-parse to verify it's valid JSON
        payload = json.loads(payload_str)
        assert payload["content"] == "line1\nline2"  # nosec B101


class TestMakeDone:
    """make_done: signals end-of-stream with elapsed time."""

    def test_event_type_is_done(self):
        out = make_done(1234)
        assert out.startswith("event: done\n")  # nosec B101

    def test_data_carries_ms(self):
        out = make_done(1234)
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        payload = json.loads(data_line[6:])
        assert payload["type"] == "done"  # nosec B101
        assert payload["ms"] == 1234  # nosec B101

    def test_zero_elapsed(self):
        out = make_done(0)
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        payload = json.loads(data_line[6:])
        assert payload["ms"] == 0  # nosec B101


class TestMakeError:
    """make_error: error in the stream."""

    def test_event_type_is_error(self):
        out = make_error("oops")
        assert out.startswith("event: error\n")  # nosec B101

    def test_data_carries_message(self):
        out = make_error("oops")
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        payload = json.loads(data_line[6:])
        assert payload["type"] == "error"  # nosec B101
        assert payload["message"] == "oops"  # nosec B101

    def test_message_with_quotes_escaped(self):
        out = make_error('He said "hi"')
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        payload = json.loads(data_line[6:])
        assert payload["message"] == 'He said "hi"'  # nosec B101


class TestMakeVision:
    """make_vision: streams image description in real-time."""

    def test_event_type_is_vision(self):
        out = make_vision("A cat sitting on a mat", provider="gpt-4v")
        assert out.startswith("event: vision\n")  # nosec B101

    def test_data_carries_content_and_provider(self):
        out = make_vision("description", provider="claude")
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        payload = json.loads(data_line[6:])
        assert payload["type"] == "vision"  # nosec B101
        assert payload["content"] == "description"  # nosec B101
        assert payload["provider"] == "claude"  # nosec B101

    def test_empty_provider_default(self):
        out = make_vision("x", provider="")
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        payload = json.loads(data_line[6:])
        assert payload["provider"] == ""  # nosec B101


class TestMakeVisionDone:
    """make_vision_done: signals Step 1 (vision) is complete."""

    def test_event_type_is_vision_done(self):
        out = make_vision_done(567, "ollama")
        assert out.startswith("event: vision_done\n")  # nosec B101

    def test_data_carries_ms_and_provider(self):
        out = make_vision_done(567, "ollama")
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        payload = json.loads(data_line[6:])
        assert payload["type"] == "vision_done"  # nosec B101
        assert payload["ms"] == 567  # nosec B101
        assert payload["provider"] == "ollama"  # nosec B101


class TestSseFormatContract:
    """Cross-cutting: every helper returns a valid SSE frame."""

    @pytest.mark.parametrize("factory,args", [
        (make_meta, ("m", "p")),
        (make_content, ("x",)),
        (make_done, (100,)),
        (make_error, ("e",)),
        (make_vision, ("v",)),
        (make_vision_done, (50, "prov")),
    ])
    def test_output_ends_with_blank_line(self, factory, args):
        out = factory(*args)
        assert out.endswith("\n\n")  # nosec B101

    @pytest.mark.parametrize("factory,args", [
        (make_meta, ("m", "p")),
        (make_content, ("x",)),
        (make_done, (100,)),
        (make_error, ("e",)),
        (make_vision, ("v",)),
        (make_vision_done, (50, "prov")),
    ])
    def test_output_has_event_and_data_lines(self, factory, args):
        out = factory(*args)
        lines = out.splitlines()
        # First non-empty line is the event
        assert lines[0].startswith("event: ")  # nosec B101
        # Second non-empty line is the data
        assert any(l.startswith("data: ") for l in lines)  # nosec B101

    @pytest.mark.parametrize("factory,args", [
        (make_meta, ("m", "p")),
        (make_content, ("x",)),
        (make_done, (100,)),
        (make_error, ("e",)),
        (make_vision, ("v",)),
        (make_vision_done, (50, "prov")),
    ])
    def test_data_payload_is_valid_json(self, factory, args):
        out = factory(*args)
        data_line = [l for l in out.splitlines() if l.startswith("data: ")][0]
        # Must not raise
        json.loads(data_line[6:])  # nosec B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
