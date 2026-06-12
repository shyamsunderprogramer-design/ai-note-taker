/**
 * Study Plan - Personalized Learning Path Generator
 * Handles setup form, API calls, and plan rendering
 * Focus Areas organized as cards with sequential unlock
 */

var API_BASE = typeof API_BASE !== 'undefined' ? API_BASE : 'http://127.0.0.1:8000';
const DEFAULT_USER_ID = 'default';

class StudyPlanManager {
  constructor() {
    this.planData = null;
    this.completedTasks = {};  // { taskId: true } — persisted in localStorage
    this.focusAreas = [];     // Grouped tasks by focus area
    this.state = 'setup'; // 'setup' | 'loading' | 'content' | 'empty'
  }

  // === Completion Persistence ===

  /** Get a localStorage key scoped to the plan's role/company/days */
  _storageKey() {
    if (!this.planData) return 'studyplan_completed_default';
    const role = (this.planData.target_role || 'default').replace(/\s+/g, '_').toLowerCase();
    const company = (this.planData.target_company || '').replace(/\s+/g, '_').toLowerCase();
    const days = this.planData.duration_days || 30;
    return `studyplan_completed_${role}${company ? '_' + company : ''}_${days}`;
  }

  /** Save completed task IDs to localStorage */
  _saveCompleted() {
    try {
      localStorage.setItem(this._storageKey(), JSON.stringify(this.completedTasks));
    } catch (e) { /* ignore storage errors */ }
  }

  /** Load completed task IDs from localStorage */
  _loadCompleted() {
    try {
      const saved = localStorage.getItem(this._storageKey());
      if (saved) {
        this.completedTasks = JSON.parse(saved);
        return true;
      }
    } catch (e) { /* ignore */ }
    this.completedTasks = {};
    return false;
  }

  /** Apply completed state from localStorage to plan data and update progress */
  _applyCompletedState() {
    if (!this.planData) return;

    let completedCount = 0;
    const totalTasks = this.planData.progress?.total_tasks || 0;

    // Mark tasks in sessions as completed
    for (const session of (this.planData.sessions || [])) {
      for (const task of (session.tasks || [])) {
        if (this.completedTasks[task.id]) {
          task.completed = true;
          completedCount++;
        } else {
          task.completed = false;
        }
      }
    }

    // Update progress
    const percentage = totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0;
    if (this.planData.progress) {
      this.planData.progress.completed_tasks = completedCount;
      this.planData.progress.percentage = percentage;
    }
  }

  // === Focus Area Grouping ===

  /** Group all tasks from all sessions by parent_area, ordered by weak_areas */
  _groupTasksByFocusArea() {
    const weakAreas = this.planData?.weak_areas || [];
    const sessions = this.planData?.sessions || [];
    const skillGaps = this.planData?.skill_gaps || [];

    // Build a task lookup by parent_area
    const tasksByArea = {};
    for (const session of sessions) {
      for (const task of session.tasks) {
        const area = task.parent_area || 'General';
        if (!tasksByArea[area]) tasksByArea[area] = [];
        // Avoid duplicates (same task could appear across sessions via review)
        if (!tasksByArea[area].find(t => t.id === task.id)) {
          tasksByArea[area].push(task);
        }
      }
    }

    // Build focus area groups, ordered by weak_areas (lowest confidence first)
    const seenAreas = new Set();
    const focusAreas = [];

    for (const area of weakAreas) {
      const name = area.name;
      if (seenAreas.has(name)) continue;
      seenAreas.add(name);

      const tasks = tasksByArea[name] || [];
      // Find matching skill gaps for this area
      const relatedGaps = skillGaps.filter(g =>
        g.skill && (name.toLowerCase().includes(g.skill.toLowerCase()) ||
                    g.skill.toLowerCase().includes(name.toLowerCase()))
      );

      focusAreas.push({
        name,
        confidence: area.confidence || 0.5,
        category: area.category || 'general',
        source: area.source || '',
        tasks,
        skillGaps: relatedGaps,
        sub_topics: area.sub_topics || [],
      });
    }

    // Add any areas from tasks that weren't in weak_areas
    for (const [areaName, tasks] of Object.entries(tasksByArea)) {
      if (!seenAreas.has(areaName)) {
        focusAreas.push({
          name: areaName,
          confidence: 0.5,
          category: tasks[0]?.category || 'general',
          source: '',
          tasks,
          skillGaps: [],
          sub_topics: [],
        });
      }
    }

    return focusAreas;
  }

  /** Determine state of each focus area: completed, active, or locked */
  _calculateFocusAreaStates() {
    let activeFound = false;
    return this.focusAreas.map(area => {
      const total = area.tasks.length;
      const done = area.tasks.filter(t => this.completedTasks[t.id]).length;
      const isComplete = total > 0 && done >= total;

      let state;
      if (isComplete) {
        state = 'completed';
      } else if (!activeFound) {
        state = 'active';
        activeFound = true;
      } else {
        state = 'locked';
      }

      return {
        ...area,
        state,
        done,
        total,
        progress: total > 0 ? Math.round((done / total) * 100) : 0,
      };
    });
  }

  async init() {
    this.setupEventListeners();
    this.loadSavedFormData();
    this.showState('setup');

    // Retry generation if auth succeeds after login overlay
    window.addEventListener('auth-success', () => {
      if (this._pendingGeneration) {
        this._pendingGeneration = false;
        this.handleGenerate();
      }
    });
  }

  // === State Management ===

  showState(state) {
    this.state = state;
    const setup = document.getElementById('setupSection');
    const loading = document.getElementById('loadingState');
    const content = document.getElementById('planContent');
    const empty = document.getElementById('emptyState');

    if (setup) setup.style.display = state === 'setup' ? 'block' : 'none';
    if (loading) loading.style.display = state === 'loading' ? 'block' : 'none';
    if (content) content.style.display = state === 'content' ? 'block' : 'none';
    if (empty) empty.style.display = state === 'empty' ? 'block' : 'none';
  }

  showSetup() {
    this.showState('setup');
  }

  generateNewPlan() {
    this.showState('setup');
  }

  // === Event Listeners ===

  setupEventListeners() {
    const btn = document.getElementById('generateBtn');
    if (btn) {
      btn.addEventListener('click', () => this.handleGenerate());
    }

    // Save form data on input
    ['roleInput', 'companyInput', 'jdInput', 'skillsInput', 'daysInput'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.addEventListener('input', () => this.saveFormData());
    });
  }

  // === Form Persistence ===

  saveFormData() {
    const data = {
      role: document.getElementById('roleInput')?.value || '',
      company: document.getElementById('companyInput')?.value || '',
      jd: document.getElementById('jdInput')?.value || '',
      skills: document.getElementById('skillsInput')?.value || '',
      days: document.getElementById('daysInput')?.value || '30'
    };
    localStorage.setItem('studyplan_form', JSON.stringify(data));
  }

  loadSavedFormData() {
    const saved = localStorage.getItem('studyplan_form');
    if (saved) {
      try {
        const data = JSON.parse(saved);
        if (data.role) document.getElementById('roleInput').value = data.role;
        if (data.company) document.getElementById('companyInput').value = data.company;
        if (data.jd) document.getElementById('jdInput').value = data.jd;
        if (data.skills) document.getElementById('skillsInput').value = data.skills;
        if (data.days) document.getElementById('daysInput').value = data.days;
      } catch (e) { /* ignore */ }
    }
  }

  // === Generate Plan ===

  async handleGenerate() {
    const role = document.getElementById('roleInput')?.value.trim();
    if (!role) {
      alert('Please enter a target role');
      document.getElementById('roleInput')?.focus();
      return;
    }

    const company = document.getElementById('companyInput')?.value.trim() || '';
    const jd = document.getElementById('jdInput')?.value.trim() || '';
    const skills = document.getElementById('skillsInput')?.value.trim() || '';
    const days = document.getElementById('daysInput')?.value || '30';

    this.saveFormData();

    // Ensure auth token is available before making API call
    if (typeof AuthHelper !== 'undefined' && !AuthHelper.isAuthenticated()) {
      this._pendingGeneration = true;
      AuthHelper.ensureAuth(); // Shows login overlay if needed
      return; // Will retry via auth-success event after login
    }

    const btn = document.getElementById('generateBtn');
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Generating...';
    }

    this.showState('loading');

    try {
      let data;
      // Use JSON body endpoint for large JD text, query params otherwise
      if (jd.length > 200) {
        data = await this.generatePersonalized(role, company, jd, skills, days);
      } else {
        data = await this.generateWithParams(role, company, jd, skills, days);
      }

      if (data.error) throw new Error(data.error.message || data.error);

      this.planData = data;
      this.renderPlan(data);
      this.showState('content');
    } catch (error) {
      console.error('[StudyPlan] Error generating plan:', error);
      alert('Failed to generate study plan. Please try again.');
      this.showState('setup');
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.textContent = 'Generate Personalized Plan';
      }
    }
  }

  async generateWithParams(role, company, jd, skills, days) {
    const params = new URLSearchParams({
      user_id: DEFAULT_USER_ID,
      days: days,
      daily_minutes: '60',
      target_role: role,
    });
    if (company) params.set('target_company', company);
    if (jd) params.set('job_description', jd);
    if (skills) params.set('current_skills', skills);

    const url = `${API_BASE}/study-plan/generate?${params.toString()}`;
    const options = { method: 'POST' };
    if (typeof AuthHelper !== 'undefined') {
      return (await AuthHelper.authFetch(url, options)).json();
    }
    return (await fetch(url, options)).json();
  }

  async generatePersonalized(role, company, jd, skills, days) {
    const url = `${API_BASE}/study-plan/generate-personalized`;
    const options = {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: DEFAULT_USER_ID,
        target_role: role,
        target_company: company || null,
        job_description: jd || null,
        current_skills: skills ? skills.split(',').map(s => s.trim()).filter(Boolean) : null,
        days: parseInt(days),
        daily_minutes: 60,
      })
    };
    if (typeof AuthHelper !== 'undefined') {
      return (await AuthHelper.authFetch(url, options)).json();
    }
    return (await fetch(url, options)).json();
  }

  // === Render Plan ===

  renderPlan(data) {
    if (!data) return;

    // Load completed state from localStorage and apply to plan
    this._loadCompleted();
    this._applyCompletedState();

    // Progress (now reflects actual completed tasks)
    const progress = data.progress || {};
    this.updateProgress(progress, data.duration_days || 30);

    // Personalization header
    this.renderPersonalizationHeader(data);

    // Personalization context
    this.renderPersonalizationContext(data);

    // Study tips
    this.renderStudyTips(data);

    // Group tasks by focus area
    this.focusAreas = this._groupTasksByFocusArea();

    // Render focus area stepper + cards
    this.renderFocusAreaStepper();
    this.renderFocusAreaCards();

    // Render milestones (compact, inside progress section)
    this.renderMilestones(data.milestones || []);
  }

  renderPersonalizationHeader(data) {
    const subtitle = document.querySelector('.study-plan-header-subtitle');
    if (subtitle) {
      let text = '';
      if (data.target_role) text += `for ${data.target_role}`;
      if (data.target_company) text += ` at ${data.target_company}`;
      if (data.plan_type === 'personalized') text += ' (Personalized)';
      subtitle.textContent = text || 'Personalized learning path';
    }
  }

  renderPersonalizationContext(data) {
    let existing = document.getElementById('personalizationContext');
    if (existing) existing.remove();

    const ctx = data.personalization_context;
    if (!ctx) return;

    const sources = ctx.sources || {};
    const activeSources = Object.entries(sources).filter(([k, v]) => v).map(([k]) => k.replace(/_/g, ' '));

    const content = document.querySelector('.study-plan-content');
    if (!content) return;

    const el = document.createElement('div');
    el.id = 'personalizationContext';
    el.className = 'personalization-context';
    el.innerHTML = `
      <h3>Plan Personalization</h3>
      <div class="context-stats">
        <span>Based on: ${activeSources.join(', ') || 'Generic'}</span>
        <span>${ctx.weak_areas_count || ctx.weak_area_count || 0} focus areas</span>
        <span>${ctx.skill_gaps_count || ctx.skill_gap_count || 0} skill gaps</span>
        <span>${ctx.total_tasks_generated || ctx.task_count || 0} tasks</span>
      </div>
    `;

    const progressSection = content.querySelector('.progress-section');
    if (progressSection) {
      progressSection.parentNode.insertBefore(el, progressSection.nextSibling);
    }
  }

  renderStudyTips(data) {
    let existing = document.getElementById('studyTipsSection');
    if (existing) existing.remove();

    const role = (data.target_role || '').toLowerCase();
    const company = data.target_company || '';
    const tips = this.getStudyTips(role, company);
    if (!tips || tips.length === 0) return;

    const content = document.querySelector('.study-plan-content');
    const el = document.createElement('div');
    el.id = 'studyTipsSection';
    el.className = 'study-tips-section';
    el.innerHTML = `
      <h3>Study Tips${data.target_role ? ' for ' + data.target_role : ''}</h3>
      <ul class="tips-list">
        ${tips.map(t => `<li>${t}</li>`).join('')}
      </ul>
    `;

    const after = document.getElementById('personalizationContext') || document.querySelector('.progress-section');
    if (after) after.parentNode.insertBefore(el, after.nextSibling);
  }

  getStudyTips(role, company) {
    const tips = [];

    if (role.includes('devops') || role.includes('sre') || role.includes('platform')) {
      tips.push('Set up a home lab with Docker and Kubernetes — hands-on practice is irreplaceable.');
      tips.push('Practice explaining infrastructure decisions out loud, as if in an interview.');
      tips.push('Review incident response runbooks from public post-mortems (Google, Netflix).');
    }
    if (role.includes('frontend') || role.includes('react') || role.includes('vue')) {
      tips.push('Build a small project for each framework concept you want to master.');
      tips.push('Practice whiteboarding component hierarchies and data flow diagrams.');
      tips.push('Review the browser rendering pipeline — most senior FE interviews test this.');
    }
    if (role.includes('backend') || role.includes('java') || role.includes('python')) {
      tips.push('Practice system design with real-world examples — design Instagram, URL shortener, etc.');
      tips.push('Review database indexing, query optimization, and concurrency patterns.');
      tips.push('Write clean API designs — understand REST vs GraphQL vs gRPC tradeoffs.');
    }
    if (role.includes('data') || role.includes('ml') || role.includes('analyst')) {
      tips.push('Practice SQL queries — window functions, CTEs, and optimization are key.');
      tips.push('Build a portfolio project that demonstrates end-to-end data pipeline skills.');
    }
    if (role.includes('security')) {
      tips.push('Review OWASP Top 10 and practice explaining each vulnerability and mitigation.');
      tips.push('Set up a vulnerable lab environment to practice penetration testing safely.');
    }

    if (company) {
      tips.push(`Research ${company}'s engineering blog and recent technical talks.`);
      tips.push(`Practice questions commonly asked at ${company} — see the company-specific tasks in your plan.`);
    }

    tips.push('Spend 30 minutes daily on spaced review rather than cramming.');
    tips.push('Mock interviews with a peer dramatically improve performance — schedule one per week.');

    return tips;
  }

  updateProgress(progress, durationDays) {
    const totalTasks = progress.total_tasks || 0;
    const completedTasks = progress.completed_tasks || 0;
    const percentage = progress.percentage || 0;
    const daysLeft = Math.max(0, (durationDays || 30) - Math.floor(completedTasks / Math.max(totalTasks / (durationDays || 30), 1)));
    const studyHours = Math.round((totalTasks - completedTasks) * 0.75);

    const bar = document.getElementById('progressBar');
    if (bar) {
      bar.style.width = percentage + '%';
      if (percentage >= 100) {
        bar.style.background = 'linear-gradient(90deg, #10b981, #34d399)';
      } else if (percentage >= 75) {
        bar.style.background = 'linear-gradient(90deg, #3b82f6, #10b981)';
      } else if (percentage >= 50) {
        bar.style.background = 'linear-gradient(90deg, #3b82f6, #8b5cf6)';
      }
    }
    const text = document.getElementById('progressText');
    if (text) text.textContent = Math.round(percentage) + '%';
    const total = document.getElementById('totalTasks');
    if (total) total.textContent = totalTasks;
    const completed = document.getElementById('completedTasks');
    if (completed) completed.textContent = completedTasks;
    const days = document.getElementById('daysLeft');
    if (days) days.textContent = daysLeft;
    const hours = document.getElementById('studyHours');
    if (hours) hours.textContent = studyHours;
  }

  // === Focus Area Stepper ===

  renderFocusAreaStepper() {
    const container = document.getElementById('focusAreaStepper');
    if (!container) return;

    const states = this._calculateFocusAreaStates();
    if (states.length === 0) {
      container.innerHTML = '';
      return;
    }

    container.innerHTML = states.map((area, i) => {
      const stepClass = area.state === 'completed' ? 'completed' :
                        area.state === 'active' ? 'active' : 'locked';
      const icon = area.state === 'completed' ? '✓' :
                   area.state === 'active' ? (i + 1) : '🔒';
      const connectorClass = i < states.length - 1
        ? `<div class="stepper-connector ${area.state === 'completed' ? 'completed' : ''}"></div>`
        : '';

      return `
        <div class="stepper-step ${stepClass}" data-step="${i}"
             ${area.state === 'completed' ? `onclick="studyPlan.scrollToArea(${i})"` : ''}
             title="${area.state === 'locked' ? 'Complete previous focus area to unlock' : area.name}">
          <span class="stepper-icon">${icon}</span>
          <span>${area.name.length > 16 ? area.name.slice(0, 14) + '...' : area.name}</span>
        </div>
        ${connectorClass}
      `;
    }).join('');
  }

  /** Scroll to a completed focus area card when clicking its stepper step */
  scrollToArea(index) {
    const card = document.querySelector(`.focus-area-card[data-area-index="${index}"]`);
    if (card) {
      card.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Briefly highlight
      card.style.boxShadow = '0 0 20px rgba(16, 185, 129, 0.3)';
      setTimeout(() => card.style.boxShadow = '', 1000);
    }
  }

  // === Focus Area Cards ===

  renderFocusAreaCards(unlockIndex = -1) {
    const container = document.getElementById('focusAreaCards');
    if (!container) return;

    const states = this._calculateFocusAreaStates();
    if (states.length === 0) {
      container.innerHTML = '<p style="color: var(--text-secondary, #888); text-align: center; padding: 40px;">No focus areas generated yet</p>';
      return;
    }

    container.innerHTML = states.map((area, i) => {
      const cardClass = area.state;
      const isUnlocked = i === unlockIndex;
      const confidencePct = Math.round(area.confidence * 100);
      const confidenceColor = confidencePct < 30 ? '#ef4444' : confidencePct < 50 ? '#f59e0b' : '#10b981';
      const sourceClass = area.source === 'job_description' ? 'focus-area-source-jd' :
                          area.source === 'company_focus' ? 'focus-area-source-company' :
                          area.source === 'role_pattern' ? 'focus-area-source-role' :
                          area.source === 'cognitive_graph' ? 'focus-area-source-graph' : '';
      const sourceLabel = area.source === 'job_description' ? 'JD' :
                          area.source === 'company_focus' ? 'Company' :
                          area.source === 'role_pattern' ? 'Role' :
                          area.source === 'cognitive_graph' ? 'Graph' : '';

      if (area.state === 'locked') {
        return `
          <div class="focus-area-card locked" data-area-index="${i}">
            <div class="focus-area-header">
              <div class="focus-area-icon">🔒</div>
              <div class="focus-area-info">
                <div class="focus-area-name">${area.name}</div>
                <div class="focus-area-meta">
                  <span class="task-count">${area.total} tasks</span>
                  <span>Complete previous area to unlock</span>
                </div>
              </div>
              <span class="focus-area-status-badge">Locked</span>
            </div>
          </div>
        `;
      }

      // Active or completed card
      const bodyStyle = area.state === 'active' ? '' : 'display:none;';
      const headerClick = area.state === 'completed'
        ? `onclick="studyPlan.toggleAreaExpand(${i})"`
        : '';

      // Build task list HTML
      const taskListHtml = area.tasks.map(task => {
        const isCompleted = !!this.completedTasks[task.id];
        const focusBadge = task.is_focus ? '<span class="task-badge focus-badge">Focus</span>' : '';
        const stretchBadge = task.is_stretch ? '<span class="task-badge stretch-badge">Stretch</span>' : '';
        const desc = task.description ? `<div class="task-description">${task.description}</div>` : '';
        const resources = (task.resources && task.resources.length > 0)
          ? `<div class="task-resources">${task.resources.map(r =>
              `<a href="${r.url || '#'}" class="resource-link" target="_blank">${r.type === 'leetcode' ? 'LeetCode' : r.type === 'concept' ? 'Guide' : 'Link'}: ${r.name}</a>`
            ).join('')}</div>` : '';

        return `
          <div class="focus-area-task-card ${isCompleted ? 'completed' : ''}" data-task-id="${task.id}">
            <div class="task-header">
              <div class="task-title">
                <div class="task-checkbox ${isCompleted ? 'checked' : ''}" onclick="studyPlan.toggleTaskComplete('${task.id}')"></div>
                ${focusBadge}${stretchBadge}${task.title}
              </div>
              <div class="task-meta">
                <span class="task-difficulty difficulty-${task.difficulty}">${task.difficulty}</span>
                <span class="task-time">${task.estimated_minutes}min</span>
                <span class="task-category">${task.category}</span>
              </div>
            </div>
            ${desc}
            ${resources}
          </div>
        `;
      }).join('');

      // Skill gap badges
      const gapBadges = area.skillGaps.length > 0
        ? `<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:8px;">
            ${area.skillGaps.slice(0, 4).map(g => {
              const priority = g.priority || 'medium';
              return `<span class="skill-gap-priority priority-${priority}" style="font-size:10px;padding:2px 6px;border-radius:4px;">${g.skill}</span>`;
            }).join('')}
          </div>`
        : '';

      const statusBadgeText = area.state === 'completed' ? 'Completed' : 'In Progress';
      const areaIconText = area.state === 'completed' ? '✓' : '🎯';

      return `
        <div class="focus-area-card ${cardClass} ${isUnlocked ? 'unlocking' : ''}" data-area-index="${i}">
          <div class="focus-area-header" ${headerClick}>
            <div class="focus-area-icon">${areaIconText}</div>
            <div class="focus-area-info">
              <div class="focus-area-name">
                ${area.name}
                ${sourceLabel ? `<span class="focus-area-source-tag ${sourceClass}">${sourceLabel}</span>` : ''}
              </div>
              <div class="focus-area-meta">
                <span class="task-count">${area.done}/${area.total} tasks</span>
                <div class="focus-area-progress-mini">
                  <div class="focus-area-progress-mini-fill" style="width: ${area.progress}%;"></div>
                </div>
              </div>
            </div>
            <span class="focus-area-status-badge">${statusBadgeText}</span>
            ${area.state === 'completed' ? '<span class="focus-area-chevron">▼</span>' : ''}
          </div>
          <div class="focus-area-body" style="${bodyStyle}">
            <div class="focus-area-confidence-row">
              <span class="focus-area-confidence-label">Confidence</span>
              <div class="focus-area-confidence-bar">
                <div class="focus-area-confidence-fill" style="width: ${confidencePct}%; background: ${confidenceColor};"></div>
              </div>
              <span class="focus-area-confidence-pct" style="color: ${confidenceColor};">${confidencePct}%</span>
            </div>
            ${gapBadges}
            <div class="focus-area-task-list">
              ${taskListHtml}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  /** Toggle expand/collapse on a completed focus area card */
  toggleAreaExpand(index) {
    const card = document.querySelector(`.focus-area-card[data-area-index="${index}"]`);
    if (!card) return;
    const body = card.querySelector('.focus-area-body');
    if (!body) return;

    if (body.style.display === 'none') {
      body.style.display = '';
      card.querySelector('.focus-area-chevron').style.transform = 'rotate(180deg)';
    } else {
      body.style.display = 'none';
      card.querySelector('.focus-area-chevron').style.transform = '';
    }
  }

  // === Milestones (compact, inside progress section) ===

  renderMilestones(milestones) {
    const container = document.getElementById('milestonesList');
    if (!container) return;

    if (!milestones || milestones.length === 0) {
      const roadmap = document.getElementById('milestoneRoadmap');
      if (roadmap) roadmap.style.display = 'none';
      return;
    }

    const roadmap = document.getElementById('milestoneRoadmap');
    if (roadmap) roadmap.style.display = '';

    const sessions = this.planData?.sessions || [];
    const totalTasks = this.planData?.progress?.total_tasks || 1;
    const completedCount = Object.keys(this.completedTasks).length;

    const today = new Date();
    const allComplete = milestones.every(m => {
      const targetDate = new Date(m.target_date);
      const diffDays = Math.ceil((targetDate - today) / (1000 * 60 * 60 * 24));
      const isCompletionType = m.type === 'completion';
      let progress = 0;
      if (m.week && sessions.length > 0) {
        const weekStart = (m.week - 1) * 7;
        const weekEnd = m.week * 7;
        const weekSessions = sessions.filter(s => s.day_number > weekStart && s.day_number <= weekEnd);
        let weekTasks = 0, weekDone = 0;
        for (const s of weekSessions) {
          for (const t of s.tasks) {
            if (!t.id.startsWith('review_')) { weekTasks++; if (this.completedTasks[t.id]) weekDone++; }
          }
        }
        progress = weekTasks > 0 ? Math.round((weekDone / weekTasks) * 100) : 0;
      } else if (isCompletionType) {
        progress = totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0;
      }
      return isCompletionType ? progress >= 100 : (m.week ? progress >= 100 : diffDays <= 0);
    });

    if (allComplete) container.classList.add('all-complete');
    else container.classList.remove('all-complete');

    container.innerHTML = milestones.map(m => {
      const targetDate = new Date(m.target_date);
      const diffDays = Math.ceil((targetDate - today) / (1000 * 60 * 60 * 24));
      const isCompletionType = m.type === 'completion';

      let milestoneProgress = 0;
      if (m.week && sessions.length > 0) {
        const weekStart = (m.week - 1) * 7;
        const weekEnd = m.week * 7;
        const weekSessions = sessions.filter(s => s.day_number > weekStart && s.day_number <= weekEnd);
        let weekTasks = 0, weekDone = 0;
        for (const s of weekSessions) {
          for (const t of s.tasks) {
            if (!t.id.startsWith('review_')) { weekTasks++; if (this.completedTasks[t.id]) weekDone++; }
          }
        }
        milestoneProgress = weekTasks > 0 ? Math.round((weekDone / weekTasks) * 100) : 0;
      } else if (isCompletionType) {
        milestoneProgress = totalTasks > 0 ? Math.round((completedCount / totalTasks) * 100) : 0;
      }

      const isCompleted = isCompletionType
        ? milestoneProgress >= 100
        : (m.week ? milestoneProgress >= 100 : diffDays <= 0);
      const isUpcoming = !isCompleted && (diffDays > 0 && diffDays <= 7);

      const nodeClass = isCompleted ? 'completed' : isUpcoming ? 'upcoming' : 'pending';
      const dotClass = isCompleted ? 'completed' : isUpcoming ? 'upcoming' : 'pending';
      const dotIcon = isCompleted ? '✓' : isCompletionType ? '★' : isUpcoming ? String(m.week || '?') : '○';
      const progressBadgeClass = isCompleted ? 'done' : isUpcoming ? 'in-progress' : 'pending';
      const progressBadgeText = isCompleted ? 'Done' : milestoneProgress > 0 ? `${milestoneProgress}%` : 'Upcoming';

      const focusTags = (m.focus_areas && m.focus_areas.length > 0)
        ? `<div class="milestone-focus-tags">${m.focus_areas.slice(0, 3).map(f => `<span class="milestone-focus-tag">${f}</span>`).join('')}</div>`
        : '';

      const rewardHtml = m.reward ? `<div class="milestone-reward">🎯 ${m.reward}</div>` : '';
      const descHtml = m.description ? `<div class="milestone-desc">${m.description}</div>` : '';

      const progressBar = milestoneProgress > 0 && !isCompleted
        ? `<div class="milestone-progress-bar"><div class="milestone-progress-bar-fill" style="width: ${milestoneProgress}%"></div></div>`
        : isCompleted
          ? `<div class="milestone-progress-bar"><div class="milestone-progress-bar-fill" style="width: 100%"></div></div>`
          : '';

      const dateLabel = isCompleted ? 'Completed' : diffDays === 0 ? 'Today' : diffDays > 0 ? `${diffDays} days away` : 'Past due';

      return `
        <div class="milestone-node ${nodeClass} ${isCompletionType ? 'completion' : ''}">
          <div class="milestone-dot ${dotClass}">${dotIcon}</div>
          <div class="milestone-card">
            <div class="milestone-name">
              ${m.name}
              <span class="milestone-progress-badge ${progressBadgeClass}">${progressBadgeText}</span>
            </div>
            ${descHtml}
            ${focusTags}
            ${progressBar}
            <div class="milestone-meta-row">
              <div class="milestone-date">📅 ${m.target_date} · ${dateLabel}</div>
              ${rewardHtml}
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  // === Task Completion ===

  async toggleTaskComplete(taskId) {
    // Toggle completion state
    const isNowCompleted = !this.completedTasks[taskId];

    if (isNowCompleted) {
      this.completedTasks[taskId] = true;
    } else {
      delete this.completedTasks[taskId];
    }

    // Save to localStorage immediately
    this._saveCompleted();

    // Update the task card UI
    const taskCard = document.querySelector(`[data-task-id="${taskId}"]`);
    if (taskCard) {
      if (isNowCompleted) {
        taskCard.classList.add('completed');
      } else {
        taskCard.classList.remove('completed');
      }
      const checkbox = taskCard.querySelector('.task-checkbox');
      if (checkbox) {
        if (isNowCompleted) {
          checkbox.classList.add('checked');
        } else {
          checkbox.classList.remove('checked');
        }
      }
    }

    // Apply completed state and update progress
    this._applyCompletedState();
    const progress = this.planData?.progress || {};
    this.updateProgress(progress, this.planData?.duration_days || 30);

    // Check if this task completion unlocked the next focus area
    let unlockIndex = -1;
    const prevStates = this._calculateFocusAreaStates();
    const areaJustCompleted = prevStates.find(a =>
      a.state === 'completed' && a.tasks.some(t => t.id === taskId)
    );

    if (areaJustCompleted) {
      // Find the next area that was locked but is now active
      const newStates = this._calculateFocusAreaStates();
      for (let i = 0; i < newStates.length; i++) {
        if (newStates[i].state === 'active' && prevStates[i]?.state === 'locked') {
          unlockIndex = i;
          break;
        }
      }

      // Re-render cards with unlock animation
      this.renderFocusAreaCards(unlockIndex);
      this.renderFocusAreaStepper();

      // Pulse the stepper step for the newly unlocked area
      if (unlockIndex >= 0) {
        setTimeout(() => {
          const step = document.querySelector(`.stepper-step[data-step="${unlockIndex}"]`);
          if (step) step.classList.add('pulse');

          // Scroll to the newly unlocked card
          const card = document.querySelector(`.focus-area-card[data-area-index="${unlockIndex}"]`);
          if (card) {
            card.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 100);
      }
    } else {
      // Just update the card's progress indicators without full re-render
      this._updateCardProgress(taskId);
      this.renderFocusAreaStepper();
    }

    // Re-render milestones
    this.renderMilestones(this.planData?.milestones || []);

    // Check if all tasks are completed
    if (progress.percentage >= 100) {
      this.showPlanComplete();
    }

    // Also notify backend (best-effort, non-blocking)
    try {
      const url = `${API_BASE}/study-plan/${DEFAULT_USER_ID}/complete-task?task_id=${taskId}&performance_score=0.8`;
      if (typeof AuthHelper !== 'undefined') {
        await AuthHelper.authFetch(url, { method: 'POST' });
      } else {
        await fetch(url, { method: 'POST' });
      }
    } catch (e) {
      console.warn('[StudyPlan] Backend notification failed (completion saved locally):', e.message);
    }
  }

  /** Update just the card-level progress without full re-render */
  _updateCardProgress(taskId) {
    // Find which area this task belongs to
    const states = this._calculateFocusAreaStates();
    for (let i = 0; i < states.length; i++) {
      const area = states[i];
      if (area.tasks.some(t => t.id === taskId)) {
        // Update the progress mini bar and task count
        const card = document.querySelector(`.focus-area-card[data-area-index="${i}"]`);
        if (card) {
          const countEl = card.querySelector('.task-count');
          if (countEl) countEl.textContent = `${area.done}/${area.total} tasks`;
          const miniFill = card.querySelector('.focus-area-progress-mini-fill');
          if (miniFill) miniFill.style.width = area.progress + '%';

          // If area just completed, update status
          if (area.state === 'completed' && !card.classList.contains('completed')) {
            card.classList.add('completed');
            card.classList.add('just-completed');
            setTimeout(() => card.classList.remove('just-completed'), 500);
            const badge = card.querySelector('.focus-area-status-badge');
            if (badge) badge.textContent = 'Completed';
          }
        }
        break;
      }
    }
  }

  showPlanComplete() {
    // Don't show if already displayed
    if (document.getElementById('planCompleteModal')) return;

    const role = this.planData?.target_role || 'your target role';
    const company = this.planData?.target_company;
    const totalTasks = this.planData?.progress?.total_tasks || 0;

    const overlay = document.createElement('div');
    overlay.id = 'planCompleteModal';
    overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.8);z-index:99999;display:flex;align-items:center;justify-content:center;font-family:system-ui,sans-serif;';

    overlay.innerHTML = `
      <div style="background:#1e1e2e;border-radius:16px;padding:40px;max-width:480px;width:90%;box-shadow:0 20px 60px rgba(0,0,0,0.5);text-align:center;">
        <div style="font-size:64px;margin-bottom:16px;">🎉</div>
        <h2 style="color:#fff;margin:0 0 8px 0;font-size:24px;">Plan Complete!</h2>
        <p style="color:#aaa;margin:0 0 20px 0;font-size:15px;">
          You've completed all ${totalTasks} tasks for <strong style="color:#3b82f6;">${role}</strong>${company ? ` at <strong style="color:#8b5cf6;">${company}</strong>` : ''}.
          You're ready for your interview!
        </p>
        <div style="background:#2a2a3a;border-radius:12px;padding:20px;margin-bottom:24px;text-align:left;">
          <h3 style="color:#10b981;margin:0 0 12px 0;font-size:14px;text-transform:uppercase;letter-spacing:1px;">What's Next?</h3>
          <ul style="color:#ddd;margin:0;padding-left:20px;font-size:14px;line-height:2;">
            <li>Schedule a <strong>mock interview</strong> with a peer or mentor</li>
            <li>Review your <strong>weak areas</strong> one more time before the interview</li>
            ${company ? `<li>Research <strong>${company}'s latest engineering blog posts</strong></li>` : ''}
            <li>Practice <strong>system design whiteboarding</strong> under time pressure</li>
            <li>Prepare your <strong>STAR stories</strong> for behavioral questions</li>
            <li>Generate a <strong>new plan</strong> for a different role or deeper focus</li>
          </ul>
        </div>
        <div style="display:flex;gap:12px;justify-content:center;">
          <button onclick="studyPlan.dismissComplete()" style="padding:12px 24px;background:#374151;color:#fff;border:none;border-radius:8px;font-size:14px;cursor:pointer;">Close</button>
          <button onclick="studyPlan.startNewPlan()" style="padding:12px 24px;background:linear-gradient(135deg,#3b82f6,#8b5cf6);color:#fff;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;">New Plan</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
  }

  dismissComplete() {
    const modal = document.getElementById('planCompleteModal');
    if (modal) modal.remove();
  }

  startNewPlan() {
    this.dismissComplete();
    // Clear completion state for this plan
    try { localStorage.removeItem(this._storageKey()); } catch(e) {}
    this.completedTasks = {};
    this.showSetup();
  }
}

// Initialize
const studyPlan = new StudyPlanManager();
document.addEventListener('DOMContentLoaded', () => studyPlan.init());