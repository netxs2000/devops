/**
 * @file test-cases.js
 * @description 测试用例管理模块。
 */

/**
 * 加载并渲染测试用例列表
 * @param {boolean} silent 是否静默加载（不显示 loading 遮罩）
 */
async function loadTestCases(silent = false) {
    const projectId = document.getElementById('projectId').value;
    if (!projectId) return alert("Project ID Required");

    const resultsDiv = document.getElementById('results');
    if (!silent) {
        resultsDiv.innerHTML = '<div class="empty-state">Decoding GitLab Objects...</div>';
        UI.toggleLoading("Decoding GitLab Objects...", true);
    }

    try {
        const [data, summary] = await Promise.all([
            Api.get(`/projects/${projectId}/test-cases`),
            Api.get(`/projects/${projectId}/test-summary`)
        ]);

        UI.toggleLoading("", false);

        // 更新头部信息
        const titleEl = document.getElementById('projectTitle');
        if (titleEl) titleEl.innerText = `Viewing Suite for PID: ${projectId} • ${data.length} Scenarios`;

        updateSummaryStats(data, summary);

        if (data.length === 0) {
            resultsDiv.innerHTML = '<div class="empty-state">No structured "type::test" issues found.</div>';
            return;
        }

        renderTestCaseCards(data, resultsDiv);
        loadExtraData(); // 加载最近项目和流水线状态
    } catch (err) {
        UI.toggleLoading("", false);
        console.error(err);
        alert("Sync Failed: " + err.message);
    }
}

/**
 * 渲染统计卡片
 */
function updateSummaryStats(data, summary) {
    let totalBugs = 0;
    data.forEach(item => totalBugs += (item.linked_bugs ? item.linked_bugs.length : 0));

    const getVal = (id) => parseInt(document.getElementById(id)?.innerText) || 0;

    UI.animateValue('stat-passed', getVal('stat-passed'), summary.passed, 500);
    UI.animateValue('stat-failed', getVal('stat-failed'), summary.failed, 500);
    UI.animateValue('stat-total', getVal('stat-total'), summary.total, 500);
    UI.animateValue('stat-bugs', getVal('stat-bugs'), totalBugs, 500);

    const bugAlert = document.getElementById('bug-alert-icon');
    if (bugAlert) bugAlert.style.display = totalBugs > 5 ? 'block' : 'none';

    const rate = summary.total > 0 ? Math.round((summary.passed / summary.total) * 100) : 0;
    UI.animateValue('stat-rate', getVal('stat-rate'), rate, 500);

    const grid = document.getElementById('statsGrid');
    if (grid) grid.style.display = 'grid';
}

/**
 * 渲染测试用例卡片
 */
function renderTestCaseCards(data, container) {
    container.innerHTML = '';
    data.forEach(item => {
        const card = document.createElement('div');
        card.className = `test-card card-${item.iid}`;

        const stepsHtml = (item.steps || []).map(s => `
            <div class="step-item">
                <div class="step-count">${s.step_number}</div>
                <div class="step-text">
                    <div class="step-action-text">${s.action}</div>
                    <div class="step-expected-text">${s.expected_result}</div>
                </div>
            </div>
        `).join('');

        const isStale = (item.labels || []).includes('status::stale');

        card.innerHTML = `
            <div class="test-header">
                <div class="test-info">
                    <div class="custom-checkbox" onclick="toggleSelection(${item.iid}, event)"></div>
                    <div class="status-blob blob-${item.result}"></div>
                    <div class="test-title-group" onclick="toggleTestCase(${item.iid})">
                        <span class="test-iid">#${item.iid}</span>
                        <span class="test-title">${item.title}</span>
                        ${isStale ? '<span class="status-stale-badge" title="Requirement changed!">⚠️ Outdated</span>' : ''}
                    </div>
                </div>
                <div class="test-badges">
                    <span class="tag-badge tag-priority-${item.priority}">${item.priority}</span>
                    <span class="tag-badge">${item.test_type}</span>
                    <div class="btn-action">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg>
                    </div>
                </div>
            </div>
            <div id="trend-${item.iid}" class="trend-dots" style="padding: 0 24px 10px; display: flex; gap: 4px;"></div>
            <div class="test-content" id="content-${item.iid}">
                <div class="grid-detail">
                    <div class="flow-zone">
                        <div class="section-label">Execution Flow</div>
                        <div class="steps-list">${stepsHtml || '<p style="color:var(--text-dim);">No steps.</p>'}</div>
                    </div>
                    <div class="meta-zone">
                        <div class="section-label">Traceability</div>
                        <div class="meta-pill"><b>Requirement</b> <span>${item.requirement_id ? '#' + item.requirement_id : 'None'}</span></div>
                        <div class="meta-pill"><b>Defects</b> <div>${renderBugPills(item.linked_bugs)}</div></div>
                        <div class="meta-pill"><b>Pre-conditions</b><p>${item.pre_conditions.join('<br>') || 'None'}</p></div>
                        <a href="${item.web_url}" target="_blank" class="gitlab-link">View in GitLab</a>
                        <div id="history-container-${item.iid}" style="margin-top:20px;">
                            <div class="section-label">Audit Trail</div>
                            <div id="history-${item.iid}" class="history-list"></div>
                        </div>
                    </div>
                </div>
                <div class="execution-shelf">
                    <button class="btn-shelf" id="bug-btn-${item.iid}" style="display:none;" onclick="createBug(${item.iid})">Report Bug</button>
                    <button class="btn-shelf btn-warn" onclick="executeTest(${item.iid}, 'blocked')">Block</button>
                    <button class="btn-shelf btn-error" onclick="executeTest(${item.iid}, 'failed')">Fail</button>
                    <button class="btn-shelf btn-magic" onclick="generateMagicCode(${item.iid})">Magic Code</button>
                    <button class="btn-shelf btn-success" onclick="executeTest(${item.iid}, 'passed')">Pass Case</button>
                    ${isStale ? `<button class="btn-shelf btn-ack" onclick="ackTestChange(${item.iid})">✓ Sync & Ack</button>` : ''}
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderBugPills(bugs) {
    if (!bugs || bugs.length === 0) return '<span style="color:var(--text-dim);">No defects</span>';
    return bugs.map(b => `<span class="bug-pill">#${b.iid}</span>`).join('');
}

/**
 * 执行测试用例
 */
async function executeTest(issueIid, result) {
    const projectId = document.getElementById('projectId').value;
    const btn = event.target;
    const originalHtml = btn.innerHTML;

    btn.disabled = true;
    btn.innerHTML = "Submitting...";

    try {
        const data = await Api.post(`/projects/${projectId}/test-cases/${issueIid}/execute?result=${result}`);
        if (data.status === 'success') {
            const blob = document.querySelector(`.card-${issueIid} .status-blob`);
            if (blob) blob.className = `status-blob blob-${result}`;
            loadTestCases(true); // 静默刷新数据
        }
    } catch (err) {
        alert("Execution Error: " + err.message);
        btn.disabled = false;
        btn.innerHTML = originalHtml;
    }
}

/**
 * 批量通过已选中的用例
 */
async function executeBatchPass() {
    if (selectedIids.size === 0) return alert("Please select test cases first");
    const projectId = document.getElementById('projectId').value;

    if (!confirm(`Mark ${selectedIids.size} cases as PASSED?`)) return;

    UI.toggleLoading(`Batch Processing ${selectedIids.size} items...`, true);

    try {
        const tasks = Array.from(selectedIids).map(iid =>
            Api.post(`/projects/${projectId}/test-cases/${iid}/execute?result=passed`)
        );
        await Promise.all(tasks);
        selectedIids.clear();
        UI.showToast("Batch execution completed!", "success");
        loadTestCases();
    } catch (err) {
        alert("Batch execution failed: " + err.message);
    } finally {
        UI.toggleLoading("", false);
    }
}

/**
 * 确认需求变更
 */
async function ackTestChange(iid) {
    const projectId = document.getElementById('projectId').value;
    try {
        const res = await Api.post(`/projects/${projectId}/test-cases/${iid}/ack`, {});
        if (res.ok) {
            UI.showToast(`Test #${iid} synced and active.`, "success");
            loadTestCases();
        }
    } catch (e) {
        UI.showToast("Failed to acknowledge change", "error");
    }
}

/**
 * [AI 核心] 魔法填充步骤。
 * 根据当前填写的关联需求 ID，调用 AI 生成测试路径。
 */
async function generateMagicSteps() {
    const projectId = document.getElementById('projectId').value;
    const reqIid = document.getElementById('new_req_iid').value;

    if (!projectId || !reqIid) {
        return UI.showToast("请先选择项目并填入关联需求 ID", "warning");
    }

    UI.toggleLoading(true, "🪄 AI 正在深度解析验收标准 (AC)...");

    try {
        const res = await Api.post(`/projects/${projectId}/test-cases/generate-from-ac?requirement_iid=${reqIid}`);
        const data = await res.json();

        if (data.error) throw new Error(data.error);

        // 提示发现的 AC 数量
        UI.showToast(`AI 已解析 ${data.ac_found} 条验收标准并生成步骤`, "success");

        // 清空现有步骤并自动回填
        const container = document.getElementById('stepsContainer');
        container.innerHTML = ''; // 清空

        if (data.steps && data.steps.length > 0) {
            data.steps.forEach(step => {
                const row = document.createElement('div');
                row.className = 'step-row';
                row.style.display = 'flex';
                row.style.gap = '8px';
                row.style.marginBottom = '8px';
                row.innerHTML = `
                    <input type="text" placeholder="Action" class="form-control step-action" style="flex:2;" value="${step.action}">
                    <input type="text" placeholder="Expected" class="form-control step-expected" style="flex:1;" value="${step.expected}">
                `;
                container.appendChild(row);
            });
        }

        if (data.warning) {
            UI.showToast(data.warning, "warning");
        }

    } catch (err) {
        UI.showToast("AI 生成失败: " + err.message, "error");
    } finally {
        UI.toggleLoading(false);
    }
}

function toggleTestCase(iid) {
    const content = document.getElementById(`content-${iid}`);
    document.querySelectorAll('.test-content').forEach(c => {
        if (c.id !== `content-${iid}`) c.classList.remove('active');
    });
    content.classList.toggle('active');
}

let selectedIids = new Set();
function toggleSelection(iid, event) {
    event.stopPropagation();
    const checkbox = event.currentTarget;
    if (selectedIids.has(iid)) {
        selectedIids.delete(iid);
        checkbox.classList.remove('checked');
    } else {
        selectedIids.add(iid);
        checkbox.classList.add('checked');
    }
}
