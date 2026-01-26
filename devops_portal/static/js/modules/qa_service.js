/**
 * @file qa_service.js
 * @description QA Management API Service Layer
 */
import { Api } from './sys_core.js';

export const QAService = {
    /**
     * Get test cases for a project or aggregated scope
     * @param {string} scopeType - 'project' | 'product' | 'org'
     * @param {string} id - project_id | product_id | org_id
     */
    async getTestCases(scopeType, id) {
        if (scopeType === 'project') {
            return await Api.get(`/projects/${id}/test-cases`);
        } else {
            const queryParam = scopeType === 'product' ? `product_id=${id}` : `org_id=${id}`;
            return await Api.get(`/test-management/aggregated/test-cases?${queryParam}`);
        }
    },

    /**
     * Get test summary stats
     */
    async getTestSummary(projectId) {
        return await Api.get(`/projects/${projectId}/test-summary`);
    },

    /**
     * Create a new test case
     */
    async createTestCase(projectId, payload) {
        return await Api.post(`/projects/${projectId}/test-cases`, payload);
    },

    /**
     * Execute a test case
     */
    async executeTest(projectId, iid, result) {
        return await Api.post(`/projects/${projectId}/test-cases/${iid}/execute?result=${result}`);
    },

    /**
     * Acknowledge requirement changes (mark as active)
     */
    async ackTestChange(projectId, iid) {
        return await Api.post(`/projects/${projectId}/test-cases/${iid}/ack`, {});
    },

    /**
     * AI: Suggest steps from requirement
     */
    async suggestSteps(projectId, reqIid) {
        return await Api.get(`/projects/${projectId}/requirements/${reqIid}/suggest-test-steps`);
    },

    /**
     * AI: Suggest automation code
     */
    async suggestCode(projectId, iid) {
        return await Api.get(`/projects/${projectId}/test-cases/${iid}/suggest-code`);
    }
};
