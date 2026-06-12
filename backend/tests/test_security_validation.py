"""
Test suite for backend/security/validation.py
Covers SecurityHeaders, InputValidator, FileValidator, and the
check_security_threats() convenience walker.

All functions are pure / static — no I/O, no module-level state —
so tests are straightforward: construct inputs, call, assert.

Run with: python -m pytest backend/tests/test_security_validation.py -v
"""

import json
import os
import sys

import pytest

# Add backend/ to sys.path so `from security.validation import ...` resolves.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from security.validation import (  # noqa: E402
    SecurityHeaders,
    InputValidator,
    FileValidator,
    sanitize_input,
    validate_file_upload,
    check_security_threats,
    MAX_TEXT_LENGTH,
    ALLOWED_EXTENSIONS,
)


class TestInputValidatorSanitizeString:
    """sanitize_string: trim, length cap, HTML escape."""

    def test_strips_surrounding_whitespace(self):
        result = InputValidator.sanitize_string("  hello world  ")
        assert result == "hello world"  # nosec B101

    def test_truncates_oversize_to_max(self):
        long_text = "a" * (MAX_TEXT_LENGTH + 100)
        result = InputValidator.sanitize_string(long_text)
        assert len(result) == MAX_TEXT_LENGTH  # nosec B101

    def test_honors_custom_max_length(self):
        result = InputValidator.sanitize_string("abcdefgh", max_length=3)
        assert result == "abc"  # nosec B101

    def test_escapes_html_by_default(self):
        # < and > must be escaped to &lt; / &gt; when allow_html=False
        result = InputValidator.sanitize_string("<b>x</b>")
        assert "&lt;b&gt;" in result  # nosec B101
        assert "<b>" not in result  # nosec B101

    def test_preserves_html_when_allowed(self):
        result = InputValidator.sanitize_string("<b>x</b>", allow_html=True)
        # With allow_html=True the angle brackets are NOT escaped
        assert "<b>x</b>" in result  # nosec B101

    def test_coerces_non_string_input(self):
        # Numbers etc. should be converted to string
        result = InputValidator.sanitize_string(12345)  # type: ignore[arg-type]
        assert result == "12345"  # nosec B101


class TestInputValidatorValidateEmail:
    """validate_email: regex + length check + lowercase."""

    def test_valid_email_lowercased(self):
        assert InputValidator.validate_email("  User@Example.COM  ") == "user@example.com"  # nosec B101

    def test_returns_none_for_empty(self):
        assert InputValidator.validate_email("") is None  # nosec B101

    def test_returns_none_for_missing_at_sign(self):
        assert InputValidator.validate_email("not-an-email") is None  # nosec B101

    def test_returns_none_for_missing_tld(self):
        assert InputValidator.validate_email("user@example") is None  # nosec B101

    def test_returns_none_for_too_long(self):
        long_local = "a" * 250
        result = InputValidator.validate_email(f"{long_local}@example.com")
        assert result is None  # nosec B101

    def test_accepts_subdomain(self):
        assert InputValidator.validate_email("user@mail.example.co.uk") == "user@mail.example.co.uk"  # nosec B101


class TestInputValidatorValidateUsername:
    """validate_username: 3-30 chars, [A-Za-z0-9_-] only."""

    def test_valid_username(self):
        assert InputValidator.validate_username("alice_42") == "alice_42"  # nosec B101

    def test_strips_whitespace(self):
        assert InputValidator.validate_username("  bob  ") == "bob"  # nosec B101

    def test_returns_none_for_too_short(self):
        assert InputValidator.validate_username("ab") is None  # nosec B101

    def test_returns_none_for_too_long(self):
        assert InputValidator.validate_username("a" * 31) is None  # nosec B101

    def test_returns_none_for_invalid_chars(self):
        assert InputValidator.validate_username("alice@example") is None  # nosec B101
        assert InputValidator.validate_username("alice bob") is None  # nosec B101

    def test_returns_none_for_empty(self):
        assert InputValidator.validate_username("") is None  # nosec B101


class TestInputValidatorValidateFilename:
    """validate_filename: path-strip, length cap, traversal check, ext allowlist."""

    def test_simple_filename_preserved(self):
        assert InputValidator.validate_filename("notes.txt") == "notes.txt"  # nosec B101

    def test_strips_path_components(self):
        # Path("foo/bar.txt").name == "bar.txt"
        assert InputValidator.validate_filename("foo/bar.txt") == "bar.txt"  # nosec B101

    def test_rejects_lone_dotdot(self):
        # `Path("..").name == ".."` — the dotdot survives the path-strip
        # and is then caught by the traversal patterns.
        assert InputValidator.validate_filename("..") is None  # nosec B101

    def test_documented_limitation_path_prefix_stripped(self):
        # DOCUMENTED BUG: `Path("../etc/passwd").name` returns "passwd",
        # so the traversal check runs on a clean string. The dotdot
        # is lost during the path-strip step. This test pins the
        # current behavior so we notice if it ever changes. A fix
        # would need to check the ORIGINAL string for traversal
        # patterns BEFORE stripping the path component.
        assert InputValidator.validate_filename("../etc/passwd") == "passwd"  # nosec B101

    def test_documented_limitation_encoded_traversal_in_path(self):
        # DOCUMENTED BUG: The traversal check runs on the POST-STRIP
        # filename. `Path("%2e%2e/passwd").name == "passwd"`, so the
        # encoded-dotdot is lost. A fix would either URL-decode the
        # input first, or run the traversal check on the original
        # string before the path-strip step. This test pins current
        # behavior so a future fix can update it.
        assert InputValidator.validate_filename("%2e%2e/passwd") == "passwd"  # nosec B101

    def test_rejects_too_long(self):
        assert InputValidator.validate_filename("a" * 300 + ".txt") is None  # nosec B101

    def test_rejects_disallowed_extension(self):
        assert InputValidator.validate_filename("evil.exe") is None  # nosec B101

    def test_strips_dangerous_chars(self):
        # \x00 is a NUL byte — should be removed
        result = InputValidator.validate_filename("ok\x00name.txt")
        assert result is not None  # nosec B101
        assert "\x00" not in result  # nosec B101

    def test_filename_with_no_extension_rejected_if_empty_after_strip(self):
        # After stripping, if there's nothing left, return None
        assert InputValidator.validate_filename("") is None  # nosec B101


class TestInputValidatorSecurityQuestionAnswer:
    """Security question/answer validation."""

    def test_valid_question(self):
        q = "What was the name of your first pet?"
        assert InputValidator.validate_security_question(q) == q  # nosec B101

    def test_question_too_short(self):
        assert InputValidator.validate_security_question("ab") is None  # nosec B101

    def test_question_too_long(self):
        assert InputValidator.validate_security_question("a" * 201) is None  # nosec B101

    def test_answer_strips_whitespace(self):
        assert InputValidator.validate_security_answer("  rover  ") == "rover"  # nosec B101

    def test_answer_too_short(self):
        assert InputValidator.validate_security_answer("a") is None  # nosec B101

    def test_empty_answer_rejected(self):
        assert InputValidator.validate_security_answer("") is None  # nosec B101


class TestInputValidatorCheckSqlInjection:
    """check_sql_injection: 3 regex families."""

    def test_clean_text_passes(self):
        assert InputValidator.check_sql_injection("hello world") is False  # nosec B101

    def test_detects_select_with_quote(self):
        assert InputValidator.check_sql_injection("SELECT * FROM users WHERE 1=1'") is True  # nosec B101

    def test_detects_drop_table_with_quote(self):
        assert InputValidator.check_sql_injection("DROP TABLE users;") is True  # nosec B101

    def test_detects_union_inject(self):
        assert InputValidator.check_sql_injection("1' UNION SELECT password FROM users--") is True  # nosec B101

    def test_detects_sql_comment(self):
        # The -- comment marker should trigger
        assert InputValidator.check_sql_injection("admin' --") is True  # nosec B101

    def test_detects_block_comment(self):
        assert InputValidator.check_sql_injection("/* malicious */") is True  # nosec B101

    def test_detects_waitfor_delay(self):
        assert InputValidator.check_sql_injection("'; WAITFOR DELAY '0:0:5'--") is True  # nosec B101

    def test_keyword_alone_is_not_enough(self):
        # Just the word "select" with no quote/operator should NOT trigger
        # (the pattern requires `...['";]` at the end)
        assert InputValidator.check_sql_injection("Please select an option") is False  # nosec B101


class TestInputValidatorCheckXss:
    """check_xss: 4 regex families."""

    def test_clean_text_passes(self):
        assert InputValidator.check_xss("hello world") is False  # nosec B101

    def test_detects_script_tag(self):
        assert InputValidator.check_xss("<script>alert(1)</script>") is True  # nosec B101

    def test_detects_javascript_url(self):
        assert InputValidator.check_xss("javascript:alert(1)") is True  # nosec B101

    def test_detects_data_url_html(self):
        assert InputValidator.check_xss("data:text/html,<script>alert(1)</script>") is True  # nosec B101

    def test_detects_event_handler(self):
        assert InputValidator.check_xss('<img src=x onerror="alert(1)">') is True  # nosec B101

    def test_detects_iframe(self):
        assert InputValidator.check_xss("<iframe src=evil.com></iframe>") is True  # nosec B101

    def test_detects_alert_call(self):
        assert InputValidator.check_xss("alert('xss')") is True  # nosec B101


class TestInputValidatorValidateJson:
    """validate_json: depth-bounded traversal."""

    def test_flat_dict_is_valid(self):
        assert InputValidator.validate_json({"a": 1, "b": "x"}) is True  # nosec B101

    def test_nested_dict_below_limit_is_valid(self):
        data = {"a": {"b": {"c": 1}}}
        assert InputValidator.validate_json(data) is True  # nosec B101

    def test_nested_list_below_limit_is_valid(self):
        data = [[1, 2], [3, [4, 5]]]
        assert InputValidator.validate_json(data) is True  # nosec B101

    def test_exceeds_max_depth_returns_false(self):
        # max_depth defaults to 10. Build a dict 12 levels deep.
        data = {}
        current = data
        for _ in range(12):
            current["next"] = {}
            current = current["next"]
        assert InputValidator.validate_json(data) is False  # nosec B101

    def test_honor_custom_max_depth(self):
        # Two levels deep, max_depth=1
        data = {"a": {"b": 1}}
        assert InputValidator.validate_json(data, max_depth=1) is False  # nosec B101
        assert InputValidator.validate_json(data, max_depth=2) is True  # nosec B101


class TestFileValidator:
    """FileValidator: size, hash, content-type magic-number sniffing."""

    def test_validate_file_size_under_limit(self):
        assert FileValidator.validate_file_size(b"x" * 100) is True  # nosec B101

    def test_validate_file_size_at_limit(self):
        assert FileValidator.validate_file_size(b"x" * 100, max_size=100) is True  # nosec B101

    def test_validate_file_size_over_limit(self):
        assert FileValidator.validate_file_size(b"x" * 200, max_size=100) is False  # nosec B101

    def test_get_file_hash_sha256(self):
        # Known SHA-256 of "hello"
        h = FileValidator.get_file_hash(b"hello")
        assert h == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"  # nosec B101

    def test_validate_content_type_png_match(self):
        png_magic = b"\x89PNG\r\n\x1a\n" + b"rest of file"
        assert FileValidator.validate_content_type(png_magic, "image/png") is True  # nosec B101

    def test_validate_content_type_png_mismatch(self):
        # File claims PNG but starts with JPEG magic
        jpeg_magic = b"\xff\xd8\xff\xe0" + b"rest"
        assert FileValidator.validate_content_type(jpeg_magic, "image/png") is False  # nosec B101

    def test_validate_content_type_unknown_type_passes(self):
        # Unknown MIME types are allowed through (defense in depth at the route layer)
        assert FileValidator.validate_content_type(b"anything", "application/x-frobnicator") is True  # nosec B101


class TestSecurityHeaders:
    """SecurityHeaders: CSP, HSTS gating, custom overrides."""

    def test_csp_includes_self_default_src(self):
        csp = SecurityHeaders.get_csp_header()
        assert "default-src 'self'" in csp  # nosec B101
        assert "object-src 'none'" in csp  # nosec B101
        assert "frame-ancestors 'none'" in csp  # nosec B101

    def test_security_headers_omits_hsts_for_localhost(self):
        headers = SecurityHeaders.get_security_headers(request_host="localhost")
        assert "Strict-Transport-Security" not in headers  # nosec B101

    def test_security_headers_omits_hsts_for_127(self):
        headers = SecurityHeaders.get_security_headers(request_host="127.0.0.1:8000")
        assert "Strict-Transport-Security" not in headers  # nosec B101

    def test_security_headers_includes_hsts_for_production_host(self):
        headers = SecurityHeaders.get_security_headers(request_host="ai-note-taker.example.com")
        assert "Strict-Transport-Security" in headers  # nosec B101
        assert "max-age=31536000" in headers["Strict-Transport-Security"]  # nosec B101

    def test_security_headers_empty_host_omits_hsts(self):
        # Empty request_host defaults to "localhost" treatment
        headers = SecurityHeaders.get_security_headers()
        assert "Strict-Transport-Security" not in headers  # nosec B101

    def test_security_headers_includes_x_frame_options(self):
        headers = SecurityHeaders.get_security_headers()
        assert headers["X-Frame-Options"] == "DENY"  # nosec B101

    def test_security_headers_includes_nosniff(self):
        headers = SecurityHeaders.get_security_headers()
        assert headers["X-Content-Type-Options"] == "nosniff"  # nosec B101


class TestCheckSecurityThreats:
    """check_security_threats: recursive dict/list walker."""

    def test_clean_data_returns_empty(self):
        assert check_security_threats({"name": "alice", "bio": "I love Python"}) == []  # nosec B101

    def test_top_level_sql_injection(self):
        result = check_security_threats({"q": "1' OR 1=1--"})
        assert "SQL_INJECTION" in result  # nosec B101

    def test_top_level_xss(self):
        result = check_security_threats({"q": "<script>alert(1)</script>"})
        assert "XSS_ATTEMPT" in result  # nosec B101

    def test_nested_threats_found(self):
        data = {
            "outer": {
                "inner": {
                    "evil": "1' UNION SELECT * FROM users--"
                }
            }
        }
        result = check_security_threats(data)
        assert "SQL_INJECTION" in result  # nosec B101

    def test_threats_in_lists(self):
        data = {"items": ["safe", "<script>alert(1)</script>", "also safe"]}
        result = check_security_threats(data)
        assert "XSS_ATTEMPT" in result  # nosec B101

    def test_dedupes_threat_labels(self):
        # Two different SQL strings should still produce only one SQL_INJECTION label
        data = {
            "a": "1' DROP TABLE x;",
            "b": "1' OR 1=1--",
        }
        result = check_security_threats(data)
        assert result.count("SQL_INJECTION") == 1  # nosec B101


class TestConvenienceFunctions:
    """Module-level helpers: sanitize_input, validate_file_upload."""

    def test_sanitize_input_default_length(self):
        result = sanitize_input("<b>x</b>")
        # HTML is escaped by default
        assert "&lt;b&gt;" in result  # nosec B101

    def test_validate_file_upload_valid_filename(self):
        ok, err = validate_file_upload("notes.txt")
        assert ok is True  # nosec B101
        assert err == ""  # nosec B101

    def test_validate_file_upload_invalid_filename(self):
        ok, err = validate_file_upload("evil.exe")
        assert ok is False  # nosec B101
        assert "filename" in err.lower()  # nosec B101

    def test_validate_file_upload_oversize(self):
        # 60 MB content with default 50 MB limit
        ok, err = validate_file_upload("big.pdf", content=b"x" * (60 * 1024 * 1024))
        assert ok is False  # nosec B101
        assert "large" in err.lower() or "MB" in err  # nosec B101

    def test_validate_file_upload_under_size(self):
        ok, err = validate_file_upload("small.pdf", content=b"x" * 100)
        assert ok is True  # nosec B101
        assert err == ""  # nosec B101


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
