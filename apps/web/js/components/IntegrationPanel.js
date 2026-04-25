/**
 * IntegrationPanel - Manages integration cards in the Settings panel
 * Handles connect/disconnect/test flows for Slack, Notion, Jira, Calendar, Phone, SSO, Teams
 */
import { API } from '../core/api.js';

export class IntegrationPanel {
  constructor() {
    this.integrations = {};
    this._bindAll();
  }

  _bindAll() {
    this._bindSlack();
    this._bindNotion();
    this._bindJira();
    this._bindCalendar();
    this._bindPhone();
    this._bindSSO();
    this._bindTeams();
  }

  async loadAll() {
    await Promise.allSettled([
      this._loadSlackStatus(),
      this._loadNotionStatus(),
      this._loadJiraStatus(),
      this._loadCalendarStatus(),
      this._loadPhoneStatus(),
      this._loadSSOStatus(),
      this._loadTeamsStatus(),
    ]);
  }

  // ── Helpers ──

  _setStatus(elId, text, cls = '') {
    const el = document.getElementById(elId);
    if (el) { el.textContent = text; el.className = 'settings-card-status ' + cls; }
  }

  _setMsg(elId, text, type = '') {
    const el = document.getElementById(elId);
    if (el) { el.textContent = text; el.className = 'int-status ' + type; }
  }

  _setLoading(btnId) {
    const btn = document.getElementById(btnId);
    if (btn) { btn.disabled = true; btn.dataset.orig = btn.textContent; btn.textContent = '...'; }
  }

  _clearLoading(btnId) {
    const btn = document.getElementById(btnId);
    if (btn && btn.dataset.orig) { btn.disabled = false; btn.textContent = btn.dataset.orig; }
  }

  // ── Slack ──

  _bindSlack() {
    document.getElementById('int-slack-save')?.addEventListener('click', () => this._saveSlack());
    document.getElementById('int-slack-test')?.addEventListener('click', () => this._testSlack());
    document.getElementById('int-slack-disconnect')?.addEventListener('click', () => this._disconnectSlack());
  }

  async _loadSlackStatus() {
    try {
      const data = await API.getIntegrationStatus('slack');
      if (data.connected) {
        this._setStatus('int-slack-status', 'Connected', 'connected');
        document.getElementById('int-slack-disconnect').style.display = '';
        document.getElementById('int-slack-save').textContent = 'Update';
        if (data.default_channel) document.getElementById('int-slack-channel').value = data.default_channel;
        if (data.auto_post !== undefined) document.getElementById('int-slack-autopost').checked = data.auto_post;
      } else {
        this._setStatus('int-slack-status', 'Not connected', '');
      }
    } catch { this._setStatus('int-slack-status', 'Error', 'error'); }
  }

  async _saveSlack() {
    this._setLoading('int-slack-save');
    const webhook = document.getElementById('int-slack-webhook').value.trim();
    const channel = document.getElementById('int-slack-channel').value.trim();
    const autoPost = document.getElementById('int-slack-autopost').checked;
    try {
      const result = await API.configureIntegration('slack', { webhook_url: webhook, default_channel: channel, auto_post: autoPost });
      this._setMsg('int-slack-msg', result.status === 'configured' ? 'Saved!' : 'Failed: ' + (result.detail || 'Unknown'), result.status === 'configured' ? 'success' : 'error');
      await this._loadSlackStatus();
    } catch (e) { this._setMsg('int-slack-msg', e.message, 'error'); }
    finally { this._clearLoading('int-slack-save'); }
  }

  async _testSlack() {
    this._setLoading('int-slack-test');
    try {
      const result = await API.postToSlack({ type: 'summary', title: 'Test', content: 'Connection test from ANT' });
      this._setMsg('int-slack-msg', result.status === 'sent' ? 'Test sent!' : 'Failed: ' + (result.detail || ''), result.status === 'sent' ? 'success' : 'error');
    } catch (e) { this._setMsg('int-slack-msg', e.message, 'error'); }
    finally { this._clearLoading('int-slack-test'); }
  }

  async _disconnectSlack() {
    try {
      await API.disconnectIntegration('slack');
      this._setStatus('int-slack-status', 'Not connected', '');
      document.getElementById('int-slack-disconnect').style.display = 'none';
      document.getElementById('int-slack-webhook').value = '';
      this._setMsg('int-slack-msg', 'Disconnected', 'success');
    } catch (e) { this._setMsg('int-slack-msg', e.message, 'error'); }
  }

  // ── Notion ──

  _bindNotion() {
    document.getElementById('int-notion-connect')?.addEventListener('click', () => this._saveNotion());
    document.getElementById('int-notion-pages')?.addEventListener('click', () => this._listNotionPages());
    document.getElementById('int-notion-disconnect')?.addEventListener('click', () => this._disconnectNotion());
  }

  async _loadNotionStatus() {
    try {
      const data = await API.getIntegrationStatus('notion');
      if (data.connected) {
        this._setStatus('int-notion-status', 'Connected', 'connected');
        document.getElementById('int-notion-disconnect').style.display = '';
        document.getElementById('int-notion-connect').textContent = 'Update';
        if (data.workspace_id) document.getElementById('int-notion-workspace').value = data.workspace_id;
      } else {
        this._setStatus('int-notion-status', 'Not connected', '');
      }
    } catch { this._setStatus('int-notion-status', 'Error', 'error'); }
  }

  async _saveNotion() {
    this._setLoading('int-notion-connect');
    const apiKey = document.getElementById('int-notion-apikey').value.trim();
    const workspace = document.getElementById('int-notion-workspace').value.trim();
    try {
      const result = await API.configureIntegration('notion', { api_key: apiKey, workspace_id: workspace });
      this._setMsg('int-notion-msg', result.status === 'connected' ? 'Connected!' : 'Failed: ' + (result.detail || ''), result.status === 'connected' ? 'success' : 'error');
      await this._loadNotionStatus();
    } catch (e) { this._setMsg('int-notion-msg', e.message, 'error'); }
    finally { this._clearLoading('int-notion-connect'); }
  }

  async _listNotionPages() {
    this._setLoading('int-notion-pages');
    try {
      const data = await API.listNotionPages();
      const list = document.getElementById('int-notion-pages-list');
      if (list && data.pages) {
        list.style.display = '';
        list.innerHTML = data.pages.map(p => `<div class="int-page-item">${p.title || 'Untitled'} — ${p.url || ''}</div>`).join('');
      }
    } catch (e) { this._setMsg('int-notion-msg', e.message, 'error'); }
    finally { this._clearLoading('int-notion-pages'); }
  }

  async _disconnectNotion() {
    try {
      await API.disconnectIntegration('notion');
      this._setStatus('int-notion-status', 'Not connected', '');
      document.getElementById('int-notion-disconnect').style.display = 'none';
      document.getElementById('int-notion-apikey').value = '';
      this._setMsg('int-notion-msg', 'Disconnected', 'success');
    } catch (e) { this._setMsg('int-notion-msg', e.message, 'error'); }
  }

  // ── Jira ──

  _bindJira() {
    document.getElementById('int-jira-connect')?.addEventListener('click', () => this._saveJira());
    document.getElementById('int-jira-projects')?.addEventListener('click', () => this._listJiraProjects());
    document.getElementById('int-jira-disconnect')?.addEventListener('click', () => this._disconnectJira());
  }

  async _loadJiraStatus() {
    try {
      const data = await API.getIntegrationStatus('jira');
      if (data.connected) {
        this._setStatus('int-jira-status', 'Connected', 'connected');
        document.getElementById('int-jira-disconnect').style.display = '';
        document.getElementById('int-jira-connect').textContent = 'Update';
        if (data.base_url) document.getElementById('int-jira-url').value = data.base_url;
        if (data.email) document.getElementById('int-jira-email').value = data.email;
      } else {
        this._setStatus('int-jira-status', 'Not connected', '');
      }
    } catch { this._setStatus('int-jira-status', 'Error', 'error'); }
  }

  async _saveJira() {
    this._setLoading('int-jira-connect');
    const baseUrl = document.getElementById('int-jira-url').value.trim();
    const email = document.getElementById('int-jira-email').value.trim();
    const token = document.getElementById('int-jira-token').value.trim();
    try {
      const result = await API.configureIntegration('jira', { base_url: baseUrl, email, api_token: token });
      this._setMsg('int-jira-msg', result.status === 'connected' ? 'Connected!' : 'Failed: ' + (result.detail || ''), result.status === 'connected' ? 'success' : 'error');
      await this._loadJiraStatus();
    } catch (e) { this._setMsg('int-jira-msg', e.message, 'error'); }
    finally { this._clearLoading('int-jira-connect'); }
  }

  async _listJiraProjects() {
    this._setLoading('int-jira-projects');
    try {
      const data = await API.listJiraProjects();
      this._setMsg('int-jira-msg', `Found ${data.total || 0} projects`, 'success');
    } catch (e) { this._setMsg('int-jira-msg', e.message, 'error'); }
    finally { this._clearLoading('int-jira-projects'); }
  }

  async _disconnectJira() {
    try {
      await API.disconnectIntegration('jira');
      this._setStatus('int-jira-status', 'Not connected', '');
      document.getElementById('int-jira-disconnect').style.display = 'none';
      this._setMsg('int-jira-msg', 'Disconnected', 'success');
    } catch (e) { this._setMsg('int-jira-msg', e.message, 'error'); }
  }

  // ── Calendar ──

  _bindCalendar() {
    document.getElementById('int-calendar-connect')?.addEventListener('click', () => this._saveCalendar());
    document.getElementById('int-calendar-disconnect')?.addEventListener('click', () => this._disconnectCalendar());
  }

  async _loadCalendarStatus() {
    try {
      const data = await API.getIntegrationStatus('calendar');
      if (data.connected) {
        this._setStatus('int-calendar-status', 'Connected', 'connected');
        document.getElementById('int-calendar-disconnect').style.display = '';
        document.getElementById('int-calendar-connect').textContent = 'Update';
        if (data.provider) document.getElementById('int-calendar-provider').value = data.provider;
        if (data.auto_join !== undefined) document.getElementById('int-calendar-autojoin').checked = data.auto_join;
      } else {
        this._setStatus('int-calendar-status', 'Not connected', '');
      }
    } catch { this._setStatus('int-calendar-status', 'Error', 'error'); }
  }

  async _saveCalendar() {
    this._setLoading('int-calendar-connect');
    const provider = document.getElementById('int-calendar-provider').value;
    const autoJoin = document.getElementById('int-calendar-autojoin').checked;
    if (!provider) { this._setMsg('int-calendar-msg', 'Select a provider', 'error'); this._clearLoading('int-calendar-connect'); return; }
    try {
      const result = await API.configureIntegration('calendar', { provider, auto_join: autoJoin });
      this._setMsg('int-calendar-msg', result.status === 'configured' ? 'Configured!' : 'Failed', result.status === 'configured' ? 'success' : 'error');
      await this._loadCalendarStatus();
    } catch (e) { this._setMsg('int-calendar-msg', e.message, 'error'); }
    finally { this._clearLoading('int-calendar-connect'); }
  }

  async _disconnectCalendar() {
    try {
      await API.disconnectIntegration('calendar');
      this._setStatus('int-calendar-status', 'Not connected', '');
      document.getElementById('int-calendar-disconnect').style.display = 'none';
      this._setMsg('int-calendar-msg', 'Disconnected', 'success');
    } catch (e) { this._setMsg('int-calendar-msg', e.message, 'error'); }
  }

  // ── Phone ──

  _bindPhone() {
    document.getElementById('int-phone-connect')?.addEventListener('click', () => this._savePhone());
    document.getElementById('int-phone-disconnect')?.addEventListener('click', () => this._disconnectPhone());
  }

  async _loadPhoneStatus() {
    try {
      const data = await API.getIntegrationStatus('phone');
      if (data.connected) {
        this._setStatus('int-phone-status', 'Connected', 'connected');
        document.getElementById('int-phone-disconnect').style.display = '';
        document.getElementById('int-phone-connect').textContent = 'Update';
        if (data.provider) document.getElementById('int-phone-provider').value = data.provider;
        if (data.phone_number) document.getElementById('int-phone-number').value = data.phone_number;
      } else {
        this._setStatus('int-phone-status', 'Not connected', '');
      }
    } catch { this._setStatus('int-phone-status', 'Error', 'error'); }
  }

  async _savePhone() {
    this._setLoading('int-phone-connect');
    const phoneNumber = document.getElementById('int-phone-number').value.trim();
    const provider = document.getElementById('int-phone-provider').value;
    if (!phoneNumber) { this._setMsg('int-phone-msg', 'Enter a phone number', 'error'); this._clearLoading('int-phone-connect'); return; }
    try {
      const result = await API.configureIntegration('phone', { phone_number: phoneNumber, provider });
      this._setMsg('int-phone-msg', result.status === 'connected' ? 'Connected!' : 'Failed', result.status === 'connected' ? 'success' : 'error');
      await this._loadPhoneStatus();
    } catch (e) { this._setMsg('int-phone-msg', e.message, 'error'); }
    finally { this._clearLoading('int-phone-connect'); }
  }

  async _disconnectPhone() {
    try {
      await API.disconnectIntegration('phone');
      this._setStatus('int-phone-status', 'Not connected', '');
      document.getElementById('int-phone-disconnect').style.display = 'none';
      this._setMsg('int-phone-msg', 'Disconnected', 'success');
    } catch (e) { this._setMsg('int-phone-msg', e.message, 'error'); }
  }

  // ── SSO ──

  _bindSSO() {
    document.getElementById('int-sso-google')?.addEventListener('click', () => this._ssoLogin('google'));
    document.getElementById('int-sso-microsoft')?.addEventListener('click', () => this._ssoLogin('microsoft'));
  }

  async _loadSSOStatus() {
    try {
      const data = await API.getSSOStatus();
      const googleOk = data?.google?.configured;
      const msOk = data?.microsoft?.configured;
      const count = (googleOk ? 1 : 0) + (msOk ? 1 : 0);
      this._setStatus('int-sso-status', count > 0 ? `${count} available` : 'Not configured', count > 0 ? 'connected' : '');
      if (!googleOk) document.getElementById('int-sso-google')?.setAttribute('disabled', '');
      if (!msOk) document.getElementById('int-sso-microsoft')?.setAttribute('disabled', '');
    } catch {
      this._setStatus('int-sso-status', 'Unavailable', 'error');
    }
  }

  async _ssoLogin(provider) {
    try {
      const data = await API.initiateSSO(provider);
      if (data.redirect_url) { window.open(data.redirect_url, '_blank'); }
    } catch (e) { this._setMsg('int-sso-msg', e.message, 'error'); }
  }

  // ── Teams ──

  _bindTeams() {
    document.getElementById('int-teams-create')?.addEventListener('click', () => this._createTeam());
  }

  async _loadTeamsStatus() {
    try {
      const data = await API.listTeams();
      const count = data.teams?.length || 0;
      this._setStatus('int-teams-status', `${count} team${count !== 1 ? 's' : ''}`, count > 0 ? 'connected' : '');
      this._renderTeams(data.teams || []);
    } catch { this._setStatus('int-teams-status', 'Error', 'error'); }
  }

  async _createTeam() {
    this._setLoading('int-teams-create');
    const name = document.getElementById('int-teams-name').value.trim();
    const desc = document.getElementById('int-teams-desc').value.trim();
    if (!name) { this._setMsg('int-teams-msg', 'Enter a team name', 'error'); this._clearLoading('int-teams-create'); return; }
    try {
      const result = await API.createTeam(name, desc);
      this._setMsg('int-teams-msg', 'Team created!', 'success');
      document.getElementById('int-teams-name').value = '';
      document.getElementById('int-teams-desc').value = '';
      await this._loadTeamsStatus();
    } catch (e) { this._setMsg('int-teams-msg', e.message, 'error'); }
    finally { this._clearLoading('int-teams-create'); }
  }

  _renderTeams(teams) {
    const list = document.getElementById('int-teams-list');
    if (!list) return;
    if (teams.length === 0) { list.innerHTML = '<div style="color:var(--text-dim);font-size:12px;padding:8px 0">No teams yet</div>'; return; }
    list.innerHTML = teams.map(t => `<div class="int-team-item"><strong>${t.name}</strong> — ${t.role} (${t.member_count} members)</div>`).join('');
  }
}