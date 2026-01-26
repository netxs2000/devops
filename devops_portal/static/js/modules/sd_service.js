/**
 * @file sd_service.js
 * @description Service Desk API Service Layer
 */

import { Api } from './sys_core.js';

export const SDService = {
    /**
     * 获取所有工单数据（用于统计）
     */
    async getTickets() {
        return await Api.get('/service-desk/tickets');
    },

    /**
     * 获取业务系统列表
     */
    async getBusinessProjects() {
        return await Api.get('/service-desk/business-projects');
    },

    /**
     * 追踪工单
     */
    async trackTicket(code) {
        return await Api.get(`/service-desk/track/${encodeURIComponent(code)}`);
    },

    /**
     * 获取当前用户的工单
     */
    async getMyTickets() {
        return await Api.get('/service-desk/my-tickets');
    },

    /**
     * 提交工单（缺陷或需求）
     */
    async submitTicket(type, mdmId, data) {
        const url = type === 'bug'
            ? `/service-desk/submit-bug?mdm_id=${mdmId}`
            : `/service-desk/submit-requirement?mdm_id=${mdmId}`;
        return await Api.post(url, data);
    }
};
