/**
 * @file pm_matrix.js
 * @description Product Traceability Matrix (RTM) Implementation
 */
import { Api, UI } from './sys_core.js';
import '../components/adm_product_selector.component.js';

const PmMatrixHandler = {
    state: {
        rawData: [],      // Store raw full dataset
        filters: {        // Current filter criteria
            keyword: '',
            status: 'all',
            coverage: 'all'
        },
        currentFilter: {  // API context
            type: null,
            id: null
        }
    },

    init() {
        console.log("Traceability Matrix Initialized");
        this.bindEvents();
    },

    bindEvents() {
        // Product Selector
        const selector = document.getElementById('matrix-product-selector');
        if (selector && !selector.dataset.bound) {
            selector.addEventListener('change', (e) => {
                const { type, id } = e.detail;
                if (id) {
                    this.state.currentFilter = { type, id };
                    this.loadMatrix();
                }
            });
            selector.dataset.bound = "true";
        }

        // Search Input (Debounced)
        const searchInput = document.getElementById('matrix-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.state.filters.keyword = e.target.value.toLowerCase();
                this.applyFilters();
            }, 300));
        }

        // Dropdown Filters
        ['status', 'coverage'].forEach(key => {
            const el = document.getElementById(`matrix-filter-${key}`);
            if (el) {
                el.addEventListener('change', (e) => {
                    this.state.filters[key] = e.target.value;
                    this.applyFilters();
                });
            }
        });
    },

    debounce(func, wait) {
        let timeout;
        return function (...args) {
            const context = this;
            clearTimeout(timeout);
            timeout = setTimeout(() => func.apply(context, args), wait);
        };
    },

    /**
     * Load matrix data from backend
     */
    async loadMatrix() {
        const { type, id } = this.state.currentFilter;
        if (!type || !id) return;

        const container = document.querySelector('.js-matrix-tbody');
        if (!container) return;

        container.innerHTML = `<tr><td colspan="5" class="u-text-center u-p-24">Loading traceability data for ${type} ${id}...</td></tr>`;

        try {
            const params = new URLSearchParams();
            if (type === 'product') params.append('product_id', id);
            if (type === 'org') params.append('org_id', id);

            const data = await Api.get(`/test-management/aggregated/requirements?${params.toString()}`);

            this.state.rawData = data || [];
            this.applyFilters(); // Apply initial filters (all)
        } catch (e) {
            container.innerHTML = `<tr><td colspan="5" class="u-text-center u-text-error u-p-24">Failed to load matrix: ${e.message}</td></tr>`;
        }
    },

    /**
     * Apply client-side filters
     */
    applyFilters() {
        const { keyword, status, coverage } = this.state.filters;
        const container = document.querySelector('.js-matrix-tbody');

        if (!this.state.rawData.length) {
            this.render([], container);
            return;
        }

        const filtered = this.state.rawData.filter(item => {
            const req = item.requirement;

            // 1. Keyword Search
            if (keyword) {
                // Combine searchable text
                const searchStr = `
                    ${req.iid} 
                    ${req.title} 
                    ${(item.merge_requests || []).map(m => m.title).join(' ')}
                    ${(item.commits || []).map(c => c.short_id).join(' ')}
                `.toLowerCase();

                if (!searchStr.includes(keyword)) return false;
            }

            // 2. Status Filter
            if (status !== 'all') {
                if (status === 'active' && req.state !== 'active') return false;
                if (status === 'draft' && req.state !== 'draft') return false;
                if (status === 'closed' && req.state !== 'closed') return false;
            }

            // 3. Coverage Filter
            if (coverage !== 'all') {
                const hasCases = item.test_cases && item.test_cases.length > 0;
                if (coverage === 'missing' && hasCases) return false;
                if (coverage === 'covered' && !hasCases) return false;
            }

            return true;
        });

        this.updateCount(filtered.length);
        this.render(filtered, container);
    },

    updateCount(count) {
        const el = document.getElementById('matrix-count-display');
        if (el) el.textContent = count;
    },

    /**
     * Render the matrix table
     * @param {Array} items - List of TraceabilityMatrixItem
     */
    render(items, container) {
        if (!items || items.length === 0) {
            container.innerHTML = `<tr><td colspan="5" class="u-text-center u-text-dim u-p-24">No matching requirements found.</td></tr>`;
            return;
        }

        const frag = document.createDocumentFragment();

        items.forEach(item => {
            const req = item.requirement;
            const cases = item.test_cases || [];
            const defects = item.defects || [];
            const changes = [...(item.merge_requests || []), ...(item.commits || [])];

            const row = document.createElement('tr');

            // 1. Requirement Cell
            row.innerHTML += `
                <td class="u-align-top">
                    <div class="test-title-group">
                        <span class="test-iid u-mr-8">#${req.iid}</span>
                        <div class="u-weight-600">${req.title}</div>
                    </div>
                </td>
            `;

            // 2. Test Cases Cell
            let casesHtml = '';
            if (cases.length > 0) {
                casesHtml = '<ul class="u-list-none u-pl-0 u-m-0">';
                cases.forEach(c => {
                    const resultClass = c.result === 'passed' ? 'status-dot--passed' : 'status-dot--failed';
                    casesHtml += `
                        <li class="u-flex u-align-center u-gap-8 u-mb-4">
                            <span class="test-iid-tiny">C-${c.iid}</span>
                            <span class="u-text-tiny u-text-truncate" title="${c.title}" style="max-width: 150px;">${c.title}</span>
                            <span class="status-dot ${resultClass}"></span>
                        </li>`;
                });
                casesHtml += '</ul>';
            } else {
                casesHtml = '<span class="u-text-dim u-text-tiny">No linked cases</span>';
            }
            row.innerHTML += `<td class="u-align-top">${casesHtml}</td>`;

            // 3. Defects Cell
            let defectsHtml = '';
            if (defects.length > 0) {
                defectsHtml = '<ul class="u-list-none u-pl-0 u-m-0">';
                defects.forEach(d => {
                    defectsHtml += `
                        <li class="u-flex u-align-center u-gap-8 u-mb-4">
                            <span class="test-iid-tiny u-text-error">BUG-${d.iid}</span>
                            <span class="u-text-tiny">${d.state}</span>
                        </li>`;
                });
                defectsHtml += '</ul>';
            } else {
                defectsHtml = '<span class="u-text-dim u-text-tiny">-</span>';
            }
            row.innerHTML += `<td class="u-align-top">${defectsHtml}</td>`;

            // 4. Code Changes Cell (MRs/Commits)
            let changesHtml = '';
            if (changes.length > 0) {
                changesHtml = '<div class="u-flex u-flex-wrap u-gap-8">';
                changes.forEach(c => {
                    const isMr = c.iid !== undefined;
                    const icon = isMr ? '🔀' : '📝';
                    const text = isMr ? `!${c.iid}` : c.short_id;
                    const cssClass = isMr ? 'sys-tag sys-tag--purple' : 'sys-tag';
                    changesHtml += `<span class="${cssClass} u-text-tiny">${icon} ${text}</span>`;
                });
                changesHtml += '</div>';
            } else {
                changesHtml = '<span class="u-text-dim u-text-tiny">No related changes</span>';
            }
            row.innerHTML += `<td class="u-align-top">${changesHtml}</td>`;

            // 5. Status Cell
            const statusClass = req.state === 'active' || req.review_state === 'approved'
                ? 'u-text-success'
                : 'u-text-dim';
            row.innerHTML += `
                <td class="u-align-top">
                    <span class="${statusClass} u-weight-600">${req.state || 'N/A'}</span>
                </td>`;

            frag.appendChild(row);
        });

        container.innerHTML = '';
        container.appendChild(frag);
    }
};

export default PmMatrixHandler;
