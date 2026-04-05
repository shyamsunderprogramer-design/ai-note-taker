/**
 * Cognitive Graph - Enhanced Frontend JavaScript
 * Modern UI with smooth animations and improved UX
 */

const API_BASE = 'http://127.0.0.1:8000';
const DEFAULT_USER_ID = 'default';

// State
let isConnected = false;
let currentTab = 'overview';
let chartInstances = {};

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await checkConnection();
  await initializeSchema();
  setupEventListeners();
  loadOverviewData();
  animateEntrance();
});

// Animate entrance
function animateEntrance() {
  const elements = document.querySelectorAll('.animate-in');
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

// Check Neo4j connection
async function checkConnection() {
  try {
    const response = await fetch(`${API_BASE}/cognitive-graph/status`);
    const data = await response.json();
    isConnected = data.connected;
    updateConnectionStatus(isConnected);
  } catch (error) {
    console.error('[CognitiveGraph] Connection check failed:', error);
    isConnected = false;
    updateConnectionStatus(false);
  }
}

function updateConnectionStatus(connected) {
  const statusEl = document.getElementById('connectionStatus');
  const dotEl = statusEl?.querySelector('.cg-status-dot');
  const textEl = document.getElementById('statusText');

  if (!statusEl) return;

  if (connected) {
    statusEl.className = 'cg-status connected';
    if (dotEl) dotEl.style.animation = 'pulse-dot 2s infinite';
    if (textEl) textEl.textContent = 'Connected';
  } else {
    statusEl.className = 'cg-status disconnected';
    if (dotEl) dotEl.style.animation = 'none';
    if (textEl) textEl.textContent = 'Disconnected';
  }
}

// Initialize schema
async function initializeSchema() {
  if (!isConnected) return;

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

// Setup event listeners
function setupEventListeners() {
  // Tab navigation with smooth transitions
  document.querySelectorAll('.cg-nav-btn[data-tab]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const tab = e.currentTarget.dataset.tab;
      switchTab(tab);
    });
  });

  // Search with debounce
  const searchInput = document.getElementById('searchInput');
  let searchTimeout;
  searchInput?.addEventListener('input', (e) => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      if (e.target.value.trim()) {
        performSearch();
      }
    }, 300);
  });

  searchInput?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      clearTimeout(searchTimeout);
      performSearch();
    }
  });

  document.getElementById('searchBtn')?.addEventListener('click', performSearch);

  // Advanced search
  document.getElementById('advancedSearchBtn')?.addEventListener('click', performAdvancedSearch);
  document.getElementById('clearFiltersBtn')?.addEventListener('click', clearSearchFilters);

  // Entity extraction
  document.getElementById('extractBtn')?.addEventListener('click', extractEntities);

  // Load stats
  loadStats();
}

// Switch tabs with animation
function switchTab(tab) {
  currentTab = tab;

  // Update nav buttons
  document.querySelectorAll('.cg-nav-btn[data-tab]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tab);
  });

  // Animate tab transition
  const currentTabEl = document.querySelector('.cg-tab:not([style*="display: none"])');
  const newTabEl = document.getElementById(`tab-${tab}`);

  if (currentTabEl && newTabEl && currentTabEl !== newTabEl) {
    currentTabEl.style.opacity = '0';
    currentTabEl.style.transform = 'translateY(10px)';

    setTimeout(() => {
      document.querySelectorAll('.cg-tab').forEach(t => {
        t.style.display = 'none';
        t.style.opacity = '0';
        t.style.transform = 'translateY(10px)';
      });

      newTabEl.style.display = 'block';
      // Force reflow
      newTabEl.offsetHeight;
      newTabEl.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      newTabEl.style.opacity = '1';
      newTabEl.style.transform = 'translateY(0)';
    }, 200);
  } else {
    document.querySelectorAll('.cg-tab').forEach(t => t.style.display = 'none');
    if (newTabEl) {
      newTabEl.style.display = 'block';
      newTabEl.style.opacity = '1';
      newTabEl.style.transform = 'translateY(0)';
    }
  }

  // Load tab-specific data
  if (tab === 'companies') {
    loadCompaniesData();
    document.getElementById('companiesGrid')?.classList.add('animate-grid');
  }
  if (tab === 'skills') loadSkillsData();
}

// Load overview data
async function loadOverviewData() {
  if (!isConnected) return;

  try {
    const response = await fetch(`${API_BASE}/cognitive-graph/history/${DEFAULT_USER_ID}?limit=10`);
    const data = await response.json();

    displayRecentInterviews(data.interviews);
    displayActivityChart(data.interviews);

    // Extract unique companies
    const companies = new Set();
    data.interviews?.forEach(interview => {
      if (interview.companies) {
        interview.companies.forEach(c => companies.add(c));
      }
    });

    displayTopCompanies(Array.from(companies).slice(0, 6));
  } catch (error) {
    console.error('[CognitiveGraph] Failed to load overview:', error);
  }
}

async function loadStats() {
  if (!isConnected) return;

  try {
    const response = await fetch(`${API_BASE}/cognitive-graph/stats`);
    const data = await response.json();

    if (data.stats) {
      animateCounter('statInterviews', data.stats.interviews || 0);
      animateCounter('statQuestions', data.stats.questions || 0);
      animateCounter('statCompanies', data.stats.companies || 0);
      animateCounter('statTopics', data.stats.topics || 0);
    }
  } catch (error) {
    console.error('[CognitiveGraph] Failed to load stats:', error);
  }
}

// Animate counter
function animateCounter(elementId, targetValue) {
  const el = document.getElementById(elementId);
  if (!el) return;

  const duration = 1000;
  const startValue = 0;
  const startTime = performance.now();

  function update(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const easeProgress = 1 - Math.pow(1 - progress, 3); // easeOutCubic
    const currentValue = Math.floor(startValue + (targetValue - startValue) * easeProgress);

    el.textContent = currentValue.toLocaleString();

    if (progress < 1) {
      requestAnimationFrame(update);
    }
  }

  requestAnimationFrame(update);
}

// Display activity chart with enhanced visuals
function displayActivityChart(interviews) {
  const container = document.getElementById('interviewChart');
  if (!interviews || interviews.length === 0) {
    container.innerHTML = `
      <div class="chart-empty">
        <div class="chart-empty-icon">📈</div>
        <p>Interview activity will appear here</p>
      </div>
    `;
    return;
  }

  // Group by month
  const byMonth = {};
  interviews.forEach(interview => {
    const date = new Date(interview.timestamp);
    const key = `${date.toLocaleString('default', { month: 'short' })} ${date.getFullYear().toString().substr(2)}`;
    byMonth[key] = (byMonth[key] || 0) + 1;
  });

  // Get last 6 months
  const months = Object.keys(byMonth).slice(-6);
  const values = months.map(m => byMonth[m]);
  const maxCount = Math.max(...values, 1);

  let html = '<div class="chart-bars">';
  months.forEach((month, idx) => {
    const count = byMonth[month];
    const height = (count / maxCount) * 100;
    html += `
      <div class="chart-bar-wrapper" style="animation-delay: ${idx * 100}ms">
        <div class="chart-bar" style="height: ${height}%" data-value="${count}">
          <div class="chart-bar-glow"></div>
        </div>
        <div class="chart-bar-label">${month}</div>
      </div>
    `;
  });
  html += '</div>';

  container.innerHTML = html;
}

// Display category chart
function displayCategoryChart(categories) {
  const container = document.getElementById('categoryChart');
  if (!categories || categories.length === 0) {
    container.innerHTML = `
      <div class="chart-empty">
        <div class="chart-empty-icon">🥧</div>
        <p>Category breakdown will appear here</p>
      </div>
    `;
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
    <div class="pie-chart-container">
      <div class="pie-chart" style="background: conic-gradient(${gradientParts.join(', ')})">
        <div class="pie-chart-center">
          <div class="pie-chart-total">${total}</div>
          <div class="pie-chart-label">Total</div>
        </div>
      </div>
      <div class="pie-legend">
        ${categories.map((cat, idx) => `
          <div class="legend-item">
            <div class="legend-color" style="background: ${colors[idx % colors.length]}"></div>
            <span class="legend-name">${cat.name}</span>
            <span class="legend-value">${cat.count}</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

function displayRecentInterviews(interviews) {
  const container = document.getElementById('recentInterviews');
  if (!container) return;

  if (!interviews || interviews.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">📋</div>
        <p>No interviews yet</p>
        <span>Start recording to build your graph</span>
      </div>
    `;
    return;
  }

  container.innerHTML = interviews.map((interview, idx) => `
    <div class="interview-card" style="animation-delay: ${idx * 50}ms" onclick="viewInterview('${interview.id}')">
      <div class="interview-card-header">
        <h4 class="interview-title">${escapeHtml(interview.title)}</h4>
        <span class="interview-date">${formatDate(interview.timestamp)}</span>
      </div>
      <div class="interview-meta">
        <span class="meta-badge">
          <span class="meta-icon">❓</span>
          ${interview.question_count} questions
        </span>
        ${interview.companies?.map(c => `
          <span class="meta-badge company">
            <span class="meta-icon">🏢</span>
            ${escapeHtml(c)}
          </span>
        `).join('') || ''}
      </div>
    </div>
  `).join('');
}

function displayTopCompanies(companies) {
  const container = document.getElementById('topCompanies');
  if (!container) return;

  if (companies.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🏢</div>
        <p>No company data yet</p>
      </div>
    `;
    return;
  }

  const gradients = [
    'linear-gradient(135deg, #3b82f6, #8b5cf6)',
    'linear-gradient(135deg, #10b981, #22c55e)',
    'linear-gradient(135deg, #f59e0b, #fbbf24)',
    'linear-gradient(135deg, #ef4444, #f87171)',
    'linear-gradient(135deg, #8b5cf6, #a78bfa)',
    'linear-gradient(135deg, #06b6d4, #22d3ee)'
  ];

  container.innerHTML = companies.map((company, idx) => `
    <div class="company-card-compact" style="animation-delay: ${idx * 80}ms" onclick="viewCompany('${escapeHtml(company)}')">
      <div class="company-icon" style="background: ${gradients[idx % gradients.length]}">
        ${company.charAt(0).toUpperCase()}
      </div>
      <div class="company-name-compact">${escapeHtml(company)}</div>
    </div>
  `).join('');
}

// Search functionality
async function performSearch() {
  const query = document.getElementById('searchInput').value.trim();
  if (!query) return;

  const container = document.getElementById('searchResults');
  container.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <span>Searching your knowledge graph...</span>
    </div>
  `;

  try {
    const response = await fetch(`${API_BASE}/cognitive-graph/search?q=${encodeURIComponent(query)}&limit=20`);
    const data = await response.json();

    displaySearchResults(data.results, query);
  } catch (error) {
    console.error('[CognitiveGraph] Search failed:', error);
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <p>Search failed</p>
        <span>Please try again</span>
      </div>
    `;
  }
}

function displaySearchResults(results, query) {
  const container = document.getElementById('searchResults');

  if (!results || results.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🔍</div>
        <p>No results found</p>
        <span>Try different keywords or check your spelling</span>
      </div>
    `;
    return;
  }

  container.innerHTML = results.map((result, idx) => `
    <div class="search-result-card" style="animation-delay: ${idx * 50}ms">
      <div class="result-question">${highlightText(escapeHtml(result.question), query)}</div>
      <div class="result-answer">${highlightText(escapeHtml(truncateText(result.answer, 180)), query)}</div>
      <div class="result-meta">
        ${result.category ? `<span class="result-tag category-${result.category}">${result.category.replace('_', ' ')}</span>` : ''}
        ${result.difficulty ? `<span class="result-tag difficulty-${result.difficulty}">${result.difficulty}</span>` : ''}
        ${result.company ? `<span class="result-tag">🏢 ${escapeHtml(result.company)}</span>` : ''}
        ${result.relevance ? `<span class="result-tag relevance">⭐ ${(result.relevance * 10).toFixed(1)}</span>` : ''}
      </div>
    </div>
  `).join('');
}

function highlightText(text, query) {
  if (!query) return text;
  const regex = new RegExp(`(${escapeRegex(query)})`, 'gi');
  return text.replace(regex, '<mark>$1</mark>');
}

function escapeRegex(string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Advanced search
async function performAdvancedSearch() {
  const query = document.getElementById('searchInput').value.trim();
  const company = document.getElementById('filterCompany').value;
  const category = document.getElementById('filterCategory').value;
  const difficulty = document.getElementById('filterDifficulty').value;

  const params = new URLSearchParams();
  if (query) params.append('query', query);
  if (company) params.append('company', company);
  if (category) params.append('category', category);
  if (difficulty) params.append('difficulty', difficulty);
  params.append('limit', '50');

  const container = document.getElementById('searchResults');
  container.innerHTML = `
    <div class="loading-state">
      <div class="spinner"></div>
      <span>Searching with filters...</span>
    </div>
  `;

  try {
    const response = await fetch(`${API_BASE}/cognitive-graph/search/advanced?${params}`);
    const data = await response.json();

    // Show search stats
    const statsEl = document.getElementById('searchStats');
    const statsText = document.getElementById('searchStatsText');
    if (data.count > 0) {
      statsEl.style.display = 'flex';
      let filters = [];
      if (company) filters.push(`Company: ${company}`);
      if (category) filters.push(`Category: ${category}`);
      if (difficulty) filters.push(`Difficulty: ${difficulty}`);
      statsText.innerHTML = `Found <strong>${data.count}</strong> results${filters.length > 0 ? ' with filters' : ''}`;
    } else {
      statsEl.style.display = 'none';
    }

    displaySearchResults(data.results, query);
  } catch (error) {
    console.error('[CognitiveGraph] Advanced search failed:', error);
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">⚠️</div>
        <p>Search failed</p>
        <span>Please try again</span>
      </div>
    `;
  }
}

function clearSearchFilters() {
  document.getElementById('searchInput').value = '';
  document.getElementById('filterCompany').value = '';
  document.getElementById('filterCategory').value = '';
  document.getElementById('filterDifficulty').value = '';
  document.getElementById('searchStats').style.display = 'none';

  document.getElementById('searchResults').innerHTML = `
    <div class="empty-state">
      <div class="empty-state-icon">🔍</div>
      <p>Search your interview history</p>
      <span>Enter keywords to find relevant Q&amp;A</span>
    </div>
  `;
}

// Companies data
async function loadCompaniesData() {
  try {
    const response = await fetch(`${API_BASE}/predict/companies`);
    const data = await response.json();

    // Populate filter dropdown
    const select = document.getElementById('filterCompany');
    if (select && data.companies) {
      select.innerHTML = '<option value="">All Companies</option>';
      data.companies.forEach(company => {
        select.innerHTML += `<option value="${escapeHtml(company)}">${escapeHtml(company)}</option>`;
      });
    }

    // Populate companies grid
    const grid = document.getElementById('companiesGrid');
    if (grid && data.companies) {
      const gradients = [
        'linear-gradient(135deg, #3b82f6, #2563eb)',
        'linear-gradient(135deg, #10b981, #059669)',
        'linear-gradient(135deg, #f59e0b, #d97706)',
        'linear-gradient(135deg, #ef4444, #dc2626)',
        'linear-gradient(135deg, #8b5cf6, #7c3aed)',
        'linear-gradient(135deg, #06b6d4, #0891b2)',
        'linear-gradient(135deg, #ec4899, #db2777)',
        'linear-gradient(135deg, #84cc16, #65a30d)'
      ];

      grid.innerHTML = data.companies.map((company, idx) => `
        <div class="company-card-large" style="animation-delay: ${idx * 30}ms" onclick="viewCompany('${escapeHtml(company)}')">
          <div class="company-card-gradient" style="background: ${gradients[idx % gradients.length]}"></div>
          <div class="company-card-content">
            <div class="company-avatar-large">${company.charAt(0).toUpperCase()}</div>
            <div class="company-info-large">
              <div class="company-name-large">${escapeHtml(company)}</div>
              <div class="company-label">Click to view insights</div>
            </div>
            <div class="company-arrow">→</div>
          </div>
        </div>
      `).join('');
    }
  } catch (error) {
    console.error('[CognitiveGraph] Failed to load companies:', error);
  }
}

async function viewCompany(companyName) {
  try {
    const response = await fetch(`${API_BASE}/cognitive-graph/company/${encodeURIComponent(companyName)}`);
    const data = await response.json();

    const container = document.getElementById('companyInsights');
    const insights = data.insights;

    if (!insights || Object.keys(insights).length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon">🏢</div>
          <p>No data for ${escapeHtml(companyName)}</p>
          <span>Conduct interviews to build company insights</span>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="company-detail-card">
        <div class="company-detail-header">
          <div class="company-detail-avatar">${companyName.charAt(0).toUpperCase()}</div>
          <div class="company-detail-info">
            <h3>${escapeHtml(companyName)}</h3>
            <span>Interview Insights</span>
          </div>
        </div>
        <div class="company-stats-row">
          <div class="company-stat">
            <div class="company-stat-value">${insights.total_questions || 0}</div>
            <div class="company-stat-label">Questions</div>
          </div>
          <div class="company-stat">
            <div class="company-stat-value">${insights.avg_confidence ? insights.avg_confidence.toFixed(1) : '-'}</div>
            <div class="company-stat-label">Avg Confidence</div>
          </div>
          <div class="company-stat">
            <div class="company-stat-value">${insights.categories?.length || 0}</div>
            <div class="company-stat-label">Categories</div>
          </div>
        </div>
        ${insights.common_topics?.length ? `
          <div class="company-topics">
            <strong>Common Topics</strong>
            <div class="topic-tags">
              ${insights.common_topics.map(t => `<span class="topic-tag">${escapeHtml(t)}</span>`).join('')}
            </div>
          </div>
        ` : ''}
      </div>
    `;
  } catch (error) {
    console.error('[CognitiveGraph] Failed to load company:', error);
  }
}

// Skills data
async function loadSkillsData() {
  const container = document.getElementById('skillsList');

  // Mock skills data for now
  const skills = [
    { name: 'JavaScript', count: 12, level: 85 },
    { name: 'System Design', count: 8, level: 70 },
    { name: 'React', count: 10, level: 80 },
    { name: 'Algorithms', count: 15, level: 75 },
    { name: 'Behavioral', count: 6, level: 90 }
  ];

  container.innerHTML = skills.map((skill, idx) => `
    <div class="skill-row" style="animation-delay: ${idx * 80}ms">
      <div class="skill-info">
        <span class="skill-name">${skill.name}</span>
        <span class="skill-count">${skill.count} questions</span>
      </div>
      <div class="skill-bar-container">
        <div class="skill-bar-bg">
          <div class="skill-bar-fill" style="width: ${skill.level}%; animation-delay: ${idx * 100 + 200}ms"></div>
        </div>
      </div>
      <div class="skill-level">${skill.level}%</div>
    </div>
  `).join('');
}

// Entity extraction
async function extractEntities() {
  const text = document.getElementById('extractText').value.trim();
  if (!text) {
    showToast('Please enter text to extract entities', 'warning');
    return;
  }

  const btn = document.getElementById('extractBtn');
  const originalText = btn.innerHTML;
  btn.innerHTML = '<span class="spinner-small"></span> Extracting...';
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
      <div class="extract-result">
        <h4>Extracted Entities</h4>
        <div class="entity-sections">
          ${data.companies?.length ? `
            <div class="entity-section">
              <span class="entity-label">🏢 Companies</span>
              <div class="entity-tags">
                ${data.companies.map(c => `<span class="entity-tag company">${escapeHtml(c)}</span>`).join('')}
              </div>
            </div>
          ` : ''}
          ${data.skills?.length ? `
            <div class="entity-section">
              <span class="entity-label">💡 Skills</span>
              <div class="entity-tags">
                ${data.skills.map(s => `<span class="entity-tag skill">${escapeHtml(s)}</span>`).join('')}
              </div>
            </div>
          ` : ''}
          ${data.topics?.length ? `
            <div class="entity-section">
              <span class="entity-label">🏷️ Topics</span>
              <div class="entity-tags">
                ${data.topics.map(t => `<span class="entity-tag topic">${escapeHtml(t)}</span>`).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      </div>
    `;
  } catch (error) {
    console.error('[CognitiveGraph] Entity extraction failed:', error);
    showToast('Extraction failed. Please try again.', 'error');
  } finally {
    btn.innerHTML = originalText;
    btn.disabled = false;
  }
}

// Utility functions
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

function truncateText(text, maxLength) {
  if (!text || text.length <= maxLength) return text;
  return text.substr(0, maxLength) + '...';
}

function formatDate(timestamp) {
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

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('show');
  }, 10);

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// Expose functions to window
window.switchTab = switchTab;
window.viewInterview = (id) => console.log('View interview:', id);
window.viewCompany = viewCompany;
window.viewSkill = (name) => console.log('View skill:', name);
