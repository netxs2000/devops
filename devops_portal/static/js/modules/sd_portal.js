/**
 * @file sd_portal.js
 * @description Service Desk Portal Controller (SPA Architecture)
 * @author Antigravity
 */

import { Auth } from './sys_core.js';

const SDPortalHandler = {
    container: null,

    async init() {
        console.log("SD Portal (SPA) Initialized.");
        this.container = document.getElementById('sd-portal-view');

        if (!this.container) {
            console.warn("SD Portal container (#sd-portal-view) not found.");
            return;
        }

        // Event Delegation for Navigation
        this.container.addEventListener('navigate', (e) => {
            const view = e.detail.view;
            const params = e.detail.params || {};
            this.handleNavigation(view, params);
        });

        // Set initial view (Landing)
        this.renderLanding();
    },

    handleNavigation(view, params) {
        console.log(`Navigating to: ${view}`, params);
        switch (view) {
            case 'landing':
                this.renderLanding();
                break;
            case 'bug_form':
                this.checkAuth(() => this.renderForm('bug'));
                break;
            case 'req_form':
                this.checkAuth(() => this.renderForm('requirement'));
                break;
            case 'my_tickets':
                this.checkAuth(() => this.renderMyTickets());
                break;
            default:
                console.error(`Unknown view: ${view}`);
        }
    },

    checkAuth(callback) {
        if (!Auth.isLoggedIn()) {
            // Use system auth modal or redirect
            // For now, assume integrated auth flow in index.html handles this or existing Auth module
            // If strictly standalone, we might need to show login.
            // Assuming Auth.requireLogin() or similar exists, or redirect to login.
            // Let's use a simple alert for now as placeholder if Auth doesn't auto-redirect.
            if (!Auth.getToken()) {
                alert("请先登录");
                // Trigger global login modal if available, or redirect
                // document.dispatchEvent(new CustomEvent('sys:login-req')); 
                return;
            }
        }
        callback();
    },

    clearView() {
        if (this.container) {
            this.container.innerHTML = '';
        }
    },

    renderLanding() {
        this.clearView();
        const landing = document.createElement('sd-landing');
        this.container.appendChild(landing);
        // Load stats if needed
        import('../components/sd_stat_card.component.js');
    },

    renderForm(type) {
        this.clearView();
        const form = document.createElement('sd-request-form');
        form.setAttribute('type', type);
        this.container.appendChild(form);
    },

    renderMyTickets() {
        this.clearView();
        const list = document.createElement('sd-ticket-list');
        this.container.appendChild(list);
    }
};

export default SDPortalHandler;
