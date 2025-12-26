// src/api.js
// API 客户端 - 封装后端接口调用

const API_BASE_URL = 'http://localhost:8000/api';
const WS_BASE_URL = 'ws://localhost:8000/ws/chat';

// ========== 本地存储管理 ==========
const TOKEN_KEY = 'access_token';
const USER_KEY = 'current_user';

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token) {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function getUser() {
  const userStr = localStorage.getItem(USER_KEY);
  return userStr ? JSON.parse(userStr) : null;
}

function setUser(user) {
  if (user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  } else {
    localStorage.removeItem(USER_KEY);
  }
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

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
    const token = getToken();

    const defaultOptions = {
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    };

    const response = await fetch(fullUrl, { ...defaultOptions, ...options });

    if (!response.ok) {
      // 尝试解析错误响应
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        console.error(`[API] 请求失败但无法解析错误响应: ${response.status}`, e);
        errorData = { message: `HTTP ${response.status}` };
      }

      // 获取详细的错误信息（FastAPI使用detail字段）
      const errorMessage = errorData.detail || errorData.message || `HTTP ${response.status}`;
      console.error(`[API] 请求失败: ${response.status} ${response.statusText}`, {
        url: fullUrl,
        error: errorData,
      });
      throw new Error(errorMessage);
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
   * 重命名对话
   * PUT /api/chats/{chatId}/rename
   */
  async renameChat(chatId, title) {
    return this.request(`/chats/${chatId}/rename`, {
      method: 'PUT',
      body: JSON.stringify({ title }),
    });
  }

  /**
   * 导出单个对话为TXT
   * GET /api/chats/{chatId}/export
   */
  async exportChatToTxt(chatId) {
    const token = getToken();
    const url = `${this.baseUrl}/chats/${chatId}/export`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    // 获取文件名 - 支持RFC 5987编码格式
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = '对话.txt';
    if (contentDisposition) {
      // 尝试匹配 RFC 5987 格式: filename*=UTF-8''encoded_filename
      const utf8Match = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
      if (utf8Match) {
        try {
          filename = decodeURIComponent(utf8Match[1]);
        } catch (e) {
          console.warn('Failed to decode UTF-8 filename:', e);
        }
      } else {
        // 回退到普通格式: filename="..."
        const regularMatch = contentDisposition.match(/filename="?([^"]+)"?/);
        if (regularMatch) {
          filename = regularMatch[1];
        }
      }
    }

    // 获取文本内容并下载
    const text = await response.text();
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  /**
   * 健康检查
   * GET /api/health
   */
  async healthCheck() {
    return this.request('/health');
  }

  // ========== 用户认证 API ==========

  /**
   * 用户注册
   * POST /api/auth/register
   */
  async register(username, password, email = null, avatarUrl = null) {
    const result = await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        username,
        password,
        email,
        avatar_url: avatarUrl,
      }),
    });

    // 保存令牌和用户信息
    if (result.access_token) {
      setToken(result.access_token);
      setUser(result.user);
    }

    return result;
  }

  /**
   * 用户登录
   * POST /api/auth/login
   */
  async login(username, password) {
    const result = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });

    // 保存令牌和用户信息
    if (result.access_token) {
      setToken(result.access_token);
      setUser(result.user);
    }

    return result;
  }

  /**
   * 获取当前用户信息
   * GET /api/auth/me
   */
  async getCurrentUser() {
    return this.request('/auth/me');
  }

  /**
   * 用户登出
   * POST /api/auth/logout
   */
  async logout() {
    try {
      await this.request('/auth/logout', {
        method: 'POST',
      });
    } finally {
      // 无论请求是否成功，都清除本地存储
      clearAuth();
    }
  }

  /**
   * 检查是否已登录
   */
  isAuthenticated() {
    return !!getToken();
  }

  /**
   * 获取本地存储的用户信息
   */
  getLocalUser() {
    return getUser();
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

  /**
   * 获取公开对话大厅（按点赞排序）
   * GET /api/public/chats
   */
  async getPublicChatHall(limit = 20) {
    return this.request(`/public/chats?limit=${limit}`);
  }

  /**
   * 点赞对话
   * POST /api/chats/{chatId}/like
   */
  async likeChat(chatId) {
    return this.request(`/chats/${chatId}/like`, {
      method: 'POST',
    });
  }

  /**
   * 取消点赞对话
   * DELETE /api/chats/{chatId}/like
   */
  async unlikeChat(chatId) {
    return this.request(`/chats/${chatId}/like`, {
      method: 'DELETE',
    });
  }

  /**
   * 公开对话
   * POST /api/chats/{chatId}/publish
   */
  async publishChat(chatId) {
    return this.request(`/chats/${chatId}/publish`, {
      method: 'POST',
    });
  }

  /**
   * 获取用户的所有对话（用于导出）
   * GET /api/chats/export
   */
  async exportAllChats() {
    const token = getToken();
    const url = `${this.baseUrl}/chats/export`;

    // 创建下载链接
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
    });

    if (!response.ok) {
      // 尝试解析错误响应
      let errorData;
      try {
        errorData = await response.json();
      } catch (e) {
        throw new Error(`HTTP ${response.status}`);
      }
      throw new Error(errorData.detail || errorData.message || `HTTP ${response.status}`);
    }

    // 获取文件名
    const contentDisposition = response.headers.get('Content-Disposition');
    let filename = '对话记录.zip';
    if (contentDisposition) {
      const match = contentDisposition.match(/filename="?([^"]+)"?/);
      if (match) {
        filename = match[1];
      }
    }

    // 获取 blob 并下载
    const blob = await response.blob();
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  /**
   * 删除用户的所有对话
   * DELETE /api/chats/all
   */
  async deleteAllChats() {
    return this.request('/chats/all', {
      method: 'DELETE',
    });
  }

  // ========== 用户个人信息 API ==========

  /**
   * 更新用户个人信息
   * PUT /api/user/profile
   */
  async updateProfile(data) {
    const result = await this.request('/user/profile', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
    // 更新本地存储的用户信息
    if (result.user) {
      setUser(result.user);
    }
    return result;
  }

  /**
   * 修改密码
   * PUT /api/user/password
   */
  async changePassword(oldPassword, newPassword) {
    return this.request('/user/password', {
      method: 'PUT',
      body: JSON.stringify({ old_password: oldPassword, new_password: newPassword }),
    });
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

// ========== 导出认证相关函数 ==========
export { getToken, setToken, getUser, setUser, clearAuth };

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
