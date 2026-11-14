/**
 * NotesSearchController.js - Apple Notes-grade search controller for ANT
 *
 * Modeled after macOS Apple Notes:
 * - ICMSearchQueryController (debouncing, aborting in-flight searches)
 * - ICSearchToken (token parsing and chip formatting)
 * - ICSectionedSearchResults (rendering Top Hits vs Notes)
 * - ICSearchResultRegexMatchFinder (match highlight spans)
 */

export class NotesSearchController {
  constructor(options = {}) {
    this.apiBase = options.apiBase || (typeof API_BASE !== 'undefined' ? API_BASE : 'http://127.0.0.1:8000');
    this.searchInputId = options.searchInputId || 'historySearch';
    this.resultsContainerId = options.resultsContainerId || 'historyList';
    this.debounceMs = options.debounceMs || 250;
    this.activeAbortController = null;
    this.debounceTimer = null;
    this.onSelectNote = options.onSelectNote || null;

    this.init();
  }

  init() {
    const input = document.getElementById(this.searchInputId);
    if (!input) return;

    input.addEventListener('input', (e) => {
      clearTimeout(this.debounceTimer);
      const query = e.target.value.trim();
      this.debounceTimer = setTimeout(() => this.search(query), this.debounceMs);
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        input.value = '';
        this.clearSearch();
      }
    });
  }

  async search(query) {
    if (!query) {
      this.clearSearch();
      return;
    }

    // Cancel in-flight query (mirrors Apple Notes _suspended queryOperationQueue)
    if (this.activeAbortController) {
      this.activeAbortController.abort();
    }
    this.activeAbortController = new AbortController();

    const container = document.getElementById(this.resultsContainerId);
    if (container) {
      container.innerHTML = `
        <div class="search-loading" style="padding: 24px; text-align: center; color: rgba(255,255,255,0.6);">
          <div class="spinner" style="display:inline-block; width:16px; height:16px; border:2px solid rgba(255,255,255,0.2); border-top-color:#3b82f6; border-radius:50%; animation:spin 0.6s linear infinite; margin-bottom:8px;"></div>
          <div>Searching notes and transcripts…</div>
        </div>
      `;
    }

    try {
      const token = window.AuthHelper?.getToken?.();
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(
        `${this.apiBase}/conversations/search?q=${encodeURIComponent(query)}&limit=30`,
        { headers, signal: this.activeAbortController.signal }
      );

      if (!res.ok) throw new Error(`Search failed: HTTP ${res.status}`);
      const data = await res.json();
      this.renderSectionedResults(data);
    } catch (err) {
      if (err.name === 'AbortError') return; // Stale query abandoned
      console.error('[NotesSearchController] Search error:', err);
      if (container) {
        container.innerHTML = `
          <div class="search-error" style="padding: 24px; text-align: center; color: #ef4444;">
            Failed to search conversations. Please try again.
          </div>
        `;
      }
    }
  }

  renderSectionedResults(data) {
    const container = document.getElementById(this.resultsContainerId);
    if (!container) return;

    const topHits = data.sections?.top_hits || [];
    const notes = data.sections?.notes || [];
    const totalCount = data.total_count || (topHits.length + notes.length);

    if (totalCount === 0) {
      container.innerHTML = `
        <div class="search-empty" style="padding: 32px 16px; text-align: center; color: rgba(255,255,255,0.5);">
          <p style="font-size: 14px; font-weight: 500; margin-bottom: 4px;">No Results Found</p>
          <span style="font-size: 12px;">Try adjusting your query, #tags, or filters.</span>
        </div>
      `;
      return;
    }

    let html = `
      <div class="search-meta" style="padding: 8px 12px; font-size: 11px; color: rgba(255,255,255,0.4); display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.06);">
        <span>Found ${totalCount} match${totalCount === 1 ? '' : 'es'} in ${data.execution_time_ms}ms</span>
        <div class="search-tokens" style="display: flex; gap: 4px;">
          ${(data.tokens || []).map(t => `<span class="search-token-badge" style="background: rgba(59,130,246,0.15); color: #60a5fa; padding: 2px 6px; border-radius: 4px; font-size: 10px;">${t.kind === 'tag' ? '#' + t.value : t.value}</span>`).join('')}
        </div>
      </div>
    `;

    // 1. Top Hits Section (Apple Notes signature feature)
    if (topHits.length > 0) {
      html += `
        <div class="search-section" style="margin-top: 8px;">
          <div class="search-section-header" style="padding: 6px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #f59e0b; display: flex; align-items: center; gap: 6px;">
            <span>★ TOP HITS</span>
          </div>
          <div class="search-cards">
            ${topHits.map(item => this.renderResultCard(item, true)).join('')}
          </div>
        </div>
      `;
    }

    // 2. Regular Notes Section
    if (notes.length > 0) {
      html += `
        <div class="search-section" style="margin-top: 12px;">
          <div class="search-section-header" style="padding: 6px 12px; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: rgba(255,255,255,0.5);">
            NOTES & CONVERSATIONS
          </div>
          <div class="search-cards">
            ${notes.map(item => this.renderResultCard(item, false)).join('')}
          </div>
        </div>
      `;
    }

    container.innerHTML = html;

    // Attach click handlers
    container.querySelectorAll('.search-result-card').forEach(card => {
      card.addEventListener('click', () => {
        const id = card.dataset.id;
        if (typeof this.onSelectNote === 'function') {
          this.onSelectNote(id);
        } else if (typeof window.loadConversationById === 'function') {
          window.loadConversationById(id);
        }
      });
    });
  }

  renderResultCard(item, isTopHit = false) {
    const titleSnippet = item.snippets?.find(s => s.field === 'title');
    const msgSnippets = item.snippets?.filter(s => s.field === 'message') || [];

    const highlightedTitle = titleSnippet ? this.applyHighlightSpans(titleSnippet.text, titleSnippet.spans) : this.escapeHtml(item.title);

    let snippetHtml = '';
    if (msgSnippets.length > 0) {
      const best = msgSnippets[0];
      const highlightedSnippet = this.applyHighlightSpans(best.text, best.spans);
      snippetHtml = `
        <div class="search-card-snippet" style="font-size: 12px; color: rgba(255,255,255,0.7); line-height: 1.4; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">
          <span style="font-weight: 600; color: rgba(255,255,255,0.4); text-transform: capitalize;">${best.role || 'Note'}:</span> ${highlightedSnippet}
        </div>
      `;
    }

    const borderStyle = isTopHit ? 'border-left: 3px solid #f59e0b; background: rgba(245,158,11,0.04);' : 'border-left: 3px solid transparent;';

    return `
      <div class="search-result-card" data-id="${item.id}" style="padding: 10px 14px; margin: 4px 8px; border-radius: 6px; cursor: pointer; transition: background 0.15s ease; ${borderStyle}">
        <div class="search-card-header" style="display: flex; justify-content: space-between; align-items: baseline;">
          <h4 style="margin: 0; font-size: 13px; font-weight: 600; color: #fff;">${highlightedTitle}</h4>
          <span style="font-size: 10px; color: rgba(255,255,255,0.4);">${item.updated_at ? new Date(item.updated_at).toLocaleDateString() : ''}</span>
        </div>
        ${snippetHtml}
        ${(item.tags || []).length > 0 ? `
          <div class="search-card-tags" style="margin-top: 6px; display: flex; gap: 4px;">
            ${item.tags.map(t => `<span style="font-size: 10px; color: #93c5fd; background: rgba(59,130,246,0.1); padding: 1px 5px; border-radius: 3px;">#${t}</span>`).join('')}
          </div>
        ` : ''}
      </div>
    `;
  }

  applyHighlightSpans(text, spans) {
    if (!spans || spans.length === 0) return this.escapeHtml(text);
    // Sort spans ascending
    const sorted = [...spans].sort((a, b) => a.start - b.start);
    let result = '';
    let lastIdx = 0;

    for (const span of sorted) {
      if (span.start < lastIdx) continue; // Skip overlaps
      result += this.escapeHtml(text.slice(lastIdx, span.start));
      result += `<mark class="search-highlight" style="background: rgba(234,179,8,0.35); color: #fef08a; padding: 1px 2px; border-radius: 2px;">${this.escapeHtml(text.slice(span.start, span.end))}</mark>`;
      lastIdx = span.end;
    }
    result += this.escapeHtml(text.slice(lastIdx));
    return result;
  }

  escapeHtml(str) {
    if (!str) return '';
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  clearSearch() {
    if (typeof window.renderHistoryList === 'function') {
      window.renderHistoryList();
    }
  }
}

// Global exposure
if (typeof window !== 'undefined') {
  window.NotesSearchController = NotesSearchController;
}
