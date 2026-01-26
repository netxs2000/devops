/**
 * @file unit_tests.js
 * @description 前端功能模块单元测试集 (Unit Testing for JS Modules)
 */

import { Auth, Api, UI } from '../js/modules/sys_core.js';

// --- Simple Test Framework ---
const results = { pass: 0, fail: 0, total: 0, details: [] };

async function describe(name, fn) {
    console.log(`%c[DESCRIBE] ${name}`, 'font-weight: bold; color: #3b82f6;');
    await fn();
}

async function it(name, fn) {
    results.total++;
    try {
        await fn();
        results.pass++;
        console.log(`%c  [PASS] %c${name}`, 'color: #10b981;', 'color: inherit;');
    } catch (e) {
        results.fail++;
        console.error(`  [FAIL] ${name}\n`, e);
        results.details.push({ name, error: e.message });
    }
}

function expect(actual) {
    return {
        toBe(expected) {
            if (actual !== expected) throw new Error(`Expected ${expected}, but got ${actual}`);
        },
        toBeTruthy() {
            if (!actual) throw new Error(`Expected truthy value, but got ${actual}`);
        },
        toBeFalsy() {
            if (actual) throw new Error(`Expected falsy value, but got ${actual}`);
        },
        toContain(substring) {
            if (typeof actual !== 'string' || !actual.includes(substring)) {
                throw new Error(`Expected "${actual}" to contain "${substring}"`);
            }
        }
    };
}

// --- Mocks ---
const originalFetch = window.fetch;
function mockFetch(response, ok = true, status = 200) {
    window.fetch = async () => ({
        ok,
        status,
        json: async () => response
    });
}

function resetFetch() {
    window.fetch = originalFetch;
}

// --- Tests ---

async function runTests() {
    console.log('%c🚀 Starting Frontend Unit Tests...', 'font-size: 16px; font-weight: bold;');

    // 1. Sys Core - Auth Tests
    await describe('SysCore - Auth', async () => {
        await it('should store and retrieve token', () => {
            const token = 'test-token-123';
            Auth.setToken(token);
            expect(Auth.getToken()).toBe(token);
        });

        await it('should clear token on logout', () => {
            Auth.setToken('tmp');
            Auth.logout();
            // Note: logout redirects, but in our test we mock location or assume cleanup
            expect(Auth.getToken()).toBe(null);
        });

        await it('should parse JWT payload correctly', () => {
            // Mock JWT: header.payload.signature (payload: {"sub":"admin@test.com", "roles":["SYSTEM_ADMIN"]})
            const mockToken = 'header.' + btoa(JSON.stringify({ sub: 'admin@test.com', roles: ['SYSTEM_ADMIN'] })) + '.sig';
            Auth.setToken(mockToken);
            const payload = Auth.getPayload();
            expect(payload.sub).toBe('admin@test.com');
            expect(Auth.isAdmin()).toBeTruthy();
        });
    });

    // 2. Sys Core - Api Tests
    await describe('SysCore - Api', async () => {
        await it('should handle successful GET requests', async () => {
            mockFetch({ success: true, data: [1, 2, 3] });
            const data = await Api.get('/api/test');
            expect(data.success).toBeTruthy();
            expect(data.data.length).toBe(3);
            resetFetch();
        });

        await it('should throw error on failed requests', async () => {
            mockFetch({ detail: 'Not Found' }, false, 404);
            try {
                await Api.get('/api/missing');
                throw new Error('Should have failed');
            } catch (e) {
                expect(e.status).toBe(404);
                expect(e.message).toBe('Not Found');
            }
            resetFetch();
        });
    });

    // 3. Sys Core - UI Tests
    await describe('SysCore - UI', async () => {
        await it('should toggle loading state', () => {
            const loading = document.createElement('div');
            loading.id = 'loading';
            document.body.appendChild(loading);

            UI.toggleLoading("Syncing...", true);
            expect(loading.classList.contains('u-block')).toBeTruthy();
            expect(loading.innerText).toBe("Syncing...");

            UI.toggleLoading("", false);
            expect(loading.classList.contains('u-hide')).toBeTruthy();
            document.body.removeChild(loading);
        });

        await it('should toggle modal visibility', () => {
            const modal = document.createElement('div');
            modal.id = 'testModal';
            modal.className = 'u-hide';
            document.body.appendChild(modal);

            UI.showModal('testModal');
            expect(modal.classList.contains('u-flex')).toBeTruthy();
            expect(modal.classList.contains('u-hide')).toBeFalsy();

            UI.hideModal('testModal');
            expect(modal.classList.contains('u-hide')).toBeTruthy();
            document.body.removeChild(modal);
        });
    });

    // 4. Sys Pulse - SysPulseHandler Tests
    await describe('SysPulse - Handler', async () => {
        // Dynamic import to avoid side effects during setup
        const { default: SysPulseHandler } = await import('../js/modules/sys_pulse.js');

        await it('should update status when already submitted', async () => {
            document.body.innerHTML += `
                <div id="faces-container">
                    <button class="js-pulse-btn" data-score="5">Match</button>
                </div>
                <div id="message"></div>
            `;

            mockFetch({ submitted: true, score: 5, message: "Done" });
            SysPulseHandler.state.userEmail = "test@user.com";
            await SysPulseHandler.checkStatus();

            const btn = document.querySelector('.js-pulse-btn');
            expect(btn.disabled).toBeTruthy();
            expect(btn.classList.contains('is-selected')).toBeTruthy();

            const msg = document.getElementById('message');
            expect(msg.textContent).toBe("Done");
            resetFetch();
        });
    });

    // 5. PM Iteration - PmIterationHandler Tests
    await describe('PM Iteration - Handler', async () => {
        const { default: PmIterationHandler } = await import('../js/modules/pm_iteration.js');

        await it('should initialize with correct elements', async () => {
            // Mock DOM for iteration plan
            document.body.innerHTML += `
                <select id="projectSelect"><option value="P1" selected>P1</option></select>
                <select id="milestoneSelect"><option value="M1" selected>M1</option></select>
                <div id="stats-board"></div>
            `;
            // Mock dependency call in loadProjects
            mockFetch([]);
            await PmIterationHandler.init();
            expect(PmIterationHandler.state.currentProjectId).toBe('P1');
            resetFetch();
        });
    });

    // 6. Service Desk - Service & Component Tests
    await describe('Service Desk - Service & Component', async () => {
        const { SDService } = await import('../js/modules/sd_service.js');
        await import('../js/components/sd_stat_card.component.js');

        await it('should fetch tickets correctly', async () => {
            mockFetch([{ id: 1, title: 'Test Ticket' }]);
            const tickets = await SDService.getTickets();
            expect(tickets.length).toBe(1);
            expect(tickets[0].title).toBe('Test Ticket');
            resetFetch();
        });

        await it('should update stat card value via attribute', async () => {
            const card = document.createElement('sd-stat-card');
            document.body.appendChild(card);

            card.setAttribute('value', '42');
            card.setAttribute('label', 'Test Cards');

            // Wait for attributeChangedCallback
            await new Promise(r => setTimeout(r, 0));

            const shadowValue = card.shadowRoot.querySelector('.value');
            expect(shadowValue.textContent).toBe('42');

            document.body.removeChild(card);
        });

        await it('should submit ticket with correct payload', async () => {
            let capturedUrl = '';
            let capturedBody = null;

            window.fetch = async (url, options) => {
                capturedUrl = url;
                capturedBody = JSON.parse(options.body);
                return {
                    ok: true,
                    json: async () => ({ tracking_code: 'BUG-123' })
                };
            };

            const payload = { title: 'Broken UI' };
            const result = await SDService.submitTicket('bug', 'MDM-1', payload);

            expect(result.tracking_code).toBe('BUG-123');
            resetFetch();
        });
    });
    // 7. PM Iteration - Service & Component Tests
    await describe('PM Iteration - Service & Component', async () => {
        const { PMIterationService } = await import('../js/modules/pm_iteration_service.js');
        await import('../js/components/pm_issue_card.component.js');

        await it('should fetch projects correctly', async () => {
            mockFetch([{ id: 101, path: 'group/project' }]);
            const projects = await PMIterationService.getProjects();
            expect(projects.length).toBe(1);
            expect(projects[0].id).toBe(101);
            resetFetch();
        });

        await it('should render issue card correctly via attributes', async () => {
            const card = document.createElement('pm-issue-card');
            document.body.appendChild(card);

            card.setAttribute('title', 'Refactor UI');
            card.setAttribute('iid', '42');
            card.setAttribute('type', 'bug');
            card.setAttribute('status', 'closed');

            // Wait for render
            await new Promise(r => setTimeout(r, 0));

            const shadow = card.shadowRoot;
            expect(shadow.querySelector('.title').textContent).toBe('Refactor UI');
            expect(shadow.querySelector('.iid').textContent).toBe('#42');
            expect(shadow.querySelector('.card').classList.contains('is-closed')).toBeTruthy();
            expect(shadow.querySelector('.label').textContent).toBe('bug');

            document.body.removeChild(card);
        });

        await it('should plan issue with correct payload', async () => {
            let capturedUrl = '';
            let capturedBody = null;

            window.fetch = async (url, options) => {
                capturedUrl = url;
                capturedBody = JSON.parse(options.body);
                return {
                    ok: true,
                    json: async () => ({ status: 'success' })
                };
            };

            await PMIterationService.planIssue(101, 42, 202);

            expect(capturedUrl).toContain('/projects/101/plan');
            expect(capturedBody.issue_iid).toBe(42);
            expect(capturedBody.milestone_id).toBe(202);
            resetFetch();
        });
    });

    // Summary
    console.log('%c---------------------------------------', 'color: #94a3b8;');
    console.log(`%cTest Suite Finished: ${results.pass} Passed, ${results.fail} Failed`,
        results.fail > 0 ? 'color: #ef4444; font-weight: bold;' : 'color: #10b981; font-weight: bold;');

    // Insert into DOM for visual feedback
    const summary = document.createElement('div');
    summary.style.padding = '20px';
    summary.style.marginTop = '20px';
    summary.style.borderRadius = '8px';
    summary.style.backgroundColor = results.fail > 0 ? '#fee2e2' : '#dcfce7';
    summary.innerHTML = `
        <h3>Test Summary</h3>
        <p>Total: ${results.total}</p>
        <p style="color: green">Pass: ${results.pass}</p>
        <p style="color: red">Fail: ${results.fail}</p>
        ${results.details.map(d => `<li style="color: red">${d.name}: ${d.error}</li>`).join('')}
    `;
    document.body.appendChild(summary);
}

// Intercept window.location.href for tests
const originalLocation = window.location.href;
// We can't actually mock window.location easily without a proxy or helper

runTests();
