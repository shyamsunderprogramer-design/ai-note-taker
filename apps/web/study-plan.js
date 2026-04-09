/**
 * Study Plan JavaScript
 * Phase 2 Task #33 - Personalized Study Plan Generator
 */

const API_BASE = 'http://127.0.0.1:8000';
const DEFAULT_USER_ID = 'default';

// Study Plan Manager
class StudyPlanManager {
  constructor() {
    this.planData = null;
    this.currentPlan = null;
  }

  async init() {
    await this.loadPlan();
    this.setupEventListeners();
  }

  setupEventListeners() {
    // Task completion checkboxes
    document.addEventListener('click', (e) => {
      if (e.target.classList.contains('task-checkbox')) {
        this.toggleTaskComplete(e.target.dataset.taskId);
      }
    });
  }

  async loadPlan() {
    try {
      const response = await fetch(`${API_BASE}/study-plan/${DEFAULT_USER_ID}`);
      const data = await response.json();

      if (data.error || !data.sessions || data.sessions.length === 0) {
        this.showEmptyState();
        return;
      }

      this.planData = data;
      this.renderPlan(data);
    } catch (error) {
      console.error('[StudyPlan] Error loading plan:', error);
      this.showEmptyState();
    }
  }

  showEmptyState() {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('planContent').style.display = 'none';
    document.getElementById('emptyState').style.display = 'block';
  }

  renderPlan(data) {
    // Hide loading, show content
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('planContent').style.display = 'block';

    // Update progress
    this.updateProgress(data.progress);

    // Render today's session
    this.renderTodaySession(data.sessions);

    // Render upcoming sessions
    this.renderUpcomingSessions(data.sessions);

    // Render weak areas
    this.renderWeakAreas(data.weak_areas);

    // Render milestones
    this.renderMilestones(data.milestones);
  }

  updateProgress(progress) {
    const percentage = progress?.percentage || 0;
    const total = progress?.total_tasks || 0;
    const completed = progress?.completed_tasks || 0;
    const daysLeft = Math.max(0, 30 - Math.floor(completed / Math.max(total / 30, 1)));
    const hours = Math.round((total - completed) * 0.75); // ~45 min avg

    document.getElementById('progressBar').style.width = `${percentage}%`;
    document.getElementById('progressText').textContent = `${percentage.toFixed(0)}%`;
    document.getElementById('totalTasks').textContent = total;
    document.getElementById('completedTasks').textContent = completed;
    document.getElementById('daysLeft').textContent = daysLeft;
    document.getElementById('studyHours').textContent = hours;
  }

  renderTodaySession(sessions) {
    const today = new Date().toISOString().split('T')[0];
    const todaySession = sessions.find(s => s.date.startsWith(today));

    const themeEl = document.getElementById('todayTheme');
    const tasksEl = document.getElementById('todayTasks');

    if (!todaySession) {
      themeEl.textContent = 'Rest Day';
      tasksEl.innerHTML = `
        <div class="empty-state" style="padding: 40px;">
          <p>No tasks scheduled for today</p>
          <p style="font-size: 13px; color: var(--text-secondary); margin-top: 10px;">
            Take a break or review past material
          </p>
        </div>
      `;
      return;
    }

    themeEl.textContent = todaySession.theme;

    tasksEl.innerHTML = todaySession.tasks.map(task => `
      <div class="task-card ${task.completed ? 'completed' : ''}" data-task-id="${task.id}">
        <div class="task-header">
          <div class="task-title">
            <div class="task-checkbox ${task.completed ? 'checked' : ''}" data-task-id="${task.id}"></div>
            ${task.title}
          </div>
        </div>
        <p style="font-size: 13px; color: var(--text-secondary); margin-left: 30px;">
          ${task.description}
        </p>
        <div class="task-meta" style="margin-left: 30px;">
          <span class="task-difficulty difficulty-${task.difficulty}">${task.difficulty}</span>
          <span class="task-category">${task.category}</span>
          <span class="task-time">⏱️ ${task.estimated_minutes} min</span>
        </div>
        ${this.renderResources(task.resources)}
      </div>
    `).join('');
  }

  renderResources(resources) {
    if (!resources || resources.length === 0) return '';

    return `
      <div class="task-resources">
        ${resources.map(r => `
          <a href="${r.url || '#'}" class="resource-link" target="_blank" rel="noopener">
            ${r.type === 'leetcode' ? '💻' : r.type === 'concept' ? '📖' : '🔗'}
            ${r.name}
          </a>
        `).join('')}
      </div>
    `;
  }

  renderUpcomingSessions(sessions) {
    const container = document.getElementById('upcomingList');
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Get next 5 future sessions
    const upcoming = sessions
      .filter(s => new Date(s.date) > today)
      .slice(0, 5);

    if (upcoming.length === 0) {
      container.innerHTML = '<p style="text-align: center; color: var(--text-secondary);">No upcoming sessions</p>';
      return;
    }

    container.innerHTML = upcoming.map(session => {
      const date = new Date(session.date);
      const day = date.getDate();
      const month = date.toLocaleString('default', { month: 'short' });
      const taskCount = session.tasks.length;
      const totalMinutes = session.total_minutes;

      return `
        <div class="session-preview" data-date="${session.date}">
          <div class="session-date">
            <div class="session-day">${day}</div>
            <div class="session-month">${month}</div>
          </div>
          <div class="session-info">
            <div class="session-theme">${session.theme}</div>
            <div class="session-meta">${taskCount} tasks • ${totalMinutes} min</div>
          </div>
        </div>
      `;
    }).join('');
  }

  renderWeakAreas(weakAreas) {
    const container = document.getElementById('weakAreasList');

    if (!weakAreas || weakAreas.length === 0) {
      container.innerHTML = '<p style="color: var(--text-secondary); font-size: 13px;">No weak areas identified yet</p>';
      return;
    }

    container.innerHTML = weakAreas.slice(0, 5).map(area => {
      const confidence = Math.round((area.confidence || 0) * 100);
      return `
        <div class="weak-area-item">
          <span class="weak-area-name">${area.name}</span>
          <span class="weak-area-confidence">${confidence}%</span>
          <div class="confidence-bar">
            <div class="confidence-fill" style="width: ${confidence}%"></div>
          </div>
        </div>
      `;
    }).join('');
  }

  renderMilestones(milestones) {
    const container = document.getElementById('milestonesList');

    if (!milestones || milestones.length === 0) {
      container.innerHTML = '<p style="color: var(--text-secondary); font-size: 13px;">No milestones set</p>';
      return;
    }

    const today = new Date();

    container.innerHTML = milestones.map(m => {
      const targetDate = new Date(m.target_date);
      const isCompleted = targetDate < today;
      const isUpcoming = !isCompleted && (targetDate - today) / (1000 * 60 * 60 * 24) < 7;

      let iconClass = 'pending';
      let iconContent = '○';

      if (isCompleted) {
        iconClass = 'completed';
        iconContent = '✓';
      } else if (isUpcoming) {
        iconClass = 'upcoming';
        iconContent = '◐';
      }

      return `
        <div class="milestone-item ${iconClass}">
          <div class="milestone-icon ${iconClass}">${iconContent}</div>
          <div class="milestone-content">
            <div class="milestone-name">${m.name}</div>
            <div class="milestone-date">${targetDate.toLocaleDateString()}</div>
            ${m.reward ? `<div class="milestone-reward">🏆 ${m.reward}</div>` : ''}
          </div>
        </div>
      `;
    }).join('');
  }

  async toggleTaskComplete(taskId) {
    try {
      // Call API to mark task complete
      const response = await fetch(
        `${API_BASE}/study-plan/${DEFAULT_USER_ID}/complete-task?task_id=${taskId}&performance_score=0.8`,
        { method: 'POST' }
      );

      if (response.ok) {
        // Update UI
        const taskCard = document.querySelector(`[data-task-id="${taskId}"]`);
        if (taskCard) {
          taskCard.classList.toggle('completed');
          const checkbox = taskCard.querySelector('.task-checkbox');
          checkbox.classList.toggle('checked');
        }

        // Reload plan to update progress
        await this.loadPlan();
      }
    } catch (error) {
      console.error('[StudyPlan] Error completing task:', error);
    }
  }

  async generateNewPlan() {
    const btn = document.querySelector('.generate-btn');
    btn.disabled = true;
    btn.textContent = 'Generating...';

    try {
      const response = await fetch(
        `${API_BASE}/study-plan/generate?user_id=${DEFAULT_USER_ID}&days=30&daily_minutes=60`,
        { method: 'POST' }
      );

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      this.renderPlan(data);
    } catch (error) {
      console.error('[StudyPlan] Error generating plan:', error);
      alert('Failed to generate study plan. Make sure the backend is running.');
    } finally {
      btn.disabled = false;
      btn.textContent = '✨ Generate Study Plan';
    }
  }

  async exportPlan(format) {
    try {
      const response = await fetch(
        `${API_BASE}/study-plan/${DEFAULT_USER_ID}/export?format=${format}`,
        { method: 'POST' }
      );

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Download file
      const blob = new Blob([data.content], { type: format === 'json' ? 'application/json' : 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `study-plan-${DEFAULT_USER_ID}.${format === 'ical' ? 'ics' : format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('[StudyPlan] Export error:', error);
    }
  }
}

// Initialize
const studyPlan = new StudyPlanManager();
document.addEventListener('DOMContentLoaded', () => studyPlan.init());
