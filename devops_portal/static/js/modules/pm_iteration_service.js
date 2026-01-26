/**
 * @file pm_iteration_service.js
 * @description ITeration Plan API Service Layer
 */

import { Api } from './sys_core.js';

export const PMIterationService = {
    /**
     * 获取 MDM 主项目列表
     */
    async getMdmProjects() {
        return await Api.get('/admin/mdm-projects');
    },

    /**
     * 获取可进行规划的 GitLab 项目列表 (旧接口，向下兼容)
     */
    async getProjects() {
        return await Api.get('/iteration-plan/projects');
    },

    /**
     * 获取项目的里程碑（迭代）
     */
    async getMilestones(projectId) {
        return await Api.get(`/iteration-plan/projects/${projectId}/milestones`);
    },

    /**
     * 获取 Backlog 数据
     */
    async getBacklog(projectId) {
        return await Api.get(`/iteration-plan/projects/${projectId}/backlog`);
    },

    /**
     * 获取 Sprint 数据
     */
    async getSprint(projectId, milestoneTitle) {
        return await Api.get(`/iteration-plan/projects/${projectId}/sprint/${encodeURIComponent(milestoneTitle)}`);
    },

    /**
     * 将任务移入迭代
     */
    async planIssue(projectId, issueIid, milestoneId) {
        return await Api.post(`/iteration-plan/projects/${projectId}/plan`, {
            issue_iid: parseInt(issueIid),
            milestone_id: parseInt(milestoneId)
        });
    },

    /**
     * 从迭代移除任务
     */
    async removeIssue(projectId, issueIid) {
        return await Api.post(`/iteration-plan/projects/${projectId}/remove`, {
            issue_iid: parseInt(issueIid)
        });
    },

    /**
     * 执行发布
     */
    async release(projectId, data) {
        return await Api.post(`/iteration-plan/projects/${projectId}/release`, data);
    },

    /**
     * 创建新迭代
     */
    async createMilestone(projectId, data) {
        return await Api.post(`/iteration-plan/projects/${projectId}/milestones`, data);
    }
};
