/**
 * @file defects.js
 * @description 缺陷管理与 AI RCA 分析。
 */

let currentBugItemId = null;
let currentPastedBlob = null;

/**
 * 加载并显示缺陷列表
 */
async function loadBugs() {
    const projectId = document.getElementById('projectId').value;
    if (!projectId) return;

    try {
        const bugs = await Api.get(`/projects/${projectId}/bugs`);
        const container = document.getElementById('bugResults');

        const open = bugs.filter(b => b.state === 'opened');
        const closed = bugs.filter(b => b.state === 'closed');
        const rate = bugs.length > 0 ? Math.round((closed.length / bugs.length) * 100) : 0;

        const rateEl = document.getElementById('bug-fix-rate');
        const countEl = document.getElementById('bug-open-count');
        if (rateEl) rateEl.innerText = `${rate}%`;
        if (countEl) countEl.innerText = open.length;

        container.innerHTML = bugs.map(b => `
            <div class="test-card">
                <div class="test-header" style="cursor:default">
                    <div class="test-info">
                        <div class="status-blob blob-${b.state === 'closed' ? 'passed' : 'failed'}"></div>
                        <div class="test-title-group">
                            <span class="test-iid">#${b.iid}</span>
                            <a href="${b.web_url}" target="_blank" class="test-title" style="text-decoration:none; color:white;">${b.title}</a>
                        </div>
                    </div>
                    <div class="test-badges">
                        ${(b.labels || []).map(l => `<span class="tag-badge">${l}</span>`).join('')}
                        <span class="tag-badge" style="background:${b.state === 'opened' ? 'rgba(239,68,68,0.1)' : 'rgba(16,185,129,0.1)'}">${b.state.toUpperCase()}</span>
                    </div>
                </div>
            </div>
        `).join('') || '<div class="empty-state">No bugs tracking for this project.</div>';
    } catch (e) {
        console.error("Failed to load bugs", e);
    }
}

/**
 * 打开报告缺陷的弹窗
 */
function createBug(iid) {
    currentBugItemId = iid;
    currentPastedBlob = null;

    const card = document.querySelector(`.card-${iid}`);
    const title = card ? card.querySelector('.test-title').innerText : "Unknown";

    document.getElementById('bug-target-id').innerText = `#${iid}`;
    document.getElementById('quick-bug-title').value = `[BUG] Failure in #${iid}: ${title}`;

    // Reset preview
    const preview = document.getElementById('img-preview');
    if (preview) preview.style.display = 'none';

    document.getElementById('bugModalOverlay').style.display = 'flex';
}

function closeBugModal() {
    document.getElementById('bugModalOverlay').style.display = 'none';
}

/**
 * 提交缺陷到后端
 */
async function submitQuickBug() {
    const projectId = document.getElementById('projectId').value;
    const title = document.getElementById('quick-bug-title').value;
    if (!title) return alert("Defect title is mandatory");

    const payload = {
        title: title,
        severity: document.getElementById('bug_severity').value,
        priority: document.getElementById('bug_priority').value,
        category: document.getElementById('bug_category').value,
        env: document.getElementById('bug_env').value,
        steps: document.getElementById('bug_steps').value,
        expected: document.getElementById('bug_expected').value,
        actual: document.getElementById('bug_actual').value,
        related_test_case_iid: currentBugItemId
    };

    const btn = event.currentTarget;
    btn.disabled = true;
    btn.innerText = "Reporting...";

    try {
        let imageListMd = "";
        // 上传粘贴的图片证据
        if (currentPastedBlob) {
            btn.innerText = "Uploading Evidence...";
            const formData = new FormData();
            formData.append('file', currentPastedBlob, 'screenshot.png');

            const uploadRes = await fetch(`/projects/${projectId}/upload`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${Auth.getToken()}` },
                body: formData
            });
            if (uploadRes.ok) {
                const uploadData = await uploadRes.json();
                imageListMd = `\n\n### 🖼️ Evidence Snapshot\n${uploadData.markdown}\n`;
            }
        }

        payload.actual += imageListMd;

        const data = await Api.post(`/projects/${projectId}/defects`, payload);
        alert(`Professional Defect #${data.iid} reported!`);
        closeBugModal();
        loadTestCases(true);
    } catch (err) {
        alert("Bug Portal Error: " + err.message);
    } finally {
        btn.disabled = false;
        btn.innerText = "Submit Defect";
    }
}

/**
 * AI RCA 分析
 */
async function openRCAAssistant(iid, projectId) {
    const overlay = document.getElementById('rcaModalOverlay');
    const titleEl = document.getElementById('rca-target-title');
    const suggsUl = document.getElementById('rca-suggestions');
    const impactDiv = document.getElementById('rca-impact');
    const similarDiv = document.getElementById('rca-similar');

    titleEl.innerText = `Analyzing Ticket #${iid}...`;
    suggsUl.innerHTML = '<li>AI 正在检索知识库...</li>';
    impactDiv.innerText = 'Calculating impact scope...';
    similarDiv.innerHTML = '';
    overlay.style.display = 'flex';

    try {
        const data = await Api.get(`/projects/${projectId}/defects/${iid}/rca`);
        titleEl.innerText = `RCA Findings for: ${data.title}`;
        suggsUl.innerHTML = data.suggestions.map(s => `<li>${s}</li>`).join('');
        impactDiv.innerText = data.impact_scope;

        if (data.similar_cases.length === 0) {
            similarDiv.innerHTML = '<div style="font-size:12px; opacity:0.5;">No similar closed cases found.</div>';
        } else {
            similarDiv.innerHTML = data.similar_cases.map(c => `
                <div style="background:rgba(255,255,255,0.03); padding:10px; border-radius:8px; border-left:3px solid var(--accent);">
                    <div style="font-weight:600; font-size:13px; color:white;">#${c.iid} ${c.title}</div>
                    <div style="font-size:11px; color:var(--text-dim); margin-top:4px;">Solution: ${c.solution}</div>
                </div>
            `).join('');
        }
    } catch (e) {
        suggsUl.innerHTML = `<li style="color:var(--failed);">AI Analysis Failed: ${e.message}</li>`;
    }
}

/**
 * 监听粘贴事件获取图片
 */
document.addEventListener('paste', function (e) {
    if (document.getElementById('bugModalOverlay').style.display !== 'flex') return;

    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (let index in items) {
        const item = items[index];
        if (item.kind === 'file' && item.type.includes('image')) {
            const blob = item.getAsFile();
            currentPastedBlob = blob;
            const reader = new FileReader();
            reader.onload = function (event) {
                const preview = document.getElementById('img-preview');
                if (preview) {
                    preview.src = event.target.result;
                    preview.style.display = 'block';
                }
            };
            reader.readAsDataURL(blob);
        }
    }
});
