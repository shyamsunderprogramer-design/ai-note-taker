"""
note_search.py - Advanced Note & Conversation Search Engine

Reverse-engineered and modeled after the macOS Apple Notes architecture:
- ICSearchToken / ICSearchUserInput (token parsing, tags, scopes)
- ICSearchQueryOperation & rankingQueries (multi-tier relevance scoring)
- ICSearchResultRegexMatchFinder (match range calculation & snippet extraction)
- ICSectionedSearchResults (top hits, notes, message matches)
"""

import math
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class SearchToken:
    """Represents a parsed query token (modeled after ICSearchToken)."""
    raw: str
    kind: str  # "term", "phrase", "tag", "role", "date_after", "date_before", "has"
    value: str


@dataclass
class SearchMatchSpan:
    """Represents character offsets for highlighting (modeled after ICSearchResultRegexMatchFinder)."""
    start: int
    end: int
    matched_text: str


@dataclass
class SearchSnippet:
    """Context snippet surrounding a match with highlight spans."""
    text: str
    spans: List[SearchMatchSpan]
    field: str  # "title", "message"
    message_index: Optional[int] = None
    role: Optional[str] = None


@dataclass
class NoteSearchResult:
    """Individual ranked note/conversation result (modeled after ICSearchResult)."""
    id: str
    title: str
    score: float
    created_at: Optional[str]
    updated_at: Optional[str]
    message_count: int
    snippets: List[SearchSnippet] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    is_pinned: bool = False
    is_top_hit: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "score": round(self.score, 2),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "message_count": self.message_count,
            "is_pinned": self.is_pinned,
            "is_top_hit": self.is_top_hit,
            "tags": self.tags,
            "snippets": [
                {
                    "text": s.text,
                    "field": s.field,
                    "message_index": s.message_index,
                    "role": s.role,
                    "spans": [{"start": sp.start, "end": sp.end, "text": sp.matched_text} for sp in s.spans]
                }
                for s in self.snippets
            ]
        }


@dataclass
class SectionedSearchResults:
    """Categorized search results (modeled after ICSectionedSearchResults)."""
    query: str
    tokens: List[Dict[str, str]]
    top_hits: List[Dict[str, Any]]
    notes: List[Dict[str, Any]]
    total_count: int
    execution_time_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "tokens": self.tokens,
            "total_count": self.total_count,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "sections": {
                "top_hits": self.top_hits,
                "notes": self.notes
            }
        }


class SearchUserInputParser:
    """Parses user input into terms, phrases, tags, and filters (ICSearchUserInput)."""

    TAG_PATTERN = re.compile(r"(?:^|\s)(?:#([a-zA-Z0-9_\-]+)|tag:([a-zA-Z0-9_\-]+))", re.IGNORECASE)
    ROLE_PATTERN = re.compile(r"(?:^|\s)(?:role|from):(user|assistant|ai|me)\b", re.IGNORECASE)
    HAS_PATTERN = re.compile(r"(?:^|\s)has:(audio|screenshot|image|code)\b", re.IGNORECASE)
    DATE_AFTER_PATTERN = re.compile(r"(?:^|\s)after:(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)
    DATE_BEFORE_PATTERN = re.compile(r"(?:^|\s)before:(\d{4}-\d{2}-\d{2})\b", re.IGNORECASE)
    PHRASE_PATTERN = re.compile(r'"([^"]+)"')

    @classmethod
    def parse(cls, query_string: str) -> List[SearchToken]:
        tokens: List[SearchToken] = []
        text = query_string.strip()
        if not text:
            return tokens

        # 1. Quoted phrases
        for match in cls.PHRASE_PATTERN.finditer(text):
            phrase = match.group(1).strip()
            if phrase:
                tokens.append(SearchToken(raw=match.group(0), kind="phrase", value=phrase.lower()))
        text = cls.PHRASE_PATTERN.sub(" ", text)

        # 2. Tags (#tag or tag:name)
        for match in cls.TAG_PATTERN.finditer(text):
            tag_val = match.group(1) or match.group(2)
            if tag_val:
                tokens.append(SearchToken(raw=match.group(0).strip(), kind="tag", value=tag_val.lower()))
        text = cls.TAG_PATTERN.sub(" ", text)

        # 3. Roles (role:user, role:assistant, from:me, from:ai)
        for match in cls.ROLE_PATTERN.finditer(text):
            role_val = match.group(1).lower()
            canonical_role = "user" if role_val in ("user", "me") else "assistant"
            tokens.append(SearchToken(raw=match.group(0).strip(), kind="role", value=canonical_role))
        text = cls.ROLE_PATTERN.sub(" ", text)

        # 4. Filter flags (has:audio, has:screenshot, etc.)
        for match in cls.HAS_PATTERN.finditer(text):
            has_val = match.group(1).lower()
            tokens.append(SearchToken(raw=match.group(0).strip(), kind="has", value=has_val))
        text = cls.HAS_PATTERN.sub(" ", text)

        # 5. Date boundaries
        for match in cls.DATE_AFTER_PATTERN.finditer(text):
            tokens.append(SearchToken(raw=match.group(0).strip(), kind="date_after", value=match.group(1)))
        text = cls.DATE_AFTER_PATTERN.sub(" ", text)

        for match in cls.DATE_BEFORE_PATTERN.finditer(text):
            tokens.append(SearchToken(raw=match.group(0).strip(), kind="date_before", value=match.group(1)))
        text = cls.DATE_BEFORE_PATTERN.sub(" ", text)

        # 6. Remaining free-text terms
        for word in text.split():
            clean_word = word.strip().lower()
            if clean_word:
                tokens.append(SearchToken(raw=word, kind="term", value=clean_word))

        return tokens


class SearchResultRegexMatchFinder:
    """Calculates highlight spans and extracts context snippets (ICSearchResultRegexMatchFinder)."""

    @staticmethod
    def build_search_regex(tokens: List[SearchToken]) -> Optional[re.Pattern]:
        patterns = []
        for t in tokens:
            if t.kind in ("term", "phrase"):
                escaped = re.escape(t.value)
                patterns.append(rf"\b{escaped}\b" if t.kind == "term" else escaped)
            elif t.kind == "tag":
                patterns.append(rf"#{re.escape(t.value)}\b")
        if not patterns:
            return None
        combined = "|".join(patterns)
        return re.compile(rf"({combined})", re.IGNORECASE)

    @classmethod
    def find_match_spans(cls, text: str, regex: re.Pattern) -> List[SearchMatchSpan]:
        spans = []
        for m in regex.finditer(text):
            spans.append(SearchMatchSpan(start=m.start(), end=m.end(), matched_text=m.group(0)))
        return spans

    @classmethod
    def extract_snippet(
        cls, text: str, spans: List[SearchMatchSpan], max_length: int = 160
    ) -> Tuple[str, List[SearchMatchSpan]]:
        """Extract a snippet around the earliest/best match with adjusted span offsets."""
        if not text:
            return "", []
        if not spans:
            # Fallback snippet: beginning of text
            snippet_text = text[:max_length].strip()
            if len(text) > max_length:
                snippet_text += "…"
            return snippet_text, []

        first_span = spans[0]
        match_center = (first_span.start + first_span.end) // 2
        half_window = max_length // 2

        start_idx = max(0, match_center - half_window)
        end_idx = min(len(text), start_idx + max_length)

        # Snap to word boundary if possible
        if start_idx > 0:
            space_pos = text.find(" ", start_idx)
            if space_pos != -1 and space_pos < first_span.start:
                start_idx = space_pos + 1

        if end_idx < len(text):
            space_pos = text.rfind(" ", start_idx, end_idx)
            if space_pos != -1 and space_pos > first_span.end:
                end_idx = space_pos

        raw_snippet = text[start_idx:end_idx]
        prefix = "… " if start_idx > 0 else ""
        suffix = " …" if end_idx < len(text) else ""
        formatted_snippet = f"{prefix}{raw_snippet}{suffix}"

        # Adjust spans relative to snippet start
        adjusted_spans = []
        offset_shift = len(prefix) - start_idx
        for s in spans:
            if s.start >= start_idx and s.end <= end_idx:
                adjusted_spans.append(
                    SearchMatchSpan(
                        start=s.start + offset_shift,
                        end=s.end + offset_shift,
                        matched_text=s.matched_text,
                    )
                )

        return formatted_snippet, adjusted_spans


class NoteSearchRanker:
    """Multi-tier relevance ranker modeled after Apple Notes rankingQueries."""

    @classmethod
    def compute_score(
        cls,
        title: str,
        messages: List[Dict[str, Any]],
        tokens: List[SearchToken],
        updated_at: Optional[datetime] = None,
        is_pinned: bool = False,
    ) -> Tuple[float, List[SearchSnippet]]:
        score = 0.0
        snippets: List[SearchSnippet] = []

        term_values = [t.value for t in tokens if t.kind in ("term", "phrase")]
        tag_values = [t.value for t in tokens if t.kind == "tag"]
        role_filters = [t.value for t in tokens if t.kind == "role"]

        regex = SearchResultRegexMatchFinder.build_search_regex(tokens)
        title_lower = (title or "").lower()

        # ----------------------------------------------------
        # Tier 1: Title exact & prefix match (Top Hit weight)
        # ----------------------------------------------------
        full_query_term = " ".join(term_values).strip()
        if full_query_term and title_lower == full_query_term:
            score += 150.0  # Exact full title match
        elif full_query_term and title_lower.startswith(full_query_term):
            score += 90.0  # Title prefix match
        elif full_query_term and full_query_term in title_lower:
            score += 60.0  # Title contains full phrase

        # Individual terms in title
        for term in term_values:
            if re.search(rf"\b{re.escape(term)}\b", title_lower):
                score += 25.0
            elif term in title_lower:
                score += 12.0

        if regex and title:
            title_spans = SearchResultRegexMatchFinder.find_match_spans(title, regex)
            if title_spans:
                snippets.append(
                    SearchSnippet(
                        text=title,
                        spans=title_spans,
                        field="title"
                    )
                )

        # ----------------------------------------------------
        # Tier 2: Message body matches
        # ----------------------------------------------------
        body_matches_found = 0
        for idx, msg in enumerate(messages):
            msg_text = str(msg.get("text", "") or msg.get("content", ""))
            msg_role = str(msg.get("role", "user")).lower()

            # Filter by role if specified
            if role_filters and msg_role not in role_filters:
                continue

            msg_lower = msg_text.lower()

            # Quoted phrase matches in body
            for t in tokens:
                if t.kind == "phrase" and t.value in msg_lower:
                    score += 35.0
                elif t.kind == "term" and t.value in msg_lower:
                    occurrences = len(re.findall(rf"\b{re.escape(t.value)}\b", msg_lower))
                    score += min(occurrences * 5.0, 30.0)

            # Extract snippet for the best matched messages (up to 3 snippets)
            if regex and body_matches_found < 3:
                msg_spans = SearchResultRegexMatchFinder.find_match_spans(msg_text, regex)
                if msg_spans:
                    body_matches_found += 1
                    snippet_text, adjusted_spans = SearchResultRegexMatchFinder.extract_snippet(msg_text, msg_spans)
                    snippets.append(
                        SearchSnippet(
                            text=snippet_text,
                            spans=adjusted_spans,
                            field="message",
                            message_index=idx,
                            role=msg_role
                        )
                    )

        # ----------------------------------------------------
        # Tier 3: Tags match
        # ----------------------------------------------------
        if tag_values:
            # Check title and messages for matching tags
            all_content = title_lower + " " + " ".join(str(m.get("text", "")) for m in messages).lower()
            for tv in tag_values:
                if f"#{tv}" in all_content or tv in all_content:
                    score += 70.0 if not term_values else 35.0

        # ----------------------------------------------------
        # Tier 4: Pinned & Recency Boost
        # ----------------------------------------------------
        if is_pinned:
            score += 10.0

        if updated_at:
            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_days = max(0.0, (now - updated_at).total_seconds() / 86400.0)
            # Exponential decay: recent notes (< 7 days) receive up to +15 pts
            recency_boost = 15.0 * math.exp(-age_days / 14.0)
            score += recency_boost

        return score, snippets


class NoteSearchEngine:
    """Coordinates search pipeline, token matching, ranking, and sectioning."""

    @classmethod
    def search_conversations(
        cls,
        conversations: List[Any],
        query: str,
        limit: int = 50,
        top_hits_threshold: float = 65.0,
    ) -> SectionedSearchResults:
        start_time = time.perf_counter()
        tokens = SearchUserInputParser.parse(query)

        token_summary = [{"kind": t.kind, "value": t.value, "raw": t.raw} for t in tokens]
        if not tokens:
            # Empty query: return most recent conversations
            results = []
            for conv in conversations[:limit]:
                title = getattr(conv, "title", "Untitled") or "Untitled"
                conv_id = str(getattr(conv, "id", ""))
                created = getattr(conv, "created_at", None)
                updated = getattr(conv, "updated_at", None)
                msg_count = getattr(conv, "message_count", 0)
                results.append(
                    NoteSearchResult(
                        id=conv_id,
                        title=title,
                        score=1.0,
                        created_at=created.isoformat() if hasattr(created, "isoformat") else str(created or ""),
                        updated_at=updated.isoformat() if hasattr(updated, "isoformat") else str(updated or ""),
                        message_count=msg_count,
                    ).to_dict()
                )
            duration = (time.perf_counter() - start_time) * 1000.0
            return SectionedSearchResults(
                query=query,
                tokens=token_summary,
                top_hits=[],
                notes=results,
                total_count=len(results),
                execution_time_ms=duration,
            )

        # Apply content and date filters before scoring
        has_filters = {t.value for t in tokens if t.kind == "has"}
        date_after_tokens = [t.value for t in tokens if t.kind == "date_after"]
        date_before_tokens = [t.value for t in tokens if t.kind == "date_before"]

        ranked_results: List[NoteSearchResult] = []

        for conv in conversations:
            title = getattr(conv, "title", "Untitled") or "Untitled"
            messages = getattr(conv, "messages", []) or []
            created = getattr(conv, "created_at", None)
            updated = getattr(conv, "updated_at", None)
            is_pinned = getattr(conv, "pinned", False)

            # Date filter checks
            if date_after_tokens and updated:
                cutoff = datetime.strptime(date_after_tokens[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                up_dt = updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)
                if up_dt < cutoff:
                    continue

            if date_before_tokens and updated:
                cutoff = datetime.strptime(date_before_tokens[0], "%Y-%m-%d").replace(tzinfo=timezone.utc)
                up_dt = updated if updated.tzinfo else updated.replace(tzinfo=timezone.utc)
                if up_dt > cutoff:
                    continue

            # Content flags (has:audio, has:screenshot, etc.)
            if "audio" in has_filters:
                has_audio = any(m.get("audio_url") or m.get("has_audio") for m in messages)
                if not has_audio:
                    continue

            if "screenshot" in has_filters or "image" in has_filters:
                has_img = any(m.get("image") or m.get("screenshot") or m.get("has_screenshot") for m in messages)
                if not has_img:
                    continue

            # Compute multi-tier score
            score, snippets = NoteSearchRanker.compute_score(
                title=title,
                messages=messages,
                tokens=tokens,
                updated_at=updated,
                is_pinned=is_pinned,
            )

            # Only include if score reflects an actual match
            if score > 5.0 and snippets:
                # Extract any tags in content
                extracted_tags = list(set(re.findall(r"#([a-zA-Z0-9_\-]+)", title + " " + " ".join(str(m.get("text", "")) for m in messages))))
                ranked_results.append(
                    NoteSearchResult(
                        id=str(getattr(conv, "id", "")),
                        title=title,
                        score=score,
                        created_at=created.isoformat() if hasattr(created, "isoformat") else str(created or ""),
                        updated_at=updated.isoformat() if hasattr(updated, "isoformat") else str(updated or ""),
                        message_count=getattr(conv, "message_count", len(messages)),
                        snippets=snippets,
                        tags=extracted_tags,
                        is_pinned=is_pinned,
                    )
                )

        # Sort descending by score
        ranked_results.sort(key=lambda r: r.score, reverse=True)

        # Sectioning: Top Hits vs Standard Notes
        top_hits = []
        regular_notes = []

        for idx, res in enumerate(ranked_results[:limit]):
            if idx == 0 and res.score >= top_hits_threshold:
                res.is_top_hit = True
                top_hits.append(res.to_dict())
            elif res.score >= top_hits_threshold and idx < 3:
                res.is_top_hit = True
                top_hits.append(res.to_dict())
            else:
                regular_notes.append(res.to_dict())

        duration = (time.perf_counter() - start_time) * 1000.0

        return SectionedSearchResults(
            query=query,
            tokens=token_summary,
            top_hits=top_hits,
            notes=regular_notes,
            total_count=len(ranked_results),
            execution_time_ms=duration,
        )
