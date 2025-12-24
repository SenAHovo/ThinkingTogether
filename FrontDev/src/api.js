// src/api.js
// API 客户端 - 封装后端接口调用

const API_BASE_URL = 'http://localhost:8000/api';
const WS_BASE_URL = 'ws://localhost:8000/ws/chat';

// ========== API 客户端类 ==========
class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.wsConnections = new Map(); // 存储WebSocket连接
  }

  /**
   * 通用请求方法
   */
  async request(url, options = {}) {
    const fullUrl = `${this.baseUrl}${url}`;
    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
      },
    };

    const response = await fetch(fullUrl, { ...defaultOptions, ...options });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: '请求失败' }));
      throw new Error(error.message || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /**
   * 创建新对话
   * POST /api/chats
   */
  async createChat(topic, title = null) {
    return this.request('/chats', {
      method: 'POST',
      body: JSON.stringify({ topic, title }),
    });
  }

  /**
   * 获取对话列表
   * GET /api/chats
   */
  async getChats(keyword = '', limit = 50) {
    const params = new URLSearchParams();
    if (keyword) params.append('keyword', keyword);
    params.append('limit', limit.toString());

    return this.request(`/chats?${params.toString()}`);
  }

  /**
   * 获取单个对话详情
   * GET /api/chats/{chatId}
   */
  async getChat(chatId) {
    return this.request(`/chats/${chatId}`);
  }

  /**
   * 获取对话消息列表
   * GET /api/chats/{chatId}/messages
   */
  async getMessages(chatId, limit = 100, before = null) {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    if (before) params.append('before', before);

    return this.request(`/chats/${chatId}/messages?${params.toString()}`);
  }

  /**
   * 发送消息
   * POST /api/messages
   */
  async sendMessage(chatId, content, action = 'send') {
    return this.request('/messages', {
      method: 'POST',
      body: JSON.stringify({ chat_id: chatId, content, action }),
    });
  }

  /**
   * 让AI继续发言
   * POST /api/chats/{chatId}/continue
   */
  async continueChat(chatId) {
    return this.request(`/chats/${chatId}/continue`, {
      method: 'POST',
    });
  }

  /**
   * 生成对话总结（对话继续进行）
   * POST /api/chats/{chatId}/summary
   */
  async summarizeChat(chatId) {
    return this.request(`/chats/${chatId}/summary`, {
      method: 'POST',
    });
  }

  /**
   * 删除对话
   * DELETE /api/chats/{chatId}
   */
  async deleteChat(chatId) {
    return this.request(`/chats/${chatId}`, {
      method: 'DELETE',
    });
  }

  /**
   * 健康检查
   * GET /api/health
   */
  async healthCheck() {
    return this.request('/health');
  }

  // ========== 管理员 API ==========

  /**
   * 获取所有用户列表
   * GET /api/admin/users
   */
  async getUsers() {
    return this.request('/admin/users');
  }

  /**
   * 创建新用户
   * POST /api/admin/users
   */
  async createUser(userData) {
    return this.request('/admin/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  /**
   * 更新用户信息
   * PUT /api/admin/users/{userId}
   */
  async updateUser(userId, userData) {
    return this.request(`/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(userData),
    });
  }

  /**
   * 删除用户
   * DELETE /api/admin/users/{userId}
   */
  async deleteUser(userId) {
    return this.request(`/admin/users/${userId}`, {
      method: 'DELETE',
    });
  }

  /**
   * 获取所有对话公开请求
   * GET /api/admin/publication-requests
   */
  async getPublicationRequests(status = 'pending') {
    return this.request(`/admin/publication-requests?status=${status}`);
  }

  /**
   * 审核对话公开请求
   * POST /api/admin/publication-requests/{requestId}/review
   */
  async reviewPublicationRequest(requestId, approved, reason = '') {
    return this.request(`/admin/publication-requests/${requestId}/review`, {
      method: 'POST',
      body: JSON.stringify({ approved, reason }),
    });
  }

  /**
   * 获取已公开的对话列表
   * GET /api/admin/public-chats
   */
  async getPublicChats() {
    return this.request('/admin/public-chats');
  }

  // ========== WebSocket 方法 ==========

  /**
   * 建立WebSocket连接
   */
  connectWebSocket(chatId, onMessage, onError = null, onClose = null) {
    // 如果已有连接，先关闭
    if (this.wsConnections.has(chatId)) {
      this.disconnectWebSocket(chatId);
    }

    const ws = new WebSocket(`${WS_BASE_URL}/${chatId}`);

    ws.onopen = () => {
      console.log(`WebSocket connected for chat: ${chatId}`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onerror = (error) => {
      console.error(`WebSocket error for chat ${chatId}:`, error);
      if (onError) onError(error);
    };

    ws.onclose = () => {
      console.log(`WebSocket closed for chat: ${chatId}`);
      this.wsConnections.delete(chatId);
      if (onClose) onClose();
    };

    this.wsConnections.set(chatId, ws);
    return ws;
  }

  /**
   * 断开WebSocket连接
   */
  disconnectWebSocket(chatId) {
    const ws = this.wsConnections.get(chatId);
    if (ws) {
      ws.close();
      this.wsConnections.delete(chatId);
    }
  }

  /**
   * 断开所有WebSocket连接
   */
  disconnectAll() {
    this.wsConnections.forEach((ws) => ws.close());
    this.wsConnections.clear();
  }
}

// ========== 导出单例实例 ==========
export const apiClient = new ApiClient();

// ========== 工具函数 ==========
export function now() {
  const d = new Date();
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

export function stamp() {
  const d = new Date();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${m}/${day} ${now()}`;
}

export function uid() {
  return crypto.randomUUID?.() || String(Math.random());
}

// ========== 映射函数 ==========
export function mapSpeakerToMemberId(speaker) {
  const map = {
    '理论家': 'theorist',
    '实践者': 'practitioner',
    '质疑者': 'skeptic',
    '组织者': 'facilitator',
  };
  return map[speaker] || 'theorist';
}

export function mapMemberIdToName(memberId) {
  const map = {
    'user': '用户',
    'theorist': '理论家',
    'practitioner': '实践者',
    'skeptic': '质疑者',
    'facilitator': '组织者',
  };
  return map[memberId] || memberId;
}
