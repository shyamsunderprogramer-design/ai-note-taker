/**
 * Job Application Tracker
 * Manages job applications and displays pipeline view
 */

class JobTracker {
    constructor() {
        this.apiUrl = 'http://127.0.0.1:8000';
        this.applications = [];
        this.stats = {};

        this.statusColumns = [
            { id: 'saved', label: 'Saved', color: '#6b7280' },
            { id: 'applied', label: 'Applied', color: '#3b82f6' },
            { id: 'phone_screen', label: 'Phone Screen', color: '#8b5cf6' },
            { id: 'technical', label: 'Technical', color: '#f59e0b' },
            { id: 'onsite', label: 'Onsite', color: '#ec4899' },
            { id: 'offer', label: 'Offer', color: '#10b981' },
            { id: 'accepted', label: 'Accepted', color: '#059669' }
        ];

        this.init();
    }

    async init() {
        await this.loadData();
        this.renderPipeline();
        this.updateStats();
    }

    async loadData() {
        try {
            document.getElementById('loadingState').classList.remove('hidden');
            document.getElementById('emptyState').classList.add('hidden');

            // Load applications
            const appResponse = await fetch(`${this.apiUrl}/job-tracker/applications`);
            const appData = await appResponse.json();

            if (appData.error) {
                console.error('Error loading applications:', appData.error);
                return;
            }

            this.applications = appData.applications || [];

            // Load stats
            const statsResponse = await fetch(`${this.apiUrl}/job-tracker/stats`);
            const statsData = await statsResponse.json();

            if (!statsData.error) {
                this.stats = statsData;
            }

            document.getElementById('loadingState').classList.add('hidden');

            if (this.applications.length === 0) {
                document.getElementById('emptyState').classList.remove('hidden');
            }
        } catch (error) {
            console.error('Error loading data:', error);
            document.getElementById('loadingState').classList.add('hidden');
        }
    }

    updateStats() {
        const stats = this.stats;
        const pipeline = stats.pipeline || {};

        document.getElementById('statTotal').textContent = stats.total_applications || 0;
        document.getElementById('statApplied').textContent = stats.total_applied || 0;

        const interviews = (pipeline.phone_screen || 0) +
                           (pipeline.technical || 0) +
                           (pipeline.onsite || 0);
        document.getElementById('statInterviews').textContent = interviews;

        document.getElementById('statOffers').textContent = stats.total_offers || 0;
        document.getElementById('statResponse').textContent =
            (stats.response_rate ? `${stats.response_rate}%` : '0%');
    }

    renderPipeline() {
        const container = document.getElementById('pipelineContainer');
        container.innerHTML = '';

        this.statusColumns.forEach(column => {
            const columnApps = this.applications.filter(app => app.status === column.id);

            const columnEl = document.createElement('div');
            columnEl.className = 'pipeline-column';
            columnEl.innerHTML = `
                <div class="pipeline-header" style="border-left: 3px solid ${column.color}">
                    <span>${column.label}</span>
                    <span class="pipeline-count">${columnApps.length}</span>
                </div>
                <div class="pipeline-items" data-status="${column.id}">
                    ${columnApps.map(app => this.renderJobCard(app)).join('')}
                </div>
            `;

            container.appendChild(columnEl);
        });
    }

    renderJobCard(app) {
        const priorityClass = app.priority === 'high' ? 'priority-high' :
                            app.priority === 'medium' ? 'priority-medium' : '';

        const date = app.applied_date ?
            new Date(app.applied_date).toLocaleDateString() :
            new Date(app.created_at).toLocaleDateString();

        return `
            <div class="job-card" onclick="jobTracker.openJobDetail('${app.id}')">
                <div class="job-card-header">
                    <span class="job-company">${this.escapeHtml(app.company)}</span>
                    ${app.priority !== 'low' ? `<span class="job-tag ${priorityClass}">${app.priority}</span>` : ''}
                </div>
                <div class="job-role">${this.escapeHtml(app.role)}</div>
                <div class="job-meta">
                    <span class="job-tag">${date}</span>
                    ${app.location ? `<span class="job-tag">${this.escapeHtml(app.location)}</span>` : ''}
                </div>
            </div>
        `;
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    openModal() {
        document.getElementById('addJobModal').classList.add('active');
    }

    closeModal() {
        document.getElementById('addJobModal').classList.remove('active');
        document.getElementById('addJobForm').reset();
    }

    async submitForm(event) {
        event.preventDefault();

        const data = {
            company: document.getElementById('companyInput').value,
            role: document.getElementById('roleInput').value,
            location: document.getElementById('locationInput').value,
            status: document.getElementById('statusInput').value,
            priority: document.getElementById('priorityInput').value,
            salary_range: document.getElementById('salaryInput').value,
            job_url: document.getElementById('urlInput').value
        };

        try {
            const response = await fetch(
                `${this.apiUrl}/job-tracker/application?` +
                `company=${encodeURIComponent(data.company)}&` +
                `role=${encodeURIComponent(data.role)}&` +
                `location=${encodeURIComponent(data.location || '')}&` +
                `status=${data.status}&` +
                `priority=${data.priority}&` +
                `salary_range=${encodeURIComponent(data.salary_range || '')}&` +
                `job_url=${encodeURIComponent(data.job_url || '')}`,
                { method: 'POST' }
            );

            const result = await response.json();

            if (result.error) {
                alert('Error: ' + result.error);
                return;
            }

            this.closeModal();
            await this.loadData();
            this.renderPipeline();
            this.updateStats();

        } catch (error) {
            console.error('Error submitting form:', error);
            alert('Failed to add application');
        }
    }

    openJobDetail(appId) {
        // Navigate to job detail page (can be implemented)
        console.log('Open job detail:', appId);
        // For now, just show in console
        const app = this.applications.find(a => a.id === appId);
        if (app) {
            console.log('Application details:', app);
        }
    }
}

// Initialize
const jobTracker = new JobTracker();

// Close modal on outside click
document.getElementById('addJobModal').addEventListener('click', (e) => {
    if (e.target.id === 'addJobModal') {
        jobTracker.closeModal();
    }
});
