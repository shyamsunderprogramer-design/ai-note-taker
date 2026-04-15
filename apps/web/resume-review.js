/**
 * Resume Review
 * Analyzes resumes and provides AI feedback
 */
class ResumeReview {
    constructor() {
        this.apiUrl = 'http://127.0.0.1:8000';
        this.uploadedFile = null;
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
        // Validate file type
        const allowedTypes = ['.pdf', '.docx', '.doc', '.txt', '.md', '.rtf'];
        const fileName = file.name.toLowerCase();

        if (!allowedTypes.some(ext => fileName.endsWith(ext))) {
            alert('Unsupported file type. Please upload PDF, DOCX, TXT, MD, or RTF files.');
            return;
        }

        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            alert('File too large. Maximum size is 10MB.');
            return;
        }

        this.uploadedFile = file;

        // Display file info
        const fileInfo = document.getElementById('fileInfo');
        fileInfo.innerHTML = `
            <span class="file-info-name">📄 ${file.name}</span>
            <span class="file-info-size">${(file.size / 1024).toFixed(1)} KB</span>
            <button class="file-remove-btn" onclick="resumeReview.removeFile()">Remove</button>
        `;
        fileInfo.classList.remove('hidden');

        // Disable text input
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

        // Check if file uploaded or text entered
        if (!this.uploadedFile && !resumeText) {
            alert('Please upload a resume file or paste your resume text');
            return;
        }

        analyzeBtn.disabled = true;
        analyzeBtn.textContent = 'Analyzing...';
        document.getElementById('loadingState').classList.remove('hidden');
        document.getElementById('emptyState').classList.add('hidden');
        document.getElementById('resultsContent').classList.add('hidden');

        try {
            let data;

            if (this.uploadedFile) {
                // Upload file for analysis
                const formData = new FormData();
                formData.append('file', this.uploadedFile);
                if (jobDesc) formData.append('job_description', jobDesc);

                const response = await fetch(`${this.apiUrl}/resume/upload`, {
                    method: 'POST',
                    body: formData
                });

                data = await response.json();

                // Auto-fill extracted text
                if (data.file_info && data.file_info.extracted_length > 0) {
                    document.getElementById('resumeInput').value = `[Extracted from ${this.uploadedFile.name}]\nExtracted ${data.file_info.extracted_length} characters.`;
                }
            } else {
                // Text-based analysis
                const url = `${this.apiUrl}/resume/analyze?` +
                    `resume_text=${encodeURIComponent(resumeText)}` +
                    `${jobDesc ? '&job_description=' + encodeURIComponent(jobDesc) : ''}`;

                const response = await fetch(url, { method: 'POST' });
                data = await response.json();
            }

            if (data.error) {
                throw new Error(data.error);
            }

            this.displayResults(data);

        } catch (error) {
            console.error('Error analyzing resume:', error);

            // Extract actual error message if it's an object
            let errorMessage = error.message;
            if (error.response && error.response.data && error.response.data.error) {
                errorMessage = error.response.data.error;
            } else if (typeof error === 'object' && error !== null) {
                errorMessage = JSON.stringify(error);
            }

            alert('Error analyzing resume: ' + errorMessage);
        } finally {
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Analyze Resume';
            document.getElementById('loadingState').classList.add('hidden');
        }
    }

    displayResults(data) {
        const analysis = data.analysis;

        // Overall score & Semantic Fit
        document.getElementById('overallScore').textContent = analysis.overall_score;
        document.getElementById('semanticFit').textContent = analysis.semantic_fit
            ? `AI Match Score: ${analysis.semantic_fit}%`
            : '';

        // Section scores
        const sectionScoresEl = document.getElementById('sectionScores');
        if (analysis.section_scores) {
            sectionScoresEl.innerHTML = Object.entries(analysis.section_scores)
                .map(([section, score]) => `
                    <div class="section-score-item">
                        <div class="section-score-value">${score}</div>
                        <div class="section-score-label">${this.capitalize(section)}</div>
                    </div>
                `).join('');
        }

        // AI Rewrites (XYZ Formula)
        const rewritesEl = document.getElementById('rewritesList');
        if (analysis.rewrites && analysis.rewrites.length > 0) {
            rewritesEl.innerHTML = analysis.rewrites.map(r => `
                <div class="rewrite-item">
                    <div class="rewrite-original">${r.original}</div>
                    <div class="rewrite-improved">${r.rewritten}</div>
                    <div class="rewrite-explanation">${r.explanation}</div>
                    <div class="rewrite-impact">${r.impact}</div>
                </div>
            `).join('');
        } else {
            rewritesEl.innerHTML = '<p class="file-upload-hint">No specific rewrites suggested.</p>';
        }

        // Keyword Heatmap
        const heatmapEl = document.getElementById('keywordHeatmap');
        const allKeywords = [...analysis.missing_keywords, ... (data.analysis.found_keywords || [])];

        if (allKeywords.length > 0) {
            heatmapEl.innerHTML = allKeywords.map(kw => {
                const isMissing = analysis.missing_keywords.includes(kw);
                return `<span class="keyword-pill ${isMissing ? 'kw-missing' : 'kw-found'}">${kw}</span>`;
            }).join('');
        } else {
            heatmapEl.innerHTML = '<p class="file-upload-hint">No keywords analyzed.</p>';
        }

        // Strengths
        document.getElementById('strengthsList').innerHTML = analysis.strengths
            .map(s => `<li class="result-item"><span class="result-icon strength">✓</span>${s}</li>`)
            .join('');

        // Improvements
        document.getElementById('improvementsList').innerHTML = analysis.improvements
            .map(i => `<li class="result-item"><span class="result-icon improvement">→</span>${i}</li>`)
            .join('');

        document.getElementById('resultsContent').classList.remove('hidden');
    }

    capitalize(str) {
        return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }
}

const resumeReview = new ResumeReview();
