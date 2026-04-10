// Background Service Worker

const API_BASE = 'http://localhost:8000';

// Initialize extension
chrome.runtime.onInstalled.addListener(() => {
  console.log('[ANT] Extension installed');

  // Set default settings
  chrome.storage.local.set({
    autoSave: false,
    notifications: true,
    apiUrl: API_BASE
  });
});

// Listen for messages from content script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'saveJob') {
    handleSaveJob(request.data).then(sendResponse);
    return true; // Will respond asynchronously
  }

  if (request.action === 'getStats') {
    getJobStats().then(sendResponse);
    return true;
  }
});

// Handle saving job to backend
async function handleSaveJob(jobData) {
  try {
    const response = await fetch(`${API_BASE}/job-tracker/application`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        company: jobData.company,
        role: jobData.title,
        location: jobData.location,
        job_url: jobData.url,
        description: jobData.description,
        salary_range: jobData.salary,
        status: 'saved',
        source: jobData.platform
      })
    });

    if (response.ok) {
      return { success: true, message: 'Job saved' };
    } else {
      const error = await response.json();
      return { success: false, error: error.error || 'Failed to save' };
    }
  } catch (e) {
    console.error('[ANT] Background save error:', e);
    return { success: false, error: 'Network error' };
  }
}

// Get job stats
async function getJobStats() {
  try {
    const response = await fetch(`${API_BASE}/job-tracker/stats`);
    if (response.ok) {
      return await response.json();
    }
  } catch (e) {
    console.log('[ANT] Stats fetch error:', e);
  }
  return { total_jobs: 0, by_status: {} };
}

// Periodic health check (every 5 minutes)
setInterval(async () => {
  try {
    await fetch(`${API_BASE}/health`);
  } catch (e) {
    // Ignore errors - backend might be temporarily down
  }
}, 5 * 60 * 1000);
