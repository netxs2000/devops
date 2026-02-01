/**
 * @file adm_service.js
 * @description Administration Domain API Service Layer
 */

import { Api } from './sys_core.js';

export const AdmService = {
    /**
     * 获取产品列表
     */
    async getProducts() {
        return await Api.get('/admin/products');
    },

    /**
     * 创建产品
     */
    async createProduct(data) {
        return await Api.post('/admin/products', data);
    },

    /**
     * 获取 MDM 项目列表
     */
    async getMdmProjects() {
        return await Api.get('/admin/mdm-projects');
    },

    /**
     * 创建 MDM 项目
     */
    async createMdmProject(data) {
        return await Api.post('/admin/mdm-projects', data);
    },

    /**
     * 获取未关联的 GitLab 仓库
     */
    async getUnlinkedRepos() {
        return await Api.get('/admin/unlinked-repos');
    },

    /**
     * 关联产品与项目
     */
    async linkProductProject(data) {
        return await Api.post('/admin/link-product', data);
    },

    /**
     * 获取身份映射列表
     */
    async getIdentityMappings() {
        return await Api.get('/admin/identity-mappings');
    },

    /**
     * 创建身份映射
     */
    async createIdentityMapping(data) {
        return await Api.post('/admin/identity-mappings', data);
    },

    /**
     * 删除身份映射
     */
    async deleteIdentityMapping(id) {
        return await Api.request(`/admin/identity-mappings/${id}`, { method: 'DELETE' });
    },

    /**
     * 获取系统用户列表 (用于映射选择)
     */
    async getUsers() {
        return await Api.get('/admin/users');
    },

    /**
     * 获取审批中心用户列表
     */
    async getRegistrationUsers(status = 'pending') {
        let url = `/service-desk/admin/all-users`;
        if (status !== 'all') {
            url += `?status=${status}`;
        }
        return await Api.get(url);
    },

    /**
     * 执行用户审批操作
     */
    async approveUser(email, approved, reason = '', gitlabId = '') {
        const params = { email, approved };
        if (reason) params.reject_reason = reason;
        if (gitlabId) params.gitlab_user_id = gitlabId;

        const queryStr = new URLSearchParams(params).toString();
        return await Api.post(`/service-desk/admin/approve-user?${queryStr}`, {});
    },

    /**
     * 获取组织架构列表
     */
    async getOrganizations() {
        return await Api.get('/admin/organizations');
    },

    /**
     * 创建组织
     */
    async createOrganization(data) {
        return await Api.post('/admin/organizations', data);
    },

    /**
     * 导入用户
     */
    async importUsers(file) {
        const formData = new FormData();
        formData.append('file', file);
        return await Api.upload('/admin/import/users', formData);
    },

    /**
     * 导入组织
     */
    async importOrganizations(file) {
        const formData = new FormData();
        formData.append('file', file);
        return await Api.upload('/admin/import/organizations', formData);
    }
};
