import { Api, UI } from './sys_core.js';

/**
 * Security Service Handler
 * Handles dependency-check reports and security scans.
 */
const SecService = {
    state: {
        scans: [],
        projects: []
    },

    init() {
        console.log("Security Service Initialized.");
        this.bindEvents();
    },

    bindEvents() {
        // Form submission for upload
        const form = document.getElementById('sec-upload-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleUpload(e));
        }

        // Global buttons from sys_app delegation
        document.addEventListener('click', (e) => {
            if (e.target.closest('.js-btn-open-sec-upload')) {
                this.openUploadModal();
            }
            if (e.target.closest('.js-btn-close-sec-modal')) {
                UI.hideModal('securityUploadModal');
            }
        });
    },

    /**
     * Load scan history from API
     */
    async loadHistory() {
        try {
            const scans = await Api.get('/security/dependency-scans');
            this.state.scans = scans;
            this.renderHistory(scans);
            this.updateStats(scans);
        } catch (e) {
            console.error("Failed to load security scans", e);
            UI.showToast("加载安全扫描历史失败", "error");
        }
    },

    /**
     * Render scan history table
     */
    renderHistory(scans) {
        const tbody = document.getElementById('sec-scan-history-tbody');
        if (!tbody) return;

        if (scans.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="u-text-center u-p-24 u-text-dim">暂无扫描记录，请点击上方按钮自行上传报告。</td></tr>`;
            return;
        }

        tbody.innerHTML = scans.map(scan => `
            <tr>
                <td>
                    <div class="u-flex u-flex-direction-column">
                        <span class="u-weight-600">${scan.project?.name || 'Unknown Project'}</span>
                        <span class="u-text-tiny u-text-dim">#${scan.project_id}</span>
                    </div>
                </td>
                <td>${new Date(scan.scan_date).toLocaleString()}</td>
                <td>${scan.total_dependencies || 0}</td>
                <td>
                    <span class="sys-tag ${scan.vulnerable_dependencies > 0 ? 'u-bg-error-light u-text-error' : 'u-bg-success-light u-text-success'}">
                        ${scan.vulnerable_dependencies || 0}
                    </span>
                </td>
                <td>
                    <span class="sys-tag ${this.getStatusClass(scan.scan_status)}">${scan.scan_status}</span>
                </td>
                <td>
                    <button class="btn-ghost btn--small" onclick="window.alert('详情功能维护中...')">详情</button>
                </td>
            </tr>
        `).join('');
    },

    getStatusClass(status) {
        switch (status) {
            case 'completed': return 'u-bg-success-light u-text-success';
            case 'failed': return 'u-bg-error-light u-text-error';
            case 'in_progress': return 'u-bg-primary-light u-text-primary';
            default: return 'u-bg-subtle u-text-dim';
        }
    },

    /**
     * Update top stats cards
     */
    updateStats(scans) {
        const stats = {
            vulnerabilities: 0,
            critical: 0,
            licenses: 0,
            projects: new Set()
        };

        scans.forEach(s => {
            stats.vulnerabilities += (s.vulnerable_dependencies || 0);
            stats.licenses += (s.high_risk_licenses || 0);
            stats.projects.add(s.project_id);
            // Assuming critical count might be in summary or raw_json if we want deep analysis
            // For now, let's use vulnerable count as a placeholder for critical if not separate
        });

        UI.setText('sec-stat-vulnerabilities', stats.vulnerabilities);
        UI.setText('sec-stat-licenses', stats.licenses);
        UI.setText('sec-stat-projects', stats.projects.size);
    },

    /**
     * Open upload modal and load projects for selection
     */
    async openUploadModal() {
        UI.showModal('securityUploadModal');
        const select = document.querySelector('.js-sec-project-select');
        if (!select) return;

        try {
            // Use common project list from Api if available, or fetch
            const projects = await Api.get('/admin/projects/repos');
            select.innerHTML = '<option value="">请选择项目...</option>' +
                projects.map(p => `<option value="${p.id}">${p.name} (${p.path_with_namespace})</option>`).join('');
        } catch (e) {
            console.error("Failed to load projects", e);
            select.innerHTML = '<option value="">加载项目失败</option>';
        }
    },

    /**
     * Handle form submission
     */
    async handleUpload(e) {
        e.preventDefault();
        const form = e.target;
        const formData = new FormData(form);
        const submitBtn = form.querySelector('button[type="submit"]');

        submitBtn.disabled = true;
        submitBtn.textContent = '解析扫描报告中...';

        try {
            const data = await Api.upload('/security/dependency-check/upload', formData);
            UI.showToast(`上传成功！发现 ${data.summary.vulnerable} 个漏洞。`, "success");
            UI.hideModal('securityUploadModal');
            form.reset();
            this.loadHistory(); // Refresh list
        } catch (err) {
            console.error("Upload error", err);
            UI.showToast(err.message, "error");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = '开始上传解析';
        }
    }
};

export default SecService;
