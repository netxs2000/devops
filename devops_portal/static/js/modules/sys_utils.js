/**
 * @file utils.js
 * @description 杂项辅助函数，包括 GitLab 链接生成和历史记录渲染。
 * @author Antigravity
 */

const SysUtilsHandler = {
    /**
     * 加载额外数据（最近项目、流水线状态、用例历史）
     */
    async loadExtraData() {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;

        // 1. 最近项目
        try {
            const projects = await Api.get('/recent-projects');
            const container = document.getElementById('recentProjects');
            const template = document.getElementById('sys-recent-project-tpl');
            if (container && template) {
                container.innerHTML = '';
                projects.forEach(id => {
                    const clone = template.content.cloneNode(true);
                    clone.querySelector('.js-proj-info').textContent = `PID ${id}`;
                    const link = clone.querySelector('.js-recent-proj');
                    link.addEventListener('click', () => {
                        projectIdInput.value = id;
                        if (window.qa_loadTestCases) window.qa_loadTestCases();
                    });
                    container.appendChild(clone);
                });
            }
        } catch (e) { }

        // 2. 流水线状态
        try {
            const pipe = await Api.get(`/projects/${projectId}/pipeline-status`);
            const monitor = document.getElementById('pipelineMonitor');
            if (monitor && pipe.status !== 'unknown') {
                monitor.classList.remove('u-hide');
                monitor.classList.add('u-block');
                const pipeInfo = document.getElementById('pipe-info');
                if (pipeInfo) pipeInfo.textContent = `#${pipe.id} [${pipe.sha}]`;
                const dot = document.getElementById('pipe-status-dot');
                if (dot) {
                    dot.className = `status-blob blob-${pipe.status === 'success' ? 'passed' : (pipe.status === 'failed' ? 'failed' : 'pending')}`;
                }
            }
        } catch (e) { }

        // 3. 为可见用例加载历史轨迹
        const visibleIids = Array.from(document.querySelectorAll('.js-test-card')).map(c => {
            return c.dataset.iid;
        }).filter(id => id);

        for (let iid of visibleIids) {
            this.updateItemHistory(iid);
        }
    },

    async updateItemHistory(iid) {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;

        try {
            const history = await Api.get(`/projects/${projectId}/test-cases/${iid}/history`);

            // 更新趋势圆点
            const trend = document.getElementById(`trend-${iid}`);
            if (trend) {
                trend.innerHTML = '';
                history.slice(0, 10).reverse().forEach(h => {
                    const blob = document.createElement('div');
                    blob.className = `status-blob blob-${h.result} u-square-16 u-opacity-60`;
                    blob.title = `${h.result} @ ${new Date(h.executed_at).toLocaleString()}`;
                    trend.appendChild(blob);
                });
            }

            // 审计历史列表 (取前 3 条)
            const list = document.getElementById(`history-${iid}`);
            if (list) {
                list.innerHTML = '';
                history.slice(0, 3).forEach(h => {
                    const item = document.createElement('div');
                    item.className = 'u-text-dim u-flex u-align-center u-gap-8 u-text-tiny';

                    const res = document.createElement('span');
                    res.className = `u-weight-600 ${h.result === 'passed' ? 'u-text-success' : 'u-text-error'}`;
                    res.textContent = h.result.toUpperCase();

                    const name = document.createTextNode(` by ${h.executor.split(' ')[0]} `);

                    const time = document.createElement('span');
                    time.className = 'u-opacity-60 u-text-tiny';
                    time.textContent = new Date(h.executed_at).toLocaleTimeString();

                    item.appendChild(res);
                    item.appendChild(name);
                    item.appendChild(time);
                    list.appendChild(item);
                });
            }

            // 如果最后一次失败，显示 Bug 按钮
            const bugBtn = document.getElementById(`bug-btn-${iid}`);
            if (bugBtn) {
                if (history[0] && history[0].result === 'failed') {
                    bugBtn.classList.remove('u-hide');
                    bugBtn.classList.add('u-flex');
                } else {
                    bugBtn.classList.add('u-hide');
                    bugBtn.classList.remove('u-flex');
                }
            }
        } catch (e) { }
    },

    /**
     * 资产库管理
     */
    async loadAssetLibrary() {
        UI.toggleLoading("Loading assets...", true);
        try {
            const assets = await Api.get('/assets/test-cases');
            const list = document.getElementById('assetList');
            const template = document.getElementById('qa-asset-card-tpl');
            if (list && template) {
                list.innerHTML = '';
                if (assets.length === 0) {
                    const empty = document.createElement('div');
                    empty.className = 'empty-state';
                    empty.textContent = 'No assets found.';
                    list.appendChild(empty);
                } else {
                    assets.forEach(a => {
                        const clone = template.content.cloneNode(true);
                        clone.querySelector('.js-asset-title').textContent = a.title;
                        clone.querySelector('.js-asset-meta').textContent = `${a.priority} | ${a.test_type}`;
                        const btn = clone.querySelector('.js-asset-import');
                        btn.addEventListener('click', () => this.importAsset(a.iid, a.project_id));
                        list.appendChild(clone);
                    });
                }
            }
            UI.showModal('assetModalOverlay');
        } catch (e) {
            UI.showToast("Failed to load assets", "error");
        } finally {
            UI.toggleLoading("", false);
        }
    },

    async importAsset(iid, pid) {
        UI.showToast(`Importing asset ${iid} from project ${pid}...`, "info");
        // TODO: Implement actual asset import
    }
};

export default SysUtilsHandler;
