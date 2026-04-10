/**
 * Study Plan - Personalized Learning Path Generator
 * Handles setup form, API calls, and plan rendering
 */

var API_BASE = typeof API_BASE !== 'undefined' ? API_BASE : 'http://127.0.0.1:8000';
const DEFAULT_USER_ID = 'default';

class StudyPlanManager {
  constructor() {
    this.planData = null;
    this.state = 'setup'; // 'setup' | 'loading' | 'content' | 'empty'
  }

  async init() {
    this.setupEventListeners();
    this.loadSavedFormData();
    this.showState('setup');
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
    if (typeof AuthHelper !== 'undefined') {
      if (!AuthHelper.isAuthenticated()) {
        try {
          console.log('[StudyPlan] No token found, attempting auto-login...');
          await AuthHelper.ensureAuth();
          console.log('[StudyPlan] Auto-login result, token present:', AuthHelper.isAuthenticated());
        } catch (e) {
          console.error('[StudyPlan] Auth failed:', e);
          alert('Authentication required. Please reload the page and try again.');
          return;
        }
      } else {
        console.log('[StudyPlan] Token already present, proceeding');
      }
    } else {
      console.warn('[StudyPlan] AuthHelper not available — requests may fail with 401');
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

    // Progress
    const progress = data.progress || {};
    this.updateProgress(progress);

    // Weak areas
    this.renderWeakAreas(data.weak_areas || []);

    // Milestones
    this.renderMilestones(data.milestones || []);

    // Sessions
    const sessions = data.sessions || [];
    this.renderTodaySession(sessions);
    this.renderUpcomingSessions(sessions);

    // Skill gaps
    this.renderSkillGaps(data.skill_gaps || []);

    // Personalization header
    this.renderPersonalizationHeader(data);
  }

  renderPersonalizationHeader(data) {
    // Update subtitle with role/company info
    const subtitle = document.querySelector('.study-plan-header-subtitle');
    if (subtitle) {
      let text = '';
      if (data.target_role) text += `for ${data.target_role}`;
      if (data.target_company) text += ` at ${data.target_company}`;
      if (data.plan_type === 'personalized') text += ' (Personalized)';
      subtitle.textContent = text || 'Personalized learning path';
    }
  }

  updateProgress(progress) {
    const totalTasks = progress.total_tasks || 0;
    const completedTasks = progress.completed_tasks || 0;
    const percentage = progress.percentage || 0;
    const daysLeft = Math.max(0, 30 - Math.floor(completedTasks / Math.max(totalTasks / 30, 1)));
    const studyHours = Math.round((totalTasks - completedTasks) * 0.75);

    const bar = document.getElementById('progressBar');
    if (bar) bar.style.width = percentage + '%';
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

  renderTodaySession(sessions) {
    const container = document.getElementById('todayTasks');
    const themeEl = document.getElementById('todayTheme');
    if (!container) return;

    const today = new Date().toISOString().split('T')[0];
    const todaySession = sessions.find(s => s.date && s.date.startsWith(today));

    if (!todaySession || !todaySession.tasks || todaySession.tasks.length === 0) {
      if (themeEl) themeEl.textContent = 'Rest Day';
      container.innerHTML = '<p style="color: var(--text-secondary, #888); text-align: center; padding: 20px;">No study session scheduled for today. Take a break or review!</p>';
      return;
    }

    if (themeEl) themeEl.textContent = todaySession.theme || "Today's Session";

    container.innerHTML = todaySession.tasks.map(task => `
      <div class="task-item ${task.completed ? 'completed' : ''}" data-task-id="${task.id}">
        <div class="task-checkbox ${task.completed ? 'checked' : ''}" onclick="studyPlan.toggleTaskComplete('${task.id}')"></div>
        <div class="task-content">
          <div class="task-title">${task.title}</div>
          <div class="task-meta">
            <span class="task-tag category-${task.category}">${task.category}</span>
            <span class="task-tag difficulty-${task.difficulty}">${task.difficulty}</span>
            <span class="task-tag">${task.estimated_minutes}min</span>
          </div>
        </div>
      </div>
    `).join('');
  }

  renderUpcomingSessions(sessions) {
    const container = document.getElementById('upcomingList');
    if (!container) return;

    const today = new Date().toISOString().split('T')[0];
    const upcoming = sessions.filter(s => s.date && !s.date.startsWith(today)).slice(0, 5);

    if (upcoming.length === 0) {
      container.innerHTML = '<p style="color: var(--text-secondary, #888);">No upcoming sessions</p>';
      return;
    }

    container.innerHTML = upcoming.map(session => {
      const date = new Date(session.date);
      const dateStr = date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
      return `
        <div class="upcoming-session">
          <div class="upcoming-date">${dateStr}</div>
          <div class="upcoming-info">
            <div class="upcoming-theme">${session.theme}</div>
            <div class="upcoming-meta">${session.tasks?.length || 0} tasks &middot; ${session.total_minutes || 0}min</div>
          </div>
        </div>
      `;
    }).join('');
  }

  renderWeakAreas(weakAreas) {
    const container = document.getElementById('weakAreasList');
    if (!container) return;

    if (!weakAreas || weakAreas.length === 0) {
      container.innerHTML = '<p style="color: var(--text-secondary, #888);">No weak areas identified</p>';
      return;
    }

    container.innerHTML = weakAreas.slice(0, 5).map(area => {
      const confidence = Math.round((area.confidence || 0) * 100);
      const sourceTag = area.source === 'job_description' ? ' (JD)' :
                       area.source === 'company_focus' ? ' (Company)' :
                       area.source === 'role_pattern' ? ' (Role)' : '';
      return `
        <div class="weak-area-item">
          <div class="weak-area-name">${area.name}${sourceTag}</div>
          <div class="weak-area-bar">
            <div class="weak-area-fill" style="width: ${confidence}%; background: ${confidence < 30 ? '#ef4444' : confidence < 50 ? '#f59e0b' : '#10b981'}"></div>
          </div>
          <div class="weak-area-confidence">${confidence}%</div>
        </div>
      `;
    }).join('');
  }

  renderSkillGaps(skillGaps) {
    const container = document.getElementById('skillGapsList');
    if (!container) return;

    if (!skillGaps || skillGaps.length === 0) {
      document.getElementById('skillGapsSection').style.display = 'none';
      return;
    }

    document.getElementById('skillGapsSection').style.display = 'block';
    const header = document.getElementById('skillGapsHeader');
    if (header) header.style.display = 'block';

    container.innerHTML = skillGaps.slice(0, 8).map(gap => {
      const status = gap.current_level === 'known' ? '✅' : '🔴';
      const label = gap.current_level === 'known'
        ? `${gap.skill} (known)`
        : `${gap.skill} (gap)`;
      return `<div class="skill-gap-item"><span>${status}</span> <span>${label}</span></div>`;
    }).join('');
  }

  renderMilestones(milestones) {
    const container = document.getElementById('milestonesList');
    if (!container) return;

    if (!milestones || milestones.length === 0) {
      container.innerHTML = '<p style="color: var(--text-secondary, #888);">No milestones</p>';
      return;
    }

    const today = new Date();
    container.innerHTML = milestones.map(m => {
      const targetDate = new Date(m.target_date);
      const diffDays = Math.ceil((targetDate - today) / (1000 * 60 * 60 * 24));
      let icon, statusClass;
      if (m.type === 'completion' || diffDays <= 0) {
        icon = '✅'; statusClass = 'milestone-complete';
      } else if (diffDays <= 7) {
        icon = '🔶'; statusClass = 'milestone-upcoming';
      } else {
        icon = '⭕'; statusClass = 'milestone-pending';
      }
      return `
        <div class="milestone-item ${statusClass}">
          <span class="milestone-icon">${icon}</span>
          <div class="milestone-info">
            <div class="milestone-name">${m.name}</div>
            <div class="milestone-date">${m.target_date}${m.reward ? ' — ' + m.reward : ''}</div>
          </div>
        </div>
      `;
    }).join('');
  }

  async toggleTaskComplete(taskId) {
    try {
      const url = `${API_BASE}/study-plan/${DEFAULT_USER_ID}/complete-task?task_id=${taskId}&performance_score=0.8`;
      if (typeof AuthHelper !== 'undefined') {
        await AuthHelper.authFetch(url, { method: 'POST' });
      } else {
        await fetch(url, { method: 'POST' });
      }
    } catch (e) {
      console.error('[StudyPlan] Toggle task error:', e);
    }
  }
}

// Initialize
const studyPlan = new StudyPlanManager();
document.addEventListener('DOMContentLoaded', () => studyPlan.init());