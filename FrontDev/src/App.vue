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
        <button class="newChatBtn" @click="goToHomePage" title="开启新对话">+</button>
      </div>

      <!-- 已公开历史对话轮播图 -->
      <div class="section carouselSection">
        <div class="sectionTitle rowBetween">
          <span style="cursor: pointer;" @click="showPublicChatsModule">已公开对话</span>
          <button class="ghost" @click="refreshPublicChats">刷新</button>
        </div>

        <div class="publicChatCarousel">
          <div
            v-if="publicChats.length > 0"
            class="publicChatItem"
            @click="showPublicChatsModule"
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
        <div class="sectionTitle">
          <span>历史对话</span>
        </div>

<input
  class="search"
  v-model="keyword"
  placeholder="搜索会话…"
/>

        <div class="chatList">
  <div
    v-for="c in visibleChats"
    :key="c.id"
    class="chatItem"
    :class="{ active: c.id === activeChatId }"
  >
    <div class="chatMain" @click="switchChat(c.id)">
      <!-- 重命名输入框 -->
      <input
        v-if="c.isEditing"
        class="chatTitleInput"
        v-model="c.editingTitle"
        @blur="finishRename(c)"
        @keyup.enter="finishRename(c)"
        @keyup.esc="cancelRename(c)"
        ref="renameInput"
        @click.stop
      />
      <div v-else class="chatTitle">{{ c.title }}</div>
      <div class="chatMeta">
        <span>{{ c.updatedAt }}</span>
        <span>·</span>
        <span>{{ c.messages.length }} 条</span>
      </div>
    </div>

    <!-- 三点菜单按钮 -->
    <div class="chatActions" @click.stop>
      <button
        class="moreBtn"
        :class="{ active: showMenuFor === c.id }"
        @click="toggleMenu(c.id)"
        ref="moreBtn"
      >
        ⋯
      </button>
      <div v-if="showMenuFor === c.id" class="menuDropdown" @click.stop>
        <template v-if="!c.publicationStatus || c.publicationStatus === 'draft'">
          <button
            v-if="currentUser && currentUser?.role !== 'super_admin'"
            class="menuItem"
            @click="submitForPublication(c)"
          >
            <span class="menuIcon">📤</span> 申请公开
          </button>
          <button
            v-else-if="currentUser && currentUser?.role === 'super_admin'"
            class="menuItem disabled"
            disabled
            title="超级管理员不可申请公开"
          >
            <span class="menuIcon">📤</span> 申请公开
          </button>
          <button
            v-else
            class="menuItem disabled"
            disabled
            title="请先登录后申请公开"
          >
            <span class="menuIcon">📤</span> 申请公开
          </button>
        </template>
        <template v-else-if="c.publicationStatus === 'pending'">
          <button class="menuItem disabled" disabled>
            <span class="menuIcon">⏳</span> 审核中
          </button>
        </template>
        <template v-else-if="c.publicationStatus === 'published'">
          <button class="menuItem published" @click="showPublishedChatInfo(c)">
            <span class="menuIcon">✅</span> 已公开
          </button>
        </template>
        <template v-else-if="c.publicationStatus === 'rejected'">
          <button class="menuItem rejected" @click="showRejectionReason(c)">
            <span class="menuIcon">❌</span> 已驳回
          </button>
        </template>
        <button class="menuItem" @click="startRename(c)">
          <span class="menuIcon">✏️</span> 重命名
        </button>
        <button
          v-if="currentUser"
          class="menuItem"
          @click="exportSingleChat(c)"
        >
          <span class="menuIcon">📥</span> 导出 TXT
        </button>
        <button
          v-else
          class="menuItem disabled"
          disabled
          title="请先登录后导出"
        >
          <span class="menuIcon">📥</span> 导出 TXT
        </button>
        <button class="menuItem delete" @click="confirmDeleteSingle(c)">
          <span class="menuIcon">🗑️</span> 删除
        </button>
      </div>
    </div>

  </div>
</div>

        <div class="hint" v-if="error">
          {{ error }}
        </div>
      </div>
      <!-- 左下角：用户信息 -->
      <div class="userBar">
        <div class="uAvatar" :class="currentUser?.role" @click="handleAvatarClick">
          <img v-if="currentUser?.avatar_url" :src="currentUser.avatar_url" alt="用户头像" class="userAvatarImage" />
          <span v-else>{{ user.short }}</span>
        </div>
        <div class="uMeta">
          <div class="uName" :class="currentUser?.role">{{ user.name }}</div>
          <div class="uSub">在线</div>
        </div>
        <button class="gear" @click="showSettingsModal = true" title="设置">⚙</button>
      </div>
    </aside>

    <!-- 右侧：聊天区 -->
    <main class="main" :class="{ 'home-mode': (isHomePage && !showPublicChats) || showPublicChats }">
      <!-- 已公开对话模块 -->
      <div v-if="showPublicChats" class="publicChatsWrapper">
        <PublicChats
          :current-user="currentUser"
          @close="hidePublicChatsModule"
          @show-login="showLoginModal = true"
        />
      </div>

      <!-- 主页介绍界面 -->
      <div v-if="!showPublicChats && isHomePage" class="homePage">
        <div class="homeContent">
          <div class="homeLogo">
            <div class="logoLarge">智炬</div>
            <div class="logoText">智炬五维 - 多智能体协同学习平台</div>
          </div>

          <div class="homeIntro">
            <h2>欢迎来到智炬五维</h2>
            <p>这是一个多智能体协同学习的前端演示系统</p>
            <ul class="featureList">
              <li>🤖 多个AI智能体协同工作，为您提供多视角的讨论</li>
              <li>💬 实时对话，智能体会根据话题发表独特见解</li>
              <li>📚 支持历史对话管理和导出，方便回顾学习内容</li>
              <li>🎨 优雅的界面设计，流畅的交互体验</li>
            </ul>
          </div>

          <div class="homeInput">
            <div class="inputRow homeInputRow">
              <div class="inputWrapper">
                <textarea
                  ref="homeInputRef"
                  v-model="homeDraft"
                  class="input homeInput"
                  rows="3"
                  placeholder="输入您想要讨论的话题，开启一段新的对话..."
                  @keydown.enter.exact.prevent="handleHomeSend()"
                  @input="autoResizeTextarea(homeInputRef, 3, 10)"
                  :disabled="isCreating"
                />
                <button
                  class="sendArrowBtn"
                  :disabled="isCreating || !homeDraft.trim()"
                  @click="handleHomeSend()"
                  title="开始对话"
                >
                  ↑
                </button>
              </div>
            </div>
            <div class="tips">
              <span>Enter 发送</span><span>·</span>
              <span>输入话题后即可开启多智能体协同讨论</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 对话界面 -->
      <div v-if="!showPublicChats && !isHomePage" class="chatContainer">
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

          <!-- 对话被锁定时的提示 -->
          <div v-if="isChatLocked" class="inputRow locked-hint">
            <div class="lock-info">
              <span class="lock-icon">🔒</span>
              <span v-if="activeChat.publicationStatus === 'pending'">对话已提交审核，暂时无法继续</span>
              <span v-else-if="activeChat.publicationStatus === 'published'">对话已公开，无法继续编辑</span>
            </div>
          </div>

          <!-- 正常输入框 -->
          <div v-else class="inputRow">
            <div class="inputWrapper">
              <textarea
                ref="inputRef"
                v-model="draft"
                class="input"
                rows="2"
                :placeholder="inputPlaceholder"
                @keydown.enter.exact.prevent="handleSendOrContinue()"
                @input="autoResizeTextarea(inputRef, 2, 1000)"
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
      </div>
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

          <!-- 头像上传 -->
          <div class="avatarUploadContainer">
            <div class="avatarPreview" @click="triggerRegisterAvatarInput">
              <img v-if="registerForm.avatarPreview" :src="registerForm.avatarPreview" alt="头像预览" />
              <span v-else class="avatarPlaceholder">+</span>
            </div>
            <div class="avatarUploadHint">点击上传头像</div>
            <input
              ref="registerAvatarInputRef"
              type="file"
              accept="image/*"
              style="display: none"
              @change="handleRegisterAvatarChange"
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
    <div v-if="showSettingsModal" class="modalOverlay">
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
              <h4>账号</h4>
              <div class="userInfo">
                <span class="userNameLabel">当前用户：</span>
                <span class="userName" :class="currentUser.role">
                  {{ currentUser.username }}
                </span>
                <span class="userRoleBadge">({{ getRoleDisplayName(currentUser.role) }})</span>
              </div>
              <button class="logoutBtn" @click="handleLogout">
                退出登录
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
            <div v-else class="accountManagementContainer">
              <!-- 左侧：个人信息 -->
              <div class="accountLeftPanel">
                <h3>个人信息</h3>

                <!-- 头像上传 -->
                <div class="profileAvatarContainer">
                  <div class="profileAvatarPreview" @click="triggerProfileAvatarInput">
                    <img v-if="profileForm.avatarPreview || profileForm.avatarUrl" :src="profileForm.avatarPreview || profileForm.avatarUrl" alt="头像预览" />
                    <span v-else class="avatarPlaceholder">+</span>
                  </div>
                  <button class="changeAvatarBtn" @click="triggerProfileAvatarInput">修改头像</button>
                  <input
                    ref="profileAvatarInputRef"
                    type="file"
                    accept="image/*"
                    style="display: none"
                    @change="handleProfileAvatarChange"
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
              </div>

              <!-- 右侧：修改密码 -->
              <div class="accountRightPanel">
                <h3>修改密码</h3>
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
import PublicChats from "./PublicChats.vue";

// 定义 emits
const emit = defineEmits(['switch-to-admin']);

// ========== 用户认证状态 ==========
const currentUser = ref(null);
const showLoginModal = ref(false);

// ========== 已公开对话模块状态 ==========
const showPublicChats = ref(false);
const showRegisterModal = ref(false);

// ========== 设置相关状态 ==========
const showSettingsModal = ref(false);
const activeSettingsTab = ref('general'); // general | account | data
const theme = ref(localStorage.getItem('theme') || 'dark');

// ========== 主页状态 ==========
const homeDraft = ref('');
const homeInputRef = ref(null);

// ========== 公开对话大厅 ==========
const publicChats = ref([]);
const currentPublicChatIndex = ref(0);
let carouselTimer = null;

// ========== 个人信息表单 ==========
const profileForm = ref({
  avatarUrl: '',
  avatarPreview: '',
  username: '',
  email: '',
});

// 头像上传 input refs
const registerAvatarInputRef = ref(null);
const profileAvatarInputRef = ref(null);

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
  avatarPreview: '', // 头像预览
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
const showMenuFor = ref(null); // 当前显示菜单的对话ID
const renameInput = ref(null); // 重命名输入框的引用

// 全局点击监听 - 用于关闭三点菜单
function handleClickOutside(event) {
  // 如果点击的不是菜单按钮或菜单内部，则关闭菜单
  if (showMenuFor.value !== null) {
    const menuDropdown = document.querySelector('.menuDropdown');
    const moreBtn = document.querySelector('.moreBtn.active');

    if (menuDropdown && !menuDropdown.contains(event.target) &&
        moreBtn && !moreBtn.contains(event.target)) {
      showMenuFor.value = null;
    }
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

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

/**
 * 自动调整textarea高度
 * @param {HTMLTextAreaElement} textarea - 目标textarea元素
 * @param {number} minRows - 最小行数
 * @param {number} maxRows - 最大行数
 */
function autoResizeTextarea(textarea, minRows = 2, maxRows = 12) {
  if (!textarea) return;

  // 保存当前滚动位置
  const scrollTop = textarea.scrollTop;

  // 重置高度以获取正确的scrollHeight
  textarea.style.height = 'auto';

  // 计算行高（包含padding）
  const computedStyle = window.getComputedStyle(textarea);
  const lineHeight = parseFloat(computedStyle.lineHeight);
  const paddingTop = parseFloat(computedStyle.paddingTop);
  const paddingBottom = parseFloat(computedStyle.paddingBottom);

  // 计算每行的实际高度
  const rowHeight = lineHeight;

  // 计算最小和最大高度
  const minHeight = rowHeight * minRows;
  const maxHeight = rowHeight * maxRows;

  // 获取实际内容高度
  const scrollHeight = textarea.scrollHeight;

  // 计算新高度（在最小和最大值之间）
  let newHeight = scrollHeight;
  if (newHeight < minHeight) {
    newHeight = minHeight;
  } else if (newHeight > maxHeight) {
    newHeight = maxHeight;
  }

  // 设置新高度
  textarea.style.height = newHeight + 'px';

  // 如果内容超过了最大高度，确保滚动条在底部
  if (scrollHeight > maxHeight && scrollTop > 0) {
    textarea.scrollTop = scrollTop;
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
      avatarPreview: localUser.avatar_url || '',
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
  // 不自动选中对话，显示欢迎主页
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

// ========== 监听弹窗状态，清除历史数据 ==========
watch(showLoginModal, (isOpen) => {
  if (isOpen) {
    // 登录弹窗打开时，清除历史数据
    loginForm.value = { username: '', password: '' };
    formError.value = '';
  }
});

watch(showRegisterModal, (isOpen) => {
  if (isOpen) {
    // 注册弹窗打开时，清除历史数据
    registerForm.value = {
      username: '',
      password: '',
      confirmPassword: '',
      email: '',
      avatarUrl: '',
      avatarPreview: '',
    };
    formError.value = '';
    registerErrors.value = {};
  }
});

// 监听设置弹窗打开，刷新个人资料数据
watch(showSettingsModal, (isOpen) => {
  if (isOpen && currentUser.value) {
    // 刷新个人资料数据
    profileForm.value = {
      avatarUrl: currentUser.value.avatar_url || '',
      avatarPreview: currentUser.value.avatar_url || '',
      username: currentUser.value.username || '',
      email: currentUser.value.email || '',
    };
    // 清空密码表单和消息
    passwordForm.value = {
      oldPassword: '',
      newPassword: '',
      confirmPassword: '',
    };
    profileError.value = '';
    profileSuccess.value = '';
    // 切换到通用设置标签
    activeSettingsTab.value = 'general';
  }
});

// ========== 监听用户登录状态变化 ==========
watch(currentUser, async (newUser, oldUser) => {
  // 当用户登录状态发生变化时（登录或登出），重新加载对话列表
  // 如果是从游客变为登录用户，或从登录用户变为游客
  if ((newUser === null && oldUser !== null) || (newUser !== null && oldUser === null) ||
      (newUser && oldUser && newUser.user_id !== oldUser.user_id)) {
    await loadChats();
    // 用户状态变化后，回到欢迎主页
    activeChatId.value = null;
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
      publicationStatus: chat.publicationStatus || 'draft', // 默认为草稿状态
      rejectionReason: chat.rejectionReason || '', // 驳回原因
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
      publicationStatus: 'draft', // 新对话默认为草稿状态
      rejectionReason: '',
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
    // 后端立即返回 {status: "processing"}
    // 智能体的实际响应通过WebSocket推送
    const result = await apiClient.continueChat(chatId);
    console.log('[ContinueChat] 智能体正在思考:', result);
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
      // 保存现有的loading消息
      const loadingMessages = chat.messages.filter(m => m.isLoading);

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

      // 恢复loading消息（如果有）
      if (loadingMessages.length > 0) {
        chat.messages = [...chat.messages, ...loadingMessages];
      }

      chat.updatedAt = result.updated_at || stamp();
      // 更新发布状态和驳回原因
      chat.publicationStatus = result.publication_status || 'draft';
      chat.rejectionReason = result.rejection_reason || '';
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
      console.log('[WebSocket] 收到消息:', data);

      if (data.type === 'new_message') {
        // 后端推送的新消息
        const chat = chats.value.find(c => c.id === chatId);
        if (chat) {
          const msgId = data.message.message_id;

          // 检查消息是否已存在
          if (!chat.messages.find(m => m.id === msgId)) {
            // 移除loading消息
            chat.messages = chat.messages.filter(m => !m.isLoading);

            // 添加新消息
            chat.messages.push({
              id: msgId,
              authorId: data.message.author_id,
              author_name: data.message.author_name,
              text: data.message.content,
              content: data.message.content,
              time: data.message.timestamp,
              role: data.message.role
            });
            chat.updatedAt = stamp();
            console.log('[WebSocket] 新消息已添加:', data.message);
          }
        }
      } else if (data.type === 'error') {
        // 后端推送的错误消息
        console.error('[WebSocket] 收到错误:', data.message);
        const chat = chats.value.find(c => c.id === chatId);
        if (chat) {
          // 移除loading消息
          chat.messages = chat.messages.filter(m => !m.isLoading);
          // 显示错误提示
          alert('智能体生成失败: ' + data.message);
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

// 判断是否在主页
const isHomePage = computed(() => {
  return chats.value.length === 0 || !activeChatId.value;
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
      messages: [],
      publicationStatus: 'draft'
    };
  }
  return chats.value.find((c) => c.id === activeChatId.value) || {
    id: 'empty',
    title: '暂无对话',
    pinned: false,
    updatedAt: stamp(),
    messages: [],
    publicationStatus: 'draft'
  };
});

// 判断当前对话是否被锁定（已提交审核或已公开）
const isChatLocked = computed(() => {
  const status = activeChat.value?.publicationStatus;
  return status === 'pending' || status === 'published';
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
    // 切换对话时，滚动到底部显示最新消息
    nextTick(() => {
      scrollToBottom(false);
    });
  }
});

// ========== 监听消息变化，自动滚动到底部 ==========
watch(
  () => activeChat.messages,
  (newMessages, oldMessages) => {
    // 当有新消息时，自动滚动到底部
    if (newMessages && oldMessages) {
      // 检查是否有新消息
      const hasNewMessages = newMessages.length !== oldMessages.length;

      // 检查最后一条消息是否从 loading 状态变为有内容
      const lastMessageUpdated = newMessages.length > 0 &&
        (!oldMessages || oldMessages.length === 0 ||
          newMessages[newMessages.length - 1].id !== oldMessages[oldMessages.length - 1].id ||
          (newMessages[newMessages.length - 1].isLoading !== oldMessages[oldMessages.length - 1]?.isLoading));

      if (hasNewMessages || lastMessageUpdated) {
        nextTick(() => {
          scrollToBottom(true);
        });
      }
    }
  },
  { deep: true }
);

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
  showPublicChats.value = false; // 重置已公开对话状态

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

// 回到欢迎主页
function goToHomePage() {
  activeChatId.value = null;
  homeDraft.value = '';
  draft.value = '';
  showPublicChats.value = false; // 重置已公开对话状态
  nextTick(() => {
    if (homeInputRef.value) {
      autoResizeTextarea(homeInputRef.value, 3, 100);
    }
  });
}

// 主页输入框发送消息
async function handleHomeSend() {
  const text = homeDraft.value.trim();
  if (!text || isCreating.value) return;

  // 将主页输入的内容转移到对话输入框
  draft.value = text;
  homeDraft.value = '';

  // 重置主页输入框高度
  nextTick(() => {
    if (homeInputRef.value) {
      autoResizeTextarea(homeInputRef.value, 3, 100);
    }
  });

  // 调用send函数创建新对话
  await send();
}

async function send() {
  const text = draft.value.trim();
  if (!text || isSending.value || isCreating.value) return;

  // 检查对话是否被锁定
  if (isChatLocked.value) {
    alert('对话已锁定，无法继续发送消息');
    return;
  }

  // 如果没有活跃对话或对话为空，创建新对话
  if (!activeChat.value || activeChat.value.id === 'empty') {
    draft.value = "";
    quoted.value = null;
    nextTick(() => {
      if (inputRef.value) {
        autoResizeTextarea(inputRef.value, 2, 10);
      }
    });

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
  nextTick(() => {
    if (inputRef.value) {
      autoResizeTextarea(inputRef.value, 2, 10);
    }
  });

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

    // 4. 检查响应状态
    if (result.status === 'processing') {
      // 后端正在处理，保留loading消息，等待WebSocket推送
      console.log('[App] AI正在后台处理，等待WebSocket推送...');
    } else {
      // 旧版本后端：立即返回了AI响应，移除loading消息
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
    }

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

  // 检查对话是否被锁定
  if (isChatLocked.value) {
    alert('对话已锁定，无法继续发送消息');
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

    // 调用继续API（后端立即返回，消息通过WebSocket推送）
    await apiClient.continueChat(chat.id);

    // 注意：loading消息会在收到WebSocket消息时被移除
    // 这里不需要立即移除，让用户看到"正在思考"的提示
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

  // 检查对话是否被锁定
  if (isChatLocked.value) {
    alert('对话已锁定，无法继续发送消息');
    return;
  }

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
  console.log('当前用户角色:', role); // 调试日志

  // 只有管理员和超级管理员可以进入
  if (role !== 'admin' && role !== 'super_admin') {
    alert('您没有权限访问管理后台\n需要管理员或超级管理员权限');
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
    // 登录成功后显示欢迎主页
    activeChatId.value = null;
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
      avatarPreview: '',
    };

    // 注册成功后重新加载对话列表
    await loadChats();
    // 注册成功后显示欢迎主页
    activeChatId.value = null;
  } catch (err) {
    formError.value = err.message || '注册失败，请重试';
  }
}

/**
 * 获取角色显示名称
 */
function getRoleDisplayName(role) {
  const roleMap = {
    'guest': '游客',
    'user': '普通用户',
    'admin': '管理员',
    'super_admin': '超级管理员'
  };
  return roleMap[role] || role;
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
 * 处理头像点击事件
 */
function handleAvatarClick() {
  if (currentUser.value) {
    showSettingsModal.value = true;
  } else {
    showLoginModal.value = true;
  }
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

/**
 * 显示已公开对话模块
 */
function showPublicChatsModule() {
  console.log('[App] showPublicChatsModule called, showPublicChats =', showPublicChats.value, '-> true');
  showPublicChats.value = true;
}

/**
 * 隐藏已公开对话模块
 */
function hidePublicChatsModule() {
  console.log('[App] hidePublicChatsModule called, showPublicChats =', showPublicChats.value, '-> false');
  showPublicChats.value = false;
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
    // 更新个人信息表单的预览
    profileForm.value.avatarPreview = profileForm.value.avatarUrl;
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

// ========== 头像上传相关函数 ==========

/**
 * 压缩图片
 * @param {File} file - 原始图片文件
 * @param {number} maxWidth - 最大宽度（默认800）
 * @param {number} maxHeight - 最大高度（默认800）
 * @param {number} quality - 压缩质量 0-1（默认0.8）
 */
function compressImage(file, maxWidth = 800, maxHeight = 800, quality = 0.8) {
  return new Promise((resolve, reject) => {
    // 如果文件已经很小（小于200KB），直接返回
    if (file.size < 200 * 1024) {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result);
      reader.onerror = error => reject(error);
      return;
    }

    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = (e) => {
      const img = new Image();
      img.src = e.target.result;

      img.onload = () => {
        // 计算压缩后的尺寸
        let width = img.width;
        let height = img.height;

        // 按比例缩放
        if (width > height) {
          if (width > maxWidth) {
            height *= maxWidth / width;
            width = maxWidth;
          }
        } else {
          if (height > maxHeight) {
            width *= maxHeight / height;
            height = maxHeight;
          }
        }

        // 创建 canvas 进行压缩
        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        // 转换为 base64，使用指定质量
        const compressedDataUrl = canvas.toDataURL('image/jpeg', quality);
        resolve(compressedDataUrl);
      };

      img.onerror = (error) => {
        reject(new Error('图片加载失败'));
      };
    };

    reader.onerror = (error) => {
      reject(error);
    };
  });
}

/**
 * 将文件转换为 base64
 */
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.readAsDataURL(file);
    reader.onload = () => resolve(reader.result);
    reader.onerror = error => reject(error);
  });
}

/**
 * 触发注册头像文件选择
 */
function triggerRegisterAvatarInput() {
  registerAvatarInputRef.value?.click();
}

/**
 * 处理注册头像选择
 */
async function handleRegisterAvatarChange(event) {
  const file = event.target.files[0];
  if (!file) return;

  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    formError.value = '请选择图片文件';
    return;
  }

  // 验证文件大小（限制为 10MB，但会自动压缩）
  const maxSize = 10 * 1024 * 1024; // 10MB
  if (file.size > maxSize) {
    formError.value = '图片大小不能超过 10MB';
    return;
  }

  try {
    formError.value = '正在处理图片...';

    // 压缩图片（最大800x800，质量0.8）
    const compressedImage = await compressImage(file, 800, 800, 0.8);

    registerForm.value.avatarPreview = compressedImage;
    registerForm.value.avatarUrl = compressedImage;
    formError.value = '';
  } catch (err) {
    console.error('Failed to process image:', err);
    formError.value = '图片处理失败，请重试';
  }
}

/**
 * 触发个人资料头像文件选择
 */
function triggerProfileAvatarInput() {
  profileAvatarInputRef.value?.click();
}

/**
 * 处理个人资料头像选择
 */
async function handleProfileAvatarChange(event) {
  const file = event.target.files[0];
  if (!file) return;

  // 验证文件类型
  if (!file.type.startsWith('image/')) {
    profileError.value = '请选择图片文件';
    return;
  }

  // 验证文件大小（限制为 10MB，但会自动压缩）
  const maxSize = 10 * 1024 * 1024; // 10MB
  if (file.size > maxSize) {
    profileError.value = '图片大小不能超过 10MB';
    return;
  }

  try {
    profileError.value = '正在处理图片...';

    // 压缩图片（最大800x800，质量0.8）
    const compressedImage = await compressImage(file, 800, 800, 0.8);

    profileForm.value.avatarPreview = compressedImage;
    profileForm.value.avatarUrl = compressedImage;
    profileError.value = '';
  } catch (err) {
    console.error('Failed to process image:', err);
    profileError.value = '图片处理失败，请重试';
  }
}

// ========== 数据管理相关 ==========

/**
 * 导出所有数据
 */
async function exportAllData() {
  try {
    // 后端直接返回 ZIP 文件
    await apiClient.exportAllChats();
  } catch (err) {
    console.error('导出失败:', err);
    alert('导出失败: ' + err.message);
  }
}

// ========== 菜单相关函数 ==========

/**
 * 切换菜单显示状态
 */
function toggleMenu(chatId) {
  if (showMenuFor.value === chatId) {
    showMenuFor.value = null;
  } else {
    showMenuFor.value = chatId;
  }
}

/**
 * 开始重命名对话
 */
function startRename(chat) {
  // 先关闭菜单
  showMenuFor.value = null;
  // 设置编辑状态
  chat.isEditing = true;
  // 去除旧的"主题："前缀（如果存在）
  const titleWithoutPrefix = chat.title.replace(/^主题：/, '');
  chat.editingTitle = titleWithoutPrefix;
  // 聚焦输入框
  nextTick(() => {
    const inputs = document.querySelectorAll('.chatTitleInput');
    if (inputs.length > 0) {
      inputs[0].focus();
      inputs[0].select();
    }
  });
}

/**
 * 完成重命名
 */
async function finishRename(chat) {
  if (!chat.isEditing) return;

  const newTitle = chat.editingTitle?.trim();
  const oldTitle = chat.title;

  if (!newTitle) {
    // 标题为空，取消编辑
    cancelRename(chat);
    return;
  }

  // 检查是否实际修改了（与去除前缀的原标题比较）
  const oldTitleWithoutPrefix = oldTitle.replace(/^主题：/, '');
  if (newTitle === oldTitleWithoutPrefix) {
    // 未修改，取消编辑
    cancelRename(chat);
    return;
  }

  // 立即更新前端显示（乐观更新）
  chat.title = newTitle;
  chat.isEditing = false;
  chat.editingTitle = '';

  // 异步更新数据库
  try {
    await apiClient.renameChat(chat.id, newTitle);
    console.log('重命名成功:', newTitle);
  } catch (err) {
    console.error('重命名失败:', err);
    // 失败时恢复原来的名字
    chat.title = oldTitle;
    alert('重命名失败: ' + err.message);
  }
}

/**
 * 取消重命名
 */
function cancelRename(chat) {
  chat.isEditing = false;
  chat.editingTitle = '';
}

/**
 * 导出单个对话为TXT
 */
async function exportSingleChat(chat) {
  // 关闭菜单
  showMenuFor.value = null;
  try {
    await apiClient.exportChatToTxt(chat.id);
  } catch (err) {
    console.error('导出失败:', err);
    alert('导出失败: ' + err.message);
  }
}

/**
 * 确认删除单个对话
 */
async function confirmDeleteSingle(chat) {
  // 关闭菜单
  showMenuFor.value = null;

  if (!confirm(`⚠️ 确定要删除对话"${chat.title}"吗？此操作不可恢复！`)) {
    return;
  }

  try {
    await apiClient.deleteChat(chat.id);
    // 从列表中移除
    chats.value = chats.value.filter(c => c.id !== chat.id);
    // 如果删除的是当前对话，回到欢迎主页
    if (activeChatId.value === chat.id) {
      activeChatId.value = null;
    }
  } catch (err) {
    console.error('删除失败:', err);
    alert('删除失败: ' + err.message);
  }
}

/**
 * 提交对话公开申请
 */
async function submitForPublication(chat) {
  // 关闭菜单
  showMenuFor.value = null;

  if (!confirm(`📤 确定要申请公开对话"${chat.title}"吗？\n提交后将进入审核流程，对话将被锁定。`)) {
    return;
  }

  try {
    // 调用API提交公开申请
    await apiClient.publishChat(chat.id);
    // 更新对话状态
    chat.publicationStatus = 'pending';
    alert('✅ 已提交公开申请，等待管理员审核');
  } catch (err) {
    console.error('提交公开申请失败:', err);
    alert('提交失败: ' + err.message);
  }
}

/**
 * 查看驳回原因
 */
function showRejectionReason(chat) {
  // 关闭菜单
  showMenuFor.value = null;

  if (chat.rejectionReason) {
    alert(`❌ 驳回原因:\n\n${chat.rejectionReason}`);
  } else {
    alert('❌ 对话公开申请已被驳回');
  }
}

/**
 * 查看已公开对话提示
 */
function showPublishedChatInfo(chat) {
  // 关闭菜单
  showMenuFor.value = null;

  // TODO: 跳转到公开对话详情页
  alert(`📖 对话"${chat.title}"已公开\n此功能将在后续版本中实现`);
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

  // 立即清空本地对话列表（乐观更新）
  chats.value = [];
  activeChatId.value = null;

  try {
    await apiClient.deleteAllChats();
    alert('所有对话已删除');
    // 重新加载对话列表（虽然应该为空了）
    await loadChats();
    // 删除所有对话后，保持欢迎主页状态
    activeChatId.value = null;
  } catch (err) {
    console.error('删除失败:', err);
    alert('删除失败: ' + err.message);
    // 失败后重新加载
    await loadChats();
  }
}

</script>

<style>
/* 确保页面不会滚动 */
html, body {
  margin: 0;
  padding: 0;
  overflow: hidden;
  height: 100%;
  width: 100%;
}
</style>

<style scoped>
.app{
  height:100vh;
  display:grid;
  grid-template-columns: 340px 1fr;
  overflow: hidden;
  transition: grid-template-columns .3s ease;
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
  position: relative;
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

/* 开启新对话按钮 */
.newChatBtn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 40px;
  border-radius: 12px;
  border: 1px solid rgba(106,167,255,.3);
  background: rgba(106,167,255,.15);
  color: #6aa7ff;
  font-size: 24px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .2s ease;
  flex-shrink: 0;
}

.newChatBtn:hover {
  background: rgba(106,167,255,.25);
  border-color: rgba(106,167,255,.5);
  transform: translateY(-50%) scale(1.05);
  box-shadow: 0 0 15px rgba(106,167,255,.3);
}

.newChatBtn:active {
  transform: translateY(-50%) scale(0.95);
}

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
.chatMeta{
  margin-top:6px;
  font-size:12px;
  color:var(--muted);
  display:flex;
  gap:6px;
  align-items:center;
}

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
  width:38px;height:38px;border-radius:50%;
  display:grid;place-items:center;
  font-weight:900;
  border:1px solid rgba(255,255,255,.18);
  background: rgba(255,255,255,.06);
  overflow: hidden;
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

/* 主页模式 */
.main.home-mode {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 对话容器模式 - 保持grid布局 */
.chatContainer {
  display: contents;
}

.homePage {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--home-bg);
}

.publicChatsWrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.homeContent {
  max-width: 800px;
  width: 90%;
  text-align: center;
  animation: fadeIn 0.6s ease-out;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.homeLogo {
  margin-bottom: 40px;
}

.logoLarge {
  font-size: 72px;
  font-weight: 900;
  color: var(--text);
  margin-bottom: 12px;
  letter-spacing: 4px;
}

.logoText {
  font-size: 20px;
  color: var(--muted);
  font-weight: 600;
  letter-spacing: 2px;
}

.homeIntro {
  margin-bottom: 50px;
  color: var(--text);
}

.homeIntro h2 {
  font-size: 32px;
  font-weight: 800;
  margin-bottom: 16px;
  color: var(--text);
}

.homeIntro p {
  font-size: 16px;
  color: var(--muted);
  margin-bottom: 24px;
}

.featureList {
  list-style: none;
  padding: 0;
  margin: 0;
  text-align: left;
  display: inline-block;
}

.featureList li {
  font-size: 15px;
  color: var(--text);
  margin-bottom: 12px;
  padding: 8px 16px;
  background: rgba(255,255,255,0.03);
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.08);
  transition: all 0.3s ease;
}

.featureList li:hover {
  background: rgba(255,255,255,0.06);
  border-color: rgba(106,167,255,0.3);
  transform: translateX(5px);
}

.homeInput {
  max-width: 700px;
  margin: 0 auto;
  margin-right: 20px;
}

.homeInputRow {
  margin-bottom: 12px;
}

.homeInput {
  font-size: 16px;
  padding: 16px 50px 16px 16px;
  overflow-y: auto;
  line-height: 1.5;
  min-height: 76px;
  box-sizing: border-box;
}

.topbar{
  display:flex;
  align-items:center;
  justify-content:space-between;
  padding:16px 18px;
  border-bottom:1px solid var(--line);
  background: rgba(10,16,34,.45);
  backdrop-filter: blur(10px);
  gap: 16px;
}
.topicTitle .big {
  font-weight:900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 600px;
}
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
  max-width: 800px;
  width: fit-content;
  border-radius:18px;
  border:1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  padding:12px 14px;
  box-shadow: 0 10px 30px rgba(0,0,0,.18);
  word-wrap: break-word;
  overflow-wrap: break-word;
}
.msg.me .bubble{
  max-width: 500px;
  min-width: 100px;
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
.content p{ margin:0; line-height:1.55; font-size:14px; color: var(--text); word-wrap: break-word; overflow-wrap: break-word; }
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
  position: relative;
  z-index: 10;
}
.inputRow{
  max-width: 1000px;
  margin: 0 auto;
  display:flex;
  gap:10px;
  align-items:flex-end;
}
.inputRow.locked-hint {
  justify-content: center;
  padding: 20px;
  background: rgba(255, 107, 107, 0.08);
  border-radius: 14px;
  border: 1px solid rgba(255, 107, 107, 0.2);
}
.lock-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
  color: var(--muted);
}
.lock-icon {
  font-size: 20px;
}
.inputWrapper{
  flex:1;
  position:relative;
  display:flex;
  align-items:flex-end;
  gap:8px;
  overflow: visible;
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
  overflow-y: auto;
  overflow-x: hidden;
  line-height: 1.5;
  min-height: 57px;
  box-sizing: border-box;
}
.input:focus{ border-color: rgba(106,167,255,.35); }
.sendArrowBtn{
  position:absolute;
  right:24px;
  top: 50%;
  transform: translateY(-50%);
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
  max-width:1000px;
  margin: 10px auto 0;
  font-size:12px;
  color:var(--muted);
  display:flex;
  gap:8px;
  align-items:center;
}

.quote{
  max-width:1000px;
  margin: 0 auto 10px;
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
  gap: 12px;
  padding: 16px 12px;
  align-items: center;
}

.dot-bounce {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(106,167,255,.8), rgba(106,167,255,.6));
  box-shadow: 0 0 10px rgba(106,167,255,.4);
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

/* ========== 头像上传组件样式 ========== */
.avatarUploadContainer {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
}

.avatarPreview {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 2px dashed rgba(106,167,255,.40);
  background: rgba(255,255,255,.03);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  transition: all .18s ease;
}

.avatarPreview:hover {
  border-color: rgba(106,167,255,.60);
  background: rgba(106,167,255,.08);
}

.avatarPreview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatarPlaceholder {
  font-size: 36px;
  color: rgba(106,167,255,.60);
  font-weight: 300;
}

.avatarUploadHint {
  margin-top: 8px;
  font-size: 12px;
  color: var(--muted);
}

/* 个人资料头像上传容器 */
.profileAvatarContainer {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 20px;
  padding: 16px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.02);
}

.profileAvatarPreview {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 2px solid rgba(106,167,255,.40);
  background: rgba(255,255,255,.03);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  overflow: hidden;
  transition: all .18s ease;
}

.profileAvatarPreview:hover {
  border-color: rgba(106,167,255,.60);
  background: rgba(106,167,255,.08);
}

.profileAvatarPreview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.changeAvatarBtn {
  margin-top: 12px;
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid rgba(106,167,255,.30);
  background: rgba(106,167,255,.15);
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
}

.changeAvatarBtn:hover {
  background: rgba(106,167,255,.25);
  border-color: rgba(106,167,255,.45);
}

/* 用户头像图片样式 */
.userAvatarImage {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 50%;
}

/* ========== 账号管理左右分栏样式 ========== */
.accountManagementContainer {
  display: flex;
  gap: 24px;
  align-items: flex-start;
}

.accountLeftPanel,
.accountRightPanel {
  flex: 1;
  min-width: 0;
  padding: 20px;
  border-radius: 14px;
  border: 1px solid rgba(255,255,255,.08);
  background: rgba(255,255,255,.02);
}

.accountLeftPanel h3,
.accountRightPanel h3 {
  margin: 0 0 16px 0;
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
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

/* 用户信息显示 */
.userInfo {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 12px 0;
}

.userNameLabel {
  font-size: 14px;
  color: var(--muted);
}

.userName {
  font-size: 15px;
  font-weight: 700;
}

.userName.user {
  color: var(--text);
}

.userName.admin {
  color: #c77dff; /* 紫色 */
  text-shadow: 0 0 10px rgba(199, 125, 255, 0.3);
}

.userName.super_admin {
  background: linear-gradient(135deg, #ffc757 0%, #ffb347 50%, #ff9500 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 800;
  filter: drop-shadow(0 0 8px rgba(255, 199, 87, 0.5));
}

.userRoleBadge {
  font-size: 12px;
  color: var(--muted);
  font-weight: normal;
}

/* 退出登录按钮 */
.logoutBtn {
  padding: 12px 20px;
  border-radius: 12px;
  border: 1px solid rgba(255,102,102,.25);
  background: rgba(255,102,102,.15);
  color: #ff8888;
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
  width: 100%;
}

.logoutBtn:hover {
  filter: brightness(1.05);
  border-color: rgba(255,102,102,.45);
  background: rgba(255,102,102,.25);
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

/* 浅色模式下的退出登录按钮 */
:root[data-theme="light"] .logoutBtn {
  background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
  border-color: #e53935;
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(229, 57, 53, 0.3);
}

:root[data-theme="light"] .logoutBtn:hover {
  box-shadow: 0 4px 12px rgba(229, 57, 53, 0.4);
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

/* ========== 菜单和重命名相关样式 ========== */

/* 对话操作区域 */
.chatActions {
  position: relative;
  display: flex;
  align-items: center;
}

/* 三点菜单按钮 */
.moreBtn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.04);
  color: var(--muted);
  cursor: pointer;
  font-size: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .18s ease;
  position: relative;
}

.moreBtn:hover {
  background: rgba(255,255,255,.08);
  border-color: rgba(255,255,255,.20);
  color: var(--text);
}

.moreBtn.active {
  background: rgba(106,167,255,.15);
  border-color: rgba(106,167,255,.35);
  color: #6aa7ff;
  box-shadow: 0 0 0 3px rgba(106,167,255,.12);
}

/* 菜单下拉框 */
.menuDropdown {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 6px;
  min-width: 150px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.12);
  background: rgba(17,26,51,.98);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 24px rgba(0,0,0,.35);
  overflow: hidden;
  z-index: 1000;
  animation: menuIn .2s ease-out;
}

@keyframes menuIn {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 菜单项 */
.menuItem {
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: 13px;
  font-weight: 600;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all .15s ease;
}

.menuItem:hover {
  background: rgba(106,167,255,.10);
}

.menuItem.delete {
  color: #ff8888;
}

.menuItem.delete:hover {
  background: rgba(255,102,102,.12);
}

.menuItem.published {
  color: #51d18a;
}

.menuItem.published:hover {
  background: rgba(81,209,138,.12);
}

.menuItem.rejected {
  color: #ff8888;
}

.menuItem.rejected:hover {
  background: rgba(255,102,102,.12);
}

.menuItem.disabled {
  color: var(--muted);
  cursor: not-allowed;
  opacity: 0.6;
}

.menuItem.disabled:hover {
  background: transparent;
}

.menuIcon {
  font-size: 14px;
  width: 18px;
  text-align: center;
}

/* 重命名输入框 */
.chatTitleInput {
  width: 100%;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--text);
  font-size: inherit;
  font-weight: 900;
  outline: none;
  border-bottom: 2px solid rgba(106,167,255,.4);
  transition: border-color .18s ease;
}

.chatTitleInput:focus {
  border-bottom-color: rgba(106,167,255,.8);
}

.chatTitleInput::placeholder {
  color: rgba(255,255,255,.45);
}

/* 聊天主区域（适配新的操作按钮布局） */
.chatMain {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.chatItem {
  display: flex;
  align-items: center;
  gap: 8px;
}

.chatTitle {
  font-weight: 900;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

/* 浅色模式下的菜单 */
:root[data-theme="light"] .menuDropdown {
  background: rgba(255,255,255,.98);
  border-color: #e0e0e0;
  box-shadow: 0 8px 24px rgba(0,0,0,.15);
}

:root[data-theme="light"] .menuItem {
  color: #000000;
}

:root[data-theme="light"] .menuItem:hover {
  background: rgba(106,167,255,.12);
}

:root[data-theme="light"] .menuItem.delete {
  color: #e53935;
}

:root[data-theme="light"] .menuItem.delete:hover {
  background: rgba(229,57,53,.12);
}

:root[data-theme="light"] .moreBtn.active {
  background: rgba(106,167,255,.20);
  border-color: #6aa7ff;
  box-shadow: 0 0 0 3px rgba(106,167,255,.15);
}

:root[data-theme="light"] .chatTitleInput {
  color: #000000;
  border-bottom-color: rgba(106,167,255,.5);
}

:root[data-theme="light"] .chatTitleInput:focus {
  border-bottom-color: #6aa7ff;
}

:root[data-theme="light"] .chatTitleInput::placeholder {
  color: rgba(0,0,0,.45);
}

</style>
