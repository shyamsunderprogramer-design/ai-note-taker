/**
 * Cognitive Graph Component
 * Modular class-based component for managing the cognitive graph feature
 */

import { State } from '../core/state.js';
import { Events, EventNames } from '../core/events.js';

const API_BASE = 'http://127.0.0.1:8000';
const DEFAULT_USER_ID = 'default';

export class CognitiveGraph {
  constructor() {
    this.container = document.querySelector('.cg-container');
    this.currentTab = 'overview';
    this.isConnected = false;
    this.searchTimeout = null;

    if (this.container) {
      this.init();
    }
  }

  init() {
    // Initialize state
    State.init();

    // Check connection and load initial data
    this.checkConnection().then(() => {
      this.initializeSchema();
      this.loadOverviewData();
      this.loadStats();
    });

    // Setup event listeners
    this.setupEventListeners();

    // Animate entrance
    this.animateEntrance();

    console.log('[CognitiveGraph] Initialized');
  }

  // Animation
  animateEntrance() {
    const elements = document.querySelectorAll('.cg-animate-in');
    elements.forEach((el, i) => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      setTimeout(() => {
        el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        el.style.opacity = '1';
        el.style.transform = 'translateY(0)';
      }, i * 80);
    });
  }

  // Connection Management
  async checkConnection() {
    try {
      const response = await fetch(`${API_BASE}/cognitive-graph/status`);
      const data = await response.json();
      this.isConnected = data.connected;
      this.updateConnectionStatus(data.connected);
    } catch (error) {
      console.error('[CognitiveGraph] Connection check failed:', error);
      this.isConnected = false;
      this.updateConnectionStatus(false);
    }
  }

  updateConnectionStatus(connected) {
    const statusEl = document.getElementById('connectionStatus');
    const textEl = document.getElementById('statusText');

    if (!statusEl) return;

    statusEl.className = `cg-status ${connected ? 'connected' : 'disconnected'}`;
    if (textEl) {
      textEl.textContent = connected ? 'Connected' : 'Disconnected';
    }
  }

  async initializeSchema() {
    if (!this.isConnected) return;

    try {
      const response = await fetch(`${API_BASE}/cognitive-graph/initialize`, {
        method: 'POST'
      });
      const data = await response.json();
      console.log('[CognitiveGraph] Schema initialized:', data.initialized);
    } catch (error) {
      console.error('[CognitiveGraph] Schema init failed:', error);
    }
  }

  // Event Listeners
  setupEventListeners() {
    // Tab navigation
    document.querySelectorAll('.cg-nav-btn[data-tab]').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.dataset.tab;
        this.switchTab(tab);
      });
    });

    // Search with debounce
    const searchInput = document.getElementById('searchInput');
    searchInput?.addEventListener('input', (e) => {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        if (e.target.value.trim()) {
          this.performSearch();
        }
      }, 300);
    });

    searchInput?.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        clearTimeout(this.searchTimeout);
        this.performSearch();
      }
    });

    document.getElementById('searchBtn')?.addEventListener('click', () => this.performSearch());

    // Advanced search
    document.getElementById('advancedSearchBtn')?.addEventListener('click', () => this.performAdvancedSearch());
    document.getElementById('clearFiltersBtn')?.addEventListener('click', () => this.clearSearchFilters());

    // Entity extraction
    document.getElementById('extractBtn')?.addEventListener('click', () => this.extractEntities());
  }

  // Tab Management
  switchTab(tab) {
    this.currentTab = tab;

    // Update nav buttons
    document.querySelectorAll('.cg-nav-btn[data-tab]').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.tab === tab);
    });

    // Animate tab transition
    const currentTabEl = document.querySelector('.cg-tab.active');
    const newTabEl = document.getElementById(`tab-${tab}`);

    if (currentTabEl && newTabEl && currentTabEl !== newTabEl) {
      currentTabEl.style.opacity = '0';
      currentTabEl.style.transform = 'translateY(10px)';

      setTimeout(() => {
        document.querySelectorAll('.cg-tab').forEach(t => {
          t.classList.remove('active');
          t.style.opacity = '0';
          t.style.transform = 'translateY(10px)';
        });

        newTabEl.classList.add('active');
        newTabEl.offsetHeight; // Force reflow
        newTabEl.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
        newTabEl.style.opacity = '1';
        newTabEl.style.transform = 'translateY(0)';
      }, 200);
    } else {
      document.querySelectorAll('.cg-tab').forEach(t => t.classList.remove('active'));
      if (newTabEl) {
        newTabEl.classList.add('active');
        newTabEl.style.opacity = '1';
        newTabEl.style.transform = 'translateY(0)';
      }
    }

    // Load tab-specific data
    if (tab === 'companies') {
      this.loadCompaniesData();
    }
    if (tab === 'skills') {
      this.loadSkillsData();
    }
  }

  // Data Loading
  async loadOverviewData() {
    if (!this.isConnected) return;

    try {
      const response = await fetch(`${API_BASE}/cognitive-graph/history/${DEFAULT_USER_ID}?limit=10`);
      const data = await response.json();

      this.displayRecentInterviews(data.interviews);
      this.displayActivityChart(data.interviews);

      // Extract unique companies
      const companies = new Set();
      data.interviews?.forEach(interview => {
        if (interview.companies) {
          interview.companies.forEach(c => companies.add(c));
        }
      });

      this.displayTopCompanies(Array.from(companies).slice(0, 6));
    } catch (error) {
      console.error('[CognitiveGraph] Failed to load overview:', error);
    }
  }

  async loadStats() {
    if (!this.isConnected) return;

    try {
      const response = await fetch(`${API_BASE}/cognitive-graph/stats`);
      const data = await response.json();

      if (data.stats) {
        this.animateCounter('statInterviews', data.stats.interviews || 0);
        this.animateCounter('statQuestions', data.stats.questions || 0);
        this.animateCounter('statCompanies', data.stats.companies || 0);
        this.animateCounter('statTopics', data.stats.topics || 0);
      }
    } catch (error) {
      console.error('[CognitiveGraph] Failed to load stats:', error);
    }
  }

  animateCounter(elementId, targetValue) {
    const el = document.getElementById(elementId);
    if (!el) return;

    const duration = 1000;
    const startValue = 0;
    const startTime = performance.now();

    const update = (currentTime) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const easeProgress = 1 - Math.pow(1 - progress, 3);
      const currentValue = Math.floor(startValue + (targetValue - startValue) * easeProgress);

      el.textContent = currentValue.toLocaleString();

      if (progress < 1) {
        requestAnimationFrame(update);
      }
    };

    requestAnimationFrame(update);
  }

  // Charts
  displayActivityChart(interviews) {
    const container = document.getElementById('interviewChart');
    if (!container) return;

    if (!interviews || interviews.length === 0) {
      container.innerHTML = this.getEmptyChartHtml('📈', 'Interview activity will appear here');
      return;
    }

    // Group by month
    const byMonth = {};
    interviews.forEach(interview => {
      const date = new Date(interview.timestamp);
      const key = `${date.toLocaleString('default', { month: 'short' })} ${date.getFullYear().toString().substr(2)}`;
      byMonth[key] = (byMonth[key] || 0) + 1;
    });

    const months = Object.keys(byMonth).slice(-6);
    const values = months.map(m => byMonth[m]);
    const maxCount = Math.max(...values, 1);

    let html = '<div class="cg-bar-chart">';
    months.forEach((month, idx) => {
      const count = byMonth[month];
      const height = (count / maxCount) * 100;
      html += `
        <div class="cg-bar" style="height: ${height}%; animation-delay: ${idx * 100}ms">
          <span class="cg-bar-value">${count}</span>
          <span class="cg-bar-label">${month}</span>
        </div>
      `;
    });
    html += '</div>';

    container.innerHTML = html;
  }

  displayCategoryChart(categories) {
    const container = document.getElementById('categoryChart');
    if (!container) return;

    if (!categories || categories.length === 0) {
      container.innerHTML = this.getEmptyChartHtml('🥧', 'Category breakdown will appear here');
      return;
    }

    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ef4444', '#ec4899'];
    const total = categories.reduce((sum, cat) => sum + cat.count, 0);

    let currentAngle = 0;
    let gradientParts = [];

    categories.forEach((cat, idx) => {
      const percentage = (cat.count / total) * 100;
      const angle = (cat.count / total) * 360;
      const color = colors[idx % colors.length];
      gradientParts.push(`${color} ${currentAngle}deg ${currentAngle + angle}deg`);
      currentAngle += angle;
    });

    container.innerHTML = `
      <div class="cg-pie-chart">
        <div class="cg-pie" style="background: conic-gradient(${gradientParts.join(', ')})">
          <div class="cg-pie-center">
            <div class="cg-pie-total">${total}</div>
            <div class="cg-pie-label">Total</div>
          </div>
        </div>
        <div class="cg-pie-legend">
          ${categories.map((cat, idx) => `
            <div class="cg-legend-item">
              <div class="cg-legend-color" style="background: ${colors[idx % colors.length]}"></div>
              <span>${cat.name}</span>
              <span>${cat.count}</span>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  getEmptyChartHtml(icon, text) {
    return `
      <div class="cg-empty">
        <div class="cg-empty-icon">${icon}</div>
        <p>${text}</p>
      </div>
    `;
  }

  // Recent Interviews
  displayRecentInterviews(interviews) {
    const container = document.getElementById('recentInterviews');
    if (!container) return;

    if (!interviews || interviews.length === 0) {
      container.innerHTML = `
        <div class="cg-empty">
          <div class="cg-empty-icon">📋</div>
          <div class="cg-empty-title">No interviews yet</div>
          <div class="cg-empty-subtitle">Start recording to build your graph</div>
        </div>
      `;
      return;
    }

    container.innerHTML = interviews.map((interview, idx) => `
      <div class="cg-interview-card cg-animate-in" style="animation-delay: ${idx * 50}ms" data-id="${interview.id}">
        <div class="cg-interview-header">
          <span class="cg-interview-title">${this.escapeHtml(interview.title)}</span>
          <span class="cg-interview-date">${this.formatDate(interview.timestamp)}</span>
        </div>
        <div class="cg-interview-meta">
          <span class="cg-meta-badge">
            <span>❓</span>
            ${interview.question_count} questions
          </span>
          ${interview.companies?.map(c => `
            <span class="cg-meta-badge company">
              <span>🏢</span>
              ${this.escapeHtml(c)}
            </span>
          `).join('') || ''}
        </div>
      </div>
    `).join('');

    // Add click handlers
    container.querySelectorAll('.cg-interview-card').forEach(card => {
      card.addEventListener('click', () => this.viewInterview(card.dataset.id));
    });
  }

  // Top Companies
  displayTopCompanies(companies) {
    const container = document.getElementById('topCompanies');
    if (!container) return;

    if (companies.length === 0) {
      container.innerHTML = `
        <div class="cg-empty">
          <div class="cg-empty-icon">🏢</div>
          <div class="cg-empty-title">No company data yet</div>
        </div>
      `;
      return;
    }

    container.innerHTML = companies.map((company, idx) => `
      <div class="cg-company-card cg-animate-in" style="animation-delay: ${idx * 80}ms" data-company="${this.escapeHtml(company)}">
        <div class="cg-company-name">${this.escapeHtml(company)}</div>
        <div class="cg-company-count">-</div>
        <div class="cg-company-label">questions</div>
      </div>
    `).join('');

    // Add click handlers
    container.querySelectorAll('.cg-company-card').forEach(card => {
      card.addEventListener('click', () => this.viewCompany(card.dataset.company));
    });
  }

  // Search
  async performSearch() {
    const query = document.getElementById('searchInput')?.value.trim();
    if (!query) return;

    const container = document.getElementById('searchResults');
    container.innerHTML = `
      <div class="cg-loading">
        <div class="cg-spinner"></div>
        <p>Searching your knowledge graph...</p>
      </div>
    `;

    try {
      const response = await fetch(`${API_BASE}/cognitive-graph/search?q=${encodeURIComponent(query)}&limit=20`);
      const data = await response.json();
      this.displaySearchResults(data.results, query);
    } catch (error) {
      console.error('[CognitiveGraph] Search failed:', error);
      container.innerHTML = `
        <div class="cg-empty">
          <div class="cg-empty-icon">⚠️</div>
          <div class="cg-empty-title">Search failed</div>
          <div class="cg-empty-subtitle">Please try again</div>
        </div>
      `;
    }
  }

  displaySearchResults(results, query) {
    const container = document.getElementById('searchResults');
    if (!container) return;

    if (!results || results.length === 0) {
      container.innerHTML = `
        <div class="cg-empty">
          <div class="cg-empty-icon">🔍</div>
          <div class="cg-empty-title">No results found</div>
          <div class="cg-empty-subtitle">Try different keywords or check your spelling</div>
        </div>
      `;
      return;
    }

    container.innerHTML = results.map((result, idx) => `
      <div class="cg-result-item cg-animate-in" style="animation-delay: ${idx * 50}ms">
        <div class="cg-result-question">${this.highlightText(this.escapeHtml(result.question), query)}</div>
        <div class="cg-result-answer">${this.highlightText(this.escapeHtml(this.truncateText(result.answer, 180)), query)}</div>
        <div class="cg-result-meta">
          ${result.category ? `<span class="cg-result-tag category-${result.category}">${result.category.replace('_', ' ')}</span>` : ''}
          ${result.difficulty ? `<span class="cg-result-tag difficulty-${result.difficulty}">${result.difficulty}</span>` : ''}
          ${result.company ? `<span class="cg-result-tag">🏢 ${this.escapeHtml(result.company)}</span>` : ''}
          ${result.relevance ? `<span class="cg-result-tag relevance">⭐ ${(result.relevance * 10).toFixed(1)}</span>` : ''}
        </div>
      </div>
    `).join('');
  }

  // Advanced Search
  async performAdvancedSearch() {
    const query = document.getElementById('searchInput')?.value.trim() || '';
    const company = document.getElementById('filterCompany')?.value;
    const category = document.getElementById('filterCategory')?.value;
    const difficulty = document.getElementById('filterDifficulty')?.value;

    const params = new URLSearchParams();
    if (query) params.append('query', query);
    if (company) params.append('company', company);
    if (category) params.append('category', category);
    if (difficulty) params.append('difficulty', difficulty);
    params.append('limit', '50');

    const container = document.getElementById('searchResults');
    container.innerHTML = `
      <div class="cg-loading">
        <div class="cg-spinner"></div>
        <p>Searching with filters...</p>
      </div>
    `;

    try {
      const response = await fetch(`${API_BASE}/cognitive-graph/search/advanced?${params}`);
      const data = await response.json();

      // Show search stats
      const statsEl = document.getElementById('searchStats');
      const statsText = document.getElementById('searchStatsText');
      if (statsEl && statsText && data.count > 0) {
        statsEl.classList.add('visible');
        statsText.innerHTML = `Found <strong>${data.count}</strong> results`;
      } else if (statsEl) {
        statsEl.classList.remove('visible');
      }

      this.displaySearchResults(data.results, query);
    } catch (error) {
      console.error('[CognitiveGraph] Advanced search failed:', error);
      container.innerHTML = `
        <div class="cg-empty">
          <div class="cg-empty-icon">⚠️</div>
          <div class="cg-empty-title">Search failed</div>
          <div class="cg-empty-subtitle">Please try again</div>
        </div>
      `;
    }
  }

  clearSearchFilters() {
    const searchInput = document.getElementById('searchInput');
    const filterCompany = document.getElementById('filterCompany');
    const filterCategory = document.getElementById('filterCategory');
    const filterDifficulty = document.getElementById('filterDifficulty');
    const searchStats = document.getElementById('searchStats');

    if (searchInput) searchInput.value = '';
    if (filterCompany) filterCompany.value = '';
    if (filterCategory) filterCategory.value = '';
    if (filterDifficulty) filterDifficulty.value = '';
    if (searchStats) searchStats.classList.remove('visible');

    const container = document.getElementById('searchResults');
    if (container) {
      container.innerHTML = `
        <div class="cg-empty">
          <div class="cg-empty-icon">🔍</div>
          <div class="cg-empty-title">Search your interview history</div>
          <div class="cg-empty-subtitle">Enter keywords to find relevant Q&A</div>
        </div>
      `;
    }
  }

  // Companies
  async loadCompaniesData() {
    try {
      const response = await fetch(`${API_BASE}/predict/companies`);
      const data = await response.json();

      // Populate filter dropdown
      const select = document.getElementById('filterCompany');
      if (select && data.companies) {
        select.innerHTML = '<option value="">All Companies</option>';
        data.companies.forEach(company => {
          select.innerHTML += `<option value="${this.escapeHtml(company)}">${this.escapeHtml(company)}</option>`;
        });
      }

      // Populate company insights container
      const insightsContainer = document.getElementById('companyInsights');
      if (insightsContainer && data.companies) {
        insightsContainer.innerHTML = `
          <div class="cg-company-grid">
            ${data.companies.map((company, idx) => `
              <div class="cg-company-card cg-animate-in" style="animation-delay: ${idx * 30}ms" data-company="${this.escapeHtml(company)}">
                <div class="cg-company-name">${this.escapeHtml(company)}</div>
                <div class="cg-company-label">Click to view insights</div>
              </div>
            `).join('')}
          </div>
        `;

        // Add click handlers
        insightsContainer.querySelectorAll('.cg-company-card').forEach(card => {
          card.addEventListener('click', () => this.viewCompany(card.dataset.company));
        });
      }
    } catch (error) {
      console.error('[CognitiveGraph] Failed to load companies:', error);
    }
  }

  async viewCompany(companyName) {
    try {
      const response = await fetch(`${API_BASE}/cognitive-graph/company/${encodeURIComponent(companyName)}`);
      const data = await response.json();

      const container = document.getElementById('companyInsights');
      const insights = data.insights;

      if (!insights || Object.keys(insights).length === 0) {
        container.innerHTML = `
          <div class="cg-empty">
            <div class="cg-empty-icon">🏢</div>
            <div class="cg-empty-title">No data for ${this.escapeHtml(companyName)}</div>
            <div class="cg-empty-subtitle">Conduct interviews to build company insights</div>
          </div>
        `;
        return;
      }

      container.innerHTML = `
        <div class="cg-company-detail">
          <div class="cg-company-detail-header">
            <div class="cg-company-avatar">${companyName.charAt(0).toUpperCase()}</div>
            <div class="cg-company-detail-info">
              <h3>${this.escapeHtml(companyName)}</h3>
              <span>Interview Insights</span>
            </div>
          </div>
          <div class="cg-company-stats-row">
            <div class="cg-company-stat">
              <div class="cg-company-stat-value">${insights.total_questions || 0}</div>
              <div class="cg-company-stat-label">Questions</div>
            </div>
            <div class="cg-company-stat">
              <div class="cg-company-stat-value">${insights.avg_confidence ? insights.avg_confidence.toFixed(1) : '-'}</div>
              <div class="cg-company-stat-label">Avg Confidence</div>
            </div>
            <div class="cg-company-stat">
              <div class="cg-company-stat-value">${insights.categories?.length || 0}</div>
              <div class="cg-company-stat-label">Categories</div>
            </div>
          </div>
          ${insights.common_topics?.length ? `
            <div class="cg-company-topics">
              <strong>Common Topics</strong>
              <div class="cg-topic-tags">
                ${insights.common_topics.map(t => `<span class="cg-topic-tag">${this.escapeHtml(t)}</span>`).join('')}
              </div>
            </div>
          ` : ''}
          <button class="cg-search-btn secondary" id="backToCompanies" style="margin-top: var(--space-4)">
            ← Back to Companies
          </button>
        </div>
      `;

      document.getElementById('backToCompanies')?.addEventListener('click', () => this.loadCompaniesData());
    } catch (error) {
      console.error('[CognitiveGraph] Failed to load company:', error);
    }
  }

  // Skills
  async loadSkillsData() {
    const container = document.getElementById('skillsList');
    if (!container) return;

    try {
      const resp = await fetch(`${API_BASE}/cognitive-graph/stats`);
      if (resp.ok) {
        const data = await resp.json();
        const skills = data.skills || [];

        if (skills.length > 0) {
          container.innerHTML = skills.map((skill, idx) => `
            <div class="cg-skill-item cg-animate-in" style="animation-delay: ${idx * 80}ms">
              <span class="cg-skill-name">${this.escapeHtml(skill.name)}</span>
              <div class="cg-skill-bar">
                <div class="cg-skill-progress" style="width: ${skill.level || skill.count * 5}%"></div>
              </div>
              <span class="cg-skill-count">${skill.count}</span>
            </div>
          `).join('');
          return;
        }
      }
    } catch (e) {
      console.warn('[CognitiveGraph] Could not load skills from API:', e);
    }

    // Fallback if API is unavailable
    container.innerHTML = '<div class="cg-empty-state">Connect Neo4j to see skill data</div>';
  }

  // Entity Extraction
  async extractEntities() {
    const text = document.getElementById('extractText')?.value.trim();
    if (!text) {
      this.showToast('Please enter text to extract entities', 'warning');
      return;
    }

    const btn = document.getElementById('extractBtn');
    const originalText = btn.textContent;
    btn.innerHTML = '<span class="cg-spinner" style="width: 16px; height: 16px; border-width: 2px; margin: 0 8px 0 0; vertical-align: middle;"></span> Extracting...';
    btn.disabled = true;

    try {
      const response = await fetch(`${API_BASE}/extract-entities`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });

      const data = await response.json();
      const resultDiv = document.getElementById('extractResult');

      resultDiv.innerHTML = `
        <div class="cg-extract-result">
          <h4 style="margin-bottom: var(--space-4); color: var(--text-bright);">Extracted Entities</h4>
          ${data.companies?.length ? `
            <div class="cg-entity-section">
              <span class="cg-entity-label">🏢 Companies</span>
              <div class="cg-entity-tags">
                ${data.companies.map(c => `<span class="cg-entity-tag cg-tag-company">${this.escapeHtml(c)}</span>`).join('')}
              </div>
            </div>
          ` : ''}
          ${data.skills?.length ? `
            <div class="cg-entity-section">
              <span class="cg-entity-label">💡 Skills</span>
              <div class="cg-entity-tags">
                ${data.skills.map(s => `<span class="cg-entity-tag cg-tag-skill">${this.escapeHtml(s)}</span>`).join('')}
              </div>
            </div>
          ` : ''}
          ${data.topics?.length ? `
            <div class="cg-entity-section">
              <span class="cg-entity-label">🏷️ Topics</span>
              <div class="cg-entity-tags">
                ${data.topics.map(t => `<span class="cg-entity-tag cg-tag-topic">${this.escapeHtml(t)}</span>`).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      `;
    } catch (error) {
      console.error('[CognitiveGraph] Entity extraction failed:', error);
      this.showToast('Extraction failed. Please try again.', 'error');
    } finally {
      btn.textContent = originalText;
      btn.disabled = false;
    }
  }

  // Utilities
  escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  truncateText(text, maxLength) {
    if (!text || text.length <= maxLength) return text;
    return text.substr(0, maxLength) + '...';
  }

  formatDate(timestamp) {
    if (!timestamp) return 'Unknown';
    const date = new Date(timestamp);
    const now = new Date();
    const diffDays = Math.floor((now - date) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return `${diffDays} days ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  highlightText(text, query) {
    if (!query) return text;
    const regex = new RegExp(`(${this.escapeRegex(query)})`, 'gi');
    return text.replace(regex, '<mark style="background: var(--primary-light); color: var(--primary); border-radius: 2px; padding: 0 2px;">$1</mark>');
  }

  escapeRegex(string) {
    return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `cg-toast cg-toast-${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);

    setTimeout(() => toast.classList.add('show'), 10);

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  viewInterview(id) {
    console.log('[CognitiveGraph] View interview:', id);
    this.showToast('Interview detail view coming soon', 'info');
  }
}
