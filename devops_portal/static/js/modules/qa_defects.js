import { Auth, Api, UI } from './sys_core.js';
import QaTestCaseHandler from './qa_test_cases.js';

const QaDefectHandler = {
    currentBugItemId: null,
    currentPastedBlob: null,

    /**
     * 初始化事件监听器 (事件委派)
     */
    init() {
        const modal = document.getElementById('bugModalOverlay');
        if (modal && !modal.dataset.initialized) {
            modal.addEventListener('click', (e) => {
                const target = e.target;
                if (target.classList.contains('js-btn-close-bug-modal')) this.closeModal();
                if (target.classList.contains('js-btn-submit-bug')) this.submit(e);
            });
            this.initPasteListener();
            modal.dataset.initialized = "true";
        }
    },

    /**
     * 关闭模态框
     */
    closeModal() {
        UI.hideModal('bugModalOverlay');
        this.currentBugItemId = null;
        this.currentPastedBlob = null;
        const preview = document.getElementById('img-preview');
        if (preview) {
            preview.src = '';
            preview.classList.add('u-hide');
        }
    },

    /**
     * 粘贴监听
     */
    initPasteListener() {
        document.addEventListener('paste', (e) => {
            const modal = document.getElementById('bugModalOverlay');
            if (!modal || modal.classList.contains('u-hide')) return;

            const items = (e.clipboardData || e.originalEvent.clipboardData).items;
            for (let index in items) {
                const item = items[index];
                if (item.kind === 'file' && item.type.includes('image')) {
                    const blob = item.getAsFile();
                    this.currentPastedBlob = blob;
                    const reader = new FileReader();
                    reader.onload = (event) => {
                        const preview = document.getElementById('img-preview');
                        if (preview) {
                            preview.src = event.target.result;
                            preview.classList.remove('u-hide');
                        }
                    };
                    reader.readAsDataURL(blob);
                }
            }
        });
    },

    /**
     * 加载缺陷列表
     */
    async load() {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;
        if (!projectId) return;

        this.init();

        try {
            const bugs = await Api.get(`/projects/${projectId}/bugs`);
            const container = document.getElementById('bugResults');
            if (!container) return;

            const open = bugs.filter(b => b.state === 'opened');
            const closed = bugs.filter(b => b.state === 'closed');
            const rate = bugs.length > 0 ? Math.round((closed.length / bugs.length) * 100) : 0;

            const rateEl = document.getElementById('bug-fix-rate');
            const countEl = document.getElementById('bug-open-count');
            if (rateEl) rateEl.textContent = `${rate}%`;
            if (countEl) countEl.textContent = open.length;

            container.innerHTML = '';

            if (bugs.length === 0) {
                const empty = document.createElement('div');
                empty.className = 'empty-state';
                empty.textContent = 'No bugs tracking for this project.';
                container.appendChild(empty);
                return;
            }

            const template = document.getElementById('qa-defect-tpl');
            const fragment = document.createDocumentFragment();

            bugs.forEach(b => {
                const clone = template.content.cloneNode(true);
                const statusBlob = clone.querySelector('.js-defect-status-blob');
                statusBlob.classList.add(`blob-${b.state === 'closed' ? 'passed' : 'failed'}`);

                clone.querySelector('.js-defect-iid').textContent = `#${b.iid}`;

                const titleLink = clone.querySelector('.js-defect-title');
                titleLink.textContent = b.title;
                titleLink.href = b.web_url;

                const badgeContainer = clone.querySelector('.js-defect-badges');
                if (b.labels && b.labels.length > 0) {
                    b.labels.forEach(l => {
                        const span = document.createElement('span');
                        span.className = 'tag-badge';
                        span.textContent = l;
                        badgeContainer.insertBefore(span, badgeContainer.firstChild);
                    });
                }

                const stateBadge = clone.querySelector('.js-defect-state');
                stateBadge.textContent = b.state.toUpperCase();
                stateBadge.classList.add(b.state === 'opened' ? 'u-bg-error-10' : 'u-bg-success-10');

                fragment.appendChild(clone);
            });

            container.appendChild(fragment);

        } catch (e) {
            console.error("Failed to load bugs", e);
            UI.showToast("Bug Load Failed: " + e.message, "error");
        }
    },

    /**
     * 初始化报告缺陷弹窗
     */
    initCreateForm(iid) {
        this.currentBugItemId = iid;
        this.currentPastedBlob = null;

        const card = document.querySelector(`.card-${iid}`);
        const title = card ? card.querySelector('.js-case-title').textContent : "Unknown";

        const targetIdEl = document.getElementById('bug-target-id');
        const titleInput = document.getElementById('quick-bug-title');
        if (targetIdEl) targetIdEl.textContent = `#${iid}`;
        if (titleInput) titleInput.value = `[BUG] Failure in #${iid}: ${title}`;

        const preview = document.getElementById('img-preview');
        if (preview) preview.classList.add('u-hide');

        UI.showModal('bugModalOverlay');
    },

    /**
     * 提交缺陷
     */
    async submit(e) {
        const projectIdInput = document.getElementById('projectId');
        if (!projectIdInput) return;
        const projectId = projectIdInput.value;

        const titleInput = document.getElementById('quick-bug-title');
        const title = titleInput ? titleInput.value : '';

        if (!title) return alert("Defect title is mandatory");

        const btn = e ? e.currentTarget : document.querySelector('.js-submit-bug');
        if (btn) {
            btn.disabled = true;
            btn.textContent = "Reporting...";
        }

        try {
            const payload = {
                title: title,
                severity: document.getElementById('bug_severity').value,
                env: document.getElementById('bug_env').value,
                steps: document.getElementById('bug_steps').value,
                related_test_case_iid: this.currentBugItemId
            };

            let imageListMd = "";
            if (this.currentPastedBlob) {
                if (btn) btn.textContent = "Uploading Evidence...";
                const formData = new FormData();
                formData.append('file', this.currentPastedBlob, 'screenshot.png');

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

            payload.steps += imageListMd;

            const data = await Api.post(`/projects/${projectId}/defects`, payload);
            UI.showToast(`Professional Defect #${data.iid} reported!`, "success");
            UI.hideModal('bugModalOverlay');

            // 刷新看板
            QaTestCaseHandler.load(true);
            this.load();
        } catch (err) {
            UI.showToast("Bug Portal Error: " + err.message, "error");
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Submit Defect";
            }
        }
    },

    /**
     * AI RCA 助手 (安全渲染)
     */
    async openRCA(iid, projectId) {
        const titleEl = document.getElementById('rca-target-title');
        const suggsUl = document.getElementById('rca-suggestions');
        const impactDiv = document.getElementById('rca-impact');
        const similarDiv = document.getElementById('rca-similar');

        if (titleEl) titleEl.textContent = `Analyzing Ticket #${iid}...`;
        if (suggsUl) {
            suggsUl.innerHTML = '';
            const loadingLi = document.createElement('li');
            loadingLi.textContent = 'AI 正在检索知识库...';
            suggsUl.appendChild(loadingLi);
        }
        if (impactDiv) impactDiv.textContent = 'Calculating impact scope...';
        if (similarDiv) similarDiv.innerHTML = '';

        UI.showModal('rcaModalOverlay');

        try {
            const data = await Api.get(`/projects/${projectId}/defects/${iid}/rca`);
            if (titleEl) titleEl.textContent = `RCA Findings for: ${data.title}`;

            if (suggsUl) {
                suggsUl.innerHTML = '';
                data.suggestions.forEach(s => {
                    const li = document.createElement('li');
                    li.textContent = s;
                    suggsUl.appendChild(li);
                });
            }

            if (impactDiv) impactDiv.textContent = data.impact_scope;

            if (similarDiv) {
                similarDiv.innerHTML = '';
                if (data.similar_cases.length === 0) {
                    const empty = document.createElement('div');
                    empty.className = 'u-text-tiny u-opacity-60';
                    empty.textContent = 'No similar closed cases found.';
                    similarDiv.appendChild(empty);
                } else {
                    data.similar_cases.forEach(c => {
                        const card = document.createElement('div');
                        card.className = 'sys-rca-similar-card';

                        const head = document.createElement('div');
                        head.className = 'u-weight-600 u-text-small u-color-white';
                        head.textContent = `#${c.iid} ${c.title}`;

                        const sol = document.createElement('div');
                        sol.className = 'u-text-tiny u-text-dim u-mt-4';
                        sol.textContent = `Solution: ${c.solution}`;

                        card.appendChild(head);
                        card.appendChild(sol);
                        similarDiv.appendChild(card);
                    });
                }
            }
        } catch (e) {
            if (suggsUl) {
                suggsUl.innerHTML = '';
                const errorLi = document.createElement('li');
                errorLi.style.color = 'var(--status-error)';
                errorLi.textContent = `AI Analysis Failed: ${e.message}`;
                suggsUl.appendChild(errorLi);
            }
        }
    }
};

export default QaDefectHandler;
