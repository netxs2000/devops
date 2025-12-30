/**
 * @file utils.js
 * @description 杂项辅助函数，包括 GitLab 链接生成和历史记录渲染。
 */

/**
 * 加载额外数据（最近项目、流水线状态、用例历史）
 */
async function loadExtraData() {
    const projectId = document.getElementById('projectId').value;

    // 1. 最近项目
    try {
        const projects = await Api.get('/recent-projects');
        const container = document.getElementById('recentProjects');
        if (container) {
            container.innerHTML = projects.map(id => `
                <div class="nav-link" style="cursor:pointer;" onclick="document.getElementById('projectId').value=${id}; loadTestCases();">
                    <span style="opacity:0.5">#</span> PID ${id}
                </div>
            `).join('');
        }
    } catch (e) { }

    // 2. 流水线状态
    try {
        const pipe = await Api.get(`/projects/${projectId}/pipeline-status`);
        const monitor = document.getElementById('pipelineMonitor');
        if (monitor && pipe.status !== 'unknown') {
            monitor.style.display = 'block';
            document.getElementById('pipe-info').innerText = `#${pipe.id} [${pipe.sha}]`;
            const dot = document.getElementById('pipe-status-dot');
            dot.className = `status-blob blob-${pipe.status === 'success' ? 'passed' : (pipe.status === 'failed' ? 'failed' : 'pending')}`;
        }
    } catch (e) { }

    // 3. 为可见用例加载历史轨迹
    const visibleIids = Array.from(document.querySelectorAll('.test-card')).map(c => c.className.match(/card-(\d+)/)[1]);
    for (let iid of visibleIids) {
        updateItemHistory(iid);
    }
}

async function updateItemHistory(iid) {
    const projectId = document.getElementById('projectId').value;
    try {
        const history = await Api.get(`/projects/${projectId}/test-cases/${iid}/history`);

        // 更新趋势圆点
        const trend = document.getElementById(`trend-${iid}`);
        if (trend) {
            trend.innerHTML = history.slice(0, 10).reverse().map(h => `
                <div class="status-blob blob-${h.result}" style="width:6px; height:6px; opacity:0.6" title="${h.result} @ ${new Date(h.executed_at).toLocaleString()}"></div>
            `).join('');
        }

        // 审计历史列表 (取前 3 条)
        const list = document.getElementById(`history-${iid}`);
        if (list) {
            list.innerHTML = history.slice(0, 3).map(h => `
                <div style="color:var(--text-dim); display:flex; align-items:center; gap:4px; font-size:12px;">
                    <span style="color:var(--${h.result === 'passed' ? 'passed' : 'failed'}); font-weight:600;">${h.result.toUpperCase()}</span> 
                    by ${h.executor.split(' ')[0]} 
                    <span style="opacity:0.4; font-size:10px;">${new Date(h.executed_at).toLocaleTimeString()}</span>
                </div>
            `).join('');
        }

        // 如果最后一次失败，显示 Bug 按钮
        const bugBtn = document.getElementById(`bug-btn-${iid}`);
        if (bugBtn) {
            bugBtn.style.display = (history[0] && history[0].result === 'failed') ? 'flex' : 'none';
        }
    } catch (e) { }
}

/**
 * 资产库管理
 */
async function loadAssetLibrary() {
    UI.toggleLoading("Loading assets...", true);
    try {
        const assets = await Api.get('/assets/test-cases');
        const list = document.getElementById('assetList');
        if (list) {
            list.innerHTML = assets.map(a => `
                <div class="asset-card" style="display:flex; justify-content:space-between; padding:12px; background:rgba(255,255,255,0.02); margin-bottom:10px; border-radius:8px;">
                    <div class="asset-info">
                        <h4 style="margin:0;">${a.title}</h4>
                        <div style="font-size:12px; color:var(--text-dim);">${a.priority} | ${a.test_type}</div>
                    </div>
                    <button class="btn-primary" style="padding:4px 12px; font-size:12px;" onclick="importAsset(${a.iid}, ${a.project_id})">Import</button>
                </div>
            `).join('') || '<div class="empty-state">No assets found.</div>';
        }
        document.getElementById('assetModalOverlay').style.display = 'flex';
    } catch (e) {
        alert("Failed to load assets");
    } finally {
        UI.toggleLoading("", false);
    }
}
