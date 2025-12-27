<template>
  <div class="admin">
    <header class="topbar">
      <div class="brand">
        <div class="logo">管理</div>
        <div class="title">
          <div class="name">智炬五维管理后台</div>
          <div class="sub">用户管理 · 对话审核</div>
        </div>
      </div>
      <button class="back-btn" @click="$emit('back')">
        ← 返回主界面
      </button>
    </header>

    <main class="main">
      <div class="tabs" :class="{ 'three-tabs': currentUser?.role !== 'super_admin' }">
        <!-- 只有超级管理员才能看到用户管理标签 -->
        <button
          v-if="currentUser && (currentUser.role === 'super_admin')"
          class="tab"
          :class="{ active: activeTab === 'users' }"
          @click="activeTab = 'users'"
        >
          用户管理
        </button>
        <!-- 管理员和超级管理员都可以看到公开对话管理 -->
        <button
          v-if="currentUser && (currentUser.role === 'admin' || currentUser.role === 'super_admin')"
          class="tab"
          :class="{ active: activeTab === 'reviews' }"
          @click="activeTab = 'reviews'"
        >
          公开对话管理
          <span v-if="pendingCount > 0" class="badge">{{ pendingCount }}</span>
        </button>
        <!-- 管理员和超级管理员都可以看到评论管理 -->
        <button
          v-if="currentUser && (currentUser.role === 'admin' || currentUser.role === 'super_admin')"
          class="tab"
          :class="{ active: activeTab === 'comments' }"
          @click="activeTab = 'comments'"
        >
          评论管理
        </button>
        <!-- 管理员和超级管理员都可以看到数据看板 -->
        <button
          v-if="currentUser && (currentUser.role === 'admin' || currentUser.role === 'super_admin')"
          class="tab"
          :class="{ active: activeTab === 'dashboard' }"
          @click="activeTab = 'dashboard'"
        >
          数据看板
        </button>
      </div>

      <!-- 用户管理 -->
      <div v-show="activeTab === 'users'" class="tab-content">
        <div class="actions">
          <input
            v-model="userSearch"
            @input="filterUsers"
            class="search-input"
            placeholder="搜索用户名或邮箱..."
          />
          <button class="primary-btn" @click="openAddUserModal">
            + 新增用户
          </button>
        </div>

        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>用户名</th>
                <th>邮箱</th>
                <th>角色</th>
                <th>状态</th>
                <th>创建时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in paginatedUsers" :key="user.id">
                <td class="mono">{{ user.id.slice(0, 8) }}...</td>
                <td :class="['username-cell', user.role]">{{ user.username }}</td>
                <td>{{ user.email }}</td>
                <td>
                  <span class="role-tag" :class="user.role">{{ getRoleName(user.role) }}</span>
                </td>
                <td>
                  <span class="status-tag" :class="{ active: user.is_active }">
                    {{ user.is_active ? '正常' : '禁用' }}
                  </span>
                </td>
                <td>{{ formatDate(user.created_at) }}</td>
                <td>
                  <div class="action-buttons">
                    <button v-if="user.is_active" class="action-btn ban" @click="banUser(user)" title="封禁">封禁</button>
                    <button v-else class="action-btn unban" @click="unbanUser(user)" title="解禁">解禁</button>
                    <button class="action-btn role" @click="openRoleChangeModal(user)" title="修改权限">权限</button>
                    <button class="icon-btn danger" @click="confirmDeleteUser(user)" title="删除">🗑</button>
                  </div>
                </td>
              </tr>
              <tr v-if="paginatedUsers.length === 0">
                <td colspan="7" class="empty-state">暂无用户数据</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页控件 -->
        <div v-if="totalPages > 1" class="pagination">
          <button
            class="pagination-btn"
            :disabled="userCurrentPage === 1"
            @click="goToPage(userCurrentPage - 1)"
          >
            上一页
          </button>
          <span class="pagination-info">
            第 {{ userCurrentPage }} / {{ totalPages }} 页，共 {{ filteredUsers.length }} 个用户
          </span>
          <button
            class="pagination-btn"
            :disabled="userCurrentPage === totalPages"
            @click="goToPage(userCurrentPage + 1)"
          >
            下一页
          </button>
        </div>
      </div>

      <!-- 对话审核 -->
      <div v-show="activeTab === 'reviews'" class="tab-content">
        <div class="filter-row">
          <!-- 第一级筛选：角色（仅超级管理员可见） -->
          <select v-if="currentUser?.role === 'super_admin'" v-model="requestUserRole" @change="handleFilterChange" class="status-select">
            <option value="all">所有角色</option>
            <option value="user">普通用户</option>
            <option value="admin">管理员</option>
          </select>
          <!-- 第二级筛选：状态 -->
          <select v-model="requestStatus" @change="handleFilterChange" class="status-select">
            <option value="all">全部状态</option>
            <option value="pending">待审核</option>
            <option value="published">已通过</option>
            <option value="rejected">已驳回</option>
          </select>
          <button class="refresh-btn" @click="loadRequests">刷新</button>
        </div>

        <div class="requests-list">
          <div
            v-for="request in displayRequests"
            :key="request.id"
            class="request-card"
          >
            <div class="request-header">
              <div class="request-title" :title="request.chat_title">{{ truncateTitle(request.chat_title) }}</div>
              <div class="request-meta">
                <span class="request-user">{{ request.username }}</span>
                <span class="request-time">{{ formatDate(request.created_at) }}</span>
              </div>
            </div>

            <div class="request-body">
              <div class="request-section">
                <div class="section-label">对话内容预览（前3条）：</div>
                <div class="chat-preview">
                  <div
                    v-for="(msg, idx) in request.messages_preview.slice(0, 3)"
                    :key="idx"
                    class="preview-message"
                  >
                    <span class="msg-author">{{ msg.author_name }}：</span>
                    <span class="msg-text">{{ msg.content }}</span>
                  </div>
                </div>
              </div>

              <div v-if="request.status !== 'pending'" class="request-section review-result">
                <div class="section-label">审核结果：</div>
                <div class="section-content" :class="{ approved: request.status === 'approved', rejected: request.status === 'rejected' }">
                  {{ request.status === 'approved' ? '✓ 已通过' : '✗ 已驳回' }}
                  <span v-if="request.reject_reason"> - {{ request.reject_reason }}</span>
                </div>
              </div>
            </div>

            <div class="request-actions">
              <button class="detail-btn" @click="openDetailModal(request)">
                查看详情
              </button>
              <button v-if="request.status === 'pending'" class="reject-btn" @click="openRejectModal(request)">
                驳回
              </button>
              <button v-if="request.status === 'pending'" class="approve-btn" @click="approveRequest(request)">
                通过
              </button>
            </div>
          </div>

          <div v-if="displayRequests.length === 0" class="empty-state">
            暂无数据
          </div>
        </div>
      </div>

      <!-- 评论管理 -->
      <div v-show="activeTab === 'comments'" class="tab-content">
        <div class="comments-section">
          <h2>评论管理</h2>
          <p class="info-text">此功能将在后续版本中实现</p>
          <div class="placeholder-box">
            <div class="placeholder-icon">💬</div>
            <p>评论区将包括：</p>
            <ul class="feature-list">
              <li>查看所有评论</li>
              <li>设置违禁词</li>
              <li>删除违规评论</li>
              <li>评论审核</li>
            </ul>
          </div>
        </div>
      </div>

      <!-- 数据看板 -->
      <div v-show="activeTab === 'dashboard'" class="tab-content">
        <div class="dashboard-section">
          <h2>数据看板</h2>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-number">{{ stats.userCount }}</div>
              <div class="stat-label">用户总数</div>
            </div>
            <div class="stat-card">
              <div class="stat-number">{{ stats.adminCount }}</div>
              <div class="stat-label">管理员数量</div>
            </div>
            <div class="stat-card">
              <div class="stat-number">{{ stats.threadCount }}</div>
              <div class="stat-label">总对话数量</div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <!-- 用户新增弹窗 -->
    <div v-if="showUserModal" class="modal-overlay" @click.self="showUserModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>新增用户</h3>
          <button class="close-btn" @click="showUserModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="userForm.username" class="form-input" placeholder="请输入用户名" />
          </div>
          <div class="form-group">
            <label>邮箱</label>
            <input v-model="userForm.email" type="email" class="form-input" placeholder="请输入邮箱（可选）" />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input v-model="userForm.password" type="password" class="form-input" placeholder="请输入密码" />
          </div>
          <div class="form-group">
            <label>角色</label>
            <select v-model="userForm.role" class="form-input">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
              <option value="super_admin">超级管理员</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="secondary-btn" @click="showUserModal = false">取消</button>
          <button class="primary-btn" @click="saveUser">创建</button>
        </div>
      </div>
    </div>

    <!-- 驳回理由弹窗 -->
    <div v-if="showRejectModal" class="modal-overlay" @click.self="showRejectModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>驳回公开请求</h3>
          <button class="close-btn" @click="showRejectModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>驳回原因</label>
            <textarea
              v-model="rejectReason"
              class="form-textarea"
              rows="4"
              placeholder="请输入驳回原因（可选）"
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="secondary-btn" @click="showRejectModal = false">取消</button>
          <button class="danger-btn" @click="confirmReject">确认驳回</button>
        </div>
      </div>
    </div>

    <!-- 删除确认弹窗 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="modal small">
        <div class="modal-header">
          <h3>确认删除</h3>
          <button class="close-btn" @click="showDeleteConfirm = false">×</button>
        </div>
        <div class="modal-body">
          <p>确定要删除用户 <strong>{{ userToDelete?.username }}</strong> 吗？此操作不可恢复。</p>
        </div>
        <div class="modal-footer">
          <button class="secondary-btn" @click="showDeleteConfirm = false">取消</button>
          <button class="danger-btn" @click="deleteUser">确认删除</button>
        </div>
      </div>
    </div>

    <!-- 角色修改弹窗 -->
    <div v-if="showRoleChangeModal" class="modal-overlay" @click.self="cancelRoleChange">
      <div class="modal small">
        <div class="modal-header">
          <h3>修改用户权限</h3>
          <button class="close-btn" @click="cancelRoleChange">×</button>
        </div>
        <div class="modal-body">
          <p>修改用户 <strong>{{ roleChangeUser?.username }}</strong> 的权限：</p>
          <div class="form-group">
            <label>选择角色</label>
            <select v-model="selectedRole" class="form-input">
              <option value="user" :disabled="roleChangeUser?.role === 'user'">普通用户</option>
              <option value="admin" :disabled="roleChangeUser?.role === 'admin'">管理员</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button class="secondary-btn" @click="cancelRoleChange">取消</button>
          <button class="primary-btn" @click="confirmRoleChange" :disabled="selectedRole === roleChangeUser?.role">确认</button>
        </div>
      </div>
    </div>

    <!-- 对话详情弹窗 -->
    <div v-if="showDetailModal" class="modal-overlay" @click.self="showDetailModal = false">
      <div class="modal large">
        <div class="modal-header">
          <h3 class="detail-modal-title" :title="detailRequest?.chat_title">对话详情 - {{ truncateTitle(detailRequest?.chat_title) }}</h3>
          <button class="close-btn" @click="showDetailModal = false">×</button>
        </div>
        <div class="modal-body">
          <div v-if="detailRequest" class="detail-content">
            <div class="detail-section">
              <div class="detail-label">申请用户：</div>
              <div class="detail-value">{{ detailRequest.username }}</div>
            </div>
            <div class="detail-section">
              <div class="detail-label">申请时间：</div>
              <div class="detail-value">{{ formatDate(detailRequest.created_at) }}</div>
            </div>
            <div v-if="detailRequest.reason" class="detail-section">
              <div class="detail-label">申请理由：</div>
              <div class="detail-value">{{ detailRequest.reason }}</div>
            </div>
            <div class="detail-section">
              <div class="detail-label">完整对话内容：</div>
              <div class="chat-full-preview">
                <div
                  v-for="(msg, idx) in detailRequest.messages_preview"
                  :key="idx"
                  class="detail-message"
                >
                  <div class="detail-msg-author">{{ msg.author_name }}</div>
                  <div class="detail-msg-content">{{ msg.content }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="secondary-btn" @click="showDetailModal = false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { apiClient } from './api.js';

const props = defineProps({
  currentUser: {
    type: Object,
    default: null,
  }
});

defineEmits(['back']);

// 根据用户角色设置默认标签页
const getDefaultTab = () => {
  if (!props.currentUser) return 'reviews';

  const role = props.currentUser.role || 'user';
  if (role === 'super_admin') {
    return 'users'; // 超级管理员默认显示用户管理
  } else if (role === 'admin') {
    return 'reviews'; // 管理员默认显示公开对话管理
  }
  return 'reviews';
};

// 标签页状态
const activeTab = ref(getDefaultTab());

// 用户管理相关
const users = ref([]);
const userSearch = ref('');
const showUserModal = ref(false);
const editingUser = ref(null);
const userForm = ref({
  username: '',
  email: '',
  password: '',
  role: 'user',
  is_active: true,
});

// 用户分页相关
const userCurrentPage = ref(1);
const userPageSize = ref(10);

// 角色修改相关
const showRoleChangeModal = ref(false);
const roleChangeUser = ref(null);
const selectedRole = ref('user');

// 对话审核相关
const allRequests = ref([]);
const displayRequests = ref([]);
const requestStatus = ref('pending'); // 默认显示待审核
const requestUserRole = ref('all'); // 角色筛选：all/user/admin
const showRejectModal = ref(false);
const rejectReason = ref('');
const reviewingRequest = ref(null);
const pendingCount = ref(0);

// 对话详情弹窗
const showDetailModal = ref(false);
const detailRequest = ref(null);

// 已公开对话
const publicChats = ref([]);

// 数据看板
const stats = ref({
  userCount: 0,
  adminCount: 0,
  threadCount: 0,
  publishedCount: 0,
  violationCount: 0,
  commentCount: 0,
});

// 删除确认
const showDeleteConfirm = ref(false);
const userToDelete = ref(null);

// 格式化日期
function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

// 截断标题，超过60字显示省略号
function truncateTitle(title, maxLength = 60) {
  if (!title) return '';
  if (title.length <= maxLength) return title;
  return title.substring(0, maxLength) + '...';
}

// 获取角色显示名称
function getRoleName(role) {
  const roleMap = {
    'guest': '游客',
    'user': '普通用户',
    'admin': '管理员',
    'super_admin': '超级管理员'
  };
  return roleMap[role] || role;
}

// 测试用户数据
function getMockUsers() {
  return [
    { id: '1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p', username: '玿宸', email: 'user1@example.com', role: 'user', is_active: true, created_at: '2024-01-15T10:30:00' },
    { id: '2b3c4d5e-6f7g-8h9i-0j1k-2l3m4n5o6p7q', username: '张三', email: 'zhangsan@example.com', role: 'user', is_active: true, created_at: '2024-01-16T14:20:00' },
    { id: '3c4d5e6f-7g8h-9i0j-1k2l-3m4n5o6p7q8r', username: '李四', email: 'lisi@example.com', role: 'user', is_active: true, created_at: '2024-01-17T09:15:00' },
    { id: '4d5e6f7g-8h9i-0j1k-2l3m-4n5o6p7q8r9s', username: '王五', email: 'wangwu@example.com', role: 'user', is_active: false, created_at: '2024-01-18T16:45:00' },
    { id: '5e6f7g8h-9i0j-1k2l-3m4n-5o6p7q8r9s0t', username: 'admin', email: 'admin@example.com', role: 'admin', is_active: true, created_at: '2024-01-10T09:00:00' },
    { id: '6f7g8h9i-0j1k-2l3m-4n5o6p7q8r9s0t1u', username: 'superadmin', email: 'superadmin@example.com', role: 'super_admin', is_active: true, created_at: '2024-01-01T08:00:00' },
  ];
}

// 过滤后的用户列表
const filteredUsers = computed(() => {
  // 先过滤掉当前超管用户（如果是超管的话）
  let filtered = users.value;
  if (props.currentUser?.role === 'super_admin') {
    filtered = filtered.filter(u => u.id !== props.currentUser.user_id && u.id !== props.currentUser.id);
  }

  // 再按搜索关键词过滤
  if (!userSearch.value) return filtered;
  const kw = userSearch.value.toLowerCase();
  return filtered.filter(u =>
    u.username?.toLowerCase().includes(kw) ||
    u.email?.toLowerCase().includes(kw)
  );
});

// 分页后的用户列表
const paginatedUsers = computed(() => {
  const start = (userCurrentPage.value - 1) * userPageSize.value;
  const end = start + userPageSize.value;
  return filteredUsers.value.slice(start, end);
});

// 总页数
const totalPages = computed(() => {
  return Math.ceil(filteredUsers.value.length / userPageSize.value);
});

// 翻页方法
function goToPage(page) {
  if (page >= 1 && page <= totalPages.value) {
    userCurrentPage.value = page;
  }
}

// 过滤用户时重置页码
function filterUsers() {
  userCurrentPage.value = 1;
}

// 加载用户列表
async function loadUsers() {
  try {
    const result = await apiClient.request('/admin/users');
    users.value = result.users || [];
    // 确保user_id映射到id
    users.value = users.value.map(u => ({
      ...u,
      id: u.user_id || u.id
    }));
  } catch (err) {
    console.error('加载用户列表失败:', err);
    alert('加载用户列表失败: ' + err.message);
    // 如果API调用失败，使用模拟数据
    users.value = getMockUsers();
  }
}

// 打开新增用户弹窗
function openAddUserModal() {
  editingUser.value = null;
  userForm.value = {
    username: '',
    email: '',
    password: '',
    role: 'user',
    is_active: true
  };
  showUserModal.value = true;
}

// 编辑用户（已移除）
function editUser(user) {
  // 编辑功能已禁用
  alert('编辑用户信息功能已禁用\n请使用"权限"按钮修改用户角色');
}

// 修改用户角色 - 打开弹窗
function openRoleChangeModal(user) {
  roleChangeUser.value = user;
  // 默认选择与当前不同的角色（只允许在 user 和 admin 之间切换）
  if (user.role === 'user') {
    selectedRole.value = 'admin';
  } else {
    selectedRole.value = 'user';
  }
  showRoleChangeModal.value = true;
}

// 确认修改角色
async function confirmRoleChange() {
  if (!roleChangeUser.value) return;

  const user = roleChangeUser.value;
  const newRole = selectedRole.value;

  const roleMap = {
    'user': '普通用户',
    'admin': '管理员'
  };

  try {
    await apiClient.request(`/admin/users/${user.id}`, {
      method: 'PUT',
      body: JSON.stringify({ role: newRole })
    });
    // 更新本地状态
    user.role = newRole;
    showRoleChangeModal.value = false;
    roleChangeUser.value = null;
  } catch (err) {
    console.error('修改角色失败:', err);
    alert('修改角色失败: ' + err.message);
  }
}

// 取消修改角色
function cancelRoleChange() {
  showRoleChangeModal.value = false;
  roleChangeUser.value = null;
  selectedRole.value = 'user';
}

// 保存用户（仅新增）
async function saveUser() {
  if (!userForm.value.username || !userForm.value.password) {
    alert('请填写用户名和密码');
    return;
  }

  try {
    // 新增用户
    const result = await apiClient.request('/admin/users', {
      method: 'POST',
      body: JSON.stringify({
        username: userForm.value.username,
        password: userForm.value.password,
        email: userForm.value.email || '',
        role: userForm.value.role || 'user',
        is_active: true
      })
    });

    // 添加到本地列表
    users.value.push({
      id: result.user.user_id,
      username: result.user.username,
      email: result.user.email,
      role: result.user.role,
      is_active: result.user.is_active,
      created_at: new Date().toISOString()
    });

    showUserModal.value = false;
    editingUser.value = null;
    userForm.value = { username: '', email: '', password: '', role: 'user', is_active: true };
    alert('✅ 用户创建成功');
  } catch (err) {
    console.error('保存用户失败:', err);
    alert('保存用户失败: ' + err.message);
  }
}

// 确认删除用户
function confirmDeleteUser(user) {
  userToDelete.value = user;
  showDeleteConfirm.value = true;
}

// 删除用户
async function deleteUser() {
  if (!userToDelete.value) return;

  try {
    await apiClient.request(`/admin/users/${userToDelete.value.id}`, {
      method: 'DELETE'
    });
    // 从列表中移除
    users.value = users.value.filter(u => u.id !== userToDelete.value.id);
    showDeleteConfirm.value = false;
    alert('✅ 用户已删除');
  } catch (err) {
    console.error('删除用户失败:', err);
    alert('删除用户失败: ' + err.message);
  } finally {
    userToDelete.value = null;
  }
}

// 封禁用户
async function banUser(user) {
  if (!confirm(`确定要封禁用户"${user.username}"吗？`)) return;

  try {
    await apiClient.request(`/admin/users/${user.id}/ban`, {
      method: 'PUT',
      body: JSON.stringify({})
    });
    // 更新本地状态
    user.is_active = false;
    alert('✅ 用户已被封禁');
  } catch (err) {
    console.error('封禁用户失败:', err);
    alert('封禁失败: ' + err.message);
  }
}

// 解禁用户
async function unbanUser(user) {
  if (!confirm(`确定要解禁用户"${user.username}"吗？`)) return;

  try {
    await apiClient.request(`/admin/users/${user.id}/unban`, {
      method: 'PUT'
    });
    // 更新本地状态
    user.is_active = true;
    alert('✅ 用户已解禁');
  } catch (err) {
    console.error('解禁用户失败:', err);
    alert('解禁失败: ' + err.message);
  }
}

// 测试请求数据
function getMockRequests() {
  return [
    {
      id: 'req-001',
      chat_id: 'chat-001',
      chat_title: '如何学习Vue3',
      username: '玿宸',
      reason: '这个对话对学习Vue很有帮助，希望公开分享给更多初学者',
      created_at: '2024-01-20T10:30:00',
      status: 'pending',
      messages_preview: [
        { author_name: '用户', content: 'Vue3相比Vue2有哪些主要改进？' },
        { author_name: '理论家', content: 'Vue3的主要改进包括：1. Composition API 2. 性能提升 3. TypeScript支持更好' },
        { author_name: '实践者', content: '我来演示一下Composition API的使用方式...' },
      ],
    },
    {
      id: 'req-002',
      chat_id: 'chat-002',
      chat_title: 'Python数据科学入门',
      username: '张三',
      reason: '适合新手入门，内容全面易懂',
      created_at: '2024-01-19T15:45:00',
      status: 'pending',
      messages_preview: [
        { author_name: '用户', content: 'Python做数据分析需要学什么？' },
        { author_name: '理论家', content: '主要需要掌握：NumPy、Pandas、Matplotlib等库' },
      ],
    },
    {
      id: 'req-003',
      chat_id: 'chat-003',
      chat_title: 'JavaScript异步编程详解',
      username: '李四',
      reason: '异步编程是前端难点，这个对话讲解很清晰',
      created_at: '2024-01-18T09:20:00',
      status: 'pending',
      messages_preview: [
        { author_name: '用户', content: 'Promise和async/await有什么区别？' },
        { author_name: '理论家', content: 'Promise是异步编程的解决方案，async/await是Promise的语法糖...' },
        { author_name: '质疑者', content: '那错误处理有什么不同吗？' },
      ],
    },
    {
      id: 'req-004',
      chat_id: 'chat-004',
      chat_title: 'React Hooks最佳实践',
      username: '王五',
      reason: '总结了Hooks使用中的一些坑和最佳实践',
      created_at: '2024-01-17T14:00:00',
      status: 'approved',
      messages_preview: [
        { author_name: '用户', content: 'useEffect的依赖数组怎么用？' },
        { author_name: '理论家', content: '依赖数组用于控制effect何时重新执行...' },
      ],
      reject_reason: '',
    },
    {
      id: 'req-005',
      chat_id: 'chat-005',
      chat_title: '一些不合适的内容',
      username: '测试用户',
      reason: '测试用',
      created_at: '2024-01-16T11:30:00',
      status: 'rejected',
      messages_preview: [
        { author_name: '用户', content: '一些不合适的对话内容...' },
      ],
      reject_reason: '内容不符合社区规范，已驳回',
    },
  ];
}

// 加载公开请求
async function loadRequests() {
  try {
    // 如果是超级管理员，传递角色筛选参数
    const params = new URLSearchParams({ status: requestStatus.value });
    if (props.currentUser?.role === 'super_admin' && requestUserRole.value !== 'all') {
      params.append('user_role', requestUserRole.value);
    }

    const result = await apiClient.request(`/admin/publication-requests?${params.toString()}`);
    allRequests.value = result.requests || [];
    filterRequests();
    updatePendingCount();
  } catch (err) {
    console.error('加载公开请求失败:', err);
    // 如果API调用失败，使用模拟数据
    allRequests.value = getMockRequests();
    filterRequests();
    updatePendingCount();
  }
}

// 处理筛选条件变化
function handleFilterChange() {
  // 重新加载数据并过滤
  loadRequests();
}

// 过滤请求
function filterRequests() {
  let filtered = allRequests.value;

  // 按状态筛选
  if (requestStatus.value !== 'all') {
    filtered = filtered.filter(r => r.status === requestStatus.value);
  }

  // 按角色筛选（仅超级管理员）
  if (props.currentUser?.role === 'super_admin' && requestUserRole.value !== 'all') {
    filtered = filtered.filter(r => r.user_role === requestUserRole.value);
  }

  // 管理员只能看到普通用户的申请
  if (props.currentUser?.role === 'admin') {
    filtered = filtered.filter(r => r.user_role === 'user');
  }

  displayRequests.value = filtered;
}

// 更新待审核数量
function updatePendingCount() {
  pendingCount.value = allRequests.value.filter(r => r.status === 'pending').length;
}

// 打开驳回弹窗
function openRejectModal(request) {
  reviewingRequest.value = request;
  rejectReason.value = '';
  showRejectModal.value = true;
}

// 打开详情弹窗
function openDetailModal(request) {
  detailRequest.value = request;
  showDetailModal.value = true;
}

// 通过请求
async function approveRequest(request) {
  if (!confirm(`确定通过对话"${request.chat_title}"的公开请求吗？`)) return;

  try {
    await apiClient.request(`/admin/publication-requests/${request.id}/review`, {
      method: 'POST',
      body: JSON.stringify({ approved: true, reason: '' })
    });
    // 重新加载列表以获取最新状态
    await loadRequests();
    alert('✅ 已通过审核');
  } catch (err) {
    console.error('审核失败:', err);
    alert('审核失败: ' + err.message);
  }
}

// 确认驳回
async function confirmReject() {
  if (!reviewingRequest.value) return;

  try {
    await apiClient.request(`/admin/publication-requests/${reviewingRequest.value.id}/review`, {
      method: 'POST',
      body: JSON.stringify({ approved: false, reason: rejectReason.value })
    });
    // 重新加载列表以获取最新状态
    await loadRequests();
    showRejectModal.value = false;
    rejectReason.value = '';
    alert('✅ 已驳回');
  } catch (err) {
    console.error('驳回失败:', err);
    alert('驳回失败: ' + err.message);
  }
}

// 测试公开对话数据
function getMockPublicChats() {
  return [
    { id: '1', title: 'JavaScript异步编程详解', username: '李四', published_at: '2024-01-18T10:00:00', message_count: 25, view_count: 156 },
    { id: '2', title: 'React Hooks最佳实践', username: '王五', published_at: '2024-01-17T14:30:00', message_count: 18, view_count: 89 },
    { id: '3', title: 'CSS Grid布局完全指南', username: '玿宸', published_at: '2024-01-15T09:00:00', message_count: 32, view_count: 234 },
  ];
}

// 加载已公开对话
function loadPublicChats() {
  publicChats.value = getMockPublicChats();
}

// 加载数据看板统计
function loadDashboardStats() {
  // 计算统计数据
  const allUsers = getMockUsers();
  stats.value.userCount = allUsers.filter(u => u.role === 'user').length;
  stats.value.adminCount = allUsers.filter(u => u.role === 'admin').length; // 不包括超级管理员
  stats.value.threadCount = getMockRequests().length + getMockPublicChats().length;
}

// 初始化加载
onMounted(() => {
  // 只有超级管理员才加载用户列表
  if (props.currentUser?.role === 'super_admin') {
    loadUsers();
  }
  loadRequests();
  loadPublicChats();
  loadDashboardStats();
});
</script>

<style scoped>
.admin {
  display: flex;
  flex-direction: column;
  background: radial-gradient(1200px 800px at 20% 0%, #14204a 0%, #0b1020 55%);
  overflow: hidden;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255,255,255,.08);
  background: rgba(10,16,34,.45);
  backdrop-filter: blur(10px);
}

.brand {
  display: flex;
  gap: 12px;
  align-items: center;
}

.logo {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: rgba(199,125,255,.18);
  border: 1px solid rgba(199,125,255,.35);
  font-weight: 800;
}

.title .name {
  font-size: 18px;
  font-weight: 800;
}

.title .sub {
  font-size: 12px;
  color: var(--muted);
  margin-top: 2px;
}

.back-btn {
  padding: 10px 18px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
}

.back-btn:hover {
  background: rgba(255,255,255,.08);
  border-color: rgba(255,255,255,.20);
}

.main {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.tabs {
  display: flex;
  gap: 8px;
  padding: 16px 24px;
  border-bottom: 1px solid rgba(255,255,255,.08);
  background: rgba(10,16,34,.3);
}

.tab {
  position: relative;
  padding: 10px 18px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--muted);
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
}

.tab:hover {
  color: var(--text);
  background: rgba(255,255,255,.04);
}

.tab.active {
  color: var(--text);
  background: rgba(106,167,255,.15);
  border-color: rgba(106,167,255,.30);
}

.tab .badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #ff6b6b;
  color: white;
  font-size: 11px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  min-height: 0;
}

.actions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  max-width: 300px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  outline: none;
}

.search-input:focus {
  border-color: rgba(106,167,255,.40);
  background: rgba(106,167,255,.08);
}

.primary-btn, .refresh-btn, .secondary-btn, .danger-btn {
  padding: 10px 18px;
  border-radius: 12px;
  border: 1px solid rgba(106,167,255,.25);
  background: rgba(106,167,255,.18);
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
}

.primary-btn:hover, .refresh-btn:hover {
  filter: brightness(1.1);
  border-color: rgba(106,167,255,.45);
}

.secondary-btn {
  border-color: rgba(255,255,255,.15);
  background: rgba(255,255,255,.08);
}

.danger-btn {
  border-color: rgba(255,107,107,.30);
  background: rgba(255,107,107,.18);
}

.danger-btn:hover {
  border-color: rgba(255,107,107,.50);
}

/* 表格 */
.table-container {
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.03);
  overflow: hidden;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th {
  padding: 14px 16px;
  text-align: left;
  font-size: 12px;
  color: var(--muted);
  font-weight: 700;
  border-bottom: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.03);
}

.data-table td {
  padding: 14px 16px;
  border-bottom: 1px solid rgba(255,255,255,.04);
}

.data-table tr:hover td {
  background: rgba(255,255,255,.03);
}

.data-table tr:last-child td {
  border-bottom: none;
}

.mono {
  font-family: 'SF Mono', Consolas, monospace;
  font-size: 12px;
  opacity: 0.8;
}

.role-tag{
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;

  padding: 3px 10px !important;
  border-radius: 999px !important;

  font-size: 11px !important;
  font-weight: 700 !important;
  line-height: 1 !important;

  /* 关键：防止被全局样式改成“通天柱” */
  position: static !important;
  inset: auto !important;
  width: fit-content !important;
  height: auto !important;
  max-width: 100% !important;
  white-space: nowrap !important;

  background: rgba(106,167,255,.15) !important;
  color: var(--text) !important;
  border: 1px solid rgba(255,255,255,.10) !important;
}

.role-tag.admin{
  background: rgba(199,125,255,.18) !important;
  border-color: rgba(199,125,255,.35) !important;
  color: #c77dff !important;
}

.role-tag.super_admin{
  background: rgba(255,199,89,.18) !important;
  border-color: rgba(255,199,89,.35) !important;
  color: #ffc757 !important;
}

.username-cell.admin {
  color: #c77dff;
  font-weight: 700;
}

.username-cell.super_admin {
  color: #ffc757;
  font-weight: 700;
}


.status-tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 99px;
  background: rgba(255,107,107,.15);
  color: #ff8787;
}

.status-tag.active {
  background: rgba(81,209,138,.15);
  color: #51d18a;
}

.action-buttons {
  display: flex;
  gap: 8px;
  align-items: center;
}

.action-btn {
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s ease;
}

.action-btn:hover {
  background: rgba(255,255,255,.10);
}

.action-btn.ban {
  border-color: rgba(255,107,107,.30);
  background: rgba(255,107,107,.15);
  color: #ff6b6b;
}

.action-btn.ban:hover {
  border-color: rgba(255,107,107,.50);
  background: rgba(255,107,107,.25);
}

.action-btn.unban {
  border-color: rgba(81,209,138,.30);
  background: rgba(81,209,138,.15);
  color: #51d18a;
}

.action-btn.unban:hover {
  border-color: rgba(81,209,138,.50);
  background: rgba(81,209,138,.25);
}

.action-btn.role {
  border-color: rgba(199,125,255,.30);
  background: rgba(199,125,255,.15);
  color: #c77dff;
}

.action-btn.role:hover {
  border-color: rgba(199,125,255,.50);
  background: rgba(199,125,255,.25);
}

.icon-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--muted);
  cursor: pointer;
  transition: all .15s ease;
}

.icon-btn:hover {
  background: rgba(255,255,255,.10);
  color: var(--text);
}

.icon-btn.danger:hover {
  background: rgba(255,107,107,.15);
  color: #ff6b6b;
}

/* 评论管理和数据看板 */
.comments-section,
.dashboard-section {
  padding: 20px;
}

.comments-section h2,
.dashboard-section h2 {
  font-size: 20px;
  font-weight: 800;
  margin-bottom: 20px;
}

.info-text {
  color: var(--muted);
  margin-bottom: 20px;
}

.placeholder-box {
  padding: 40px;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.03);
  text-align: center;
}

.placeholder-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.feature-list {
  list-style: none;
  padding: 0;
  display: inline-block;
  text-align: left;
}

.feature-list li {
  padding: 8px 0;
  color: var(--muted);
}

.feature-list li::before {
  content: "• ";
  color: #6aa7ff;
  margin-right: 8px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.stat-card {
  padding: 24px;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.03);
  text-align: center;
}

.stat-number {
  font-size: 36px;
  font-weight: 800;
  color: #6aa7ff;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  color: var(--muted);
}

/* 标签布局 - 根据数量调整 */
.tabs.three-tabs {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
}

.tabs:not(.three-tabs) {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
}

/* 空状态 */
.empty-state {
  padding: 40px;
  text-align: center;
  color: var(--muted);
}

/* 请求列表 */
.filter-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.status-select {
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(106,167,255,.30);
  background: rgba(106,167,255,.08);
  color: #6aa7ff;
  outline: none;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.status-select:hover {
  border-color: rgba(106,167,255,.50);
  background: rgba(106,167,255,.15);
}

.status-select:focus {
  border-color: rgba(106,167,255,.60);
  box-shadow: 0 0 0 3px rgba(106,167,255,.15);
}

.status-select option {
  background: #1e1e2e;
  color: var(--text);
  padding: 8px;
}

.request-card {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.03);
}

.request-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 14px;
}

.request-title {
  font-size: 16px;
  font-weight: 800;
}

.request-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
  color: var(--muted);
  align-items: flex-end;
}

.request-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.request-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-label {
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}

.section-content {
  font-size: 14px;
  line-height: 1.5;
}

.chat-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-radius: 12px;
  background: rgba(0,0,0,.2);
}

.preview-message {
  font-size: 13px;
  line-height: 1.5;
  padding-bottom: 10px;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(255,255,255,.15);
}

.preview-message:last-child {
  padding-bottom: 0;
  margin-bottom: 0;
  border-bottom: none;
}

.msg-author {
  font-weight: 700;
  color: #6aa7ff;
}

.review-result .section-content {
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(255,255,255,.04);
}

.review-result .section-content.approved {
  color: #51d18a;
}

.review-result .section-content.rejected {
  color: #ff6b6b;
}

.request-actions {
  display: flex;
  gap: 12px;
  margin-top: 14px;
  justify-content: flex-end;
}

.approve-btn, .reject-btn {
  padding: 10px 20px;
  border-radius: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
}

.approve-btn {
  border: 1px solid rgba(81,209,138,.30);
  background: rgba(81,209,138,.18);
  color: var(--text);
}

.approve-btn:hover {
  border-color: rgba(81,209,138,.50);
}

.reject-btn {
  border: 1px solid rgba(255,107,107,.30);
  background: rgba(255,107,107,.18);
  color: var(--text);
}

.reject-btn:hover {
  border-color: rgba(255,107,107,.50);
}

/* 查看详情按钮 */
.detail-btn {
  padding: 10px 20px;
  border-radius: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
  border: 1px solid rgba(106,167,255,.30);
  background: rgba(106,167,255,.18);
  color: var(--text);
}

.detail-btn:hover {
  border-color: rgba(106,167,255,.50);
}

/* 分页控件 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 20px;
  padding: 16px;
}

.pagination-btn {
  padding: 8px 16px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  font-weight: 600;
  cursor: pointer;
  transition: all .18s ease;
}

.pagination-btn:hover:not(:disabled) {
  background: rgba(106,167,255,.15);
  border-color: rgba(106,167,255,.30);
}

.pagination-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.pagination-info {
  font-size: 14px;
  color: var(--muted);
}

/* 详情弹窗样式 */
.detail-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.detail-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-label {
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
}

.detail-value {
  font-size: 14px;
  color: var(--text);
  line-height: 1.6;
}

.chat-full-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border-radius: 12px;
  background: rgba(0,0,0,.2);
  max-height: 400px;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 详情弹窗对话内容滚动条样式 */
.chat-full-preview::-webkit-scrollbar {
  width: 8px;
}

.chat-full-preview::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 4px;
}

.chat-full-preview::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 4px;
  transition: background 0.3s ease;
}

.chat-full-preview::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.35);
}

/* 详情弹窗中的消息样式 - 完整显示，不截断 */
.detail-message {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-bottom: 16px;
  margin-bottom: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.detail-message:last-child {
  padding-bottom: 0;
  margin-bottom: 0;
  border-bottom: none;
}

.detail-msg-author {
  font-size: 14px;
  font-weight: 700;
  color: #6aa7ff;
  flex-shrink: 0;
}

.detail-msg-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text);
  white-space: pre-wrap;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  /* 确保文本不会被截断或省略 */
  overflow: visible;
  text-overflow: clip;
  max-width: 100%;
  display: block;
  width: 100%;
}

/* 强制确保详情消息内容不受全局样式影响 */
.detail-msg-content * {
  white-space: pre-wrap !important;
  text-overflow: clip !important;
  overflow: visible !important;
}

/* 公开对话列表 */
.public-chats-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.public-chat-card {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.03);
  cursor: pointer;
  transition: all .15s ease;
}

.public-chat-card:hover {
  background: rgba(255,255,255,.05);
  border-color: rgba(106,167,255,.20);
}

.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chat-title {
  font-weight: 800;
}

.chat-meta {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--muted);
}

.chat-stats {
  margin-top: 10px;
  font-size: 13px;
  color: var(--muted);
  display: flex;
  gap: 8px;
}

/* 弹窗 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  width: 90%;
  max-width: 500px;
  border-radius: 18px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(17,26,51,.98);
  box-shadow: 0 20px 60px rgba(0,0,0,.4);
}

.modal.small {
  max-width: 400px;
}

.modal.large {
  max-width: 800px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
}

.modal.large .modal-body {
  overflow-y: auto;
  max-height: calc(80vh - 140px);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255,255,255,.08);
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
}

/* 详情弹窗标题样式 - 超过60字显示省略号 */
.detail-modal-title {
  max-width: 700px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.close-btn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  cursor: pointer;
  font-size: 18px;
}

.modal-body {
  padding: 20px;
}

.modal-body p {
  margin: 0;
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid rgba(255,255,255,.08);
}

/* 表单 */
.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 8px;
  color: var(--muted);
}

.form-group.checkbox label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.form-input, .form-textarea {
  width: 100%;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  outline: none;
  font-size: 14px;
}

.form-input:focus, .form-textarea:focus {
  border-color: rgba(106,167,255,.40);
  background: rgba(106,167,255,.08);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

/* ========== 浅色模式样式 ========== */
:root[data-theme="light"] .admin {
  background: #f5f5f5;
}

/* 浅色模式下选择框选项样式 */
:root[data-theme="light"] .status-select option {
  background: #ffffff;
  color: #000000;
}

/* 修复公开对话管理页面的滚动条 */
.requests-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 20px;
  overflow-y: auto;
  max-height: calc(100vh - 200px);
}

.requests-list::-webkit-scrollbar {
  width: 8px;
}

.requests-list::-webkit-scrollbar-thumb {
  background-color: rgba(255,255,255,.2);
  border-radius: 4px;
}

.requests-list::-webkit-scrollbar-thumb:hover {
  background-color: rgba(255,255,255,.3);
}

:root[data-theme="light"] .requests-list::-webkit-scrollbar-thumb {
  background-color: rgba(0,0,0,.2);
}

:root[data-theme="light"] .requests-list::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0,0,0,.3);
}

:root[data-theme="light"] .requests-list {
  max-height: calc(100vh - 200px);
}

:root[data-theme="light"] .topbar {
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .title .name {
  color: #000000;
}

:root[data-theme="light"] .title .sub {
  color: #666666;
}

:root[data-theme="light"] .logo {
  background: rgba(199, 125, 255, 0.2);
  border-color: rgba(199, 125, 255, 0.4);
  color: #c77dff;
}

:root[data-theme="light"] .back-btn {
  background: rgba(0, 0, 0, 0.05);
  border-color: rgba(0, 0, 0, 0.1);
  color: #000000;
}

:root[data-theme="light"] .back-btn:hover {
  background: rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .tabs {
  background: rgba(255, 255, 255, 0.9);
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .tab {
  color: #666666;
}

:root[data-theme="light"] .tab:hover {
  color: #000000;
  background: rgba(0, 0, 0, 0.05);
}

:root[data-theme="light"] .tab.active {
  color: #000000;
  background: rgba(106, 167, 255, 0.15);
  border-color: rgba(106, 167, 255, 0.3);
}

:root[data-theme="light"] .tab-content {
  background: #ffffff;
}

:root[data-theme="light"] .table-container {
  background: #ffffff;
  border-color: rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .data-table th {
  color: #666666;
  background: #f5f5f5;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .data-table td {
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  color: #000000;
}

:root[data-theme="light"] .data-table tr:hover td {
  background: #f9f9f9;
}

:root[data-theme="light"] .search-input,
:root[data-theme="light"] .status-select {
  background: #ffffff;
  border-color: rgba(0, 0, 0, 0.15);
  color: #000000;
}

:root[data-theme="light"] .status-select:hover {
  border-color: rgba(0, 0, 0, 0.25);
  background: #f9f9f9;
}

:root[data-theme="light"] .search-input:focus,
:root[data-theme="light"] .status-select:focus {
  border-color: rgba(106, 167, 255, 0.4);
  background: #ffffff;
}

:root[data-theme="light"] .primary-btn,
:root[data-theme="light"] .refresh-btn {
  background: linear-gradient(135deg, #6a7dff 0%, #9d6aff 100%);
  border-color: transparent;
  color: #ffffff;
}

:root[data-theme="light"] .secondary-btn {
  background: rgba(0, 0, 0, 0.05);
  border-color: rgba(0, 0, 0, 0.15);
  color: #000000;
}

:root[data-theme="light"] .danger-btn {
  background: linear-gradient(135deg, #ff6b6b 0%, #ff8787 100%);
  border-color: transparent;
  color: #ffffff;
}

:root[data-theme="light"] .role-tag {
  background: rgba(106, 167, 255, 0.15);
  border-color: rgba(106, 167, 255, 0.3);
  color: #6a7dff;
}

:root[data-theme="light"] .role-tag.admin {
  background: rgba(199, 125, 255, 0.2);
  border-color: rgba(199, 125, 255, 0.4);
  color: #c77dff;
}

:root[data-theme="light"] .role-tag.super_admin {
  background: rgba(255, 199, 89, 0.2);
  border-color: rgba(255, 199, 89, 0.4);
  color: #ffc757;
}

:root[data-theme="light"] .username-cell.admin {
  color: #c77dff;
}

:root[data-theme="light"] .username-cell.super_admin {
  color: #ffc757;
}

:root[data-theme="light"] .request-card,
:root[data-theme="light"] .public-chat-card {
  background: #ffffff;
  border-color: rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .request-card:hover,
:root[data-theme="light"] .public-chat-card:hover {
  background: #f9f9f9;
  border-color: rgba(106, 167, 255, 0.2);
}

:root[data-theme="light"] .request-title,
:root[data-theme="light"] .chat-title {
  color: #000000;
}

:root[data-theme="light"] .request-meta,
:root[data-theme="light"] .chat-meta,
:root[data-theme="light"] .chat-stats,
:root[data-theme="light"] .section-label {
  color: #666666;
}

:root[data-theme="light"] .section-content {
  color: #000000;
}

:root[data-theme="light"] .chat-preview {
  background: #f5f5f5;
}

:root[data-theme="light"] .preview-message {
  border-bottom: 1px solid rgba(0,0,0,.15);
}

:root[data-theme="light"] .msg-author {
  color: #6a7dff;
}

:root[data-theme="light"] .modal {
  background: #ffffff;
  border-color: rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .modal-header h3 {
  color: #000000;
}

:root[data-theme="light"] .close-btn {
  background: rgba(0, 0, 0, 0.05);
  border-color: rgba(0, 0, 0, 0.1);
  color: #000000;
}

:root[data-theme="light"] .form-group label {
  color: #666666;
}

:root[data-theme="light"] .form-input,
:root[data-theme="light"] .form-textarea {
  background: #ffffff;
  border-color: rgba(0, 0, 0, 0.15);
  color: #000000;
}

:root[data-theme="light"] .form-input:focus,
:root[data-theme="light"] .form-textarea:focus {
  border-color: rgba(106, 167, 255, 0.4);
  background: #ffffff;
}

:root[data-theme="light"] .empty-state {
  color: #999999;
}

:root[data-theme="light"] .approve-btn {
  background: linear-gradient(135deg, #51d18a 0%, #7dd19a 100%);
  border-color: transparent;
  color: #ffffff;
}

:root[data-theme="light"] .reject-btn {
  background: linear-gradient(135deg, #ff6b6b 0%, #ff8787 100%);
  border-color: transparent;
  color: #ffffff;
}

:root[data-theme="light"] .icon-btn {
  background: rgba(0, 0, 0, 0.05);
  border-color: rgba(0, 0, 0, 0.1);
  color: #666666;
}

:root[data-theme="light"] .icon-btn:hover {
  background: rgba(0, 0, 0, 0.1);
  color: #000000;
}

:root[data-theme="light"] .icon-btn.danger:hover {
  background: rgba(255, 107, 107, 0.15);
  color: #ff6b6b;
}

/* 浅色模式下的分页控件 */
:root[data-theme="light"] .pagination-btn {
  background: #ffffff;
  border-color: rgba(0, 0, 0, 0.15);
  color: #000000;
}

:root[data-theme="light"] .pagination-btn:hover:not(:disabled) {
  background: #f5f5f5;
  border-color: rgba(106, 167, 255, 0.3);
}

:root[data-theme="light"] .pagination-info {
  color: #666666;
}

/* 浅色模式下的详情按钮 */
:root[data-theme="light"] .detail-btn {
  background: rgba(106, 167, 255, 0.15);
  border-color: rgba(106, 167, 255, 0.3);
  color: #000000;
}

:root[data-theme="light"] .detail-btn:hover {
  background: rgba(106, 167, 255, 0.25);
  border-color: rgba(106, 167, 255, 0.5);
}

/* 浅色模式下的详情内容 */
:root[data-theme="light"] .detail-label {
  color: #666666;
}

:root[data-theme="light"] .detail-value {
  color: #000000;
}

:root[data-theme="light"] .chat-full-preview {
  background: #f5f5f5;
}

/* 浅色模式下的详情弹窗对话内容滚动条 */
:root[data-theme="light"] .chat-full-preview::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
}

:root[data-theme="light"] .chat-full-preview::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
}

:root[data-theme="light"] .chat-full-preview::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.35);
}

/* 浅色模式下的详情消息样式 */
:root[data-theme="light"] .detail-message {
  border-bottom-color: rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .detail-msg-author {
  color: #6a7dff;
}

:root[data-theme="light"] .detail-msg-content {
  color: #000000;
}

/* 确保浅色模式下的消息内容也完整显示 */
:root[data-theme="light"] .detail-msg-content * {
  white-space: pre-wrap !important;
  text-overflow: clip !important;
  overflow: visible !important;
}
</style>
