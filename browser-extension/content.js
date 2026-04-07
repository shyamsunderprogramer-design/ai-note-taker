/**
 * Content Script - Injected into job board pages
 * Adds capture button to job listings
 */

(function() {
    'use strict';

    console.log('[ANT] Content script loaded:', window.location.href);

    // Prevent duplicate injection
    if (window.antExtensionLoaded) {
        console.log('[ANT] Already loaded, skipping');
        return;
    }
    window.antExtensionLoaded = true;

    const url = window.location.href;
    let board = null;
    let pageType = 'detail';

    // Detect board and page type (broader matching)
    if (url.includes('linkedin.com')) {
        board = 'linkedin';
        if (url.includes('/jobs/') || url.includes('/job/')) {
            pageType = 'job';
        }
    } else if (url.includes('indeed.com')) {
        board = 'indeed';
        if (url.includes('/viewjob') || url.includes('jk=')) {
            pageType = 'job';
        }
    } else if (url.includes('glassdoor.com')) {
        board = 'glassdoor';
        if (url.includes('savedJobActivity') || url.includes('savedJob')) {
            pageType = 'saved-list';
        } else if (url.includes('appliedJobActivity')) {
            pageType = 'applied-list';
        } else if (url.includes('/Job/') && url.includes('SRCH')) {
            pageType = 'search';
        } else if (url.includes('/Job/')) {
            pageType = 'job';
        }
    } else if (url.includes('icims.com')) {
        board = 'icims';
        if (url.includes('/jobs/') || url.includes('mode=submit_apply')) {
            pageType = 'job';
        }
    } else if (url.includes('greenhouse.io')) {
        board = 'greenhouse';
        pageType = 'job';
    } else if (url.includes('lever.co')) {
        board = 'lever';
        pageType = 'job';
    } else if (url.includes('workday.com') || url.includes('myworkday')) {
        board = 'workday';
        pageType = 'job';
    } else if (url.includes('ashbyhq.com')) {
        board = 'ashby';
        pageType = 'job';
    } else {
        // Generic job site detection
        board = 'generic';
        pageType = 'job';
    }

    console.log('[ANT] Board:', board, 'Type:', pageType);

    console.log('[ANT] Board:', board, 'Type:', pageType);

    let buttonContainer = null;
    let retryCount = 0;
    const MAX_RETRIES = 5;

    // Create floating button with Shadow DOM for isolation
    function createButton() {
        // Check if already exists
        if (document.getElementById('ant-extension-root')) {
            console.log('[ANT] Button already exists');
            return;
        }

        // Wait for body to be available
        if (!document.body) {
            console.log('[ANT] Body not ready, retrying...');
            if (retryCount < MAX_RETRIES) {
                retryCount++;
                setTimeout(createButton, 500);
            }
            return;
        }

        try {
            // Create container with Shadow DOM
            buttonContainer = document.createElement('div');
            buttonContainer.id = 'ant-extension-root';
            buttonContainer.style.cssText = `
                position: fixed !important;
                bottom: 20px !important;
                right: 20px !important;
                z-index: 2147483647 !important;
                pointer-events: none !important;
            `;

            // Create shadow root for isolation
            const shadow = buttonContainer.attachShadow({ mode: 'open' });

            // Create button inside shadow DOM
            const btn = document.createElement('button');
            btn.id = 'ant-capture-btn';
            btn.innerHTML = '🐜 Save Job';
            btn.style.cssText = `
                pointer-events: auto !important;
                background: linear-gradient(135deg, #10b981, #3b82f6) !important;
                color: white !important;
                border: none !important;
                padding: 12px 20px !important;
                border-radius: 8px !important;
                font-weight: 600 !important;
                font-size: 14px !important;
                cursor: pointer !important;
                box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif !important;
                transition: all 0.2s !important;
            `;

            // Hover effects
            btn.addEventListener('mouseenter', () => {
                btn.style.transform = 'translateY(-2px)';
                btn.style.boxShadow = '0 6px 16px rgba(0,0,0,0.4) !important';
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.transform = 'none';
                btn.style.boxShadow = '0 4px 12px rgba(0,0,0,0.3) !important';
            });

            btn.addEventListener('click', handleClick);

            shadow.appendChild(btn);
            document.body.appendChild(buttonContainer);
            console.log('[ANT] Button added to page');

            // Start watchdog to ensure button stays
            startWatchdog();

        } catch (e) {
            console.error('[ANT] Error creating button:', e);
        }
    }

    // Watchdog to keep button alive
    function startWatchdog() {
        setInterval(() => {
            if (!document.getElementById('ant-extension-root')) {
                console.log('[ANT] Button missing, recreating...');
                createButton();
            }
        }, 2000);
    }

    async function handleClick(e) {
        e.stopPropagation();
        e.preventDefault();

        const root = document.getElementById('ant-extension-root');
        if (!root) return;
        const shadow = root.shadowRoot;
        const btn = shadow.getElementById('ant-capture-btn');

        const info = extractJobInfo();
        console.log('[ANT] Extracted:', info);

        if (info.company && info.role) {
            await saveJob(info, btn);
        } else {
            showInlineForm(btn);
        }
    }

    function extractJobInfo() {
        let company = '', role = '', location = '';

        // Board-specific extraction strategies
        const boardStrategies = {
            linkedin: [
                // LinkedIn job page - new design
                () => {
                    // Company name from header
                    const companySelectors = [
                        '.job-details-jobs-unified-top-card__company-name a',
                        '.job-details-jobs-unified-top-card__company-name',
                        '.artdeco-entity-lockup__title',
                        'a[href*="/company/"]',
                        '[data-test-job-title] + div a'
                    ];
                    for (const sel of companySelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            company = el.textContent.trim();
                            break;
                        }
                    }

                    // Job title
                    const titleSelectors = [
                        'h1.job-details-jobs-unified-top-card__job-title',
                        'h1.t-24',
                        '.job-details-jobs-unified-top-card__job-title',
                        '[data-test-job-title]',
                        'h1:not(.visually-hidden)'
                    ];
                    for (const sel of titleSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            role = el.textContent.trim();
                            break;
                        }
                    }

                    // Location
                    const locSelectors = [
                        '.job-details-jobs-unified-top-card__primary-description-container span',
                        '.job-details-jobs-unified-top-card__job-insight span',
                        '[data-test-job-location]'
                    ];
                    for (const sel of locSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            const text = el.textContent.trim();
                            if (text.includes(',') || /remote|hybrid|onsite/i.test(text)) {
                                location = text;
                                break;
                            }
                        }
                    }
                }
            ],
            glassdoor: [
                () => {
                    // Company - look for employer name, clean up ratings
                    const companySelectors = [
                        '[data-test="employer-name"]',
                        '.employerName',
                        'a[href*="/Overview/"]',
                        '.company-header a',
                        '.JobDetails_jobDetailsHeader__zBiga h2 a',
                        '[class*="employerName"]'
                    ];
                    for (const sel of companySelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            // Clean up company name - remove ratings like "4.1", "3.5", etc.
                            let text = el.textContent.trim();
                            // Remove rating patterns (number.number at end)
                            company = text.replace(/\s*\d+\.\d+$/, '').trim();
                            break;
                        }
                    }

                    // Title
                    const titleSelectors = [
                        '[data-test="job-title"]',
                        '.job-title',
                        '.JobDetails_jobDetailsHeader__zBiga h1',
                        'h1',
                        '.job-details-header h1'
                    ];
                    for (const sel of titleSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            role = el.textContent.trim();
                            break;
                        }
                    }

                    // Location
                    const locSelectors = [
                        '[data-test="location"]',
                        '.location',
                        '.JobDetails_location__6ZrYg',
                        '[class*="location"]'
                    ];
                    for (const sel of locSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            location = el.textContent.trim();
                            break;
                        }
                    }
                }
            ],
            indeed: [
                () => {
                    // Company
                    const companySelectors = [
                        '[data-testid="company-name"]',
                        '.company-name',
                        'a[href*="/cmp/"]',
                        '[data-testid="job-detail-header"] div',
                        '.jobsearch-CompanyInfoContainer a'
                    ];
                    for (const sel of companySelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            company = el.textContent.trim();
                            break;
                        }
                    }

                    // Title
                    const titleSelectors = [
                        'h1[data-testid="job-title"]',
                        'h1.jobsearch-JobInfoHeader-title',
                        'h1:not(.visually-hidden)',
                        '.jobsearch-JobInfoHeader-title'
                    ];
                    for (const sel of titleSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            role = el.textContent.trim();
                            break;
                        }
                    }

                    // Location
                    const locSelectors = [
                        '[data-testid="job-location"]',
                        '.job-location',
                        '[data-testid="job-detail-header"] span'
                    ];
                    for (const sel of locSelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            location = el.textContent.trim();
                            break;
                        }
                    }
                }
            ],
            icims: [
                () => {
                    // iCIMS specific extraction
                    // Company from logo or header
                    const companySelectors = [
                        '.iCIMS_Header img[alt]',
                        '.iCIMS_JobsHeader h1',
                        'header h1',
                        '.company-name',
                        '[class*="company"] h1',
                        '[class*="Company"]',
                        '.iCIMS_Header_Logo + div',
                        'img[alt*="logo"]'
                    ];
                    for (const sel of companySelectors) {
                        const el = document.querySelector(sel);
                        if (el) {
                            if (el.tagName === 'IMG') {
                                company = el.alt.replace(/\s*logo\s*/i, '').trim();
                            } else {
                                company = el.textContent.trim();
                            }
                            break;
                        }
                    }

                    // Job title - iCIMS typically has job title in h1
                    const titleSelectors = [
                        '.iCIMS_JobsHeader h1',
                        '.iCIMS_JobHeader h1',
                        '.iCIMS_Header h2',
                        'h1.iCIMS_JobHeaderTitle',
                        '.job-title h1',
                        'header h2',
                        'h1[class*="job"]',
                        'h1[class*="Job"]',
                        'h1',
                        'h2[class*="title"]'
                    ];
                    for (const sel of titleSelectors) {
                        const el = document.querySelector(sel);
                        if (el && el.textContent.trim()) {
                            role = el.textContent.trim();
                            break;
                        }
                    }

                    // Location - iCIMS uses specific classes
                    const locSelectors = [
                        '.iCIMS_JobHeaderField:contains("Location") + .iCIMS_JobHeaderData',
                        '[data-field="location"]',
                        '.iCIMS_Location',
                        '[class*="location"]',
                        '[class*="Location"]'
                    ];
                    for (const sel of locSelectors) {
                        if (sel.includes(':contains')) {
                            // jQuery-style selector not supported, skip
                            continue;
                        }
                        const el = document.querySelector(sel);
                        if (el) {
                            location = el.textContent.trim();
                            break;
                        }
                    }

                    // Alternative: look for labels containing "Location"
                    if (!location) {
                        const labels = document.querySelectorAll('label, dt, .iCIMS_JobHeaderField');
                        for (const label of labels) {
                            if (/location/i.test(label.textContent)) {
                                const parent = label.closest('div, dl, .iCIMS_JobHeaderField');
                                if (parent) {
                                    const nextEl = parent.querySelector('.iCIMS_JobHeaderData, dd, + div');
                                    if (nextEl) {
                                        location = nextEl.textContent.trim();
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }
            ]
        };

        // Run board-specific strategies
        if (boardStrategies[board]) {
            for (const strategy of boardStrategies[board]) {
                strategy();
                if (company && role) break;
            }
        }

        // Generic fallback strategies - comprehensive for any job site
        const fallbackStrategies = [
            // Meta tags - Open Graph
            () => {
                const metaTitle = document.querySelector('meta[property="og:title"], meta[name="twitter:title"]');
                if (metaTitle) {
                    const content = metaTitle.getAttribute('content');
                    if (content) {
                        if (content.includes(' at ')) {
                            const parts = content.split(' at ');
                            role = parts[0].trim();
                            company = parts[1].split(' - ')[0].trim();
                        } else if (content.includes(' Jobs')) {
                            role = content.replace(' Jobs', '').trim();
                        } else if (content.includes(' | ')) {
                            const parts = content.split(' | ');
                            role = parts[0].trim();
                            if (parts[1] && !company) company = parts[1].trim();
                        }
                    }
                }
            },
            // Meta description
            () => {
                const metaDesc = document.querySelector('meta[property="og:description"], meta[name="description"]');
                if (metaDesc && !company) {
                    const content = metaDesc.getAttribute('content');
                    if (content) {
                        // Look for "at Company" or "Company is" patterns
                        const atMatch = content.match(/at\s+([A-Z][A-Za-z0-9\s]+?)(?:\s*[.\-]|$)/);
                        if (atMatch) company = atMatch[1].trim();
                    }
                }
            },
            // Page title patterns
            () => {
                const title = document.title;
                if (title.includes(' at ')) {
                    const parts = title.split(' at ');
                    role = parts[0].trim();
                    company = parts[1].split(' - ')[0].trim();
                } else if (title.includes(' Jobs')) {
                    role = title.replace(' Jobs', '').trim();
                } else if (title.includes(' | ')) {
                    const parts = title.split(' | ');
                    if (parts.length >= 2) {
                        role = parts[0].trim();
                        company = parts[parts.length - 1].trim().replace(/Careers|Jobs|Hiring/gi, '').trim();
                    }
                } else if (title.includes(' - ')) {
                    const parts = title.split(' - ');
                    if (parts.length >= 2) {
                        role = parts[0].trim();
                        company = parts[parts.length - 1].trim().replace(/Careers|Jobs|Hiring/gi, '').trim();
                    }
                } else if (title.includes(' with ')) {
                    const parts = title.split(' with ');
                    role = parts[0].trim();
                    if (parts[1]) company = parts[1].split(' - ')[0].trim();
                }
            },
            // Generic h1/h2 - look for job titles
            () => {
                if (!role) {
                    const h1 = document.querySelector('h1:not(.visually-hidden):not([class*="logo"])');
                    if (h1) {
                        const text = h1.textContent.trim();
                        // Filter out short text and generic titles
                        if (text.length > 5 && text.length < 150 &&
                            !/careers|jobs|home|welcome/i.test(text)) {
                            role = text;
                        }
                    }
                }
            },
            // Look for company in header/footer/structured data
            () => {
                if (!company) {
                    // Schema.org JSON-LD
                    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
                    for (const script of scripts) {
                        try {
                            const data = JSON.parse(script.textContent);
                            if (data.hiringOrganization?.name) {
                                company = data.hiringOrganization.name;
                            } else if (data.jobLocation?.name && !location) {
                                location = data.jobLocation.name;
                            }
                        } catch (e) {}
                    }
                }
            },
            // Look for labels/headings that indicate job info
            () => {
                const headings = document.querySelectorAll('h1, h2, h3, h4, .job-title, .jobTitle, [class*="job-title"], [class*="JobTitle"]');
                for (const h of headings) {
                    const text = h.textContent.trim();
                    if (text.length > 5 && text.length < 100 && !role) {
                        role = text;
                        break;
                    }
                }
            },
            // Look for company in common patterns
            () => {
                if (!company) {
                    // Look for company name near apply button
                    const applyBtn = document.querySelector('button:contains("Apply"), .apply-button, [class*="apply"], [class*="Apply"]');
                    if (applyBtn) {
                        const parent = applyBtn.closest('div, section, article');
                        if (parent) {
                            const companyEl = parent.querySelector('[class*="company"], [class*="Company"], [class*="employer"], [class*="Employer"]');
                            if (companyEl) company = companyEl.textContent.trim();
                        }
                    }
                }
            },
            // Look for location
            () => {
                if (!location) {
                    const locElements = document.querySelectorAll('[class*="location"], [class*="Location"], [data-field*="location"], [class*="address"]');
                    for (const el of locElements) {
                        const text = el.textContent.trim();
                        if (text.length > 3 && (text.includes(',') || /remote|hybrid|onsite|hybrid/i.test(text))) {
                            location = text;
                            break;
                        }
                    }
                }
            }
        ];

        // Run fallback strategies if needed
        if (!company || !role) {
            for (const strategy of fallbackStrategies) {
                strategy();
                if (company && role) break;
            }
        }

        return { company, role, location };
    }

    function showInlineForm(btn) {
        const root = document.getElementById('ant-extension-root');
        if (!root) return;
        const shadow = root.shadowRoot;

        // Remove existing form
        const existing = shadow.getElementById('ant-inline-form');
        if (existing) existing.remove();

        const form = document.createElement('div');
        form.id = 'ant-inline-form';
        form.style.cssText = `
            background: #1a1a1a !important;
            border: 2px solid #10b981 !important;
            border-radius: 12px !important;
            padding: 20px !important;
            width: 300px !important;
            margin-bottom: 10px !important;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
            pointer-events: auto !important;
        `;

        form.innerHTML = `
            <div style="font-weight: 600; margin-bottom: 15px; color: #10b981;">Quick Add Job</div>
            <input type="text" id="ant-company" placeholder="Company *"
                style="width: 100%; padding: 10px; margin-bottom: 10px; background: #0a0a0a; border: 1px solid #333; border-radius: 6px; color: white; box-sizing: border-box; font-family: inherit;">
            <input type="text" id="ant-role" placeholder="Job Title *"
                style="width: 100%; padding: 10px; margin-bottom: 10px; background: #0a0a0a; border: 1px solid #333; border-radius: 6px; color: white; box-sizing: border-box; font-family: inherit;">
            <input type="text" id="ant-location" placeholder="Location"
                style="width: 100%; padding: 10px; margin-bottom: 15px; background: #0a0a0a; border: 1px solid #333; border-radius: 6px; color: white; box-sizing: border-box; font-family: inherit;">
            <div style="display: flex; gap: 10px;">
                <button id="ant-save"
                    style="flex: 1; background: linear-gradient(135deg, #10b981, #3b82f6); color: white; border: none; padding: 10px; border-radius: 6px; cursor: pointer; font-weight: 600; font-family: inherit;">
                    Save to Tracker
                </button>
                <button id="ant-cancel"
                    style="background: #333; color: white; border: none; padding: 10px 15px; border-radius: 6px; cursor: pointer; font-family: inherit;">
                    Cancel
                </button>
            </div>
        `;

        shadow.insertBefore(form, btn);
        btn.style.display = 'none';

        // Focus company
        setTimeout(() => {
            const companyInput = shadow.getElementById('ant-company');
            if (companyInput) companyInput.focus();
        }, 100);

        // Save handler
        shadow.getElementById('ant-save').addEventListener('click', async () => {
            const company = shadow.getElementById('ant-company').value.trim();
            const role = shadow.getElementById('ant-role').value.trim();
            const location = shadow.getElementById('ant-location').value.trim();

            if (!company || !role) {
                alert('Please fill in company and job title');
                return;
            }

            form.remove();
            btn.style.display = 'block';
            await saveJob({ company, role, location }, btn);
        });

        // Cancel handler
        shadow.getElementById('ant-cancel').addEventListener('click', () => {
            form.remove();
            btn.style.display = 'block';
        });
    }

    async function saveJob(info, btn) {
        const originalText = btn.textContent;
        btn.textContent = 'Saving...';
        btn.disabled = true;
        btn.style.opacity = '0.8';

        try {
            // Clean up data
            const cleanCompany = info.company.replace(/\s+/g, ' ').trim();
            const cleanRole = info.role.replace(/\s+/g, ' ').trim();
            const cleanLocation = info.location ? info.location.replace(/\s+/g, ' ').trim() : '';

            const params = new URLSearchParams();
            params.append('company', cleanCompany);
            params.append('role', cleanRole);
            params.append('status', 'saved');
            if (cleanLocation) params.append('location', cleanLocation);
            if (url) params.append('job_url', url);

            console.log('[ANT] Saving job:', { company: cleanCompany, role: cleanRole, location: cleanLocation });

            const response = await fetch(`http://127.0.0.1:8000/job-tracker/application?${params.toString()}`, {
                method: 'POST',
                headers: {
                    'Accept': 'application/json'
                }
            });

            console.log('[ANT] Response status:', response.status);

            if (!response.ok) {
                const text = await response.text();
                console.error('[ANT] Error response:', text);
                throw new Error(`HTTP ${response.status}: ${text}`);
            }

            const result = await response.json();
            console.log('[ANT] Save result:', result);

            if (result.success) {
                btn.textContent = '✓ Saved!';
                btn.style.background = '#10b981';
                setTimeout(() => {
                    btn.textContent = originalText;
                    btn.style.background = 'linear-gradient(135deg, #10b981, #3b82f6)';
                    btn.disabled = false;
                    btn.style.opacity = '1';
                }, 2000);
            } else {
                throw new Error(result.error || 'Unknown error');
            }
        } catch (e) {
            console.error('[ANT] Save error:', e);
            btn.textContent = '❌ Error';
            btn.style.background = '#ef4444';
            btn.disabled = false;
            btn.style.opacity = '1';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = 'linear-gradient(135deg, #10b981, #3b82f6)';
            }, 3000);
            alert(`Failed to save: ${e.message}. Make sure ANT app is running on port 8000.`);
        }
    }

    // Initialize with retry logic
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                setTimeout(createButton, 500);
            });
        } else {
            createButton();
        }

        // Multiple retry attempts
        setTimeout(createButton, 1000);
        setTimeout(createButton, 2000);
        setTimeout(createButton, 3000);
    }

    init();

    // Re-init on URL change (SPA navigation)
    let lastUrl = location.href;
    new MutationObserver(() => {
        if (location.href !== lastUrl) {
            lastUrl = location.href;
            console.log('[ANT] URL changed, recreating button');
            setTimeout(createButton, 1500);
        }
    }).observe(document, { subtree: true, childList: true });

})();
