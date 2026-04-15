// Options Page Script — Settings persistence

document.addEventListener('DOMContentLoaded', async () => {
  const backendUrlInput = document.getElementById('backendUrl');
  const authTokenInput = document.getElementById('authToken');
  const defaultSourceSelect = document.getElementById('defaultSource');
  const autoDetectToggle = document.getElementById('autoDetect');
  const saveBtn = document.getElementById('saveBtn');
  const savedToast = document.getElementById('savedToast');

  // Load existing settings
  async function loadSettings() {
    const settings = await chrome.storage.local.get([
      'apiUrl', '_tk', 'defaultAudioSource', 'autoDetectMeetings'
    ]);

    backendUrlInput.value = settings.apiUrl || 'http://localhost:8000';
    authTokenInput.value = settings._tk || '';
    defaultSourceSelect.value = settings.defaultAudioSource || 'tab';
    autoDetectToggle.checked = settings.autoDetectMeetings !== false;
  }

  // Save settings
  async function saveSettings() {
    await chrome.storage.local.set({
      apiUrl: backendUrlInput.value.trim() || 'http://localhost:8000',
      _tk: authTokenInput.value.trim(),
      defaultAudioSource: defaultSourceSelect.value,
      autoDetectMeetings: autoDetectToggle.checked
    });

    // Show confirmation
    savedToast.classList.add('show');
    setTimeout(() => savedToast.classList.remove('show'), 2000);
  }

  saveBtn.addEventListener('click', saveSettings);

  // Load on init
  await loadSettings();
});