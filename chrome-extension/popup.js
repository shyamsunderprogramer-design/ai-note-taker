// Popup script
const API_BASE = 'http://localhost:8000';

document.addEventListener('DOMContentLoaded', async () => {
  const statusDot = document.getElementById('statusDot');
  const statusText = document.getElementById('statusText');
  const errorMessage = document.getElementById('errorMessage');
  const jobsCount = document.getElementById('jobsCount');
  const appsCount = document.getElementById('appsCount');
  const openAppBtn = document.getElementById('openAppBtn');
  const viewJobsBtn = document.getElementById('viewJobsBtn');

  // Check connection to ANT backend
  async function checkConnection() {
    try {
      const response = await fetch(`${API_BASE}/health`, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' }
      });

      if (response.ok) {
        statusDot.classList.remove('disconnected');
        statusText.textContent = 'Connected to AI Note Taker';
        errorMessage.classList.remove('show');
        return true;
      }
    } catch (e) {
      console.log('[ANT] Connection check failed:', e);
    }

    statusDot.classList.add('disconnected');
    statusText.textContent = 'Not connected';
    errorMessage.classList.add('show');
    return false;
  }

  // Load stats
  async function loadStats() {
    try {
      const response = await fetch(`${API_BASE}/job-tracker/stats`);
      if (response.ok) {
        const data = await response.json();
        jobsCount.textContent = data.total_jobs || 0;
        appsCount.textContent = data.by_status?.applied || 0;
      }
    } catch (e) {
      console.log('[ANT] Stats load failed:', e);
      jobsCount.textContent = '0';
      appsCount.textContent = '0';
    }
  }

  // Button handlers
  openAppBtn.addEventListener('click', () => {
    // Try to open the Electron app or web interface
    chrome.tabs.create({ url: 'http://localhost:8000/static' });
  });

  viewJobsBtn.addEventListener('click', () => {
    chrome.tabs.create({ url: 'http://localhost:8000/static/job-tracker.html' });
  });

  // Initialize
  await checkConnection();
  await loadStats();
});
