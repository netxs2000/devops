/**
 * @file service-desk.js
 * @description R&D 视角的工单处理模块。
 */

/**
 * 加载待处理的工单列表
 */
async function loadServiceDeskTickets() {
    const list = document.getElementById('servicedesk-list');
    list.innerHTML = '<div style="padding:20px; color:var(--accent);">Synchronizing with business portal...</div>';

    try {
        const tickets = await Api.get(`/service-desk/tickets`);
        if (tickets.length === 0) {
            list.innerHTML = '<div style="padding:40px; text-align:center; color:rgba(255,255,255,0.3);">No pending business feedback.</div>';
            return;
        }

        list.innerHTML = tickets.map(t => `
            <div class="test-item" style="border-left: 4px solid var(--accent); display:flex; justify-content:space-between; padding:15px; background:rgba(255,255,255,0.02); margin-bottom:10px; border-radius:8px;">
                <div class="test-main">
                    <span class="priority-tag" style="background:rgba(0,255,255,0.1); color:var(--accent); padding:2px 6px; border-radius:4px; font-size:12px;">#${t.iid}</span>
                    <div class="test-title" style="font-weight:600; margin:5px 0;">${t.title}</div>
                    <div class="test-meta" style="font-size:12px; color:var(--text-dim);">From: ${t.requester_email.split('@')[0]} | Created: ${t.created_at}</div>
                </div>
                <div class="test-actions" style="display:flex; gap:8px; align-items:center;">
                    <button class="btn-action-small" onclick="convertToProfessionalBug(${t.iid}, '${t.title.replace(/'/g, "\\'")}')">🐞 Defect</button>
                    <button class="btn-action-small" onclick="convertToProfessionalReq(${t.iid}, '${t.title.replace(/'/g, "\\'")}')">📐 Req</button>
                    <button class="btn-action-small btn-reject" onclick="rejectTicket(${t.iid}, ${t.project_id})">✕ Dismiss</button>
                    <button class="btn-action-small btn-ai" onclick="openRCAAssistant(${t.iid}, ${t.project_id})">🧠 AI RCA</button>
                </div>
            </div>
        `).join('');
    } catch (e) {
        list.innerHTML = `<div style="padding:20px; color:var(--failed);">${e.message}</div>`;
    }
}

/**
 * 驳回工单
 */
async function rejectTicket(iid, projectId) {
    const reason = prompt("Select reason for rejection:\n1. Invalid Data\n2. Works as Intended\n3. Out of Scope\n\nOr type custom reason:");
    if (!reason) return;

    UI.toggleLoading("Closing feedback...", true);

    try {
        await Api.post(`/service-desk/tickets/${iid}/reject`, { project_id: projectId, reason: reason });
        UI.showToast(`Ticket #${iid} has been dismissed.`, "success");
        loadServiceDeskTickets();
    } catch (e) {
        alert(e.message);
    } finally {
        UI.toggleLoading("", false);
    }
}

/**
 * 将工单转为专业缺陷并预填充
 */
async function convertToProfessionalBug(iid, title) {
    currentBugItemId = iid;
    const titleInput = document.getElementById('quick-bug-title');
    const stepsInput = document.getElementById('bug_steps');

    if (titleInput) titleInput.value = `[Bug Transferred] ${title}`;
    if (stepsInput) stepsInput.value = `Reference Ticket: #${iid}\n\n---\nSteps:`;

    switchView('test-cases');
    createBug(iid); // 借用已有的弹窗逻辑
}

/**
 * 将工单转为专业需求并预填充
 */
async function convertToProfessionalReq(iid, title) {
    const reqTitle = document.getElementById('req_title');
    const reqValue = document.getElementById('req_value');

    if (reqTitle) reqTitle.value = `[Req Transferred] ${title}`;
    if (reqValue) reqValue.value = `Origin User Request: #${iid}\n\nPlease refine business goals here.`;

    switchView('requirements');
    openReqModal();
}
