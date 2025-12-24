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
        <div class="uAvatar">{{ user.short }}</div>
        <div class="uMeta">
          <div class="uName">{{ user.name }}</div>
          <div class="uSub">在线</div>
        </div>
        <button class="admin-btn" @click="goToAdmin" title="管理后台">管</button>
        <button class="gear" title="设置（占位）">⚙</button>
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
            <span class="welcomeText">{{ currentUser.username }}</span>
            <button class="authBtn ghostBtn" @click="handleLogout">登出</button>
          </template>
          <div class="status">
            <span class="dot"></span>
            <span>已连接</span>
          </div>
        </div>
      </header>

      <section class="chat">
        <div class="timeline">
          <div class="msg" v-for="msg in activeChat.messages" :key="msg.id" :class="{me: msg.authorId==='user'}">
            <div class="bubble" :style="bubbleStyle(msg.authorId)" :class="{loading: msg.isLoading}">
              <div class="head">
                <span class="who">{{ nameOf(msg.authorId) }}</span>
                <span class="badge" v-if="roleOf(msg.authorId)">{{ roleOf(msg.authorId) }}</span>
                <span class="time">{{ msg.time }}</span>
              </div>
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
          <textarea
            v-model="draft"
            class="input"
            rows="2"
            placeholder="作为第五位成员插话：提问 / 反驳 / 补充 / 总结……"
            @keydown.enter.exact.prevent="send()"
            :disabled="isSending || isCreating"
          />
          <button class="continue-btn" :disabled="isSending || isCreating" @click="askAI" title="让AI继续发言">
            继续
          </button>
          <button class="summary-btn" :disabled="isSending || isCreating" @click="summarize" title="生成当前对话总结">
            总结
          </button>
          <button class="send" :disabled="!draft.trim() || isSending || isCreating" @click="send">
            {{ isSending ? '发送中...' : isCreating ? '创建中...' : '发送' }}
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
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from "vue";
import { apiClient, now, stamp, uid, mapSpeakerToMemberId, mapMemberIdToName, getUser } from "./api.js";

// 定义 emits
const emit = defineEmits(['switch-to-admin']);

// ========== 用户认证状态 ==========
const currentUser = ref(null);
const showLoginModal = ref(false);
const showRegisterModal = ref(false);

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

// ========== 初始化加载 ==========
onMounted(async () => {
  // 初始化用户状态
  const localUser = getUser();
  if (localUser) {
    currentUser.value = localUser;
  }

  await loadChats();
  // 加载对话列表后，自动加载第一条对话的消息
  if (chats.value.length > 0) {
    activeChatId.value = chats.value[0].id;
    await loadChatMessages(activeChatId.value);
  }
});

onUnmounted(() => {
  // 断开所有WebSocket连接
  apiClient.disconnectAll();
  // 清理WebSocket连接跟踪
  wsConnectedChats.clear();
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
          { id: uid(), authorId: "user", author_name: "用户", text, content: text, time: now(), role: "用户" },
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
      author_name: "用户",
      text: text,
      content: text,
      time: now(),
      role: "用户"
    };
    chat.messages.push(userMsg);
    chat.updatedAt = stamp();

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
  } catch (err) {
    console.error('发送消息失败:', err);
    // 失败时移除loading消息
    chat.messages = chat.messages.filter(m => !m.isLoading);
    // 恢复输入内容
    draft.value = text;
    alert('发送失败: ' + err.message);
  } finally {
    isSending.value = false;
  }
}

function quote(msg) {
  quoted.value = `${nameOf(msg.authorId)}：${msg.text?.split("\n")[0] || ''}`;
}

async function askAI() {
  if (!activeChat.value || isSending.value) return;
  if (activeChat.value.id === 'empty') {
    alert('请先选择或创建一个对话');
    return;
  }

  isSending.value = true;
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
  } catch (err) {
    console.error('继续对话失败:', err);
    // 失败时移除loading消息
    chat.messages = chat.messages.filter(m => !m.isLoading);
    alert('继续对话失败: ' + err.message);
  } finally {
    isSending.value = false;
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

function goToAdmin() {
  window.location.hash = 'admin';
  emit('switch-to-admin');
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
.uMeta{ min-width:0; }
.uName{ font-weight:900; }
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
  margin-left:8px;
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
  padding:18px;
  min-height: 0;
}
.timeline{
  max-width: 980px;
  margin: 0 auto;
  display:flex;
  flex-direction:column;
  gap:14px;
}
.msg{ display:flex; }
.msg.me{ justify-content:flex-end; }
.bubble{
  width: min(780px, 100%);
  border-radius:18px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  padding:12px 14px;
  box-shadow: 0 10px 30px rgba(0,0,0,.18);
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
.input{
  flex:1;
  resize:none;
  border-radius:14px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  padding:12px 12px;
  outline:none;
}
.input:focus{ border-color: rgba(106,167,255,.35); }
.continue-btn{
  padding:12px 14px;
  border-radius:14px;
  border:1px solid rgba(81,209,138,.25);
  background: rgba(81,209,138,.18);
  color: var(--text);
  font-weight:900;
  cursor:pointer;
  min-width: 70px;
  transition: all .18s ease;
}
.continue-btn:hover:not(:disabled){
  filter: brightness(1.05);
  border-color: rgba(81,209,138,.45);
}
.continue-btn:disabled{ opacity:.45; cursor:not-allowed; }
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
.send{
  padding:12px 14px;
  border-radius:14px;
  border:1px solid rgba(106,167,255,.25);
  background: rgba(106,167,255,.18);
  color: var(--text);
  font-weight:900;
  cursor:pointer;
  min-width: 90px;
  transition: all .18s ease;
}
.send:hover:not(:disabled){
  filter: brightness(1.05);
  border-color: rgba(106,167,255,.45);
}
.send:disabled{ opacity:.45; cursor:not-allowed; }
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
</style>
