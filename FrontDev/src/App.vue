<template>
  <div class="app">
    <!-- 左侧：历史对话 + 成员 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="logo">智炬</div>
        <div class="title">
          <div class="name">智炬五维</div>
          <div class="sub">多智能体协同学习 · 前端 Demo</div>
        </div>
      </div>

      <!-- 已公开历史对话轮播图 -->
      <div class="section carouselSection">
        <div class="sectionTitle rowBetween">
          <span>已公开对话</span>
          <button class="ghost" @click="refreshPublicChats">刷新</button>
        </div>

        <div class="publicChatCarousel">
          <div
            v-if="publicChats.length > 0"
            class="publicChatItem"
            @click="viewPublicChat(publicChats[currentPublicChatIndex].id)"
          >
            <div class="publicChatTitle">{{ publicChats[currentPublicChatIndex].title }}</div>
            <div class="publicChatMeta">
              <span class="like-count">❤️ {{ publicChats[currentPublicChatIndex].like_count || 0 }}</span>
              <span>·</span>
              <span>{{ publicChats[currentPublicChatIndex].updatedAt }}</span>
            </div>
          </div>
          <div v-else class="hint">暂无公开对话</div>

          <!-- 轮播指示器 -->
          <div v-if="publicChats.length > 1" class="carouselDots">
            <span
              v-for="(chat, index) in publicChats"
              :key="chat.id"
              class="dot"
              :class="{ active: index === currentPublicChatIndex }"
            ></span>
          </div>
        </div>
      </div>

      <!-- 历史对话 -->
      <div class="section">
        <div class="sectionTitle rowBetween">
  <span>历史对话</span>
  <button class="ghost" @click="newChat">+ 新建</button>
</div>

<input
  class="search"
  v-model="keyword"
  placeholder="搜索会话…"
/>

        <div class="exportRow">
          <button class="topic" @click="exportCurrentWithAuth('json')">导出 JSON</button>
          <button class="topic topic2" @click="exportCurrentWithAuth('txt')">导出 TXT</button>
        </div>

        <div class="chatList">
  <div
    v-for="c in visibleChats"
    :key="c.id"
    class="chatItem"
    :class="{ active: c.id === activeChatId }"
  >
    <div class="chatMain" @click="switchChat(c.id)">
      <div class="chatTitle">{{ c.title }}</div>
      <div class="chatMeta">
        <span>{{ c.updatedAt }}</span>
        <span>·</span>
        <span>{{ c.messages.length }} 条</span>
      </div>
    </div>

 <button
  class="pinText"
  :class="{ on: c.pinned }"
  @click.stop="c.pinned = !c.pinned"
>
  {{ c.pinned ? '取消置顶' : '置顶' }}
</button>

  </div>
</div>

        <div class="hint" v-if="error">
          {{ error }}
        </div>
      </div>
      <!-- 左下角：用户信息 -->
      <div class="userBar">
        <div class="uAvatar" :class="currentUser?.role">{{ user.short }}</div>
        <div class="uMeta">
          <div class="uName" :class="currentUser?.role">{{ user.name }}</div>
          <div class="uSub">在线</div>
        </div>
        <button class="gear" @click="showSettingsModal = true" title="设置">⚙</button>
      </div>
    </aside>

    <!-- 右侧：聊天区 -->
    <main class="main">
      <header class="topbar">
        <div class="topicTitle">
          <div class="big">{{ activeChat.title }}</div>
          <div class="small">可切换历史对话 · 可导出当前会话</div>
        </div>

        <div class="topbarRight">
          <!-- 未登录用户显示登录注册按钮 -->
          <template v-if="!currentUser">
            <button class="authBtn ghostBtn" @click="showRegisterModal = true">注册</button>
            <button class="authBtn primaryBtn" @click="showLoginModal = true">登录</button>
          </template>
          <!-- 已登录用户显示用户名和登出按钮 -->
          <template v-else>
            <span class="welcomeText" :class="currentUser.role">{{ currentUser.username }}</span>
            <button class="authBtn ghostBtn" @click="handleLogout">登出</button>
          </template>
          <div class="status">
            <span class="dot"></span>
            <span>已连接</span>
          </div>
        </div>
      </header>

      <section class="chat" ref="chatContainer">
        <div class="timeline" ref="timelineRef">
          <div class="msg" v-for="msg in activeChat.messages" :key="msg.id" :class="{me: msg.authorId==='user'}">
            <div class="bubble" :style="bubbleStyle(msg.authorId)" :class="{loading: msg.isLoading}">
              <template v-if="msg.authorId !== 'user'">
                <div class="head">
                  <span class="who">{{ msg.author_name || nameOf(msg.authorId) }}</span>
                  <span class="badge" v-if="roleOf(msg.authorId)">{{ roleOf(msg.authorId) }}</span>
                  <span class="time">{{ msg.time }}</span>
                </div>
              </template>
              <div class="content">
                <!-- Loading状态显示 -->
                <div v-if="msg.isLoading" class="loading-indicator">
                  <span class="dot-bounce"></span>
                  <span class="dot-bounce"></span>
                  <span class="dot-bounce"></span>
                </div>
                <p v-else v-for="(p, i) in (msg.text || msg.content || '').split('\n')" :key="i">{{ p }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <footer class="composer">
        <div class="quote" v-if="quoted">
          <span class="qtag">引用</span>
          <span class="qtext">{{ quoted }}</span>
          <button class="qclose" @click="quoted=null">×</button>
        </div>

        <div class="inputRow">
          <div class="inputWrapper">
            <textarea
              ref="inputRef"
              v-model="draft"
              class="input"
              rows="2"
              :placeholder="inputPlaceholder"
              @keydown.enter.exact.prevent="handleSendOrContinue()"
              :disabled="isSending || isCreating"
            />
            <button
              class="sendArrowBtn"
              :disabled="isSending || isCreating"
              @click="handleSendOrContinue()"
              :title="draft.trim() ? '发送消息' : '继续讨论'"
            >
              ↑
            </button>
          </div>
          <button class="summary-btn" :disabled="isSending || isCreating" @click="summarize" title="生成当前对话总结">
            总结
          </button>
        </div>

        <div class="tips">
          <span>Enter 发送</span><span>·</span>
          <span>左侧切换历史会话；可导出 JSON/TXT</span>
        </div>
      </footer>
    </main>

    <!-- 登录弹窗 -->
    <div v-if="showLoginModal" class="modalOverlay" @click.self="showLoginModal = false">
      <div class="modal">
        <div class="modalHeader">
          <h2>登录</h2>
          <button class="closeBtn" @click="showLoginModal = false">×</button>
        </div>
        <div class="modalBody">
          <div v-if="formError" class="formError">{{ formError }}</div>
          <div class="formGroup">
            <label>用户名</label>
            <input
              v-model="loginForm.username"
              type="text"
              placeholder="请输入用户名"
              @keyup.enter="handleLogin"
            />
          </div>
          <div class="formGroup">
            <label>密码</label>
            <input
              v-model="loginForm.password"
              type="password"
              placeholder="请输入密码"
              @keyup.enter="handleLogin"
            />
          </div>
          <button class="submitBtn" @click="handleLogin">登录</button>
          <div class="formFooter">
            还没有账号？
            <a @click="showLoginModal = false; showRegisterModal = true">立即注册</a>
          </div>
        </div>
      </div>
    </div>

    <!-- 注册弹窗 -->
    <div v-if="showRegisterModal" class="modalOverlay" @click.self="showRegisterModal = false">
      <div class="modal modalLarge">
        <div class="modalHeader">
          <h2>注册</h2>
          <button class="closeBtn" @click="showRegisterModal = false">×</button>
        </div>
        <div class="modalBody">
          <div v-if="formError" class="formError">{{ formError }}</div>
          <div class="formGroup">
            <label>头像URL（可选）</label>
            <input
              v-model="registerForm.avatarUrl"
              type="text"
              placeholder="https://example.com/avatar.png"
            />
          </div>
          <div class="formGroup">
            <label>用户名 <span class="required">*</span></label>
            <input
              v-model="registerForm.username"
              type="text"
              placeholder="至少3个字符"
              @keyup.enter="handleRegister"
            />
            <span v-if="registerErrors.username" class="fieldError">{{ registerErrors.username }}</span>
          </div>
          <div class="formGroup">
            <label>密码 <span class="required">*</span></label>
            <input
              v-model="registerForm.password"
              type="password"
              placeholder="至少6个字符"
            />
            <span v-if="registerErrors.password" class="fieldError">{{ registerErrors.password }}</span>
          </div>
          <div class="formGroup">
            <label>确认密码 <span class="required">*</span></label>
            <input
              v-model="registerForm.confirmPassword"
              type="password"
              placeholder="再次输入密码"
              @keyup.enter="handleRegister"
            />
            <span v-if="registerErrors.confirmPassword" class="fieldError">{{ registerErrors.confirmPassword }}</span>
          </div>
          <div class="formGroup">
            <label>邮箱（可选）</label>
            <input
              v-model="registerForm.email"
              type="email"
              placeholder="your@email.com"
            />
            <span v-if="registerErrors.email" class="fieldError">{{ registerErrors.email }}</span>
          </div>
          <button class="submitBtn" @click="handleRegister">注册</button>
          <div class="formFooter">
            已有账号？
            <a @click="showRegisterModal = false; showLoginModal = true">立即登录</a>
          </div>
        </div>
      </div>
    </div>

    <!-- 设置弹窗 -->
    <div v-if="showSettingsModal" class="modalOverlay" @click.self="showSettingsModal = false">
      <div class="modal settingsModal">
        <div class="modalHeader">
          <h2>设置</h2>
          <button class="closeBtn" @click="showSettingsModal = false">×</button>
        </div>
        <div class="modalBody settingsBody">
          <div class="settingsTabs">
            <button
              class="tabBtn"
              :class="{ active: activeSettingsTab === 'general' }"
              @click="activeSettingsTab = 'general'"
            >
              通用设置
            </button>
            <button
              class="tabBtn"
              :class="{ active: activeSettingsTab === 'account' }"
              @click="activeSettingsTab = 'account'"
            >
              账号管理
            </button>
            <button
              class="tabBtn"
              :class="{ active: activeSettingsTab === 'data' }"
              @click="activeSettingsTab = 'data'"
            >
              数据管理
            </button>
          </div>

          <!-- 通用设置 -->
          <div v-if="activeSettingsTab === 'general'" class="settingsContent">
            <h3>主题设置</h3>
            <div class="themeOptions">
              <button
                class="themeOption"
                :class="{ active: theme === 'dark' }"
                @click="setTheme('dark')"
              >
                <span class="themeIcon">🌙</span>
                <span>深色模式</span>
              </button>
              <button
                class="themeOption"
                :class="{ active: theme === 'light' }"
                @click="setTheme('light')"
              >
                <span class="themeIcon">☀️</span>
                <span>浅色模式</span>
              </button>
              <button
                class="themeOption"
                :class="{ active: theme === 'system' }"
                @click="setTheme('system')"
              >
                <span class="themeIcon">💻</span>
                <span>跟随系统</span>
              </button>
            </div>

            <div class="settingsSection" v-if="currentUser">
              <h4>管理员</h4>
              <button class="adminEntryBtn" @click="goToAdmin">
                进入管理后台
              </button>
            </div>
          </div>

          <!-- 账号管理 -->
          <div v-if="activeSettingsTab === 'account'" class="settingsContent">
            <div v-if="!currentUser" class="notLoggedIn">
              <p>请先登录以管理账号信息</p>
              <button class="submitBtn" @click="showSettingsModal = false; showLoginModal = true">立即登录</button>
            </div>
            <div v-else>
              <h3>个人信息</h3>
              <div class="formGroup">
                <label>头像URL</label>
                <input
                  v-model="profileForm.avatarUrl"
                  type="text"
                  placeholder="https://example.com/avatar.png"
                />
              </div>
              <div class="formGroup">
                <label>用户名</label>
                <input
                  v-model="profileForm.username"
                  type="text"
                  placeholder="用户名"
                />
              </div>
              <div class="formGroup">
                <label>邮箱</label>
                <input
                  v-model="profileForm.email"
                  type="email"
                  placeholder="your@email.com"
                />
              </div>
              <button class="submitBtn" @click="updateProfile">保存个人信息</button>

              <h3 style="margin-top: 24px;">修改密码</h3>
              <div v-if="profileError" class="formError">{{ profileError }}</div>
              <div v-if="profileSuccess" class="formSuccess">{{ profileSuccess }}</div>
              <div class="formGroup">
                <label>当前密码</label>
                <input
                  v-model="passwordForm.oldPassword"
                  type="password"
                  placeholder="请输入当前密码"
                />
              </div>
              <div class="formGroup">
                <label>新密码</label>
                <input
                  v-model="passwordForm.newPassword"
                  type="password"
                  placeholder="至少6个字符"
                />
              </div>
              <div class="formGroup">
                <label>确认新密码</label>
                <input
                  v-model="passwordForm.confirmPassword"
                  type="password"
                  placeholder="再次输入新密码"
                />
              </div>
              <button class="submitBtn" @click="changePassword">修改密码</button>
            </div>
          </div>

          <!-- 数据管理 -->
          <div v-if="activeSettingsTab === 'data'" class="settingsContent">
            <div v-if="!currentUser" class="notLoggedIn">
              <p>请先登录以管理数据</p>
              <button class="submitBtn" @click="showSettingsModal = false; showLoginModal = true">立即登录</button>
            </div>
            <div v-else>
              <h3>导出数据</h3>
              <p class="settingsHint">导出您的所有对话历史记录为JSON格式</p>
              <button class="actionBtn exportBtn" @click="exportAllData">
                <span>📥</span> 导出所有对话
              </button>

              <h3 style="margin-top: 24px;">删除数据</h3>
              <p class="settingsHint warning">危险操作：删除后将无法恢复</p>
              <button class="actionBtn deleteBtn" @click="confirmDeleteAll">
                <span>🗑️</span> 删除所有对话
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch, nextTick } from "vue";
import { apiClient, now, stamp, uid, mapSpeakerToMemberId, mapMemberIdToName, getUser } from "./api.js";

// 定义 emits
const emit = defineEmits(['switch-to-admin']);

// ========== 用户认证状态 ==========
const currentUser = ref(null);
const showLoginModal = ref(false);
const showRegisterModal = ref(false);

// ========== 设置相关状态 ==========
const showSettingsModal = ref(false);
const activeSettingsTab = ref('general'); // general | account | data
const theme = ref(localStorage.getItem('theme') || 'dark');

// ========== 公开对话大厅 ==========
const publicChats = ref([]);
const currentPublicChatIndex = ref(0);
let carouselTimer = null;

// ========== 个人信息表单 ==========
const profileForm = ref({
  avatarUrl: '',
  username: '',
  email: '',
});

// ========== 修改密码表单 ==========
const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
});

// ========== 个人信息错误/成功消息 ==========
const profileError = ref('');
const profileSuccess = ref('');

// 登录表单
const loginForm = ref({
  username: '',
  password: '',
});

// 注册表单
const registerForm = ref({
  username: '',
  password: '',
  confirmPassword: '',
  email: '',
  avatarUrl: '', // 可选，使用默认头像
});

// 表单错误
const formError = ref('');
const registerErrors = ref({});

// 用户信息（兼容原有逻辑）
const user = computed(() => {
  if (currentUser.value) {
    return {
      id: currentUser.value.user_id || "user",
      name: currentUser.value.username || "用户",
      short: currentUser.value.username?.substring(0, 1) || "你"
    };
  }
  return { id: "user", name: "游客", short: "游" };
});

const keyword = ref("");
const members = [
  { id: "theorist", name: "理论家", short: "理", role: "体系化", color: "#6aa7ff", desc: "梳理知识框架，把概念讲清楚、讲完整。" },
  { id: "practitioner", name: "实践者", short: "实", role: "应用派", color: "#51d18a", desc: "用例子/代码/练习把知识落地。" },
  { id: "skeptic", name: "质疑者", short: "疑", role: "挑错", color: "#ffcc66", desc: "挑战逻辑漏洞，逼你把问题说清楚。" },
  { id: "facilitator", name: "组织者", short: "组", role: "主持", color: "#c77dff", desc: "控节奏、提炼结论、分配任务。" },
];

// ========== 对话数据 ==========
const chats = ref([]);
const loading = ref(false);
const error = ref(null);

// ========== Loading状态 ==========
const isSending = ref(false);  // 正在发送消息/AI正在思考
const isCreating = ref(false);  // 正在创建对话

// ========== WebSocket 管理 ==========
let currentWsHandler = null;

// ========== DOM 引用 ==========
const chatContainer = ref(null);
const timelineRef = ref(null);
const inputRef = ref(null);

/**
 * 滚动聊天区域到底部
 */
function scrollToBottom(smooth = true) {
  nextTick(() => {
    if (chatContainer.value) {
      chatContainer.value.scrollTo({
        top: chatContainer.value.scrollHeight,
        behavior: smooth ? 'smooth' : 'auto'
      });
    }
  });
}

/**
 * 聚焦输入框
 */
function focusInput() {
  if (inputRef.value) {
    inputRef.value.focus();
  }
}

// ========== 初始化加载 ==========
onMounted(async () => {
  // 初始化用户状态
  const localUser = getUser();
  if (localUser) {
    currentUser.value = localUser;
    // 初始化个人信息表单
    profileForm.value = {
      avatarUrl: localUser.avatar_url || '',
      username: localUser.username || '',
      email: localUser.email || '',
    };
  }

  // 初始化主题
  initTheme();

  // 加载公开对话大厅（添加示例数据）
  await loadPublicChats();
  // 添加示例公开对话（用于展示效果）
  if (publicChats.value.length === 0) {
    publicChats.value = [
      {
        id: 'example-1',
        title: '示例：如何高效学习人工智能？',
        like_count: 128,
        updatedAt: '12/20 10:30'
      },
      {
        id: 'example-2',
        title: '示例：多智能体协同的优势与挑战',
        like_count: 96,
        updatedAt: '12/21 14:22'
      }
    ];
  }
  // 启动轮播
  startCarousel();

  await loadChats();
  // 加载对话列表后，自动加载第一条对话的消息
  if (chats.value.length > 0) {
    activeChatId.value = chats.value[0].id;
    await loadChatMessages(activeChatId.value);
    scrollToBottom(false);
  }
});

onUnmounted(() => {
  // 清除轮播定时器
  if (carouselTimer) {
    clearInterval(carouselTimer);
    carouselTimer = null;
  }
  // 断开所有WebSocket连接
  apiClient.disconnectAll();
  // 清理WebSocket连接跟踪
  wsConnectedChats.clear();
});

// ========== 监听用户登录状态变化 ==========
watch(currentUser, async (newUser, oldUser) => {
  // 当用户登录状态发生变化时（登录或登出），重新加载对话列表
  // 如果是从游客变为登录用户，或从登录用户变为游客
  if ((newUser === null && oldUser !== null) || (newUser !== null && oldUser === null) ||
      (newUser && oldUser && newUser.user_id !== oldUser.user_id)) {
    await loadChats();
    // 如果有对话，选中第一个
    if (chats.value.length > 0) {
      activeChatId.value = chats.value[0].id;
      await loadChatMessages(activeChatId.value);
      scrollToBottom(false);
    }
  }
});

// ========== API 调用函数 ==========
async function loadChats() {
  loading.value = true;
  error.value = null;
  try {
    const result = await apiClient.getChats(keyword.value);
    // 转换后端数据格式为前端格式
    chats.value = result.chats.map(chat => ({
      id: chat.id,
      title: chat.title,
      pinned: chat.pinned || false,
      updatedAt: chat.updatedAt,
      messages: chat.messages || [],
    }));
  } catch (err) {
    console.error('加载对话列表失败:', err);
    error.value = err.message;
    alert('无法连接到服务器，请确保后端服务已启动');
  } finally {
    loading.value = false;
  }
}

async function createChat(topic) {
  try {
    const result = await apiClient.createChat(topic);
    // 后端现在返回完整的对话信息，包括消息
    const newChat = {
      id: result.chat_id,
      title: result.title,
      pinned: false,
      updatedAt: result.updated_at,
      messages: result.messages.map(msg => ({
        id: msg.message_id || msg.id,
        authorId: msg.author_id,
        author_name: msg.author_name,
        text: msg.content,
        content: msg.content,
        time: msg.timestamp,
        role: msg.role
      })),
    };
    // 添加到聊天列表
    chats.value = [newChat, ...chats.value];
    return result.chat_id;
  } catch (err) {
    console.error('创建对话失败:', err);
    throw err;
  }
}

async function sendMessage(chatId, content, action = 'send') {
  try {
    const result = await apiClient.sendMessage(chatId, content, action);
    // 后端返回完整的消息列表，更新本地chat
    const chat = chats.value.find(c => c.id === chatId);
    if (chat && result.messages) {
      // 将后端消息格式转换为前端格式
      chat.messages = result.messages.map(msg => ({
        id: msg.message_id || msg.id,
        authorId: msg.author_id,
        author_name: msg.author_name,
        text: msg.content,
        content: msg.content,
        time: msg.timestamp,
        role: msg.role
      }));
      chat.updatedAt = result.updated_at || stamp();
    }
    return result;
  } catch (err) {
    console.error('发送消息失败:', err);
    throw err;
  }
}

async function continueChat(chatId) {
  try {
    const result = await apiClient.continueChat(chatId);
    // 后端返回完整的消息列表，更新本地chat
    const chat = chats.value.find(c => c.id === chatId);
    if (chat && result.messages) {
      // 将后端消息格式转换为前端格式
      chat.messages = result.messages.map(msg => ({
        id: msg.message_id || msg.id,
        authorId: msg.author_id,
        author_name: msg.author_name,
        text: msg.content,
        content: msg.content,
        time: msg.timestamp,
        role: msg.role
      }));
      chat.updatedAt = result.updated_at || stamp();
    }
    return result;
  } catch (err) {
    console.error('继续对话失败:', err);
    throw err;
  }
}

/**
 * 加载指定对话的完整消息历史
 */
async function loadChatMessages(chatId) {
  if (!chatId || chatId === 'empty') return;

  try {
    const result = await apiClient.getMessages(chatId, 100);
    const chat = chats.value.find(c => c.id === chatId);
    if (chat) {
      // 转换后端消息格式为前端格式
      chat.messages = result.messages.map(msg => ({
        id: msg.message_id || msg.id,
        authorId: msg.author_id,
        author_name: msg.author_name,
        text: msg.content,
        content: msg.content,
        time: msg.timestamp,
        role: msg.role
      }));
      chat.updatedAt = result.updated_at || stamp();
    }
  } catch (err) {
    console.error('加载对话消息失败:', err);
  }
}

// ========== WebSocket 消息处理 ==========
// 防止重复建立连接的标记
const wsConnectedChats = new Set();

function setupWebSocket(chatId) {
  // 防止重复建立连接
  if (wsConnectedChats.has(chatId)) {
    console.log(`WebSocket already connected for chat: ${chatId}, skipping...`);
    return;
  }

  wsConnectedChats.add(chatId);
  apiClient.connectWebSocket(
    chatId,
    (data) => {
      // 处理收到的消息
      if (data.type === 'message') {
        const chat = chats.value.find(c => c.id === chatId);
        if (chat && !chat.messages.find(m => m.message_id === data.data.message_id)) {
          chat.messages.push({
            id: data.data.message_id,
            authorId: data.data.author_id,
            author_name: data.data.author_name,
            text: data.data.content,
            time: data.data.timestamp,
          });
          chat.updatedAt = stamp();
        }
      }
    },
    (err) => {
      console.error('WebSocket错误:', err);
    },
    () => {
      // 连接关闭时清除标记
      wsConnectedChats.delete(chatId);
    }
  );
}

const visibleChats = computed(() => {
  const kw = keyword.value.trim().toLowerCase();

  let list = chats.value.filter((c) => {
    if (!kw) return true;
    if (c.title.toLowerCase().includes(kw)) return true;
    const last = c.messages[c.messages.length - 1];
    const lastText = last?.text || last?.content || '';
    return lastText.toLowerCase().includes(kw);
  });

  // 置顶的在前，其余按更新时间
  list.sort((a, b) => {
    if (a.pinned !== b.pinned) return a.pinned ? -1 : 1;
    return b.updatedAt.localeCompare(a.updatedAt);
  });

  return list;
});


// ========== 当前对话相关 ==========
const activeChatId = ref(null);
const draft = ref("");
const quoted = ref(null);
const waitingForUser = ref(false); // 标记是否等待用户操作

const activeChat = computed(() => {
  if (chats.value.length === 0) {
    // 返回一个空的默认对话对象
    return {
      id: 'empty',
      title: '暂无对话',
      pinned: false,
      updatedAt: stamp(),
      messages: []
    };
  }
  if (!activeChatId.value && chats.value.length > 0) {
    activeChatId.value = chats.value[0].id;
  }
  return chats.value.find((c) => c.id === activeChatId.value) || chats.value[0];
});

// 输入框占位符
const inputPlaceholder = computed(() => {
  if (waitingForUser.value) {
    return "按 Enter 继续（空输入）或输入你的观点…";
  }
  return "作为第五位成员插话：提问 / 反驳 / 补充 / 总结…";
});

// ========== 监听当前对话变化，建立WebSocket连接 ==========
watch(activeChatId, (newId, oldId) => {
  if (newId) {
    setupWebSocket(newId);
  }
});

function nameOf(id) {
  if (id === "user") return user.name;
  if (id === "ai-loading") return "";
  return members.find((m) => m.id === id)?.name || id;
}
function roleOf(id) {
  if (id === "user") return "用户";
  return members.find((m) => m.id === id)?.role || "";
}
function bubbleStyle(authorId) {
  if (authorId === "user") return { borderColor: "#ffffff55", background: "rgba(255,255,255,.08)" };
  const m = members.find((x) => x.id === authorId);
  return { borderColor: (m?.color || "#6aa7ff") + "66" };
}

async function switchChat(id) {
  activeChatId.value = id;
  quoted.value = null;
  draft.value = "";

  // 加载该对话的完整消息历史
  if (id && id !== 'empty') {
    await loadChatMessages(id);
    scrollToBottom(false);
  }
}

function newChat() {
  // 提示用户输入话题
  const topic = prompt("请输入讨论话题：");
  if (topic) {
    createChat(topic).then(chatId => {
      activeChatId.value = chatId;
    }).catch(err => {
      alert('创建对话失败: ' + err.message);
    });
  }
}

async function send() {
  const text = draft.value.trim();
  if (!text || isSending.value || isCreating.value) return;

  // 如果没有活跃对话或对话为空，创建新对话
  if (!activeChat.value || activeChat.value.id === 'empty') {
    draft.value = "";
    quoted.value = null;

    isCreating.value = true;
    try {
      // 先在前端显示用户消息（乐观更新）
      const tempId = uid();
      const newChat = {
        id: tempId,
        title: `主题：${text}`,
        pinned: false,
        updatedAt: stamp(),
        messages: [
          { id: uid(), authorId: "user", author_name: user.name, text, content: text, time: now(), role: "用户" },
          { id: uid(), authorId: "facilitator", author_name: "组织者", text: "正在组织讨论...", content: "正在组织讨论...", time: now(), role: "组织者", isLoading: true }
        ],
      };
      chats.value = [newChat, ...chats.value];
      activeChatId.value = tempId;

      // 异步创建对话并获取真实响应
      const result = await apiClient.createChat(text);
      const realChat = {
        id: result.chat_id,
        title: result.title,
        pinned: false,
        updatedAt: result.updated_at,
        messages: result.messages.map(msg => ({
          id: msg.message_id || msg.id,
          authorId: msg.author_id,
          author_name: msg.author_name,
          text: msg.content,
          content: msg.content,
          time: msg.timestamp,
          role: msg.role
        })),
      };

      // 替换临时对话为真实对话
      const idx = chats.value.findIndex(c => c.id === tempId);
      if (idx !== -1) {
        chats.value[idx] = realChat;
        activeChatId.value = realChat.id;

        // 检查最后一个发言者，如果是组织者，自动触发下一个智能体发言
        const lastMsg = realChat.messages[realChat.messages.length - 1];
        console.log('[创建对话] 最后一条消息:', lastMsg);
        console.log('[创建对话] 作者ID:', lastMsg?.authorId, '作者名称:', lastMsg?.author_name);

        // 同时检查 authorId 和 author_name，兼容不同的后端返回格式
        const isFacilitator = lastMsg && (
          lastMsg.authorId === 'facilitator' ||
          lastMsg.author_name === '组织者' ||
          lastMsg.role === '主持'
        );

        if (isFacilitator) {
          console.log('[创建对话] 检测到组织者发言，1秒后自动触发下一个智能体');
          setTimeout(() => {
            askAI(true);
          }, 1000);
        } else {
          console.log('[创建对话] 最后一条消息不是组织者，等待用户操作');
          waitingForUser.value = true;
        }
      }
    } catch (err) {
      console.error('创建对话失败:', err);
      // 创建失败时移除临时对话
      chats.value = chats.value.filter(c => c.id !== activeChatId.value);
      alert('创建对话失败: ' + err.message);
    } finally {
      isCreating.value = false;
    }
    return;
  }

  // 正常发送消息 - 乐观更新：立即显示用户消息
  const chat = activeChat.value;
  draft.value = "";
  quoted.value = null;

  isSending.value = true;
  try {
    // 1. 立即在前端添加用户消息
    const userMsg = {
      id: uid(),
      authorId: "user",
      author_name: user.name,
      text: text,
      content: text,
      time: now(),
      role: "用户"
    };
    chat.messages.push(userMsg);
    chat.updatedAt = stamp();
    scrollToBottom();

    // 2. 添加"正在思考"的占位消息
    const loadingMsg = {
      id: uid(),
      authorId: "ai-loading",
      author_name: "",
      text: "正在思考...",
      content: "正在思考...",
      time: now(),
      role: "",
      isLoading: true
    };
    chat.messages.push(loadingMsg);

    // 3. 异步调用后端获取AI响应
    const result = await apiClient.sendMessage(chat.id, text, 'send');

    // 4. 移除loading消息，替换为真实AI响应
    chat.messages = chat.messages.filter(m => !m.isLoading);

    // 5. 添加AI响应（只添加新消息）
    // 获取当前聊天中已存在的消息ID集合
    const existingIds = new Set(chat.messages.map(m => m.id));

    if (result.messages && result.messages.length > 0) {
      for (const msg of result.messages) {
        const msgId = msg.message_id || msg.id;
        // 只添加不存在的消息，跳过用户消息和loading消息
        if (msg.author_id === 'user' || msg.isLoading || existingIds.has(msgId)) {
          continue;
        }
        chat.messages.push({
          id: msgId,
          authorId: msg.author_id,
          author_name: msg.author_name,
          text: msg.content,
          content: msg.content,
          time: msg.timestamp,
          role: msg.role
        });
        existingIds.add(msgId);
      }
    }

    chat.updatedAt = result.updated_at || stamp();
    scrollToBottom();

    // 用户发送消息后，直接等待用户操作，不再自动触发
    waitingForUser.value = true;

    // 聚焦回输入框
    nextTick(() => {
      focusInput();
    });
  } catch (err) {
    console.error('发送消息失败:', err);
    // 失败时移除loading消息
    chat.messages = chat.messages.filter(m => !m.isLoading);
    // 恢复输入内容
    draft.value = text;
    waitingForUser.value = true;
    alert('发送失败: ' + err.message);
  } finally {
    isSending.value = false;
  }
}

function quote(msg) {
  quoted.value = `${nameOf(msg.authorId)}：${msg.text?.split("\n")[0] || ''}`;
}

async function askAI(isAutoTriggered = false) {
  if (!activeChat.value || isSending.value) return;
  if (activeChat.value.id === 'empty') {
    alert('请先选择或创建一个对话');
    return;
  }

  // 清空输入框（如果用户输入了内容）
  if (!isAutoTriggered) {
    const text = draft.value.trim();
    if (text) {
      // 用户输入了内容，作为用户消息发送
      send();
      return;
    }
  }

  isSending.value = true;
  waitingForUser.value = false;
  draft.value = "";
  quoted.value = null;
  const chat = activeChat.value;

  try {
    // 添加"正在思考"的占位消息
    const loadingMsg = {
      id: uid(),
      authorId: "ai-loading",
      author_name: "",
      text: "正在思考...",
      content: "正在思考...",
      time: now(),
      role: "",
      isLoading: true
    };
    chat.messages.push(loadingMsg);
    chat.updatedAt = stamp();

    // 调用继续API
    const result = await apiClient.continueChat(chat.id);

    // 移除loading消息
    chat.messages = chat.messages.filter(m => !m.isLoading);

    // 添加AI响应（只添加新消息）
    const existingIds = new Set(chat.messages.map(m => m.id));

    if (result.messages && result.messages.length > 0) {
      for (const msg of result.messages) {
        const msgId = msg.message_id || msg.id;
        // 只添加不存在的消息，跳过用户消息和loading消息
        if (msg.author_id === 'user' || msg.isLoading || existingIds.has(msgId)) {
          continue;
        }
        chat.messages.push({
          id: msgId,
          authorId: msg.author_id,
          author_name: msg.author_name,
          text: msg.content,
          content: msg.content,
          time: msg.timestamp,
          role: msg.role
        });
        existingIds.add(msgId);
      }
    }

    chat.updatedAt = result.updated_at || stamp();
    scrollToBottom();

    // 智能体发言完毕，等待用户决定
    waitingForUser.value = true;

    // 聚焦回输入框
    nextTick(() => {
      focusInput();
    });
  } catch (err) {
    console.error('继续对话失败:', err);
    // 失败时移除loading消息
    chat.messages = chat.messages.filter(m => !m.isLoading);
    waitingForUser.value = true;
    alert('继续对话失败: ' + err.message);
  } finally {
    isSending.value = false;
  }
}

/**
 * 处理发送或继续操作
 * - 如果输入框有内容：发送用户消息
 * - 如果输入框为空：继续讨论（让AI发言）
 */
async function handleSendOrContinue() {
  if (isSending.value || isCreating.value) return;

  const text = draft.value.trim();

  if (text) {
    // 有内容：发送用户消息
    waitingForUser.value = false;
    await send();
  } else {
    // 无内容：继续讨论
    await askAI(false);
  }
}

async function summarize() {
  if (!activeChat.value || isSending.value) return;
  if (activeChat.value.id === 'empty') {
    alert('请先选择或创建一个对话');
    return;
  }

  isSending.value = true;
  const chat = activeChat.value;

  try {
    // 添加"正在总结"的占位消息
    const loadingMsg = {
      id: uid(),
      authorId: "ai-loading",
      author_name: "",
      text: "正在生成总结...",
      content: "正在生成总结...",
      time: now(),
      role: "",
      isLoading: true
    };
    chat.messages.push(loadingMsg);
    chat.updatedAt = stamp();

    // 调用总结API
    const result = await apiClient.summarizeChat(chat.id);

    // 移除loading消息
    chat.messages = chat.messages.filter(m => !m.isLoading);

    // 添加总结消息（只添加新消息）
    const existingIds = new Set(chat.messages.map(m => m.id));

    if (result.messages && result.messages.length > 0) {
      for (const msg of result.messages) {
        const msgId = msg.message_id || msg.id;
        // 只添加不存在的消息
        if (msg.isLoading || existingIds.has(msgId)) {
          continue;
        }
        chat.messages.push({
          id: msgId,
          authorId: msg.author_id,
          author_name: msg.author_name,
          text: msg.content,
          content: msg.content,
          time: msg.timestamp,
          role: msg.role
        });
        existingIds.add(msgId);
      }
    }

    chat.updatedAt = result.updated_at || stamp();
    scrollToBottom();
  } catch (err) {
    console.error('生成总结失败:', err);
    // 失败时移除loading消息
    chat.messages = chat.messages.filter(m => !m.isLoading);
    alert('生成总结失败: ' + err.message);
  } finally {
    isSending.value = false;
  }
}

function download(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function exportCurrent(type) {
  const c = activeChat.value;
  if (!c) return;
  const exportedAt = new Date().toISOString();

  if (type === "json") {
    const payload = {
      id: c.id,
      title: c.title,
      updatedAt: c.updatedAt,
      exportedAt,
      messages: c.messages,
    };
    download(`${c.title}.json`, JSON.stringify(payload, null, 2));
    return;
  }

  const header = `# ${c.title}\n# id: ${c.id}\n# exportedAt: ${exportedAt}\n\n`;
  const body = c.messages
    .map((m) => `[${m.time}] ${nameOf(m.authorId)}：\n${m.text || m.content || ''}`)
    .join("\n\n---\n\n");

  download(`${c.title}.txt`, header + body);
}

/**
 * 进入管理后台
 */
function goToAdmin() {
  if (!currentUser.value) {
    alert('请先登录');
    showLoginModal.value = true;
    return;
  }

  // 检查用户角色
  const role = currentUser.value.role || 'user';
  if (role === 'guest' || role === 'user') {
    alert('您没有权限访问管理后台');
    return;
  }

  // 管理员和超级管理员可以进入
  emit('switch-to-admin');
}

/**
 * 检查用户是否为管理员或超级管理员
 */
function isAdminOrSuperAdmin() {
  if (!currentUser.value) return false;
  const role = currentUser.value.role || 'user';
  return role === 'admin' || role === 'super_admin';
}

/**
 * 检查用户是否为超级管理员
 */
function isSuperAdmin() {
  if (!currentUser.value) return false;
  const role = currentUser.value.role || 'user';
  return role === 'super_admin';
}

// ========== 用户认证方法 ==========

/**
 * 用户登录
 */
async function handleLogin() {
  formError.value = '';
  if (!loginForm.value.username || !loginForm.value.password) {
    formError.value = '请输入用户名和密码';
    return;
  }

  try {
    const result = await apiClient.login(loginForm.value.username, loginForm.value.password);
    currentUser.value = result.user;
    showLoginModal.value = false;
    loginForm.value = { username: '', password: '' };

    // 登录成功后重新加载对话列表
    await loadChats();
    // 如果有对话，选中第一个
    if (chats.value.length > 0) {
      activeChatId.value = chats.value[0].id;
      await loadChatMessages(activeChatId.value);
      scrollToBottom(false);
    }
  } catch (err) {
    formError.value = err.message || '登录失败，请检查用户名和密码';
  }
}

/**
 * 用户注册
 */
async function handleRegister() {
  formError.value = '';
  registerErrors.value = {};

  // 前端校验
  const errors = {};
  if (!registerForm.value.username || registerForm.value.username.length < 3) {
    errors.username = '用户名至少3个字符';
  }
  if (!registerForm.value.password || registerForm.value.password.length < 6) {
    errors.password = '密码至少6个字符';
  }
  if (registerForm.value.password !== registerForm.value.confirmPassword) {
    errors.confirmPassword = '两次密码不一致';
  }
  if (registerForm.value.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(registerForm.value.email)) {
    errors.email = '邮箱格式不正确';
  }

  if (Object.keys(errors).length > 0) {
    registerErrors.value = errors;
    return;
  }

  try {
    const result = await apiClient.register(
      registerForm.value.username,
      registerForm.value.password,
      registerForm.value.email || null,
      registerForm.value.avatarUrl || null
    );
    currentUser.value = result.user;
    showRegisterModal.value = false;
    registerForm.value = {
      username: '',
      password: '',
      confirmPassword: '',
      email: '',
      avatarUrl: '',
    };

    // 注册成功后重新加载对话列表
    await loadChats();
    // 如果有对话，选中第一个
    if (chats.value.length > 0) {
      activeChatId.value = chats.value[0].id;
      await loadChatMessages(activeChatId.value);
      scrollToBottom(false);
    }
  } catch (err) {
    formError.value = err.message || '注册失败，请重试';
  }
}

/**
 * 用户登出
 */
async function handleLogout() {
  try {
    await apiClient.logout();
    currentUser.value = null;
  } catch (err) {
    console.error('登出失败:', err);
    // 即使请求失败，也清除本地状态
    currentUser.value = null;
  }
}

/**
 * 检查用户权限（是否可以导出）
 */
function canExport() {
  return currentUser.value !== null;
}

/**
 * 处理导出功能（带权限检查）
 */
function exportCurrentWithAuth(type) {
  if (!canExport()) {
    showLoginModal.value = true;
    return;
  }
  exportCurrent(type);
}

// ========== 主题相关 ==========

/**
 * 初始化主题
 */
function initTheme() {
  const savedTheme = localStorage.getItem('theme') || 'dark';
  setTheme(savedTheme);
}

/**
 * 设置主题
 */
function setTheme(newTheme) {
  theme.value = newTheme;
  localStorage.setItem('theme', newTheme);

  const root = document.documentElement;
  if (newTheme === 'system') {
    // 检测系统主题
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    applyTheme(prefersDark ? 'dark' : 'light');
    // 监听系统主题变化
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
      applyTheme(e.matches ? 'dark' : 'light');
    });
  } else {
    applyTheme(newTheme);
  }
}

/**
 * 应用主题
 */
function applyTheme(themeMode) {
  const root = document.documentElement;
  if (themeMode === 'dark') {
    root.setAttribute('data-theme', 'dark');
    root.style.setProperty('--bg', '#0b1020');
    root.style.setProperty('--panel', '#111a33');
    root.style.setProperty('--panel2', '#0f1730');
    root.style.setProperty('--text', '#eaf0ff');
    root.style.setProperty('--muted', '#9fb0d0');
  } else if (themeMode === 'light') {
    root.setAttribute('data-theme', 'light');
    // 浅色模式：白色背景，黑色文字
    root.style.setProperty('--bg', '#ffffff');
    root.style.setProperty('--panel', '#f7f7f7');
    root.style.setProperty('--panel2', '#eeeeee');
    root.style.setProperty('--text', '#000000');
    root.style.setProperty('--muted', '#666666');
  }
}

// ========== 公开对话相关 ==========

/**
 * 加载公开对话大厅
 */
async function loadPublicChats() {
  try {
    const result = await apiClient.getPublicChatHall(20);
    publicChats.value = result.chats || [];
  } catch (err) {
    console.error('加载公开对话失败:', err);
  }
}

/**
 * 刷新公开对话
 */
async function refreshPublicChats() {
  await loadPublicChats();
  // 重置轮播
  currentPublicChatIndex.value = 0;
  restartCarousel();
}

/**
 * 启动轮播
 */
function startCarousel() {
  if (carouselTimer) {
    clearInterval(carouselTimer);
  }
  carouselTimer = setInterval(() => {
    if (publicChats.value.length > 1) {
      currentPublicChatIndex.value = (currentPublicChatIndex.value + 1) % publicChats.value.length;
    }
  }, 5000);
}

/**
 * 重启轮播
 */
function restartCarousel() {
  startCarousel();
}

/**
 * 查看公开对话
 */
async function viewPublicChat(chatId) {
  // 切换到该对话
  activeChatId.value = chatId;
  await loadChatMessages(chatId);
  scrollToBottom(false);
}

// ========== 账号管理相关 ==========

/**
 * 更新个人信息
 */
async function updateProfile() {
  profileError.value = '';
  profileSuccess.value = '';

  if (!profileForm.value.username || profileForm.value.username.length < 3) {
    profileError.value = '用户名至少3个字符';
    return;
  }

  if (profileForm.value.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(profileForm.value.email)) {
    profileError.value = '邮箱格式不正确';
    return;
  }

  try {
    const result = await apiClient.updateProfile({
      username: profileForm.value.username,
      email: profileForm.value.email || null,
      avatar_url: profileForm.value.avatarUrl || null,
    });
    currentUser.value = result.user;
    profileSuccess.value = '个人信息已更新';
    setTimeout(() => {
      profileSuccess.value = '';
    }, 3000);
  } catch (err) {
    profileError.value = err.message || '更新失败';
  }
}

/**
 * 修改密码
 */
async function changePassword() {
  profileError.value = '';
  profileSuccess.value = '';

  if (!passwordForm.value.oldPassword) {
    profileError.value = '请输入当前密码';
    return;
  }

  if (!passwordForm.value.newPassword || passwordForm.value.newPassword.length < 6) {
    profileError.value = '新密码至少6个字符';
    return;
  }

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    profileError.value = '两次密码不一致';
    return;
  }

  try {
    await apiClient.changePassword(passwordForm.value.oldPassword, passwordForm.value.newPassword);
    profileSuccess.value = '密码已修改';
    passwordForm.value = {
      oldPassword: '',
      newPassword: '',
      confirmPassword: '',
    };
    setTimeout(() => {
      profileSuccess.value = '';
    }, 3000);
  } catch (err) {
    profileError.value = err.message || '修改密码失败';
  }
}

// ========== 数据管理相关 ==========

/**
 * 导出所有数据
 */
async function exportAllData() {
  try {
    const result = await apiClient.exportAllChats();
    const exportedAt = new Date().toISOString();
    const payload = {
      exportedAt,
      chats: result.chats,
    };
    download(`all_chats_${new Date().toISOString().split('T')[0]}.json`, JSON.stringify(payload, null, 2));
    alert('导出成功');
  } catch (err) {
    console.error('导出失败:', err);
    alert('导出失败: ' + err.message);
  }
}

/**
 * 确认删除所有对话
 */
async function confirmDeleteAll() {
  if (!confirm('⚠️ 确定要删除所有对话吗？此操作不可恢复！')) {
    return;
  }

  if (!confirm('⚠️ 请再次确认：真的要删除所有对话吗？')) {
    return;
  }

  try {
    await apiClient.deleteAllChats();
    alert('所有对话已删除');
    // 重新加载对话列表
    await loadChats();
    if (chats.value.length > 0) {
      activeChatId.value = chats.value[0].id;
      await loadChatMessages(activeChatId.value);
    } else {
      activeChatId.value = null;
    }
  } catch (err) {
    console.error('删除失败:', err);
    alert('删除失败: ' + err.message);
  }
}

</script>

<style scoped>
.app{
  height:100vh;
  display:grid;
  grid-template-columns: 340px 1fr;
  overflow: hidden;
}
/* 置顶文字按钮（替代星星） */
.pinText{
  font-size:12px;
  padding:4px 8px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.04);
  color: var(--muted);
  cursor:pointer;
  white-space:nowrap;
}
/* 高级搜索框 */
.search{
  width: calc(100% - 16px);
  margin: 8px 8px 14px;
  padding: 10px 12px;
  border-radius: 14px;

  border:1px solid rgba(255,255,255,.08);
  background: linear-gradient(
    180deg,
    rgba(255,255,255,.06),
    rgba(255,255,255,.03)
  );

  color: var(--text);
  font-size:13px;
  outline:none;

  transition: all .18s ease;
}

.search::placeholder{
  color: rgba(255,255,255,.45);
}

/* 聚焦时更“高级” */
.search:focus{
  border-color: rgba(106,167,255,.45);
  background: rgba(106,167,255,.08);
  box-shadow:
    0 0 0 3px rgba(106,167,255,.12),
    inset 0 0 0 1px rgba(106,167,255,.15);
}

.pinText:hover{
  color: var(--text);
  border-color: rgba(255,255,255,.25);
}

.pinText.on{
  color: #ffcc66;
  border-color: rgba(255,204,102,.45);
  background: rgba(255,204,102,.12);
}

.chatList::-webkit-scrollbar {
  width: 6px;
}

.chatList::-webkit-scrollbar-thumb {
  background-color: rgba(255,255,255,0);
  border-radius: 999px;
  transition: background-color .25s;
}

.chatList:hover::-webkit-scrollbar-thumb {
  background-color: rgba(255,255,255,.28);
}

/* Sidebar */
.sidebar{
  border-right:1px solid var(--line);
  background: linear-gradient(180deg, rgba(17,26,51,.92), rgba(10,16,34,.92));
  padding:18px;
  display:flex;
  flex-direction:column;
  height:100vh;
  overflow:hidden;
  position:relative;
}

.brand{
  display:flex;
  gap:12px;
  align-items:center;
  padding:10px 10px 16px;
  border-bottom:1px solid var(--line);
  margin-bottom:14px;
}
.logo{
  width:44px;height:44px;
  border-radius:14px;
  display:grid;place-items:center;
  background: rgba(106,167,255,.18);
  border:1px solid rgba(106,167,255,.35);
  font-weight:800;
}
.title .name{ font-size:18px; font-weight:800; }
.title .sub{ font-size:12px; color:var(--muted); margin-top:2px; }

.section{
  margin-top:14px;
  flex:1;
  overflow:hidden;
  display:flex;
  flex-direction:column;
  min-height:0;
}
.sectionTitle{
  font-size:12px;
  color:var(--muted);
  margin:10px 6px;
  letter-spacing:.08em;
}
.rowBetween{
  display:flex;
  align-items:center;
  justify-content:space-between;
}

.ghost{
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.04);
  color: var(--text);
  padding:6px 10px;
  border-radius:10px;
  cursor:pointer;
  font-size:12px;
}
.ghost:hover{ filter:brightness(1.05); }

.chatList{
  display:flex;
  flex-direction:column;
  gap:8px;
  padding:0 4px;
  flex:1;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 6px;
  min-height: 0;
}

.chatItem{
  text-align:left;
  padding:10px 10px;
  border-radius:14px;
  border:1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.03);
  color: var(--text);
  cursor:pointer;
}
.chatItem:hover{ background: rgba(255,255,255,.05); }
.chatItem.active{
  border-color: rgba(106,167,255,.25);
  background: rgba(106,167,255,.10);
}
.chatTitle{ font-weight:900; }
.chatMeta{
  margin-top:6px;
  font-size:12px;
  color:var(--muted);
  display:flex;
  gap:6px;
  align-items:center;
}

.exportRow{
  display:flex;
  gap:10px;
  padding:10px 4px 0;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}
.topic{
  flex:1;
  padding:10px 12px;
  border-radius:12px;
  border:1px solid rgba(106,167,255,.22);
  background: rgba(106,167,255,.12);
  color: var(--text);
  cursor:pointer;
  font-weight:800;
}
.topic2{
  border-color: rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
}
.topic:hover{ filter: brightness(1.05); }

.hint{
  margin:10px 6px 0;
  font-size:12px;
  color:var(--muted);
  line-height:1.4;
}

/* Members */
.member{
  display:flex;
  gap:10px;
  padding:10px;
  border-radius:14px;
  border:1px solid transparent;
  transition:.15s;
}
.member:hover{
  background: rgba(255,255,255,.04);
  border-color: rgba(255,255,255,.06);
}
.avatar{
  width:40px;height:40px;border-radius:14px;
  display:grid;place-items:center;
  border:1px solid rgba(255,255,255,.2);
  background: rgba(255,255,255,.06);
  flex:0 0 auto;
  font-weight:700;
}
.meta{ min-width:0; }
.row{ display:flex; gap:8px; align-items:center; }
.mname{ font-weight:800; }
.tag{
  font-size:11px;
  padding:2px 8px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.08);
}
.desc{
  margin-top:4px;
  font-size:12px;
  color:var(--muted);
  line-height:1.35;
}

/* User bottom bar */
.userBar{
  position:absolute;
  left:12px;
  right:12px;
  bottom:12px;
  display:flex;
  gap:10px;
  align-items:center;
  padding:10px 10px;
  border-radius:16px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(10,16,34,.65);
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}
.uAvatar{
  width:38px;height:38px;border-radius:14px;
  display:grid;place-items:center;
  font-weight:900;
  border:1px solid rgba(255,255,255,.18);
  background: rgba(255,255,255,.06);
}

/* 管理员和超级管理员头像框颜色 */
.uAvatar.admin {
  border-color: rgba(199,125,255,.4);
  background: rgba(199,125,255,.2);
  color: #c77dff;
}

.uAvatar.super_admin {
  border-color: rgba(255,199,89,.4);
  background: rgba(255,199,89,.2);
  color: #ffc757;
}

.uMeta{ min-width:0; }
.uName{ font-weight:900; }
/* 管理员和超级管理员用户名颜色 */
.uName.admin {
  color: #c77dff;
}
.uName.super_admin {
  color: #ffc757;
}
.uSub{ font-size:12px; color:var(--muted); margin-top:2px; }
.admin-btn{
  margin-left:auto;
  width:34px;height:34px;border-radius:12px;
  border:1px solid rgba(199,125,255,.25);
  background: rgba(199,125,255,.15);
  color: var(--text);
  cursor:pointer;
  font-weight:800;
}
.admin-btn:hover{
  background: rgba(199,125,255,.25);
  border-color: rgba(199,125,255,.40);
}
.gear{
  margin-left:150px;
  width:34px;height:34px;border-radius:12px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.04);
  color: var(--text);
  cursor:pointer;
}

/* Main */
.main{
  display:grid;
  grid-template-rows: 74px 1fr auto;
  min-width:0;
  height:100vh;
  overflow:hidden;
}
.topbar{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:16px 18px;
  border-bottom:1px solid var(--line);
  background: rgba(10,16,34,.45);
  backdrop-filter: blur(10px);
}
.topicTitle .big{ font-weight:900; }
.topicTitle .small{ margin-top:4px; font-size:12px; color:var(--muted); }

.status{
  display:flex; align-items:center; gap:8px;
  font-size:12px; color:var(--muted);
  padding:8px 10px;
  border-radius:999px;
  border:1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.03);
}
.dot{
  width:8px;height:8px;border-radius:99px;
  background: var(--success);
  box-shadow: 0 0 0 6px rgba(81,209,138,.12);
}

/* Chat */
.chat{
  overflow-y: auto;
  overflow-x: hidden;
  padding:18px 18px 160px 18px;
  min-height: 0;
}
.timeline{
  max-width: 980px;
  margin: 0 auto;
  display:flex;
  flex-direction:column;
  gap:4px;
}
.msg{ display:flex; }
.msg.me{ justify-content:flex-end; padding-right: 100px; }
.bubble{
  width: 800px;
  border-radius:18px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  padding:12px 14px;
  box-shadow: 0 10px 30px rgba(0,0,0,.18);
}
.msg.me .bubble{
  width: auto;
  max-width: 500px;
}
.head{
  display:flex;
  align-items:center;
  gap:8px;
  font-size:12px;
  color:var(--muted);
  margin-bottom:6px;
}
.who{ color: var(--text); font-weight:900; }
.badge{
  font-size:11px;
  padding:2px 8px;
  border-radius:999px;
  background: rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.10);
}
.time{ margin-left:auto; opacity:.9; }
.content p{ margin:0; line-height:1.55; font-size:14px; color: var(--text); }
.content p + p{ margin-top:8px; }
.actions{ display:flex; gap:8px; margin-top:10px; }
.mini{
  padding:6px 10px;
  border-radius:10px;
  background: rgba(255,255,255,.04);
  border:1px solid rgba(255,255,255,.08);
  color: var(--muted);
  cursor:pointer;
  font-size:12px;
}
.mini:hover{ color: var(--text); }

/* Composer */
.composer{
  border-top:1px solid var(--line);
  background: rgba(10,16,34,.55);
  backdrop-filter: blur(10px);
  padding:12px 18px 14px;
  flex-shrink: 0;
}
.inputRow{
  max-width: 980px;
  margin: 0 auto;
  display:flex;
  gap:10px;
  align-items:flex-end;
}
.inputWrapper{
  flex:1;
  position:relative;
  display:flex;
  align-items:flex-end;
  gap:8px;
}
.input{
  flex:1;
  resize:none;
  border-radius:14px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  padding:12px 50px 12px 12px;
  outline:none;
}
.input:focus{ border-color: rgba(106,167,255,.35); }
.sendArrowBtn{
  position:absolute;
  right:8px;
  bottom:8px;
  width:36px;
  height:36px;
  border-radius:10px;
  border:1px solid rgba(106,167,255,.25);
  background: rgba(106,167,255,.18);
  color: var(--text);
  font-size:18px;
  font-weight:900;
  cursor:pointer;
  transition: all .18s ease;
  display:flex;
  align-items:center;
  justify-content:center;
  line-height:1;
}
.sendArrowBtn:hover:not(:disabled){
  filter: brightness(1.05);
  border-color: rgba(106,167,255,.45);
  background: rgba(106,167,255,.25);
}
.sendArrowBtn:disabled{ opacity:.45; cursor:not-allowed; }
.summary-btn{
  padding:12px 14px;
  border-radius:14px;
  border:1px solid rgba(199,125,255,.25);
  background: rgba(199,125,255,.18);
  color: var(--text);
  font-weight:900;
  cursor:pointer;
  min-width: 70px;
  transition: all .18s ease;
}
.summary-btn:hover:not(:disabled){
  filter: brightness(1.05);
  border-color: rgba(199,125,255,.45);
}
.summary-btn:disabled{ opacity:.45; cursor:not-allowed; }
.tips{
  max-width:980px;
  margin:10px auto 0;
  font-size:12px;
  color:var(--muted);
  display:flex;
  gap:8px;
  align-items:center;
}

.quote{
  max-width:980px;
  margin:0 auto 10px;
  padding:10px 12px;
  border-radius:14px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.04);
  display:flex;
  gap:10px;
  align-items:center;
}
.qtag{
  font-size:12px;
  padding:3px 8px;
  border-radius:999px;
  background: rgba(255,255,255,.06);
  border:1px solid rgba(255,255,255,.10);
  color: var(--muted);
}
.qtext{
  font-size:12px;
  color: var(--muted);
  overflow:hidden;
  white-space:nowrap;
  text-overflow:ellipsis;
}
.qclose{
  margin-left:auto;
  width:26px;height:26px;
  border-radius:10px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.04);
  color: var(--text);
  cursor:pointer;
}

/* Loading指示器 */
.loading-indicator {
  display: flex;
  gap: 8px;
  padding: 8px 0;
}

.dot-bounce {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: rgba(106,167,255,.6);
  animation: bounce 1.4s infinite ease-in-out both;
}

.dot-bounce:nth-child(1) {
  animation-delay: -0.32s;
}

.dot-bounce:nth-child(2) {
  animation-delay: -0.16s;
}

.dot-bounce:nth-child(3) {
  animation-delay: 0s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

/* Loading气泡样式 */
.bubble.loading {
  opacity: 0.8;
  border-style: dashed;
}

/* ========== 顶部导航栏右侧样式 ========== */
.topbarRight {
  display: flex;
  align-items: center;
  gap: 12px;
}

.authBtn {
  padding: 8px 16px;
  border-radius: 10px;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: all .18s ease;
}

.authBtn.ghostBtn {
  background: rgba(255,255,255,.05);
  border: 1px solid rgba(255,255,255,.15);
  color: var(--text);
}

.authBtn.ghostBtn:hover {
  background: rgba(255,255,255,.10);
  border-color: rgba(255,255,255,.25);
}

.authBtn.primaryBtn {
  background: rgba(106,167,255,.20);
  border: 1px solid rgba(106,167,255,.40);
  color: var(--text);
}

.authBtn.primaryBtn:hover {
  background: rgba(106,167,255,.30);
  border-color: rgba(106,167,255,.55);
}

.welcomeText {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

/* 管理员和超级管理员欢迎文字颜色 */
.welcomeText.admin {
  color: #c77dff;
}
.welcomeText.super_admin {
  color: #ffc757;
}

/* ========== 登录/注册弹窗样式 ========== */
.modalOverlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,.65);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.modal {
  background: linear-gradient(180deg, rgba(17,26,51,.98), rgba(10,16,34,.98));
  border: 1px solid rgba(255,255,255,.12);
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,.45);
  width: 90%;
  max-width: 400px;
  animation: modalIn .25s ease-out;
}

.modalLarge {
  max-width: 480px;
}

@keyframes modalIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.modalHeader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255,255,255,.10);
}

.modalHeader h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  color: var(--text);
}

.closeBtn {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.04);
  color: var(--text);
  font-size: 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .18s ease;
}

.closeBtn:hover {
  background: rgba(255,255,255,.10);
  border-color: rgba(255,255,255,.20);
}

.modalBody {
  padding: 24px;
}

.formError {
  padding: 12px;
  border-radius: 10px;
  background: rgba(255,102,102,.15);
  border: 1px solid rgba(255,102,102,.35);
  color: #ff8888;
  font-size: 13px;
  margin-bottom: 16px;
}

.formGroup {
  margin-bottom: 16px;
}

.formGroup label {
  display: block;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 6px;
}

.required {
  color: #ff6b6b;
}

.formGroup input {
  width: 100%;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(255,255,255,.04);
  color: var(--text);
  font-size: 14px;
  outline: none;
  transition: all .18s ease;
  box-sizing: border-box;
}

.formGroup input:focus {
  border-color: rgba(106,167,255,.45);
  background: rgba(106,167,255,.08);
  box-shadow: 0 0 0 3px rgba(106,167,255,.12);
}

.formGroup input::placeholder {
  color: rgba(255,255,255,.40);
}

.fieldError {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #ff6b6b;
}

.submitBtn {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(106,167,255,.35);
  background: rgba(106,167,255,.20);
  color: var(--text);
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  margin-top: 8px;
  transition: all .18s ease;
}

.submitBtn:hover {
  background: rgba(106,167,255,.30);
  border-color: rgba(106,167,255,.50);
}

.formFooter {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: var(--muted);
}

.formFooter a {
  color: #6aa7ff;
  cursor: pointer;
  font-weight: 700;
  text-decoration: none;
}

.formFooter a:hover {
  text-decoration: underline;
}

/* ========== 已公开对话轮播图样式 ========== */
.carouselSection {
  flex: 0 0 auto;
  max-height: 180px;
}

.publicChatCarousel {
  padding: 0 4px;
  position: relative;
}

.publicChatItem {
  text-align: left;
  padding: 12px;
  border-radius: 14px;
  border: 1px solid rgba(106,167,255,.20);
  background: rgba(106,167,255,.08);
  cursor: pointer;
  transition: all .3s ease;
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.publicChatItem:hover {
  background: rgba(106,167,255,.15);
  border-color: rgba(106,167,255,.35);
}

.publicChatTitle {
  font-weight: 700;
  font-size: 14px;
  margin-bottom: 6px;
  line-height: 1.4;
}

.publicChatMeta {
  font-size: 12px;
  color: var(--muted);
  display: flex;
  gap: 8px;
  align-items: center;
}

.like-count {
  color: #ff6b6b;
  font-weight: 700;
}

/* 轮播指示器 */
.carouselDots {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 12px;
}

.carouselDots .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(255,255,255,.20);
  transition: all .3s ease;
}

.carouselDots .dot.active {
  width: 18px;
  border-radius: 3px;
  background: var(--primary);
}

/* ========== 设置弹窗样式 ========== */
.settingsModal {
  max-width: 640px;
}

.settingsBody {
  padding: 0;
}

.settingsTabs {
  display: flex;
  border-bottom: 1px solid rgba(255,255,255,.10);
  padding: 0 20px;
}

.tabBtn {
  padding: 16px 20px;
  background: transparent;
  border: none;
  color: var(--muted);
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all .18s ease;
}

.tabBtn:hover {
  color: var(--text);
}

.tabBtn.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
}

.settingsContent {
  padding: 24px;
}

.settingsContent h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 800;
  color: var(--text);
}

.settingsContent h4 {
  margin: 24px 0 12px 0;
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}

/* 主题选项 */
.themeOptions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.themeOption {
  flex: 1;
  padding: 16px;
  border-radius: 14px;
  border: 2px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.03);
  color: var(--text);
  cursor: pointer;
  transition: all .18s ease;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.themeOption:hover {
  border-color: rgba(255,255,255,.20);
  background: rgba(255,255,255,.05);
}

.themeOption.active {
  border-color: var(--primary);
  background: rgba(106,167,255,.12);
}

.themeIcon {
  font-size: 24px;
}

.themeOption span:last-child {
  font-weight: 700;
  font-size: 13px;
}

/* 管理员入口按钮 */
.adminEntryBtn {
  padding: 12px 20px;
  border-radius: 12px;
  border: 1px solid rgba(199,125,255,.25);
  background: rgba(199,125,255,.18);
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
  width: 100%;
}

.adminEntryBtn:hover {
  filter: brightness(1.05);
  border-color: rgba(199,125,255,.40);
}

/* 设置提示 */
.settingsHint {
  font-size: 13px;
  color: var(--muted);
  margin: 8px 0 12px 0;
  line-height: 1.5;
}

.settingsHint.warning {
  color: #ff8888;
}

/* 未登录状态 */
.notLoggedIn {
  text-align: center;
  padding: 40px 20px;
}

.notLoggedIn p {
  color: var(--muted);
  margin-bottom: 16px;
}

/* 数据管理操作按钮 */
.actionBtn {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid;
  font-weight: 700;
  font-size: 14px;
  cursor: pointer;
  transition: all .18s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 12px;
}

.exportBtn {
  background: rgba(106,167,255,.15);
  border-color: rgba(106,167,255,.35);
  color: var(--text);
}

.exportBtn:hover {
  background: rgba(106,167,255,.25);
  border-color: rgba(106,167,255,.50);
}

.deleteBtn {
  background: rgba(255,102,102,.15);
  border-color: rgba(255,102,102,.35);
  color: #ff8888;
}

.deleteBtn:hover {
  background: rgba(255,102,102,.25);
  border-color: rgba(255,102,102,.50);
}

/* 成功消息样式 */
.formSuccess {
  padding: 12px;
  border-radius: 10px;
  background: rgba(81,209,138,.15);
  border: 1px solid rgba(81,209,138,.35);
  color: #51d18a;
  font-size: 13px;
  margin-bottom: 16px;
}

/* ========== 浅色模式样式 ========== */
:root[data-theme="light"] body {
  background: #ffffff !important;
}

:root[data-theme="light"] .sidebar {
  background: #f7f7f7;
  border-right-color: #e0e0e0;
}

/* 浅色模式下的按钮 - 有色彩的版本 */
:root[data-theme="light"] .ghost {
  background: #f0f4ff;
  border-color: #6aa7ff;
  color: #1976d2;
}

:root[data-theme="light"] .ghost:hover {
  background: #e3f2fd;
  border-color: #42a5f5;
}

:root[data-theme="light"] .topic {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #5a67d8;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

:root[data-theme="light"] .topic:hover {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  filter: brightness(1.1);
}

:root[data-theme="light"] .topic2 {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border-color: #e91e63;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(233, 30, 99, 0.3);
}

:root[data-theme="light"] .topic2:hover {
  box-shadow: 0 4px 12px rgba(233, 30, 99, 0.4);
  filter: brightness(1.1);
}

:root[data-theme="light"] .chatItem {
  background: #ffffff;
  border-color: #e0e0e0;
}

:root[data-theme="light"] .chatItem:hover {
  background: #f5f5f5;
  border-color: #bdbdbd;
}

:root[data-theme="light"] .chatItem.active {
  border-color: #6aa7ff;
  background: linear-gradient(135deg, #e3f2fd 0%, #f0f4ff 100%);
  box-shadow: 0 2px 8px rgba(106, 167, 255, 0.2);
}

:root[data-theme="light"] .userBar {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-color: #b0bccc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

:root[data-theme="light"] .uAvatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #5a67d8;
  color: #ffffff;
}

:root[data-theme="light"] .main {
  background: #ffffff;
}

:root[data-theme="light"] .topbar {
  background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
  border-bottom-color: #e0e0e0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

:root[data-theme="light"] .composer {
  background: linear-gradient(180deg, #f8f9fa 0%, #ffffff 100%);
  border-top-color: #e0e0e0;
}

:root[data-theme="light"] .input {
  background: #ffffff;
  border-color: #bdbdbd;
  color: #000000;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

:root[data-theme="light"] .input:focus {
  border-color: #6aa7ff;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(106, 167, 255, 0.1), 0 2px 4px rgba(0, 0, 0, 0.05);
}

/* 浅色模式下的发送按钮 */
:root[data-theme="light"] .sendArrowBtn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #5a67d8;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

:root[data-theme="light"] .sendArrowBtn:hover:not(:disabled) {
  background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transform: translateY(-1px);
}

/* 浅色模式下的总结按钮 */
:root[data-theme="light"] .summary-btn {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border-color: #e91e63;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(233, 30, 99, 0.3);
}

:root[data-theme="light"] .summary-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%);
  box-shadow: 0 4px 12px rgba(233, 30, 99, 0.4);
  transform: translateY(-1px);
}

/* 浅色模式下的气泡 */
:root[data-theme="light"] .bubble {
  background: #ffffff;
  border-color: #e0e0e0;
  color: #000000;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

:root[data-theme="light"] .bubble .content p {
  color: #000000;
}

/* 浅色模式下的公开对话 */
:root[data-theme="light"] .publicChatItem {
  background: linear-gradient(135deg, #e3f2fd 0%, #f0f4ff 100%);
  border-color: #6aa7ff;
  box-shadow: 0 2px 8px rgba(106, 167, 255, 0.15);
}

:root[data-theme="light"] .publicChatItem:hover {
  background: linear-gradient(135deg, #f0f4ff 0%, #e3f2fd 100%);
  box-shadow: 0 4px 12px rgba(106, 167, 255, 0.25);
  transform: translateY(-1px);
}

/* 浅色模式下的登录/注册按钮 */
:root[data-theme="light"] .authBtn.ghostBtn {
  background: #f0f4ff;
  border-color: #6aa7ff;
  color: #1976d2;
}

:root[data-theme="light"] .authBtn.ghostBtn:hover {
  background: #e3f2fd;
  border-color: #42a5f5;
}

:root[data-theme="light"] .authBtn.primaryBtn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #5a67d8;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

:root[data-theme="light"] .authBtn.primaryBtn:hover {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transform: translateY(-1px);
}

/* 浅色模式下的提交按钮 */
:root[data-theme="light"] .submitBtn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #5a67d8;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

:root[data-theme="light"] .submitBtn:hover {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transform: translateY(-1px);
}

/* 浅色模式下的设置按钮 */
:root[data-theme="light"] .gear {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #5a67d8;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

:root[data-theme="light"] .gear:hover {
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  transform: translateY(-1px);
}

/* 浅色模式下的滚动条 */
:root[data-theme="light"] .chatList::-webkit-scrollbar-thumb {
  background-color: rgba(0,0,0,0);
}

:root[data-theme="light"] .chatList:hover::-webkit-scrollbar-thumb {
  background-color: rgba(106, 167, 255, 0.3);
}

/* 浅色模式下的模态框 */
:root[data-theme="light"] .modal {
  background: #ffffff;
  border-color: #e0e0e0;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
}

:root[data-theme="light"] .modalOverlay {
  background: rgba(0,0,0,.6);
}

/* 浅色模式下的表单输入 */
:root[data-theme="light"] .formGroup input {
  background: #ffffff;
  border-color: #bdbdbd;
  color: #000000;
}

:root[data-theme="light"] .formGroup input:focus {
  border-color: #6aa7ff;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(106, 167, 255, 0.1);
}

/* 浅色模式下的主题选项按钮 */
:root[data-theme="light"] .themeOption {
  background: #ffffff;
  border-color: #e0e0e0;
  color: #000000;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

:root[data-theme="light"] .themeOption:hover {
  background: #f5f5f5;
  border-color: #bdbdbd;
}

:root[data-theme="light"] .themeOption.active {
  border-color: #6aa7ff;
  background: linear-gradient(135deg, #e3f2fd 0%, #f0f4ff 100%);
  box-shadow: 0 4px 12px rgba(106, 167, 255, 0.3);
}

/* 浅色模式下的管理员入口按钮 */
:root[data-theme="light"] .adminEntryBtn {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border-color: #e91e63;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(233, 30, 99, 0.3);
}

:root[data-theme="light"] .adminEntryBtn:hover {
  box-shadow: 0 4px 12px rgba(233, 30, 99, 0.4);
  transform: translateY(-1px);
}

/* 浅色模式下的数据管理按钮 */
:root[data-theme="light"] .exportBtn {
  background: linear-gradient(135deg, #56ab2f 0%, #a8e063 100%);
  border-color: #4caf50;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

:root[data-theme="light"] .exportBtn:hover {
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
  transform: translateY(-1px);
}

:root[data-theme="light"] .deleteBtn {
  background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
  border-color: #e53935;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(229, 57, 53, 0.3);
}

:root[data-theme="light"] .deleteBtn:hover {
  box-shadow: 0 4px 12px rgba(229, 57, 53, 0.4);
  transform: translateY(-1px);
}

/* 浅色模式下的关闭按钮 */
:root[data-theme="light"] .closeBtn {
  background: #f5f5f5;
  border-color: #e0e0e0;
  color: #666666;
}

:root[data-theme="light"] .closeBtn:hover {
  background: #e0e0e0;
  border-color: #bdbdbd;
  color: #000000;
}
</style>
