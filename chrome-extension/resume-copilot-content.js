/**
 * Resume Copilot Content Script
 * Auto-fills job applications and provides AI-powered resume suggestions
 * Free tier: Basic auto-fill + job tracking
 */

class ResumeCopilot {
  constructor() {
    this.userProfile = null;
    this.currentJob = null;
    this.sidebar = null;
    this.apiUrl = 'http://127.0.0.1:8000';
    this.init();
  }

  async init() {
    // Load user profile from storage
    await this.loadUserProfile();

    // Detect if we're on a job application page
    const platform = this.detectJobPlatform();
    if (platform) {
      this.currentJob = this.extractJobInfo(platform);
      this.injectFloatingButton();
      this.injectSidebar();

      // Check if there's a resume to analyze against
      if (this.userProfile?.resume_text) {
        this.analyzeJobMatch();
      }
    }
  }

  async loadUserProfile() {
    try {
      const result = await chrome.storage.local.get(['userProfile', 'resumeData']);
      this.userProfile = result.userProfile || result.resumeData || null;
    } catch (e) {
      console.log('No user profile found');
    }
  }

  detectJobPlatform() {
    const url = window.location.href;

    if (url.includes('greenhouse.io')) return 'greenhouse';
    if (url.includes('lever.co')) return 'lever';
    if (url.includes('myworkdayjobs.com')) return 'workday';
    if (url.includes('icims.com')) return 'icims';
    if (url.includes('smartrecruiters.com')) return 'smartrecruiters';
    if (url.includes('linkedin.com/jobs')) return 'linkedin';
    if (url.includes('indeed.com')) return 'indeed';
    if (url.includes('glassdoor.com')) return 'glassdoor';
    if (url.includes('jobs.')) return 'generic-careers';

    // Check for application forms
    const forms = document.querySelectorAll('form');
    for (const form of forms) {
      const text = form.textContent.toLowerCase();
      if (text.includes('resume') || text.includes('cv') ||
          text.includes('experience') || text.includes('application')) {
        return 'generic-application';
      }
    }

    return null;
  }

  extractJobInfo(platform) {
    const info = {
      platform,
      url: window.location.href,
      title: '',
      company: '',
      description: '',
      location: ''
    };

    try {
      switch (platform) {
        case 'greenhouse':
          info.title = document.querySelector('.app-title')?.textContent?.trim() ||
                      document.querySelector('h1')?.textContent?.trim() || '';
          info.company = document.querySelector('.company-name')?.textContent?.trim() ||
                        document.querySelector('[class*="company"]')?.textContent?.trim() || '';
          info.description = document.querySelector('#content')?.textContent?.trim() || '';
          break;

        case 'lever':
          info.title = document.querySelector('.posting-headline h2')?.textContent?.trim() || '';
          info.company = document.querySelector('.main-header-logo')?.textContent?.trim() || '';
          info.description = document.querySelector('.posting-description')?.textContent?.trim() || '';
          break;

        case 'linkedin':
          info.title = document.querySelector('h1')?.textContent?.trim() || '';
          info.company = document.querySelector('[data-testid="job-title"]')?.textContent?.trim() ||
                        document.querySelector('.jobs-unified-top-card__company-name')?.textContent?.trim() || '';
          info.description = document.querySelector('.jobs-description')?.textContent?.trim() || '';
          break;

        case 'indeed':
          info.title = document.querySelector('h1')?.textContent?.trim() || '';
          info.company = document.querySelector('[data-testid="company-name"]')?.textContent?.trim() ||
                        document.querySelector('.jobsearch-CompanyInfoWithoutHeaderImage')?.textContent?.trim() || '';
          info.description = document.querySelector('#jobDescriptionText')?.textContent?.trim() || '';
          break;

        default:
          // Generic extraction
          info.title = document.querySelector('h1')?.textContent?.trim() ||
                      document.title?.split('|')[0]?.trim() || '';
          info.description = document.querySelector('[class*="description"], [id*="description"]')?.textContent?.trim() || '';
      }
    } catch (e) {
      console.log('Error extracting job info:', e);
    }

    return info;
  }

  injectFloatingButton() {
    const button = document.createElement('div');
    button.id = 'resume-copilot-button';
    button.innerHTML = `
      <div class="copilot-btn-icon">📝</div>
      <div class="copilot-btn-text">Resume Copilot</div>
    `;
    button.onclick = () => this.toggleSidebar();

    const style = document.createElement('style');
    style.textContent = `
      #resume-copilot-button {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: linear-gradient(135deg, #8b5cf6, #ec4899);
        color: white;
        padding: 14px 20px;
        border-radius: 50px;
        cursor: pointer;
        z-index: 999999;
        display: flex;
        align-items: center;
        gap: 10px;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-weight: 600;
        font-size: 14px;
        box-shadow: 0 4px 15px rgba(139, 92, 246, 0.4);
        transition: all 0.3s;
      }
      #resume-copilot-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(139, 92, 246, 0.5);
      }
      #resume-copilot-button.active {
        right: 420px;
      }
      .copilot-btn-icon { font-size: 18px; }
      .copilot-badge {
        position: absolute;
        top: -5px;
        right: -5px;
        background: #10b981;
        color: white;
        font-size: 10px;
        padding: 2px 6px;
        border-radius: 10px;
      }
    `;

    document.head.appendChild(style);
    document.body.appendChild(button);
  }

  injectSidebar() {
    const sidebar = document.createElement('div');
    sidebar.id = 'resume-copilot-sidebar';
    sidebar.innerHTML = `
      <div class="copilot-header">
        <div class="copilot-title">
          <span class="copilot-icon">📝</span>
          Resume Copilot
          <span class="copilot-badge-free">FREE</span>
        </div>
        <button class="copilot-close" onclick="this.closest('#resume-copilot-sidebar').classList.remove('active')">×</button>
      </div>
      <div class="copilot-content">
        <div class="copilot-section job-info">
          <h4>📋 Current Job</h4>
          <div id="copilot-job-details">Loading...</div>
        </div>

        <div class="copilot-section match-score" id="matchScoreSection" style="display:none;">
          <h4>🎯 Resume Match Score</h4>
          <div class="match-score-display">
            <div class="score-circle" id="matchScoreCircle">--</div>
            <div class="score-label">Match Score</div>
          </div>
          <div class="missing-keywords" id="missingKeywords"></div>
          <button class="btn-primary" id="analyzeBtn" onclick="resumeCopilot.analyzeJobMatch()">
            Analyze Match
          </button>
        </div>

        <div class="copilot-section auto-fill">
          <h4>⚡ Quick Actions</h4>
          <button class="btn-action" onclick="resumeCopilot.autoFillForm()">
            🤖 Auto-Fill Application
          </button>
          <button class="btn-action" onclick="resumeCopilot.trackApplication()">
            📊 Track Application
          </button>
          <button class="btn-action" onclick="resumeCopilot.saveJob()">
            💾 Save Job
          </button>
        </div>

        <div class="copilot-section suggestions" id="suggestionsSection">
          <h4>✨ Tailor Your Resume</h4>
          <div id="tailorSuggestions">
            <p class="suggestion-hint">Upload your resume to see tailored suggestions</p>
          </div>
        </div>

        <div class="copilot-section upgrade">
          <div class="upgrade-banner">
            <div class="upgrade-title">🚀 Pro Features</div>
            <div class="upgrade-features">
              • Smart follow-up reminders<br>
              • A/B test tracking<br>
              • Rejection analysis
            </div>
            <button class="btn-upgrade" onclick="window.open('http://127.0.0.1:8000/resume-review-v2.html', '_blank')">
              Upgrade $9/mo
            </button>
          </div>
        </div>
      </div>
    `;

    const style = document.createElement('style');
    style.textContent = `
      #resume-copilot-sidebar {
        position: fixed;
        top: 0;
        right: -400px;
        width: 380px;
        height: 100vh;
        background: #0a0a0a;
        border-left: 1px solid #333;
        z-index: 999998;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        transition: right 0.3s ease;
        display: flex;
        flex-direction: column;
      }
      #resume-copilot-sidebar.active { right: 0; }

      .copilot-header {
        background: linear-gradient(135deg, #8b5cf6, #ec4899);
        padding: 16px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .copilot-title {
        color: white;
        font-size: 16px;
        font-weight: 600;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .copilot-icon { font-size: 20px; }

      .copilot-badge-free {
        background: #10b981;
        color: white;
        font-size: 10px;
        padding: 2px 8px;
        border-radius: 10px;
        margin-left: 5px;
      }

      .copilot-close {
        background: none;
        border: none;
        color: white;
        font-size: 24px;
        cursor: pointer;
        opacity: 0.8;
      }

      .copilot-close:hover { opacity: 1; }

      .copilot-content {
        flex: 1;
        overflow-y: auto;
        padding: 20px;
      }

      .copilot-section {
        background: rgba(255, 255, 255, 0.03);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
      }

      .copilot-section h4 {
        margin: 0 0 12px 0;
        font-size: 14px;
        color: #fff;
      }

      .job-info h4 { color: #8b5cf6; }
      .match-score h4 { color: #10b981; }
      .auto-fill h4 { color: #f59e0b; }
      .suggestions h4 { color: #ec4899; }

      .job-title {
        font-weight: 600;
        margin-bottom: 4px;
      }

      .job-company {
        color: #888;
        font-size: 13px;
      }

      .match-score-display {
        text-align: center;
        padding: 20px;
      }

      .score-circle {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, #8b5cf6, #ec4899);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0 auto 10px;
        font-size: 28px;
        font-weight: 700;
        color: white;
      }

      .score-label {
        color: #888;
        font-size: 13px;
      }

      .btn-primary, .btn-action {
        width: 100%;
        padding: 12px;
        border-radius: 8px;
        border: none;
        font-weight: 600;
        cursor: pointer;
        margin-bottom: 10px;
        font-size: 13px;
        transition: all 0.2s;
      }

      .btn-primary {
        background: linear-gradient(135deg, #8b5cf6, #ec4899);
        color: white;
      }

      .btn-action {
        background: rgba(255, 255, 255, 0.08);
        color: #fff;
        border: 1px solid rgba(255, 255, 255, 0.1);
      }

      .btn-action:hover {
        background: rgba(255, 255, 255, 0.12);
      }

      .missing-keywords {
        margin: 15px 0;
      }

      .keyword-pill {
        display: inline-block;
        background: rgba(239, 68, 68, 0.2);
        color: #ef4444;
        padding: 4px 10px;
        border-radius: 15px;
        font-size: 11px;
        margin: 3px;
      }

      .suggestion-hint {
        color: #888;
        font-size: 13px;
        text-align: center;
        padding: 20px;
      }

      .suggestion-item {
        background: rgba(139, 92, 246, 0.1);
        border-left: 3px solid #8b5cf6;
        padding: 12px;
        margin-bottom: 10px;
        border-radius: 0 8px 8px 0;
      }

      .suggestion-type {
        font-size: 11px;
        color: #8b5cf6;
        margin-bottom: 4px;
      }

      .suggestion-text {
        font-size: 13px;
      }

      .upgrade-banner {
        background: linear-gradient(135deg, rgba(139, 92, 246, 0.1), rgba(236, 72, 153, 0.1));
        border: 1px solid rgba(139, 92, 246, 0.3);
        border-radius: 10px;
        padding: 16px;
        text-align: center;
      }

      .upgrade-title {
        font-weight: 600;
        margin-bottom: 8px;
        color: #8b5cf6;
      }

      .upgrade-features {
        font-size: 12px;
        color: #888;
        margin-bottom: 12px;
        text-align: left;
        line-height: 1.8;
      }

      .btn-upgrade {
        width: 100%;
        padding: 10px;
        background: linear-gradient(135deg, #8b5cf6, #ec4899);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        cursor: pointer;
      }
    `;

    document.head.appendChild(style);
    document.body.appendChild(sidebar);

    this.sidebar = sidebar;

    // Update job info
    this.updateJobInfo();
  }

  updateJobInfo() {
    const details = document.getElementById('copilot-job-details');
    if (details && this.currentJob) {
      details.innerHTML = `
        <div class="job-title">${this.currentJob.title || 'Unknown Position'}</div>
        <div class="job-company">${this.currentJob.company || 'Unknown Company'}</div>
        ${this.currentJob.location ? `<div class="job-location">📍 ${this.currentJob.location}</div>` : ''}
      `;
    }
  }

  async analyzeJobMatch() {
    if (!this.userProfile?.resume_text) {
      this.showNotification('Please upload your resume in the main app first', 'info');
      return;
    }

    const btn = document.getElementById('analyzeBtn');
    btn.disabled = true;
    btn.textContent = 'Analyzing...';

    try {
      const response = await fetch(`${this.apiUrl}/resume/analyze-v2`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resume_text: this.userProfile.resume_text,
          job_description: this.currentJob.description
        })
      });

      const data = await response.json();

      if (data.success) {
        this.displayMatchResults(data.analysis);
      }
    } catch (e) {
      console.error('Analysis error:', e);
      this.showNotification('Analysis failed. Please try again.', 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = 'Re-Analyze';
    }
  }

  displayMatchResults(analysis) {
    const section = document.getElementById('matchScoreSection');
    section.style.display = 'block';

    const score = analysis.overall_score || 0;
    document.getElementById('matchScoreCircle').textContent = score;
    document.getElementById('matchScoreCircle').style.background =
      score >= 80 ? 'linear-gradient(135deg, #10b981, #059669)' :
      score >= 60 ? 'linear-gradient(135deg, #f59e0b, #d97706)' :
      'linear-gradient(135deg, #ef4444, #dc2626)';

    // Display missing keywords
    const keywordsContainer = document.getElementById('missingKeywords');
    if (analysis.missing_keywords?.length) {
      keywordsContainer.innerHTML = `
        <p style="font-size: 12px; color: #888; margin-bottom: 8px;">Missing keywords:</p>
        ${analysis.missing_keywords.slice(0, 5).map(k =>
          `<span class="keyword-pill">${k}</span>`
        ).join('')}
      `;
    }

    // Display tailored suggestions
    const suggestionsContainer = document.getElementById('tailorSuggestions');
    if (analysis.tailored_suggestions?.length) {
      suggestionsContainer.innerHTML = analysis.tailored_suggestions.slice(0, 3).map(s => `
        <div class="suggestion-item">
          <div class="suggestion-type">💡 Suggestion</div>
          <div class="suggestion-text">${s}</div>
        </div>
      `).join('');
    }
  }

  autoFillForm() {
    if (!this.userProfile) {
      this.showNotification('Please upload your resume first', 'info');
      return;
    }

    const profile = this.userProfile;
    let filled = 0;

    // Common field mappings
    const fieldMap = {
      // Personal info
      'first name': profile.first_name || profile.firstName,
      'lastname': profile.last_name || profile.lastName,
      'last name': profile.last_name || profile.lastName,
      'email': profile.email,
      'phone': profile.phone,
      'linkedin': profile.linkedin_url || profile.linkedin,
      'portfolio': profile.portfolio_url || profile.website,

      // Current job
      'current company': profile.current_company || profile.experience?.[0]?.company,
      'current title': profile.current_title || profile.experience?.[0]?.title,
      'current employer': profile.current_company || profile.experience?.[0]?.company,

      // Experience
      'years of experience': profile.years_experience || this.calculateYearsExperience(profile),
    };

    // Find and fill form fields
    const inputs = document.querySelectorAll('input, textarea, select');

    inputs.forEach(input => {
      const label = this.findLabelForInput(input).toLowerCase();
      const placeholder = (input.placeholder || '').toLowerCase();
      const name = (input.name || '').toLowerCase();
      const id = (input.id || '').toLowerCase();

      // Check all field identifiers
      const fieldText = `${label} ${placeholder} ${name} ${id}`;

      for (const [key, value] of Object.entries(fieldMap)) {
        if (value && fieldText.includes(key)) {
          this.fillField(input, value);
          filled++;
          break;
        }
      }
    });

    if (filled > 0) {
      this.showNotification(`Auto-filled ${filled} fields! ✓`, 'success');
    } else {
      this.showNotification('No matching fields found. Try filling manually.', 'info');
    }
  }

  findLabelForInput(input) {
    // Try to find associated label
    if (input.id) {
      const label = document.querySelector(`label[for="${input.id}"]`);
      if (label) return label.textContent;
    }

    // Check parent label
    const parentLabel = input.closest('label');
    if (parentLabel) return parentLabel.textContent;

    // Check previous sibling
    let prev = input.previousElementSibling;
    while (prev) {
      if (prev.tagName === 'LABEL') return prev.textContent;
      prev = prev.previousElementSibling;
    }

    return '';
  }

  fillField(input, value) {
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));

    // Highlight filled field
    input.style.borderColor = '#10b981';
    input.style.backgroundColor = 'rgba(16, 185, 129, 0.1)';
  }

  calculateYearsExperience(profile) {
    if (!profile.experience) return '';
    // Simple calculation - could be improved
    return '';
  }

  async trackApplication() {
    if (!this.currentJob) return;

    try {
      await chrome.runtime.sendMessage({
        action: 'saveJob',
        data: {
          ...this.currentJob,
          status: 'applied',
          applied_at: new Date().toISOString()
        }
      });

      this.showNotification('Application tracked! 📊', 'success');
    } catch (e) {
      console.error('Track error:', e);
    }
  }

  async saveJob() {
    if (!this.currentJob) return;

    try {
      await chrome.runtime.sendMessage({
        action: 'saveJob',
        data: this.currentJob
      });

      this.showNotification('Job saved! 💾', 'success');
    } catch (e) {
      console.error('Save error:', e);
    }
  }

  toggleSidebar() {
    const sidebar = document.getElementById('resume-copilot-sidebar');
    const button = document.getElementById('resume-copilot-button');

    if (sidebar) {
      sidebar.classList.toggle('active');
      button?.classList.toggle('active');
    }
  }

  showNotification(message, type = 'info') {
    // Create notification element
    const notif = document.createElement('div');
    notif.className = `copilot-notification ${type}`;
    notif.textContent = message;

    const style = document.createElement('style');
    style.textContent = `
      .copilot-notification {
        position: fixed;
        bottom: 90px;
        right: 20px;
        padding: 14px 20px;
        border-radius: 10px;
        color: white;
        font-weight: 500;
        z-index: 9999999;
        animation: slideIn 0.3s ease;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
      }
      .copilot-notification.success { background: #10b981; }
      .copilot-notification.error { background: #ef4444; }
      .copilot-notification.info { background: #3b82f6; }
      @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
    `;

    document.head.appendChild(style);
    document.body.appendChild(notif);

    setTimeout(() => notif.remove(), 3000);
  }
}

// Initialize
const resumeCopilot = new ResumeCopilot();

// Expose to global scope for inline event handlers
window.resumeCopilot = resumeCopilot;

// Listen for messages from popup/background
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'fillForm') {
    resumeCopilot.autoFillForm();
    sendResponse({ success: true });
  }
});
