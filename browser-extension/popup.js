/**
 * Browser Extension Popup
 * Captures job details and sends to ANT
 */

document.addEventListener('DOMContentLoaded', async () => {
    const statusBox = document.getElementById('statusBox');
    const jobForm = document.getElementById('jobForm');
    const captureBtn = document.getElementById('captureBtn');
    const openAppBtn = document.getElementById('openAppBtn');
    const successMsg = document.getElementById('successMsg');
    const errorMsg = document.getElementById('errorMsg');

    // Input fields
    const companyInput = document.getElementById('companyInput');
    const roleInput = document.getElementById('roleInput');
    const locationInput = document.getElementById('locationInput');

    // Get current tab
    let tab;
    try {
        [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    } catch (e) {
        console.error('Error getting tab:', e);
    }

    if (!tab) {
        statusBox.textContent = '⚠️ Cannot access page';
        return;
    }

    const url = tab.url;
    console.log('Current URL:', url);

    // Try to extract job info from page
    let jobDetected = false;

    // Check if on supported site
    const isSupported = url.includes('linkedin.com') ||
                       url.includes('indeed.com') ||
                       url.includes('glassdoor.com');

    if (isSupported) {
        try {
            // Inject extraction script
            const results = await chrome.scripting.executeScript({
                target: { tabId: tab.id },
                func: extractFromPage
            });

            const info = results[0]?.result;
            console.log('Extracted:', info);

            if (info && (info.company || info.role)) {
                companyInput.value = info.company || '';
                roleInput.value = info.role || '';
                locationInput.value = info.location || '';
                jobDetected = true;
                statusBox.textContent = '✓ Job detected!';
                statusBox.className = 'status detected';
                jobForm.style.display = 'block';
                captureBtn.disabled = false;
            }
        } catch (e) {
            console.log('Extraction failed:', e);
        }
    }

    if (!jobDetected) {
        statusBox.textContent = isSupported
            ? 'ℹ️ Fill in job details below'
            : '⚠️ Navigate to a job site';
        statusBox.className = 'status not-detected';
        jobForm.style.display = 'block';
        captureBtn.disabled = false;
    }

    // Check backend connectivity first
    async function checkBackend() {
        try {
            const response = await fetch('http://127.0.0.1:8000/health', {
                method: 'GET',
                headers: { 'Accept': 'application/json' }
            });
            return response.ok;
        } catch (e) {
            console.error('Backend check failed:', e);
            return false;
        }
    }

    // Capture button handler
    captureBtn.addEventListener('click', async () => {
        const company = companyInput.value.trim();
        const role = roleInput.value.trim();
        const location = locationInput.value.trim();

        if (!company || !role) {
            showError('Please enter company and job title');
            return;
        }

        captureBtn.disabled = true;
        captureBtn.textContent = 'Checking...';

        // Check if backend is accessible
        const backendOk = await checkBackend();
        if (!backendOk) {
            showError('Cannot connect to ANT app. Make sure it\'s running on http://127.0.0.1:8000');
            captureBtn.disabled = false;
            captureBtn.textContent = 'Capture Job';
            return;
        }

        captureBtn.textContent = 'Saving...';

        try {
            const params = new URLSearchParams();
            params.append('company', company);
            params.append('role', role);
            params.append('status', 'saved');
            if (location) params.append('location', location);
            if (url) params.append('job_url', url);

            console.log('[ANT] Saving job:', { company, role, location, url });

            const response = await fetch(`http://127.0.0.1:8000/job-tracker/application?${params.toString()}`, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json'
                }
            });

            if (!response.ok) {
                const text = await response.text();
                throw new Error(`HTTP ${response.status}: ${text}`);
            }

            const result = await response.json();

            if (result.success) {
                successMsg.style.display = 'block';
                errorMsg.style.display = 'none';
                captureBtn.textContent = '✓ Captured!';
                setTimeout(() => window.close(), 1500);
            } else {
                throw new Error(result.error || 'Unknown error');
            }
        } catch (error) {
            console.error('Save error:', error);
            showError(`Failed to save: ${error.message}. Make sure ANT is running.`);
            captureBtn.disabled = false;
            captureBtn.textContent = 'Capture Job';
        }
    });

    // Open app button
    openAppBtn.addEventListener('click', () => {
        chrome.tabs.create({ url: 'http://127.0.0.1:8000' });
    });

    function showError(msg) {
        errorMsg.textContent = msg;
        errorMsg.style.display = 'block';
        successMsg.style.display = 'none';
    }
});

// Function to run in page context
function extractFromPage() {
    const url = window.location.href;
    let company = '', role = '', location = '';

    // Strategy 1: Meta tags
    const metaTitle = document.querySelector('meta[property="og:title"]');
    if (metaTitle) {
        const content = metaTitle.getAttribute('content');
        if (content) {
            if (content.includes(' at ')) {
                const parts = content.split(' at ');
                role = parts[0].trim();
                company = parts[1].split(' - ')[0].trim();
            } else if (content.includes(' Jobs')) {
                role = content.replace(' Jobs', '').trim();
            }
        }
    }

    // Strategy 2: H1 title
    if (!role) {
        const h1 = document.querySelector('h1');
        if (h1) role = h1.textContent.trim();
    }

    // Strategy 3: Page title
    if (!role) {
        const title = document.title;
        if (title.includes(' at ')) {
            const parts = title.split(' at ');
            role = parts[0].trim();
            company = parts[1].split(' - ')[0].trim();
        }
    }

    // Strategy 4: Look for common job selectors
    if (!company) {
        const companySelectors = [
            '.employerName', '[data-test="employer-name"]',
            '[data-testid="company-name"]', '.company-name',
            'a[href*="company"]', 'a[href*="employer"]'
        ];
        for (const sel of companySelectors) {
            const el = document.querySelector(sel);
            if (el) {
                company = el.textContent.trim();
                break;
            }
        }
    }

    // Strategy 5: Look for job title
    if (!role) {
        const titleSelectors = [
            '.jobTitle', '[data-test="job-title"]',
            '[data-testid="job-title"]', '[class*="job-title"]'
        ];
        for (const sel of titleSelectors) {
            const el = document.querySelector(sel);
            if (el) {
                role = el.textContent.trim();
                break;
            }
        }
    }

    // Strategy 6: Location
    const locSelectors = [
        '[data-test="location"]', '[data-testid="location"]',
        '.location', '[class*="location"]'
    ];
    for (const sel of locSelectors) {
        const el = document.querySelector(sel);
        if (el) {
            location = el.textContent.trim();
            break;
        }
    }

    return { company, role, location };
}
