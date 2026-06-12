/**
 * Interview Simulator Frontend
 * Handles recording, API communication, and UI updates
 */

class InterviewSimulator {
  constructor() {
    this.sessionId = null;
    this.currentQuestion = null;
    this.isRecording = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
    this.transcript = '';
    this.numQuestions = 5;
    this.recordingStartTime = null;

    // API base URL - Electron uses file:// protocol, so we need absolute URL
    this.apiUrl = 'http://127.0.0.1:8000';

    // Check if running in Electron
    if (typeof process !== 'undefined' && process.versions && process.versions.electron) {
      // In Electron, use the window.api if available
      if (window.api && window.api.backendUrl) {
        this.apiUrl = window.api.backendUrl;
      }
    }

    // DOM Elements
    this.setupElements();
    this.setupEventListeners();
  }

  setupElements() {
    // Sections
    this.setupSection = document.getElementById('setupSection');
    this.loadingSection = document.getElementById('loadingSection');
    this.sessionSection = document.getElementById('sessionSection');
    this.summarySection = document.getElementById('summarySection');

    // Inputs
    this.companyInput = document.getElementById('companyInput');
    this.roleInput = document.getElementById('roleInput');

    // Session elements
    this.progressText = document.getElementById('progressText');
    this.progressPercent = document.getElementById('progressPercent');
    this.progressBar = document.getElementById('progressBar');
    this.questionText = document.getElementById('questionText');
    this.questionCategory = document.getElementById('questionCategory');
    this.questionDifficulty = document.getElementById('questionDifficulty');
    this.recordBtn = document.getElementById('recordBtn');
    this.recordStatus = document.getElementById('recordStatus');
    this.transcriptPreview = document.getElementById('transcriptPreview');
    this.submitBtn = document.getElementById('submitBtn');

    // Evaluation
    this.evaluationCard = document.getElementById('evaluationCard');
    this.overallScore = document.getElementById('overallScore');
    this.completenessScore = document.getElementById('completenessScore');
    this.structureScore = document.getElementById('structureScore');
    this.technicalScore = document.getElementById('technicalScore');
    this.strengthsList = document.getElementById('strengthsList');
    this.improvementsList = document.getElementById('improvementsList');
    this.missingList = document.getElementById('missingList');
    this.missingSection = document.getElementById('missingSection');

    // Summary
    this.summaryMessage = document.getElementById('summaryMessage');
    this.totalQuestions = document.getElementById('totalQuestions');
    this.avgScore = document.getElementById('avgScore');
    this.duration = document.getElementById('duration');
    this.readiness = document.getElementById('readiness');
    this.categoryBreakdown = document.getElementById('categoryBreakdown');
  }

  setupEventListeners() {
    // Option cards for question count
    const optionCards = document.querySelectorAll('.option-card');
    optionCards.forEach(card => {
      card.addEventListener('click', () => {
        optionCards.forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        this.numQuestions = parseInt(card.dataset.questions);
      });
    });

    // Transcript input
    this.transcriptPreview.addEventListener('input', () => {
      this.submitBtn.disabled = !this.transcriptPreview.textContent.trim();
    });
  }

  async startSession() {
    const company = this.companyInput.value.trim();
    const role = this.roleInput.value.trim();

    if (!company) {
      alert('Please enter a company name');
      return;
    }

    // Show loading
    this.setupSection.classList.add('hidden');
    this.loadingSection.classList.remove('hidden');

    try {
      // Create interview session
      const response = await fetch(
        `${this.apiUrl}/interview-simulator/create?company=${encodeURIComponent(company)}&role=${encodeURIComponent(role)}&num_questions=${this.numQuestions}`
      );
      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      this.sessionId = data.session_id;
      console.log('Session created:', this.sessionId);

      // Get first question
      await this.loadNextQuestion();

      // Show session section
      this.loadingSection.classList.add('hidden');
      this.sessionSection.classList.add('active');

    } catch (error) {
      console.error('Error starting session:', error);
      alert('Error starting interview: ' + error.message);
      this.loadingSection.classList.add('hidden');
      this.setupSection.classList.remove('hidden');
    }
  }

  async loadNextQuestion() {
    try {
      const response = await fetch(`${this.apiUrl}/interview-simulator/${this.sessionId}/question`);
      const data = await response.json();

      if (data.status === 'complete') {
        // Interview complete
        await this.finishInterview();
        return;
      }

      if (data.error) {
        throw new Error(data.error);
      }

      this.currentQuestion = data;
      this.updateQuestionUI(data);

      // Reset UI
      this.resetForNewQuestion();

    } catch (error) {
      console.error('Error loading question:', error);
      alert('Error loading question: ' + error.message);
    }
  }

  updateQuestionUI(data) {
    // Update progress
    this.progressText.textContent = `Question ${data.question_number} of ${data.total_questions}`;
    this.progressPercent.textContent = `${data.progress_percent}%`;
    this.progressBar.style.width = `${data.progress_percent}%`;

    // Update question
    this.questionText.textContent = data.question;

    // Update category
    this.questionCategory.textContent = this.capitalize(data.category);
    this.questionCategory.className = `question-tag category-${data.category}`;

    // Update difficulty
    this.questionDifficulty.textContent = this.capitalize(data.difficulty);
    this.questionDifficulty.className = `question-tag difficulty-${data.difficulty}`;
  }

  resetForNewQuestion() {
    // Reset recording state
    this.isRecording = false;
    this.audioChunks = [];
    this.transcript = '';
    this.transcriptPreview.textContent = '';
    this.submitBtn.disabled = true;
    this.recordBtn.classList.remove('recording');
    this.recordStatus.textContent = 'Tap microphone to start answering';

    // Hide evaluation
    this.evaluationCard.classList.add('hidden');

    // Enable submit button
    this.submitBtn.textContent = 'Submit Answer';
  }

  async toggleRecording() {
    if (!this.isRecording) {
      await this.startRecording();
    } else {
      await this.stopRecording();
    }
  }

  async startRecording() {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      this.audioChunks = [];

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = async () => {
        await this.processAudio();
      };

      this.mediaRecorder.start(100); // Collect data every 100ms

      this.isRecording = true;
      this.recordingStartTime = Date.now();
      this.recordBtn.classList.add('recording');
      this.recordStatus.textContent = 'Recording... Click to stop';

      // Auto-stop after 3 minutes
      setTimeout(() => {
        if (this.isRecording) {
          this.stopRecording();
        }
      }, 180000);

    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  }

  async stopRecording() {
    if (!this.mediaRecorder || !this.isRecording) return;

    this.mediaRecorder.stop();
    this.isRecording = false;
    this.recordBtn.classList.remove('recording');
    this.recordStatus.textContent = 'Processing speech...';

    // Stop all tracks
    this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
  }

  async processAudio() {
    try {
      const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });

      // Create form data
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      // Send to transcription API
      const response = await fetch(`${this.apiUrl}/transcribe`, {
        method: 'POST',
        body: formData
      });

      const data = await response.json();

      if (data.text) {
        this.transcript = data.text;
        this.transcriptPreview.textContent = data.text;
        this.submitBtn.disabled = false;
        this.recordStatus.textContent = 'Recording complete';
      } else {
        this.recordStatus.textContent = 'No speech detected. Try again.';
      }

    } catch (error) {
      console.error('Error processing audio:', error);
      this.recordStatus.textContent = 'Error processing audio. Please try again.';
    }
  }

  async submitAnswer() {
    if (!this.transcript.trim()) {
      alert('Please record your answer first');
      return;
    }

    // Disable submit button
    this.submitBtn.disabled = true;
    this.submitBtn.textContent = 'Evaluating...';

    // Calculate duration
    const durationMs = this.recordingStartTime ? Date.now() - this.recordingStartTime : 0;

    try {
      const response = await fetch(
        `${this.apiUrl}/interview-simulator/${this.sessionId}/answer?transcript=${encodeURIComponent(this.transcript)}&duration_ms=${durationMs}`,
        { method: 'POST' }
      );

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Show evaluation
      this.displayEvaluation(data.evaluation, data.is_complete);

    } catch (error) {
      console.error('Error submitting answer:', error);
      alert('Error submitting answer: ' + error.message);
      this.submitBtn.disabled = false;
      this.submitBtn.textContent = 'Submit Answer';
    }
  }

  displayEvaluation(evaluation, isComplete) {
    // Update scores
    const overall = evaluation.overall_score;
    this.overallScore.textContent = overall;
    this.overallScore.className = `score-value ${this.getScoreClass(overall)}`;

    this.completenessScore.textContent = evaluation.completeness_score;
    this.structureScore.textContent = evaluation.structure_score;
    this.technicalScore.textContent = evaluation.technical_accuracy;

    // Update strengths
    this.strengthsList.innerHTML = evaluation.strengths
      .map(s => `<li class="feedback-item"><span class="feedback-icon strength">✓</span>${s}</li>`)
      .join('');

    // Update improvements
    this.improvementsList.innerHTML = evaluation.improvements
      .map(i => `<li class="feedback-item"><span class="feedback-icon improvement">→</span>${i}</li>`)
      .join('');

    // Update missing points
    if (evaluation.missing_points && evaluation.missing_points.length > 0) {
      this.missingSection.classList.remove('hidden');
      this.missingList.innerHTML = evaluation.missing_points
        .map(m => `<li class="feedback-item"><span class="feedback-icon missing">!</span>${m}</li>`)
        .join('');
    } else {
      this.missingSection.classList.add('hidden');
    }

    // Show evaluation card
    this.evaluationCard.classList.remove('hidden');

    // Update next button
    const nextBtn = document.getElementById('nextBtn');
    nextBtn.textContent = isComplete ? 'See Results →' : 'Next Question →';
    nextBtn.onclick = isComplete ? () => this.finishInterview() : () => this.nextQuestion();

    // Scroll to evaluation
    this.evaluationCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  getScoreClass(score) {
    if (score >= 85) return 'excellent';
    if (score >= 70) return 'good';
    if (score >= 55) return 'fair';
    return 'needs-work';
  }

  async nextQuestion() {
    await this.loadNextQuestion();
  }

  async skipQuestion() {
    // Submit empty answer to skip
    this.transcript = '[Skipped]';
    await this.submitAnswer();
  }

  async finishInterview() {
    try {
      const response = await fetch(
        `${this.apiUrl}/interview-simulator/${this.sessionId}/finish`,
        { method: 'POST' }
      );

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      // Show summary
      this.displaySummary(data.summary);

      // Hide session, show summary
      this.sessionSection.classList.remove('active');
      this.summarySection.classList.add('active');

    } catch (error) {
      console.error('Error finishing interview:', error);
      alert('Error completing interview: ' + error.message);
    }
  }

  displaySummary(summary) {
    // Update message
    this.summaryMessage.textContent = summary.estimated_readiness || 'Interview complete!';

    // Update stats
    this.totalQuestions.textContent = summary.total_questions || 0;
    this.avgScore.textContent = summary.average_scores?.overall || 0;
    this.duration.textContent = summary.duration_minutes || 0;
    this.readiness.textContent = this.getReadinessLabel(summary.average_scores?.overall);

    // Update category breakdown
    if (summary.category_breakdown) {
      this.categoryBreakdown.innerHTML = `
        <h3 class="category-title">Performance by Category</h3>
        ${Object.entries(summary.category_breakdown)
          .map(([category, score]) => `
            <div class="category-item">
              <span>${this.capitalize(category)}</span>
              <div class="category-bar">
                <div class="category-fill" style="width: ${score}%"></div>
              </div>
              <span>${score}</span>
            </div>
          `).join('')}
      `;
    }
  }

  getReadinessLabel(score) {
    if (!score) return 'N/A';
    if (score >= 85) return 'Excellent';
    if (score >= 70) return 'Good';
    if (score >= 55) return 'Fair';
    return 'Needs Work';
  }

  capitalize(str) {
    if (!str) return '';
    return str.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }

  restart() {
    // Reset all state
    this.sessionId = null;
    this.currentQuestion = null;
    this.isRecording = false;
    this.audioChunks = [];
    this.transcript = '';

    // Hide summary, show setup
    this.summarySection.classList.remove('active');
    this.setupSection.classList.remove('hidden');

    // Reset form
    this.companyInput.value = '';
    this.roleInput.value = '';
  }
}

// Initialize
const interviewSim = new InterviewSimulator();
