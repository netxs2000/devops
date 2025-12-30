/**
 * @file requirements.js
 * @description 需求生命周期管理、审批流与冲突分析。
 */

/**
 * 加载需求列表
 */
async function loadRequirements() {
    const projectId = document.getElementById('projectId').value;
    if (!projectId) return;

    const container = document.getElementById('reqResults');
    container.innerHTML = '<div class="empty-state">Loading Requirements...</div>';

    try {
        const [reqs, stats] = await Promise.all([
            Api.get(`/projects/${projectId}/requirements`),
            Api.get(`/projects/${projectId}/requirements/stats`)
        ]);

        updateRequirementStats(stats);
        renderRequirementCards(reqs, stats.risk_requirements.map(r => r.iid));
    } catch (e) {
        container.innerHTML = `<div class="empty-state" style="color:var(--failed)">Failed to load: ${e.message}</div>`;
    }
}

function updateRequirementStats(stats) {
    const map = {
        'req-coverage-rate': `${stats.coverage_rate}%`,
        'req-pass-rate': `${stats.pass_rate}%`,
        'req-risk-count': stats.risk_requirements.length,
        'req-approved-total': stats.approved_count
    };
    for (let id in map) {
        const el = document.getElementById(id);
        if (el) el.innerText = map[id];
    }
}

function renderRequirementCards(reqs, riskIids) {
    const container = document.getElementById('reqResults');
    container.innerHTML = reqs.map(r => {
        const statusInfo = {
            'draft': { label: 'Draft', color: 'var(--pending)', next: 'under-review', nextLabel: 'Submit for Review' },
            'under-review': { label: 'Reviewing', color: 'var(--blocked)', next: 'approved', nextLabel: 'Approve' },
            'approved': { label: 'Approved', color: 'var(--passed)', next: 'rejected', nextLabel: 'Reset/Reject' },
            'rejected': { label: 'Rejected', color: 'var(--failed)', next: 'draft', nextLabel: 'Back to Draft' }
        }[r.review_state];

        const isRisk = riskIids.includes(r.iid) && r.review_state === 'approved';

        return `
            <div class="test-card" style="${isRisk ? 'border-left: 4px solid var(--failed);' : ''}">
                <div class="test-header" style="cursor:default">
                    <div class="test-info">
                        <div class="status-blob" style="background:${statusInfo.color}; box-shadow: 0 0 10px ${statusInfo.color}"></div>
                        <div class="test-title-group">
                            <div style="display:flex; align-items:center; gap:8px;">
                                <span class="test-iid">#${r.iid}</span>
                                ${isRisk ? '<span style="font-size:10px; color:var(--failed); font-weight:700;">⚠ AT RISK</span>' : ''}
                            </div>
                            <span class="test-title">${r.title}</span>
                        </div>
                    </div>
                    <div style="display:flex; gap:12px; align-items:center;">
                        <span class="tag-badge" style="background:${statusInfo.color}22; color:${statusInfo.color}">${statusInfo.label}</span>
                        <button class="btn-shelf" onclick="updateReviewStatus(${r.iid}, '${statusInfo.next}')">${statusInfo.nextLabel}</button>
                        <button class="btn-shelf" onclick="checkConflictsForId(${r.iid})" title="Check conflicts">⚖️</button>
                    </div>
                </div>
            </div>
        `;
    }).join('') || '<div class="empty-state">No requirements. Click "+ Req" to add.</div>';
}

/**
 * 提交新需求
 */
async function submitRequirement() {
    const projectId = document.getElementById('projectId').value;
    if (!projectId) return alert("Select a project first");

    const payload = {
        title: document.getElementById('req_title').value,
        priority: document.getElementById('req_priority').value,
        category: document.getElementById('req_category').value,
        business_value: document.getElementById('req_value').value,
        acceptance_criteria: Array.from(document.querySelectorAll('#acContainer .ac-row input')).map(i => i.value).filter(v => v)
    };

    if (!payload.title) return alert("Title is mandatory");

    UI.toggleLoading("📐 Engineering Requirement to GitLab...", true);

    try {
        const res = await fetch(`/projects/${projectId}/requirements`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${Auth.getToken()}`
            },
            body: JSON.stringify(payload)
        });

        const data = await res.json();
        if (res.ok) {
            UI.showToast("DOR Passed: Requirement deployed!", "success");
            closeReqModal();
            loadRequirements();
        } else {
            alert("🚧 DOR Violation:\n" + (data.detail || "Deployment failed"));
        }
    } catch (e) {
        alert("Error: " + e.message);
    } finally {
        UI.toggleLoading("", false);
    }
}

async function updateReviewStatus(iid, nextState) {
    const projectId = document.getElementById('projectId').value;
    UI.toggleLoading("Updating review state...", true);
    try {
        await Api.post(`/projects/${projectId}/requirements/${iid}/review?review_state=${nextState}`);
        loadRequirements();
    } catch (e) {
        alert(e.message);
    } finally {
        UI.toggleLoading("", false);
    }
}

/**
 * 语义冲突扫描
 */
async function runDeduplicationScan() {
    const projectId = document.getElementById('projectId').value;
    if (!projectId) return alert("Select a project first");

    UI.toggleLoading("🧠 AI Semantic Scanning...", true);

    try {
        const data = await Api.get(`/projects/${projectId}/deduplication/scan?type=requirement`);

        document.getElementById('dedup-saving-val').innerText = `${data.saving_potential}%`;
        document.getElementById('dedup-group-count').innerText = data.total_groups;

        const list = document.getElementById('dedup-results-list');
        if (data.clusters.length === 0) {
            list.innerHTML = '<div class="empty-state">No duplicates detected. ✨</div>';
        } else {
            list.innerHTML = data.clusters.map(c => `
                <div class="dedup-group">
                    <div class="prime-issue"><b>PRIME:</b> #${c.prime.iid} ${c.prime.title}</div>
                    ${c.duplicates.map(d => `<div class="dup-issue">Similiar: #${d.iid} ${d.title}</div>`).join('')}
                    <div style="margin-top:10px;">
                        <button class="btn-primary" style="font-size:11px; padding:4px 10px; background:var(--passed);">Merge into Prime</button>
                    </div>
                </div>
            `).join('');
        }
        document.getElementById('dedupModalOverlay').style.display = 'flex';
    } catch (e) {
        alert("AI Scan Error: " + e.message);
    } finally {
        UI.toggleLoading("", false);
    }
}

function openReqModal() { document.getElementById('reqModalOverlay').style.display = 'flex'; }
function closeReqModal() { document.getElementById('reqModalOverlay').style.display = 'none'; }
function addACRow() {
    const container = document.getElementById('acContainer');
    const row = document.createElement('div');
    row.className = 'ac-row';
    row.style.cssText = "display:flex; gap:10px; margin-bottom:8px;";
    row.innerHTML = `
        <input type="text" class="form-control" placeholder="Requirement defined as met when..." style="flex:1;">
        <button class="btn-action" style="color:var(--failed); border:none; background:transparent;" onclick="this.parentElement.remove()">✕</button>
    `;
    container.appendChild(row);
}
