/**
 * Pre-Interview Preparation - JavaScript
 * Handles predictive interview preparation UI and API calls
 */

const API_BASE = 'http://127.0.0.1:8000';

// State
let currentPredictions = [];
let checklistData = {};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  loadSavedFormData();
});

function setupEventListeners() {
  const form = document.getElementById('prepForm');
  form.addEventListener('submit', handleFormSubmit);

  // Save form data on input
  document.getElementById('companyInput').addEventListener('input', saveFormData);
  document.getElementById('roleInput').addEventListener('input', saveFormData);
}

function saveFormData() {
  const data = {
    company: document.getElementById('companyInput').value,
    role: document.getElementById('roleInput').value
  };
  localStorage.setItem('preinterview_form', JSON.stringify(data));
}

function loadSavedFormData() {
  const saved = localStorage.getItem('preinterview_form');
  if (saved) {
    const data = JSON.parse(saved);
    if (data.company) document.getElementById('companyInput').value = data.company;
    if (data.role) document.getElementById('roleInput').value = data.role;
  }
}

async function handleFormSubmit(e) {
  e.preventDefault();

  const company = document.getElementById('companyInput').value.trim();
  const role = document.getElementById('roleInput').value.trim();

  if (!company) {
    alert('Please enter a company name');
    return;
  }

  // Show loading state
  document.getElementById('loadingState').style.display = 'block';
  document.getElementById('resultsSection').classList.remove('active');
  document.getElementById('generateBtn').disabled = true;

  try {
    // Fetch predictions and checklist in parallel
    const [predictionsRes, checklistRes] = await Promise.all([
      fetch(`${API_BASE}/predict/questions?company=${encodeURIComponent(company)}&role=${encodeURIComponent(role || '')}&limit=15`),
      fetch(`${API_BASE}/predict/checklist?company=${encodeURIComponent(company)}&role=${encodeURIComponent(role || '')}`)
    ]);

    const predictions = await predictionsRes.json();
    const checklist = await checklistRes.json();

    if (predictions.error) {
      throw new Error(predictions.error);
    }

    displayResults(predictions, checklist);
  } catch (error) {
    console.error('[PreInterview] Error:', error);
    alert('Failed to generate predictions. Please try again.');
  } finally {
    document.getElementById('loadingState').style.display = 'none';
    document.getElementById('generateBtn').disabled = false;
  }
}

function displayResults(predictions, checklist) {
  currentPredictions = predictions.predictions || [];
  checklistData = checklist.checklist || {};

  // Update company info
  document.getElementById('resultCompany').textContent = predictions.company;
  document.getElementById('resultRole').textContent = predictions.role || 'Software Engineer';

  // Update stats
  document.getElementById('statPredictions').textContent = currentPredictions.length;
  document.getElementById('statConfidence').textContent = Math.round((predictions.confidence || 0) * 100) + '%';

  // Count unique categories
  const categories = new Set(currentPredictions.map(p => p.category));
  document.getElementById('statCategories').textContent = categories.size;

  // Update confidence badge
  const confidenceBadge = document.getElementById('confidenceBadge');
  const confidence = predictions.confidence || 0;
  if (confidence >= 0.7) {
    confidenceBadge.className = 'prep-confidence high';
    confidenceBadge.innerHTML = '<span>●</span> High Confidence';
  } else if (confidence >= 0.4) {
    confidenceBadge.className = 'prep-confidence medium';
    confidenceBadge.innerHTML = '<span>●</span> Medium Confidence';
  } else {
    confidenceBadge.className = 'prep-confidence low';
    confidenceBadge.innerHTML = '<span>●</span> Low Confidence - Limited Data';
  }

  // Display questions
  displayQuestions(currentPredictions);

  // Display checklist
  displayChecklist(checklistData);

  // Show results
  document.getElementById('resultsSection').classList.add('active');
}

function displayQuestions(predictions) {
  const container = document.getElementById('questionsList');

  if (!predictions || predictions.length === 0) {
    container.innerHTML = '<div class="prep-empty">No predictions available for this company.</div>';
    return;
  }

  // Group by category
  const byCategory = {};
  predictions.forEach(pred => {
    const cat = pred.category || 'other';
    if (!byCategory[cat]) byCategory[cat] = [];
    byCategory[cat].push(pred);
  });

  // Display by category
  let html = '';
  const categoryOrder = ['technical', 'system_design', 'behavioral'];

  categoryOrder.forEach(category => {
    if (byCategory[category]) {
      const questions = byCategory[category];
      html += `
        <div style="margin-bottom: 20px;">
          <h4 style="margin-bottom: 10px; color: var(--text-secondary); text-transform: capitalize;">
            ${category.replace('_', ' ')}
          </h4>
      `;

      questions.forEach((q, idx) => {
        const likelihood = Math.round((q.likelihood || q.frequency || 0.5) * 100);
        html += `
          <div class="prep-question-card" onclick="toggleQuestionDetails(this)">
            <div class="prep-question-text">${q.question}</div>
            <div class="prep-question-meta">
              <span class="prep-tag category-${category}">${category.replace('_', ' ')}</span>
              <span class="prep-tag difficulty-${q.difficulty}">${q.difficulty}</span>
              <span class="prep-tag likelihood">${likelihood}% likely</span>
            </div>
          </div>
        `;
      });

      html += '</div>';
    }
  });

  container.innerHTML = html;
}

function toggleQuestionDetails(card) {
  // Could expand to show more details
  card.style.opacity = card.style.opacity === '0.6' ? '1' : '0.6';
}

function displayChecklist(checklist) {
  const container = document.getElementById('checklistContainer');

  if (!checklist) {
    container.innerHTML = '<div class="prep-empty">No checklist available.</div>';
    return;
  }

  // Load saved progress
  const savedProgress = JSON.parse(localStorage.getItem('preinterview_checklist') || '{}');

  let html = '<ul class="prep-checklist">';

  // Technical prep
  if (checklist.technical_prep) {
    html += '<li class="prep-checklist-header" style="font-weight: 600; padding: 10px 0;">Technical Preparation</li>';
    checklist.technical_prep.forEach(item => {
      const checked = savedProgress[item] ? 'checked' : '';
      const textClass = savedProgress[item] ? 'completed' : '';
      html += `
        <li class="prep-checklist-item">
          <div class="prep-checklist-checkbox ${checked}" onclick="toggleChecklistItem(this, '${escapeString(item)}')"></div>
          <span class="prep-checklist-text ${textClass}">${item}</span>
        </li>
      `;
    });
  }

  // System design prep
  if (checklist.system_design_prep) {
    html += '<li class="prep-checklist-header" style="font-weight: 600; padding: 10px 0;">System Design Preparation</li>';
    checklist.system_design_prep.forEach(item => {
      const checked = savedProgress[item] ? 'checked' : '';
      const textClass = savedProgress[item] ? 'completed' : '';
      html += `
        <li class="prep-checklist-item">
          <div class="prep-checklist-checkbox ${checked}" onclick="toggleChecklistItem(this, '${escapeString(item)}')"></div>
          <span class="prep-checklist-text ${textClass}">${item}</span>
        </li>
      `;
    });
  }

  // Behavioral prep
  if (checklist.behavioral_prep) {
    html += '<li class="prep-checklist-header" style="font-weight: 600; padding: 10px 0;">Behavioral Preparation</li>';
    checklist.behavioral_prep.forEach(item => {
      const checked = savedProgress[item] ? 'checked' : '';
      const textClass = savedProgress[item] ? 'completed' : '';
      html += `
        <li class="prep-checklist-item">
          <div class="prep-checklist-checkbox ${checked}" onclick="toggleChecklistItem(this, '${escapeString(item)}')"></div>
          <span class="prep-checklist-text ${textClass}">${item}</span>
        </li>
      `;
    });
  }

  // Company specific
  if (checklist.company_specific) {
    html += '<li class="prep-checklist-header" style="font-weight: 600; padding: 10px 0;">Company Specific</li>';
    checklist.company_specific.forEach(item => {
      const checked = savedProgress[item] ? 'checked' : '';
      const textClass = savedProgress[item] ? 'completed' : '';
      html += `
        <li class="prep-checklist-item">
          <div class="prep-checklist-checkbox ${checked}" onclick="toggleChecklistItem(this, '${escapeString(item)}')"></div>
          <span class="prep-checklist-text ${textClass}">${item}</span>
        </li>
      `;
    });
  }

  // Likely questions
  if (checklist.likely_technical || checklist.likely_system_design || checklist.likely_behavioral) {
    html += '<li class="prep-checklist-header" style="font-weight: 600; padding: 10px 0;">Priority Questions to Practice</li>';

    if (checklist.likely_technical) {
      checklist.likely_technical.forEach(item => {
        const checked = savedProgress[item] ? 'checked' : '';
        const textClass = savedProgress[item] ? 'completed' : '';
        html += `
          <li class="prep-checklist-item">
            <div class="prep-checklist-checkbox ${checked}" onclick="toggleChecklistItem(this, '${escapeString(item)}')"></div>
            <span class="prep-checklist-text ${textClass}" style="color: #60a5fa;">${item}</span>
          </li>
        `;
      });
    }

    if (checklist.likely_system_design) {
      checklist.likely_system_design.forEach(item => {
        const checked = savedProgress[item] ? 'checked' : '';
        const textClass = savedProgress[item] ? 'completed' : '';
        html += `
          <li class="prep-checklist-item">
            <div class="prep-checklist-checkbox ${checked}" onclick="toggleChecklistItem(this, '${escapeString(item)}')"></div>
            <span class="prep-checklist-text ${textClass}" style="color: #a78bfa;">${item}</span>
          </li>
        `;
      });
    }

    if (checklist.likely_behavioral) {
      checklist.likely_behavioral.forEach(item => {
        const checked = savedProgress[item] ? 'checked' : '';
        const textClass = savedProgress[item] ? 'completed' : '';
        html += `
          <li class="prep-checklist-item">
            <div class="prep-checklist-checkbox ${checked}" onclick="toggleChecklistItem(this, '${escapeString(item)}')"></div>
            <span class="prep-checklist-text ${textClass}" style="color: #34d399;">${item}</span>
          </li>
        `;
      });
    }
  }

  html += '</ul>';
  container.innerHTML = html;
}

function toggleChecklistItem(checkbox, item) {
  checkbox.classList.toggle('checked');
  const text = checkbox.nextElementSibling;
  text.classList.toggle('completed');

  // Save progress
  const progress = JSON.parse(localStorage.getItem('preinterview_checklist') || '{}');
  if (checkbox.classList.contains('checked')) {
    progress[item] = true;
  } else {
    delete progress[item];
  }
  localStorage.setItem('preinterview_checklist', JSON.stringify(progress));
}

function escapeString(str) {
  return str.replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// Expose functions to window
window.toggleChecklistItem = toggleChecklistItem;
window.toggleQuestionDetails = toggleQuestionDetails;
