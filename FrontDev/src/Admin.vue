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
      <div class="tabs">
        <!-- 只有超级管理员才能看到用户管理标签 -->
        <button
          v-if="currentUser && (currentUser.role === 'super_admin')"
          class="tab"
          :class="{ active: activeTab === 'users' }"
          @click="activeTab = 'users'"
        >
          用户管理
        </button>
        <!-- 管理员和超级管理员都可以看到对话审核 -->
        <button
          v-if="currentUser && (currentUser.role === 'admin' || currentUser.role === 'super_admin')"
          class="tab"
          :class="{ active: activeTab === 'requests' }"
          @click="activeTab = 'requests'"
        >
          对话审核
          <span v-if="pendingCount > 0" class="badge">{{ pendingCount }}</span>
        </button>
        <!-- 管理员和超级管理员都可以看到已公开对话 -->
        <button
          v-if="currentUser && (currentUser.role === 'admin' || currentUser.role === 'super_admin')"
          class="tab"
          :class="{ active: activeTab === 'public' }"
          @click="activeTab = 'public'"
        >
          已公开对话
        </button>
      </div>

      <!-- 用户管理 -->
      <div v-show="activeTab === 'users'" class="tab-content">
        <div class="actions">
          <input
            v-model="userSearch"
            class="search-input"
            placeholder="搜索用户..."
          />
          <button class="primary-btn" @click="showUserModal = true; editingUser = null">
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
              <tr v-for="user in filteredUsers" :key="user.id">
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
                    <button class="icon-btn" @click="editUser(user)" title="编辑">✏</button>
                    <button class="icon-btn danger" @click="confirmDeleteUser(user)" title="删除">🗑</button>
                  </div>
                </td>
              </tr>
              <tr v-if="filteredUsers.length === 0">
                <td colspan="7" class="empty-state">暂无用户数据</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 对话审核 -->
      <div v-show="activeTab === 'requests'" class="tab-content">
        <div class="filter-row">
          <select v-model="requestStatus" @change="filterRequests" class="status-select">
            <option value="pending">待审核</option>
            <option value="approved">已通过</option>
            <option value="rejected">已驳回</option>
            <option value="all">全部</option>
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
              <div class="request-title">{{ request.chat_title }}</div>
              <div class="request-meta">
                <span class="request-user">{{ request.username }}</span>
                <span class="request-time">{{ formatDate(request.created_at) }}</span>
              </div>
            </div>

            <div class="request-body">
              <div class="request-section">
                <div class="section-label">申请理由：</div>
                <div class="section-content">{{ request.reason || '无' }}</div>
              </div>

              <div class="request-section">
                <div class="section-label">对话内容预览：</div>
                <div class="chat-preview">
                  <div
                    v-for="(msg, idx) in request.messages_preview"
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

            <div v-if="request.status === 'pending'" class="request-actions">
              <button class="reject-btn" @click="openRejectModal(request)">
                驳回
              </button>
              <button class="approve-btn" @click="approveRequest(request)">
                通过
              </button>
            </div>
          </div>

          <div v-if="displayRequests.length === 0" class="empty-state">
            暂无数据
          </div>
        </div>
      </div>

      <!-- 已公开对话 -->
      <div v-show="activeTab === 'public'" class="tab-content">
        <div class="actions">
          <button class="refresh-btn" @click="loadPublicChats">刷新</button>
        </div>

        <div class="public-chats-list">
          <div
            v-for="chat in publicChats"
            :key="chat.id"
            class="public-chat-card"
          >
            <div class="chat-header">
              <div class="chat-title">{{ chat.title }}</div>
              <div class="chat-meta">
                <span>{{ chat.username }}</span>
                <span>·</span>
                <span>{{ formatDate(chat.published_at) }}</span>
              </div>
            </div>
            <div class="chat-stats">
              <span>{{ chat.message_count }} 条消息</span>
              <span>·</span>
              <span>{{ chat.view_count || 0 }} 次浏览</span>
            </div>
          </div>

          <div v-if="publicChats.length === 0" class="empty-state">
            暂无已公开对话
          </div>
        </div>
      </div>
    </main>

    <!-- 用户编辑/新增弹窗 -->
    <div v-if="showUserModal" class="modal-overlay" @click.self="showUserModal = false">
      <div class="modal">
        <div class="modal-header">
          <h3>{{ editingUser ? '编辑用户' : '新增用户' }}</h3>
          <button class="close-btn" @click="showUserModal = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label>用户名</label>
            <input v-model="userForm.username" class="form-input" placeholder="请输入用户名" />
          </div>
          <div class="form-group">
            <label>邮箱</label>
            <input v-model="userForm.email" type="email" class="form-input" placeholder="请输入邮箱" />
          </div>
          <div class="form-group">
            <label>密码</label>
            <input v-model="userForm.password" type="password" class="form-input" :placeholder="editingUser ? '留空则不修改' : '请输入密码'" />
          </div>
          <div class="form-group">
            <label>角色</label>
            <select v-model="userForm.role" class="form-input">
              <option value="user">普通用户</option>
              <option value="admin">管理员</option>
              <option value="super_admin">超级管理员</option>
            </select>
          </div>
          <div class="form-group checkbox">
            <label>
              <input v-model="userForm.is_active" type="checkbox" />
              <span>启用状态</span>
            </label>
          </div>
        </div>
        <div class="modal-footer">
          <button class="secondary-btn" @click="showUserModal = false">取消</button>
          <button class="primary-btn" @click="saveUser">保存</button>
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';

const props = defineProps({
  currentUser: {
    type: Object,
    default: null,
  }
});

defineEmits(['back']);

// 根据用户角色设置默认标签页
const getDefaultTab = () => {
  if (!props.currentUser) return 'requests';

  const role = props.currentUser.role || 'user';
  if (role === 'super_admin') {
    return 'users'; // 超级管理员默认显示用户管理
  } else if (role === 'admin') {
    return 'requests'; // 管理员默认显示对话审核
  }
  return 'requests';
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

// 对话审核相关
const allRequests = ref([]);
const displayRequests = ref([]);
const requestStatus = ref('pending');
const showRejectModal = ref(false);
const rejectReason = ref('');
const reviewingRequest = ref(null);
const pendingCount = ref(0);

// 已公开对话
const publicChats = ref([]);

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
  if (!userSearch.value) return users.value;
  const kw = userSearch.value.toLowerCase();
  return users.value.filter(u =>
    u.username?.toLowerCase().includes(kw) ||
    u.email?.toLowerCase().includes(kw)
  );
});

// 加载用户列表
function loadUsers() {
  users.value = getMockUsers();
}

// 编辑用户
function editUser(user) {
  editingUser.value = user;
  userForm.value = {
    username: user.username,
    email: user.email,
    password: '',
    role: user.role,
    is_active: user.is_active,
  };
  showUserModal.value = true;
}

// 保存用户
function saveUser() {
  if (!userForm.value.username || !userForm.value.email) {
    alert('请填写用户名和邮箱');
    return;
  }

  if (editingUser.value) {
    // 更新用户
    const idx = users.value.findIndex(u => u.id === editingUser.value.id);
    if (idx !== -1) {
      users.value[idx] = { ...users.value[idx], ...userForm.value };
    }
  } else {
    // 新增用户
    if (!userForm.value.password) {
      alert('新用户必须设置密码');
      return;
    }
    users.value.push({
      id: crypto.randomUUID(),
      ...userForm.value,
      created_at: new Date().toISOString(),
    });
  }
  showUserModal.value = false;
}

// 确认删除用户
function confirmDeleteUser(user) {
  userToDelete.value = user;
  showDeleteConfirm.value = true;
}

// 删除用户
function deleteUser() {
  if (!userToDelete.value) return;
  users.value = users.value.filter(u => u.id !== userToDelete.value.id);
  showDeleteConfirm.value = false;
  userToDelete.value = null;
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
function loadRequests() {
  allRequests.value = getMockRequests();
  filterRequests();
  updatePendingCount();
}

// 过滤请求
function filterRequests() {
  if (requestStatus.value === 'all') {
    displayRequests.value = allRequests.value;
  } else {
    displayRequests.value = allRequests.value.filter(r => r.status === requestStatus.value);
  }
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

// 通过请求
function approveRequest(request) {
  if (!confirm(`确定通过对话"${request.chat_title}"的公开请求吗？`)) return;
  request.status = 'approved';
  request.reject_reason = '';
  filterRequests();
  updatePendingCount();
}

// 确认驳回
function confirmReject() {
  if (reviewingRequest.value) {
    reviewingRequest.value.status = 'rejected';
    reviewingRequest.value.reject_reason = rejectReason.value;
    showRejectModal.value = false;
    filterRequests();
    updatePendingCount();
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

// 初始化加载
onMounted(() => {
  loadUsers();
  loadRequests();
  loadPublicChats();
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
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  outline: none;
  cursor: pointer;
}

.requests-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
</style>
