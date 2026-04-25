/**
 * Cognitive Graph Page
 * Works with in-memory backend (default) and Neo4j (when available)
 */

import { State } from '../core/state.js';

const API_BASE = 'http://127.0.0.1:8000';

class CognitiveGraph {
  constructor() {
    this.currentTab = 'overview';
    this.isConnected = false;
    this.backend = 'unknown';
    this.searchTimeout = null;
    this.init();
  }

  init() {
    State.init();
    this.setupTabs();
    this.setupSearch();
    this.setupExtract();
    this.checkConnection().then(() => {
      this.loadOverviewData();
      this.loadStats();
    });
  }

  // --- Connection ---
  async checkConnection() {
    try {
      const r = await fetch(`${API_BASE}/cognitive-graph/status`);
      const d = await r.json();
      this.isConnected = d.connected !== false && d.available !== false;
      this.backend = d.backend || 'unknown';
    } catch {
      this.isConnected = false;
    }
    const pill = document.getElementById('statusPill');
    const label = document.getElementById('statusLabel');
    if (pill) pill.className = `cg-status-pill ${this.isConnected ? 'connected' : 'disconnected'}`;
    if (label) {
      const be = this.backend === 'in_memory' ? 'In-Memory' : this.backend === 'neo4j' ? 'Neo4j' : '';
      label.textContent = this.isConnected ? `Connected · ${be}` : 'Disconnected';
    }
  }

  // --- Tabs ---
  setupTabs() {
    document.querySelectorAll('.cg-tab-btn[data-tab]').forEach(btn => {
      btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        this.currentTab = tab;
        document.querySelectorAll('.cg-tab-btn').forEach(b => b.classList.toggle('active', b.dataset.tab === tab));
        document.querySelectorAll('.cg-tab-content').forEach(el => el.classList.remove('active'));
        const el = document.getElementById(`tab-${tab}`);
        if (el) el.classList.add('active');
        if (tab === 'companies') this.loadCompaniesData();
        if (tab === 'skills') this.loadSkillsData();
      });
    });
  }

  // --- Data Loading ---
  async loadOverviewData() {
    try {
      const r = await fetch(`${API_BASE}/cognitive-graph/history/${DEFAULT_USER_ID}?limit=10`);
      if (!r.ok) throw new Error();
      const d = await r.json();
      this.displayRecentInterviews(d.interviews);
      this.displayActivityChart(d.interviews);
      const companies = new Set();
      (d.interviews || []).forEach(i => {
        if (i.properties?.company) companies.add(i.properties.company);
      });
      this.displayTopCompanies([...companies]);
    } catch (e) {
      console.error('[CG] loadOverview failed:', e);
    }
  }

  async loadStats() {
    try {
      const r = await fetch(`${API_BASE}/cognitive-graph/stats`);
      if (!r.ok) throw new Error();
      const d = await r.json();
      if (d.stats) {
        this.animateNum('statInterviews', d.stats.interviews || 0);
        this.animateNum('statQuestions', d.stats.questions || 0);
        this.animateNum('statCompanies', d.stats.companies || 0);
        this.animateNum('statTopics', d.stats.topics || 0);
      }
      if (d.stats && d.stats.questions > 0) this.loadCategoryChart();
    } catch (e) {
      console.error('[CG] loadStats failed:', e);
    }
  }

  animateNum(id, target) {
    const el = document.getElementById(id);
    if (!el) return;
    const start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / 800, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.floor(target * ease).toLocaleString();
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }

  // --- Activity Chart ---
  displayActivityChart(interviews) {
    const c = document.getElementById('activityChart');
    if (!c) return;
    if (!interviews || interviews.length === 0) {
      c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div><div class="cg-empty-title">No interviews yet</div></div>';
      return;
    }
    const byMonth = {};
    interviews.forEach(i => {
      const ts = i.created_at || i.properties?.date || i.timestamp;
      const d = ts ? new Date(ts) : new Date();
      const k = d.toLocaleString('default', { month: 'short' });
      byMonth[k] = (byMonth[k] || 0) + 1;
    });
    const months = Object.keys(byMonth).slice(-6);
    const max = Math.max(...months.map(m => byMonth[m]), 1);
    c.innerHTML = '<div class="cg-bar-chart">' +
      months.map((m, i) => `<div class="cg-bar" style="height:${(byMonth[m]/max)*100}%;animation-delay:${i*100}ms">
        <span class="cg-bar-value">${byMonth[m]}</span><span class="cg-bar-label">${m}</span></div>`).join('') + '</div>';
  }

  // --- Category Chart ---
  async loadCategoryChart() {
    try {
      const r = await fetch(`${API_BASE}/cognitive-graph/search?q=&limit=100`);
      const d = await r.json();
      const cats = {};
      (d.results || []).forEach(r => {
        const cat = r.properties?.category || r.label || 'Other';
        cats[cat] = (cats[cat] || 0) + 1;
      });
      const data = Object.entries(cats).map(([name, count]) => ({ name, count }));
      this.displayCategoryChart(data);
    } catch {}
  }

  displayCategoryChart(data) {
    const c = document.getElementById('categoryChart');
    if (!c) return;
    if (!data || data.length === 0) {
      c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/></svg></div><div class="cg-empty-title">No categories yet</div></div>';
      return;
    }
    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#ec4899'];
    const total = data.reduce((s, d) => s + d.count, 0);
    let angle = 0;
    const parts = data.map((d, i) => {
      const a = (d.count / total) * 360;
      const s = angle;
      angle += a;
      return `${colors[i % colors.length]} ${s}deg ${angle}deg`;
    });
    c.innerHTML = `<div class="cg-pie-wrap">
      <div class="cg-pie" style="background:conic-gradient(${parts.join(',')})">
        <div class="cg-pie-hole"><div class="cg-pie-total">${total}</div><div class="cg-pie-label">Total</div></div>
      </div>
      <div class="cg-legend">
        ${data.map((d, i) => `<div class="cg-legend-row"><div class="cg-legend-dot" style="background:${colors[i % colors.length]}"></div>${esc(d.name)} <span style="margin-left:auto;color:rgba(255,255,255,0.5)">${d.count}</span></div>`).join('')}
      </div>
    </div>`;
  }

  // --- Recent Interviews ---
  displayRecentInterviews(interviews) {
    const c = document.getElementById('recentInterviews');
    if (!c) return;
    if (!interviews || interviews.length === 0) {
      c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg></div><div class="cg-empty-title">No interviews yet</div><div class="cg-empty-sub">Start recording to build your graph</div></div>';
      return;
    }
    c.innerHTML = interviews.map(i => {
      const p = i.properties || {};
      const title = p.company ? `${p.company} — ${p.role || 'Interview'}` : 'Interview';
      const ts = i.created_at || p.date || i.timestamp;
      const qCount = p.question_count || 0;
      return `<div class="cg-interview-item">
        <div class="cg-interview-title-row">
          <span class="cg-interview-name">${esc(title)}</span>
          <span class="cg-interview-date">${fmtDate(ts)}</span>
        </div>
        <div class="cg-interview-badges">
          <span class="cg-badge cg-badge-questions">${qCount} questions</span>
          ${p.company ? `<span class="cg-badge cg-badge-company">${esc(p.company)}</span>` : ''}
        </div>
      </div>`;
    }).join('');
  }

  // --- Top Companies ---
  displayTopCompanies(companies) {
    const c = document.getElementById('topCompanies');
    if (!c) return;
    if (!companies || companies.length === 0) {
      c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></div><div class="cg-empty-title">No companies yet</div></div>';
      return;
    }
    c.innerHTML = '<div class="cg-company-grid">' + companies.map(name => {
      const cls = name.toLowerCase() === 'google' ? 'google' : name.toLowerCase() === 'meta' ? 'meta' : name.toLowerCase() === 'amazon' ? 'amazon' : 'default';
      return `<div class="cg-company-card" data-company="${esc(name)}">
        <div class="cg-company-avatar ${cls}">${name.charAt(0)}</div>
        <div class="cg-company-name">${esc(name)}</div>
        <div class="cg-company-sub">Click for insights</div>
      </div>`;
    }).join('') + '</div>';
    c.querySelectorAll('.cg-company-card').forEach(card => {
      card.addEventListener('click', () => this.viewCompany(card.dataset.company));
    });
  }

  // --- Search ---
  setupSearch() {
    const input = document.getElementById('searchInput');
    input?.addEventListener('input', (e) => {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => { if (e.target.value.trim()) this.performSearch(); }, 300);
    });
    input?.addEventListener('keypress', (e) => { if (e.key === 'Enter') { clearTimeout(this.searchTimeout); this.performSearch(); } });
    document.getElementById('searchBtn')?.addEventListener('click', () => this.performSearch());
    document.getElementById('advancedSearchBtn')?.addEventListener('click', () => this.performAdvancedSearch());
    document.getElementById('clearFiltersBtn')?.addEventListener('click', () => this.clearSearchFilters());
  }

  async performSearch() {
    const q = document.getElementById('searchInput')?.value.trim();
    if (!q) return;
    const c = document.getElementById('searchResults');
    c.innerHTML = '<div class="cg-loading"><div class="cg-spinner"></div></div>';
    try {
      const r = await fetch(`${API_BASE}/cognitive-graph/search?q=${encodeURIComponent(q)}&limit=20`);
      const d = await r.json();
      this.displaySearchResults(d.results, q);
    } catch {
      c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div><div class="cg-empty-title">Search failed</div></div>';
    }
  }

  async performAdvancedSearch() {
    const q = document.getElementById('searchInput')?.value.trim() || '';
    const company = document.getElementById('filterCompany')?.value;
    const category = document.getElementById('filterCategory')?.value;
    const difficulty = document.getElementById('filterDifficulty')?.value;
    const params = new URLSearchParams();
    if (q) params.append('query', q);
    if (company) params.append('company', company);
    if (category) params.append('category', category);
    if (difficulty) params.append('difficulty', difficulty);
    params.append('limit', '50');
    const c = document.getElementById('searchResults');
    c.innerHTML = '<div class="cg-loading"><div class="cg-spinner"></div></div>';
    try {
      const r = await fetch(`${API_BASE}/cognitive-graph/search/advanced?${params}`);
      const d = await r.json();
      const stats = document.getElementById('searchStats');
      if (stats) { stats.style.display = d.count > 0 ? 'block' : 'none'; stats.textContent = `Found ${d.count} results`; }
      this.displaySearchResults(d.results, q);
    } catch {
      c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div><div class="cg-empty-title">Search failed</div></div>';
    }
  }

  displaySearchResults(results, query) {
    const c = document.getElementById('searchResults');
    if (!c) return;
    if (!results || results.length === 0) {
      c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div><div class="cg-empty-title">No results found</div><div class="cg-empty-sub">Try different keywords</div></div>';
      return;
    }
    c.innerHTML = results.map(r => {
      const p = r.properties || {};
      const text = p.text || p.name || r.label || '';
      const cat = p.category || '';
      return `<div class="cg-result-card">
        <div class="cg-result-q">${highlight(esc(text), query)}</div>
        <div class="cg-result-tags">
          <span class="cg-tag cg-tag-node">${esc(r.label || 'Node')}</span>
          ${cat ? `<span class="cg-tag cg-tag-cat">${cat.replace('_', ' ')}</span>` : ''}
          ${r.relevance ? `<span class="cg-tag cg-tag-score">⭐ ${(r.relevance*10).toFixed(1)}</span>` : ''}
        </div>
      </div>`;
    }).join('');
  }

  clearSearchFilters() {
    ['searchInput', 'filterCompany', 'filterCategory', 'filterDifficulty'].forEach(id => {
      const el = document.getElementById(id); if (el) el.value = '';
    });
    const stats = document.getElementById('searchStats');
    if (stats) stats.style.display = 'none';
    const c = document.getElementById('searchResults');
    if (c) c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg></div><div class="cg-empty-title">Search your knowledge graph</div></div>';
  }

  // --- Companies ---
  async loadCompaniesData() {
    try {
      const r = await fetch(`${API_BASE}/predict/companies`);
      const d = await r.json();
      const select = document.getElementById('filterCompany');
      if (select && d.companies) {
        select.innerHTML = '<option value="">All Companies</option>';
        d.companies.forEach(c => { select.innerHTML += `<option value="${esc(c)}">${esc(c)}</option>`; });
      }
      const c = document.getElementById('companyInsights');
      if (c && d.companies?.length > 0) {
        c.innerHTML = '<div class="cg-company-grid">' + d.companies.map(name => {
          const cls = name.toLowerCase() === 'google' ? 'google' : name.toLowerCase() === 'meta' ? 'meta' : name.toLowerCase() === 'amazon' ? 'amazon' : 'default';
          return `<div class="cg-company-card" data-company="${esc(name)}">
            <div class="cg-company-avatar ${cls}">${name.charAt(0)}</div>
            <div class="cg-company-name">${esc(name)}</div>
            <div class="cg-company-sub">Click for insights</div>
          </div>`;
        }).join('') + '</div>';
        c.querySelectorAll('.cg-company-card').forEach(card => {
          card.addEventListener('click', () => this.viewCompany(card.dataset.company));
        });
      } else if (c) {
        c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></div><div class="cg-empty-title">No companies yet</div></div>';
      }
    } catch (e) { console.error('[CG] loadCompanies failed:', e); }
  }

  async viewCompany(name) {
    try {
      const r = await fetch(`${API_BASE}/cognitive-graph/company/${encodeURIComponent(name)}`);
      const d = await r.json();
      const c = document.getElementById('companyInsights');
      const ins = d.insights;
      if (!ins || (ins.total_questions === 0 && !ins.common_topics?.length)) {
        c.innerHTML = `<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg></div><div class="cg-empty-title">No data for ${esc(name)}</div></div>`;
        return;
      }
      const cls = name.toLowerCase() === 'google' ? 'google' : name.toLowerCase() === 'meta' ? 'meta' : name.toLowerCase() === 'amazon' ? 'amazon' : 'default';
      c.innerHTML = `
        <div class="cg-detail-header">
          <div class="cg-company-avatar ${cls}" style="width:56px;height:56px;font-size:22px;">${name.charAt(0)}</div>
          <div><h3 style="font-size:20px;font-weight:700;color:#fff;margin-bottom:2px">${esc(name)}</h3><span style="font-size:13px;color:rgba(255,255,255,0.4)">Interview Insights</span></div>
        </div>
        <div class="cg-detail-stats">
          <div class="cg-detail-stat"><div class="cg-detail-val">${ins.total_questions || 0}</div><div class="cg-detail-label">Questions</div></div>
          <div class="cg-detail-stat"><div class="cg-detail-val">${ins.avg_confidence ? ins.avg_confidence.toFixed(1) : '-'}</div><div class="cg-detail-label">Confidence</div></div>
          <div class="cg-detail-stat"><div class="cg-detail-val">${ins.categories?.length || 0}</div><div class="cg-detail-label">Categories</div></div>
        </div>
        ${ins.common_topics?.length ? `<div class="cg-detail-topics"><strong>Common Topics</strong><div>${ins.common_topics.map(t => `<span class="cg-topic-chip">${esc(t)}</span>`).join('')}</div></div>` : ''}
        <button class="cg-btn cg-btn-ghost" style="margin-top:16px" onclick="window.cg.loadCompaniesData()">← Back to Companies</button>`;
    } catch (e) { console.error('[CG] viewCompany failed:', e); }
  }

  // --- Skills ---
  async loadSkillsData() {
    const c = document.getElementById('skillsList');
    if (!c) return;
    try {
      const r = await fetch(`${API_BASE}/cognitive-graph/stats`);
      if (!r.ok) throw new Error();
      const d = await r.json();
      const skills = d.skills || [];
      if (skills.length > 0) {
        const pctMap = { expert: 90, advanced: 75, intermediate: 50, beginner: 25 };
        c.innerHTML = skills.map(s => {
          const level = s.level || s.proficiency || 'intermediate';
          const pct = pctMap[level] || 50;
          return `<div class="cg-skill-row">
            <span class="cg-skill-name">${esc(s.name || s.skill)}</span>
            <div class="cg-skill-track"><div class="cg-skill-fill ${level}" style="width:${pct}%"></div></div>
            <span class="cg-skill-level">${level}</span>
          </div>`;
        }).join('');
        return;
      }
    } catch {}
    c.innerHTML = '<div class="cg-empty"><div class="cg-empty-icon"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg></div><div class="cg-empty-title">No skills data yet</div><div class="cg-empty-sub">Complete interviews to track skill progression</div></div>';
  }

  // --- Extract ---
  setupExtract() {
    document.getElementById('extractBtn')?.addEventListener('click', () => this.extractEntities());
  }

  async extractEntities() {
    const text = document.getElementById('extractText')?.value.trim();
    if (!text) { this.showToast('Please enter text to extract entities', 'warning'); return; }
    const btn = document.getElementById('extractBtn');
    btn.disabled = true; btn.textContent = 'Extracting...';
    try {
      const r = await fetch(`${API_BASE}/extract-entities`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text })
      });
      const d = await r.json();
      const companies = d.companies || d.entities?.companies || [];
      const skills = d.skills || d.entities?.skills || [];
      const topics = d.topics || d.entities?.topics || [];
      const c = document.getElementById('extractResult');
      c.innerHTML = `<div class="cg-extract-result">
        ${companies.length ? `<div class="cg-entity-group"><div class="cg-entity-label">Companies</div><div class="cg-entity-chips">${companies.map(x => `<span class="cg-chip cg-chip-company">${esc(x)}</span>`).join('')}</div></div>` : ''}
        ${skills.length ? `<div class="cg-entity-group"><div class="cg-entity-label">Skills</div><div class="cg-entity-chips">${skills.map(x => `<span class="cg-chip cg-chip-skill">${esc(x)}</span>`).join('')}</div></div>` : ''}
        ${topics.length ? `<div class="cg-entity-group"><div class="cg-entity-label">Topics</div><div class="cg-entity-chips">${topics.map(x => `<span class="cg-chip cg-chip-topic">${esc(x)}</span>`).join('')}</div></div>` : ''}
        ${!companies.length && !skills.length && !topics.length ? '<p style="color:rgba(255,255,255,0.35)">No entities found in the text.</p>' : ''}
      </div>`;
    } catch {
      this.showToast('Extraction failed', 'error');
    } finally { btn.disabled = false; btn.textContent = 'Extract Entities'; }
  }

  // --- Utilities ---
  showToast(msg, type = 'info') {
    const t = document.createElement('div');
    t.className = 'cg-toast'; t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.classList.add('show'), 10);
    setTimeout(() => { t.classList.remove('show'); setTimeout(() => t.remove(), 300); }, 3000);
  }
}

// Helpers
function esc(s) {
  if (!s) return '';
  const d = document.createElement('div'); d.textContent = s; return d.innerHTML;
}
function fmtDate(ts) {
  if (!ts) return '';
  const d = new Date(ts);
  if (isNaN(d.getTime())) return '';
  const diff = Math.floor((Date.now() - d) / 86400000);
  if (diff === 0) return 'Today'; if (diff === 1) return 'Yesterday';
  if (diff < 7) return `${diff}d ago`; if (diff < 30) return `${Math.floor(diff/7)}w ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
function highlight(text, q) {
  if (!q) return text;
  return text.replace(new RegExp(`(${q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi'),
    '<mark style="background:rgba(59,130,246,0.25);color:#93c5fd;border-radius:3px;padding:0 2px">$1</mark>');
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  window.cg = new CognitiveGraph();
});