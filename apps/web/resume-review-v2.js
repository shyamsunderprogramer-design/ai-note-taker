/**
 * Resume Review V2 - Enhanced UI
 * Features: Recruiter scan, ATS dashboard, benchmarking, interview prep, gamification
 * Free tier: All core features included
 */

class ResumeReviewV2 {
    constructor() {
        this.apiUrl = 'http://127.0.0.1:8000';
        this.uploadedFile = null;
        this.currentAnalysis = null;
        this.setupDragDrop();
    }

    setupDragDrop() {
        const uploadArea = document.getElementById('fileUploadArea');
        if (!uploadArea) return;

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                this.processFile(files[0]);
            }
        });
    }

    handleFileUpload(input) {
        if (input.files && input.files[0]) {
            this.processFile(input.files[0]);
        }
    }

    processFile(file) {
        const allowedTypes = ['.pdf', '.docx', '.doc', '.txt', '.md', '.rtf'];
        const fileName = file.name.toLowerCase();

        if (!allowedTypes.some(ext => fileName.endsWith(ext))) {
            this.showNotification('Unsupported file type. Please upload PDF, DOCX, TXT, MD, or RTF files.', 'error');
            return;
        }

        if (file.size > 10 * 1024 * 1024) {
            this.showNotification('File too large. Maximum size is 10MB.', 'error');
            return;
        }

        this.uploadedFile = file;

        const fileInfo = document.getElementById('fileInfo');
        fileInfo.innerHTML = `
            <span class="file-info-name">📄 ${file.name}</span>
            <span class="file-info-size">${(file.size / 1024).toFixed(1)} KB</span>
            <button class="file-remove-btn" onclick="resumeReviewV2.removeFile()">Remove</button>
        `;
        fileInfo.classList.remove('hidden');
        document.getElementById('resumeInput').placeholder = 'File uploaded. Resume text will be extracted automatically.';
    }

    removeFile() {
        this.uploadedFile = null;
        document.getElementById('fileInfo').classList.add('hidden');
        document.getElementById('resumeFile').value = '';
        document.getElementById('resumeInput').placeholder = 'Paste your resume content here...';
    }

    async analyze() {
        const resumeText = document.getElementById('resumeInput').value.trim();
        const jobDesc = document.getElementById('jobInput').value.trim();
        const analyzeBtn = document.getElementById('analyzeBtn');

        if (!this.uploadedFile && !resumeText) {
            this.showNotification('Please upload a resume file or paste your resume text', 'error');
            return;
        }

        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML = '<span class="spinner"></span> Analyzing...';
        document.getElementById('loadingState').classList.remove('hidden');
        document.getElementById('emptyState').classList.add('hidden');
        document.getElementById('resultsContent').classList.add('hidden');

        try {
            let data;

            if (this.uploadedFile) {
                const formData = new FormData();
                formData.append('file', this.uploadedFile);
                if (jobDesc) formData.append('job_description', jobDesc);

                const response = await fetch(`${this.apiUrl}/resume/analyze-v2`, {
                    method: 'POST',
                    body: formData
                });
                data = await response.json();
            } else {
                const response = await fetch(`${this.apiUrl}/resume/analyze-v2`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        resume_text: resumeText,
                        job_description: jobDesc || null
                    })
                });
                data = await response.json();
            }

            if (data.error) {
                throw new Error(data.error);
            }

            this.currentAnalysis = data;
            this.displayResultsV2(data);

            // Show free tier notification
            this.showNotification('✨ Free analysis complete! Unlock Pro for unlimited rewrites & video resumes.', 'info');

        } catch (error) {
            console.error('Error analyzing resume:', error);
            this.showNotification('Error: ' + error.message, 'error');
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Analyze Resume';
            document.getElementById('loadingState').classList.add('hidden');
        }
    }

    displayResultsV2(data) {
        const analysis = data.analysis;

        // Overall Score Card with Callback Probability
        document.getElementById('overallScore').textContent = analysis.overall_score;
        document.getElementById('semanticFit').textContent = analysis.semantic_fit_score
            ? `AI Match: ${analysis.semantic_fit_score}%`
            : '';

        // Callback probability
        if (analysis.callback_probability) {
            document.getElementById('callbackProbability').innerHTML = `
                <div class="callback-prediction">
                    <span class="probability-value">${analysis.callback_probability.current}</span>
                    <span class="probability-label">Estimated Callback Rate</span>
                    <span class="probability-comparison">vs ${analysis.callback_probability.industry_average} industry average</span>
                </div>
            `;
        }

        // Section Scores
        const sectionScoresEl = document.getElementById('sectionScores');
        if (analysis.section_scores) {
            sectionScoresEl.innerHTML = Object.entries(analysis.section_scores)
                .map(([section, score]) => `
                    <div class="section-score-item">
                        <div class="section-score-value" style="color: ${this.getScoreColor(score)}">${score}</div>
                        <div class="section-score-label">${this.capitalize(section)}</div>
                    </div>
                `).join('';
        }

        // 🔥 RECRUITER SCAN SIMULATOR (Free Feature)
        if (analysis.recruiter_scan) {
            this.renderRecruiterScan(analysis.recruiter_scan);
        }

        // 🔥 ATS COMPATIBILITY DASHBOARD (Free Feature)
        if (analysis.ats_compatibility) {
            this.renderATSDashboard(analysis.ats_compatibility);
        }

        // 🔥 COMPETITIVE BENCHMARKING (Free Feature)
        if (analysis.benchmark) {
            this.renderBenchmark(analysis.benchmark);
        }

        // 🔥 CONTENT QUALITY METRICS (Free Feature)
        if (analysis.content_quality) {
            this.renderContentQuality(analysis.content_quality);
        }

        // 🔥 INTERVIEW PREDICTOR (Free Feature - 5 questions)
        if (analysis.interview_prep) {
            this.renderInterviewPrep(analysis.interview_prep);
        }

        // 🔥 GAMIFICATION (Free Feature)
        if (analysis.badges) {
            this.renderBadges(analysis.badges);
        }

        if (analysis.active_quests) {
            this.renderQuests(analysis.active_quests);
        }

        // Existing features
        this.renderRewrites(analysis.rewrites);
        this.renderKeywords(analysis);
        this.renderStrengths(analysis.strengths);
        this.renderImprovements(analysis.improvements);

        // Show results
        document.getElementById('resultsContent').classList.remove('hidden');

        // Scroll to results
        document.getElementById('resultsContent').scrollIntoView({ behavior: 'smooth' });
    }

    // 🔥 RENDER RECRUITER SCAN SIMULATOR
    renderRecruiterScan(scan) {
        const container = document.getElementById('recruiterScanSection');
        if (!container) return;

        const visibleInfo = Object.entries(scan.visible_info || {})
            .map(([key, value]) => `
                <div class="visible-item">
                    <span class="visible-label">${this.capitalize(key)}:</span>
                    <span class="visible-value">${Array.isArray(value) ? value.join(', ') : value}</span>
                </div>
            `).join('');

        container.innerHTML = `
            <div class="dashboard-card recruiter-scan-card">
                <div class="card-title">
                    👁️ Recruiter Scan Simulator
                    <span class="scan-time">${scan.time_to_key_info}</span>
                </div>
                <div class="scan-description">
                    This is what recruiters see in the first ${scan.time_to_key_info || '6 seconds'}
                </div>

                <div class="scan-content">
                    <div class="visible-section">
                        <h4>✅ Immediately Visible</h4>
                        ${visibleInfo || '<p class="no-data">Upload resume to see scan simulation</p>'}
                    </div>

                    <div class="hidden-section">
                        <h4>⚠️ Often Missed</h4>
                        <ul class="hidden-list">
                            ${(scan.hidden_info || []).map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    </div>
                </div>

                <div class="scan-metrics">
                    <div class="scan-metric">
                        <span class="metric-value">${scan.scanability_score || 70}</span>
                        <span class="metric-label">Scanability Score</span>
                    </div>
                    <div class="scan-metric">
                        <span class="metric-value">${scan.first_impression || 'Good'}</span>
                        <span class="metric-label">First Impression</span>
                    </div>
                </div>

                ${scan.red_flags_visible?.length ? `
                    <div class="red-flags">
                        <h4>🚩 Red Flags Detected</h4>
                        ${scan.red_flags_visible.map(f => `<div class="flag">${f}</div>`).join('')}
                    </div>
                ` : ''}

                <div class="scan-tip">
                    💡 <strong>Tip:</strong> Put your most impressive achievements at the top - recruiters spend 80% of their time on the top third of your resume.
                </div>
            </div>
        `;
    }

    // 🔥 RENDER ATS DASHBOARD
    renderATSDashboard(ats) {
        const container = document.getElementById('atsDashboardSection');
        if (!container) return;

        const systemScores = Object.entries(ats.system_specific_scores || {})
            .map(([system, score]) => `
                <div class="ats-system" data-score="${score}">
                    <span class="system-name">${system}</span>
                    <div class="system-bar">
                        <div class="system-fill" style="width: ${score}%; background: ${this.getScoreColor(score)}"></div>
                    </div>
                    <span class="system-score">${score}%</span>
                    <span class="system-status">${score >= 90 ? '✅' : score >= 75 ? '⚠️' : '❌'}</span>
                </div>
            `).join('');

        const tips = Object.entries(ats.system_tips || {})
            .map(([system, tipList]) => `
                <div class="ats-tip-item">
                    <strong>${system}:</strong> ${Array.isArray(tipList) ? tipList.join(', ') : tipList}
                </div>
            `).join('');

        container.innerHTML = `
            <div class="dashboard-card ats-dashboard-card">
                <div class="card-title">
                    🤖 ATS Compatibility (50+ Systems)
                    <span class="badge-free">FREE</span>
                </div>

                <div class="ats-overall">
                    <div class="ats-main-score">
                        <div class="score-circle" style="--score: ${ats.overall_score}">
                            <span class="score-value">${ats.overall_score}</span>
                        </div>
                        <span class="score-label">Overall Compatibility</span>
                    </div>
                    <div class="ats-parse-confidence">
                        <span class="confidence-value">${ats.parse_confidence}%</span>
                        <span class="confidence-label">Parse Confidence</span>
                        <span class="confidence-desc">Likelihood ATS can read your resume correctly</span>
                    </div>
                </div>

                <div class="ats-systems">
                    <h4>System-Specific Scores</h4>
                    ${systemScores}
                </div>

                ${ats.format_issues?.length ? `
                    <div class="ats-issues">
                        <h4>⚠️ Formatting Issues</h4>
                        ${ats.format_issues.map(i => `<div class="issue-item">${i}</div>`).join('')}
                    </div>
                ` : ''}

                <div class="ats-tips">
                    <h4>💡 System-Specific Tips</h4>
                    ${tips}
                </div>

                <div class="ats-legend">
                    <span><span class="legend-dot" style="background: #10b981"></span> Excellent (90%+)</span>
                    <span><span class="legend-dot" style="background: #f59e0b"></span> Good (75-89%)</span>
                    <span><span class="legend-dot" style="background: #ef4444"></span> Needs Work (&lt;75%)</span>
                </div>
            </div>
        `;
    }

    // 🔥 RENDER COMPETITIVE BENCHMARKING
    renderBenchmark(benchmark) {
        const container = document.getElementById('benchmarkSection');
        if (!container) return;

        const bellCurve = benchmark.bell_curve_data || {};
        const userScore = bellCurve.user || 70;
        const p90 = bellCurve.p90 || 90;
        const userPosition = (userScore / p90) * 100;

        const sectionPercentiles = Object.entries(benchmark.section_percentiles || {})
            .map(([section, percentile]) => `
                <div class="section-percentile">
                    <span class="section-name">${this.capitalize(section)}</span>
                    <div class="percentile-bar">
                        <div class="percentile-fill" style="width: ${percentile}%"></div>
                    </div>
                    <span class="percentile-value">${percentile}th</span>
                </div>
            `).join('');

        const gaps = (benchmark.gaps_vs_top_10_percent || [])
            .map(g => `<li>${g}</li>`).join('') || '<li>Keep up the great work!</li>';

        container.innerHTML = `
            <div class="dashboard-card benchmark-card">
                <div class="card-title">
                    📊 Competitive Benchmark
                    <span class="badge-free">FREE</span>
                </div>

                <div class="percentile-rank">
                    <div class="rank-badge">
                        <span class="rank-percentile">${benchmark.percentile_rank}</span>
                        <span class="rank-label">th Percentile</span>
                    </div>
                    <div class="rank-description">
                        Your resume scores better than <strong>${benchmark.percentile_rank}%</strong> of ${benchmark.compared_to_role || 'similar'} candidates
                    </div>
                </div>

                <div class="bell-curve">
                    <h4>Distribution vs Peers</h4>
                    <div class="curve-container">
                        <div class="curve-line"></div>
                        <div class="curve-markers">
                            <span style="left: 25%">25th</span>
                            <span style="left: 50%">50th</span>
                            <span style="left: 75%">75th</span>
                            <span style="left: 90%">90th</span>
                        </div>
                        <div class="user-position" style="left: ${Math.min(userPosition, 95)}%">
                            <span class="position-marker">👤 You</span>
                            <span class="position-score">${userScore}</span>
                        </div>
                    </div>
                </div>

                <div class="section-percentiles">
                    <h4>Section Rankings</h4>
                    ${sectionPercentiles}
                </div>

                <div class="gaps-vs-top">
                    <h4>📈 Path to Top 10%</h4>
                    <ul>${gaps}</ul>
                </div>

                <div class="success-prediction">
                    <h4>🎯 Success Prediction</h4>
                    <div class="prediction-item">
                        <span>Estimated Callbacks:</span>
                        <strong>${benchmark.projected_success_rate?.estimated_callbacks || '2-4'} per 100 applications</strong>
                    </div>
                    <div class="prediction-item">
                        <span>Your Tier:</span>
                        <strong>${benchmark.projected_success_rate?.current_tier || 'Mid-tier'}</strong>
                    </div>
                </div>

                <div class="benchmark-cta">
                    <button class="btn-secondary" onclick="resumeReviewV2.shareScore()">
                        📤 Share Your Score
                    </button>
                    <span class="share-hint">Compare with friends!</span>
                </div>
            </div>
        `;
    }

    // 🔥 RENDER CONTENT QUALITY
    renderContentQuality(content) {
        const container = document.getElementById('contentQualitySection');
        if (!container) return;

        const verbTags = (content.action_verbs_used || [])
            .slice(0, 10)
            .map(v => `<span class="verb-tag">${v}</span>`)
            .join('');

        const repetitive = (content.repetitive_phrases || [])
            .map(p => `<div class="repetitive-item">
                <span class="phrase">"${p.phrase}"</span>
                <span class="count">used ${p.count} times</span>
            </div>`).join('') || '<p class="no-issues">No repetitive phrases detected!</p>';

        container.innerHTML = `
            <div class="dashboard-card content-quality-card">
                <div class="card-title">
                    ✍️ Content Quality Analysis
                    <span class="badge-free">FREE</span>
                </div>

                <div class="quality-metrics">
                    <div class="quality-metric">
                        <div class="metric-ring" style="--percent: ${content.quantification_score}">
                            <span class="ring-value">${content.quantification_score}%</span>
                        </div>
                        <span class="metric-name">Quantified</span>
                        <span class="metric-desc">Achievements with metrics</span>
                    </div>

                    <div class="quality-metric">
                        <div class="metric-ring" style="--percent: ${content.reading_level_score}">
                            <span class="ring-value">${content.reading_level_score}</span>
                        </div>
                        <span class="metric-name">Readability</span>
                        <span class="metric-desc">${content.reading_level}</span>
                    </div>

                    <div class="quality-metric">
                        <div class="metric-ring" style="--percent: ${Math.min(content.action_verb_diversity * 5, 100)}">
                            <span class="ring-value">${content.action_verb_diversity}</span>
                        </div>
                        <span class="metric-name">Verb Variety</span>
                        <span class="metric-desc">Unique action verbs</span>
                    </div>
                </div>

                <div class="action-verbs">
                    <h4>⚡ Action Verbs Used</h4>
                    <div class="verbs-cloud">${verbTags}</div>
                </div>

                <div class="word-stats">
                    <div class="stat">
                        <span class="stat-value">${content.word_count}</span>
                        <span class="stat-label">Total Words</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">${content.power_words_count}</span>
                        <span class="stat-label">Power Words</span>
                    </div>
                    <div class="stat">
                        <span class="stat-value">${content.passive_voice_count}</span>
                        <span class="stat-label">Passive Voice</span>
                    </div>
                </div>

                <div class="repetitive-phrases">
                    <h4>🔄 Repetitive Phrases</h4>
                    ${repetitive}
                </div>

                ${content.word_count > 750 ? `
                    <div class="word-count-warning">
                        ⚠️ Resume is ${content.word_count} words. Ideal range is ${content.ideal_word_count_range?.join('-')} words.
                    </div>
                ` : ''}
            </div>
        `;
    }

    // 🔥 RENDER INTERVIEW PREP (FREE: 5 Questions)
    renderInterviewPrep(questions) {
        const container = document.getElementById('interviewPrepSection');
        if (!container) return;

        const questionCards = questions.slice(0, 5).map((q, idx) => `
            <div class="question-card" data-type="${q.question_type}">
                <div class="question-header">
                    <span class="question-number">${idx + 1}</span>
                    <span class="question-type">${this.capitalize(q.question_type)}</span>
                    ${q.confidence_level ? `<span class="confidence-${q.confidence_level}">${q.confidence_level}</span>` : ''}
                </div>

                <div class="question-text">${q.question}</div>

                <div class="question-context">
                    <strong>Why they ask:</strong> ${q.why_asked || q.context}
                </div>

                <div class="preparation-tips">
                    <strong>💡 Preparation Tips:</strong>
                    <ul>${(q.preparation_tips || []).map(t => `<li>${t}</li>`).join('')}</ul>
                </div>

                ${q.star_answer_framework ? `
                    <div class="star-framework">
                        <strong>STAR Method:</strong>
                        <div class="star-grid">
                            ${Object.entries(q.star_answer_framework).map(([k, v]) => `
                                <div class="star-item">
                                    <span class="star-letter">${k[0]}</span>
                                    <span class="star-desc">${v}</span>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                ${q.common_mistakes?.length ? `
                    <div class="common-mistakes">
                        <strong>⚠️ Avoid:</strong>
                        <ul>${q.common_mistakes.map(m => `<li>${m}</li>`).join('')}</ul>
                    </div>
                ` : ''}
            </div>
        `).join('');

        container.innerHTML = `
            <div class="dashboard-card interview-prep-card">
                <div class="card-title">
                    🎤 Interview Predictor
                    <span class="badge-free">FREE: 5 Questions</span>
                    <button class="btn-upgrade" onclick="resumeReviewV2.showUpgradeModal()">Unlock 50+ Questions</button>
                </div>

                <div class="interview-intro">
                    Based on your resume analysis, here are the questions you're most likely to be asked:
                </div>

                <div class="questions-list">
                    ${questionCards}
                </div>

                <div class="interview-cta">
                    <p>Want to practice with a full mock interview?</p>
                    <button class="btn-primary" onclick="resumeReviewV2.showUpgradeModal()">
                        🚀 Get Pro Interview Prep
                    </button>
                </div>
            </div>
        `;
    }

    // 🔥 RENDER GAMIFICATION BADGES
    renderBadges(badges) {
        const container = document.getElementById('badgesSection');
        if (!container) return;

        const unlocked = badges.filter(b => b.unlocked);
        const locked = badges.filter(b => !b.unlocked);

        const badgeCards = (badges || []).map(b => `
            <div class="badge-item ${b.unlocked ? 'unlocked' : 'locked'}" data-rarity="${b.rarity}">
                <div class="badge-icon">${b.icon}</div>
                <div class="badge-name">${b.name}</div>
                <div class="badge-criteria">${b.criteria}</div>
                ${b.unlocked ? `<div class="badge-unlocked">✓ Unlocked!</div>` : ''}
                <div class="badge-points">+${b.points} pts</div>
            </div>
        `).join('');

        const totalPoints = unlocked.reduce((sum, b) => sum + (b.points || 0), 0);

        container.innerHTML = `
            <div class="dashboard-card badges-card">
                <div class="card-title">
                    🏆 Achievement Badges
                    <span class="badge-count">${unlocked.length}/${badges.length} Unlocked</span>
                </div>

                <div class="points-total">
                    <span class="points-value">${totalPoints}</span>
                    <span class="points-label">Total Points</span>
                </div>

                <div class="badges-grid">
                    ${badgeCards}
                </div>

                <div class="rarity-legend">
                    <span class="rarity-common">● Common</span>
                    <span class="rarity-rare">● Rare</span>
                    <span class="rarity-epic">● Epic</span>
                </div>
            </div>
        `;
    }

    // 🔥 RENDER IMPROVEMENT QUESTS
    renderQuests(quests) {
        const container = document.getElementById('questsSection');
        if (!container) return;

        const questCards = (quests || []).map(q => `
            <div class="quest-item ${q.status}">
                <div class="quest-progress">
                    <div class="progress-ring" style="--progress: ${(q.progress_current / q.progress_total) * 100}">
                        <span class="progress-text">${q.progress_current}/${q.progress_total}</span>
                    </div>
                </div>
                <div class="quest-content">
                    <div class="quest-title">${q.title}</div>
                    <div class="quest-description">${q.description}</div>
                    <div class="quest-meta">
                        <span class="quest-reward">🎁 ${q.reward}</span>
                        <span class="quest-time">⏱️ ${q.estimated_time}</span>
                        <span class="quest-difficulty ${q.difficulty}">${q.difficulty}</span>
                    </div>
                    ${q.suggested_edits?.length ? `
                        <div class="suggested-edits">
                            <strong>Suggested edits:</strong>
                            ${q.suggested_edits.slice(0, 2).map(e => `
                                <div class="edit-example">
                                    <div class="edit-before">❌ ${e.original || e.keyword || 'Before'}</div>
                                    <div class="edit-after">✅ ${e.improved || e.suggestion || 'After'}</div>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
                <button class="quest-action ${q.status}" ${q.status === 'completed' ? 'disabled' : ''}>
                    ${q.status === 'completed' ? '✓ Done' : q.status === 'in_progress' ? 'Continue →' : 'Start →'}
                </button>
            </div>
        `).join('');

        const completedCount = quests.filter(q => q.status === 'completed').length;

        container.innerHTML = `
            <div class="dashboard-card quests-card">
                <div class="card-title">
                    🎯 Improvement Quests
                    <span class="progress-text">${completedCount}/${quests.length} Complete</span>
                </div>

                <div class="quests-list">
                    ${questCards}
                </div>

                <div class="total-improvement-time">
                    💡 Complete all quests to improve your score by ~${this.currentAnalysis?.analysis?.overall_score ? 20 : 15} points
                    <br>
                    <small>Estimated time: ${this.currentAnalysis?.analysis?.estimated_improvement_time || '2 hours'}</small>
                </div>
            </div>
        `;
    }

    // Helper methods
    renderRewrites(rewrites) {
        const container = document.getElementById('rewritesList');
        if (!container) return;

        if (!rewrites || rewrites.length === 0) {
            container.innerHTML = '<p class="no-data">Upload resume and job description for AI rewrites</p>';
            return;
        }

        container.innerHTML = rewrites.slice(0, 3).map(r => `
            <div class="rewrite-item">
                <div class="rewrite-original">
                    <label>Original</label>
                    <p>${r.original}</p>
                </div>
                <div class="rewrite-improved">
                    <label>Improved</label>
                    <p>${r.rewritten}</p>
                </div>
                <div class="rewrite-meta">
                    <span class="rewrite-impact">${r.impact_score_increase}</span>
                    <span class="rewrite-explanation">${r.explanation}</span>
                </div>
            </div>
        `).join('');

        // Show upgrade prompt if there are more rewrites
        if (rewrites.length > 3) {
            container.innerHTML += `
                <div class="upgrade-prompt">
                    <p>✨ ${rewrites.length - 3} more AI rewrites available with Pro</p>
                    <button class="btn-secondary" onclick="resumeReviewV2.showUpgradeModal()">Unlock All</button>
                </div>
            `;
        }
    }

    renderKeywords(analysis) {
        const heatmapEl = document.getElementById('keywordHeatmap');
        if (!heatmapEl) return;

        const allKeywords = [
            ...(analysis.found_keywords || []).map(k => ({ word: k, status: 'found' })),
            ...(analysis.missing_keywords || []).map(k => ({ word: k, status: 'missing' }))
        ];

        if (allKeywords.length === 0) {
            heatmapEl.innerHTML = '<p class="no-data">No keywords analyzed. Add a job description for keyword matching.</p>';
            return;
        }

        heatmapEl.innerHTML = `
            <div class="keyword-stats">
                <span class="stat-found">${analysis.found_keywords?.length || 0} Found</span>
                <span class="stat-missing">${analysis.missing_keywords?.length || 0} Missing</span>
            </div>
            <div class="keyword-cloud">
                ${allKeywords.map(k => `
                    <span class="keyword-pill ${k.status}">${k.word}</span>
                `).join('')}
            </div>
        `;
    }

    renderStrengths(strengths) {
        const container = document.getElementById('strengthsList');
        if (!container) return;

        container.innerHTML = (strengths || [])
            .map(s => `<li class="result-item"><span class="result-icon strength">✓</span>${s}</li>`)
            .join('');
    }

    renderImprovements(improvements) {
        const container = document.getElementById('improvementsList');
        if (!container) return;

        container.innerHTML = (improvements || [])
            .map(i => `<li class="result-item"><span class="result-icon improvement">→</span>${i}</li>`)
            .join('');
    }

    // Utility methods
    getScoreColor(score) {
        if (score >= 80) return '#10b981';
        if (score >= 60) return '#f59e0b';
        return '#ef4444';
    }

    capitalize(str) {
        if (!str) return '';
        return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    showNotification(message, type = 'info') {
        const notif = document.createElement('div');
        notif.className = `notification notification-${type}`;
        notif.textContent = message;
        document.body.appendChild(notif);
        setTimeout(() => notif.remove(), 5000);
    }

    shareScore() {
        const score = this.currentAnalysis?.analysis?.overall_score || 75;
        const text = `I scored ${score}/100 on my resume using AI analysis! Can you beat it? 🚀`;

        if (navigator.share) {
            navigator.share({
                title: 'My Resume Score',
                text: text,
                url: window.location.href
            });
        } else {
            navigator.clipboard.writeText(text + ' ' + window.location.href);
            this.showNotification('Score copied to clipboard!', 'success');
        }
    }

    showUpgradeModal() {
        // Create and show upgrade modal
        const modal = document.createElement('div');
        modal.className = 'modal upgrade-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>🚀 Unlock Pro Features</h2>
                    <button class="close-btn" onclick="this.closest('.modal').remove()">×</button>
                </div>
                <div class="modal-body">
                    <div class="pricing-options">
                        <div class="pricing-card free">
                            <h3>Free</h3>
                            <div class="price">$0</div>
                            <ul>
                                <li>✓ Unlimited resume analyses</li>
                                <li>✓ 50+ ATS systems</li>
                                <li>✓ 10 AI rewrites/day</li>
                                <li>✓ Interview questions (5)</li>
                            </ul>
                            <button disabled>Current Plan</button>
                        </div>
                        <div class="pricing-card pro recommended">
                            <div class="badge">Recommended</div>
                            <h3>Pro</h3>
                            <div class="price">$9<span>/month</span></div>
                            <ul>
                                <li>✓ Unlimited AI rewrites</li>
                                <li>✓ Video resume studio</li>
                                <li>✓ Voice-to-resume</li>
                                <li>✓ 50+ interview questions</li>
                                <li>✓ A/B testing</li>
                                <li>✓ Priority support</li>
                            </ul>
                            <button class="btn-primary">Upgrade to Pro</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
    }
}

// Initialize
const resumeReviewV2 = new ResumeReviewV2();

// Export for global access
window.resumeReviewV2 = resumeReviewV2;
