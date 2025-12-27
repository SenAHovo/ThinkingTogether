<template>
  <div class="public-chats-container">
    <!-- 列表视图 -->
    <div v-if="!viewingChat" class="list-view">
      <header class="list-header">
        <h2>已公开对话</h2>
        <button class="back-btn" @click="$emit('close')">返回</button>
      </header>

      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <div v-else-if="chats.length === 0" class="empty">暂无已公开对话</div>
      <div v-else class="chats-list">
        <div
          v-for="chat in chats"
          :key="chat.id"
          class="chat-card"
          @click="viewChatDetail(chat)"
        >
          <div class="chat-title" :title="chat.title">
            {{ truncateTitle(chat.title, 60) }}
          </div>
          <div class="chat-meta">
            <span class="author">{{ chat.username || '匿名' }}</span>
            <span>·</span>
            <span>{{ formatDate(chat.created_at) }}</span>
          </div>
          <div class="chat-preview">
            <div
              v-for="(msg, idx) in (chat.messages_preview || []).slice(0, 3)"
              :key="idx"
              class="preview-message"
            >
              <span class="msg-author">{{ msg.author_name }}:</span>
              <span class="msg-content">{{ truncateContent(msg.content, 80) }}</span>
            </div>
          </div>
          <div class="chat-stats">
            <span class="like-count">❤️ {{ chat.like_count || 0 }}</span>
            <span class="comment-count">💬 {{ chat.comment_count || 0 }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情视图 -->
    <div v-else class="detail-view">
      <header class="detail-header">
        <button class="back-btn" @click="backToList">← 返回列表</button>
        <div class="header-actions">
          <button
            class="action-btn"
            :class="{ liked: currentChat?.is_liked }"
            @click="toggleLike"
          >
            {{ currentChat?.is_liked ? '❤️ 已点赞' : '🤍 点赞' }} ({{ currentChat?.like_count || 0 }})
          </button>
          <button
            v-if="isAdmin && currentChat?.publication_status === 'published'"
            class="action-btn reject-btn"
            @click="rejectPublicChat"
            title="驳回此对话"
          >
            ❌ 驳回
          </button>
        </div>
      </header>

      <div v-if="currentChat" class="detail-content">
        <div class="detail-title">{{ currentChat.title }}</div>
        <div class="detail-info">
          <span>作者: {{ currentChat.username || '匿名' }}</span>
          <span>·</span>
          <span>发布于: {{ formatDate(currentChat.created_at) }}</span>
        </div>

        <div class="messages-container">
          <div
            v-for="(msg, idx) in currentChat.messages"
            :key="idx"
            class="full-message"
            :class="{ 'user-message': msg.author_id === 'user' }"
          >
            <div class="msg-header">
              <span class="msg-name">{{ msg.author_name }}</span>
              <span v-if="msg.role" class="msg-role">{{ msg.role }}</span>
            </div>
            <div class="msg-text">{{ msg.content }}</div>
          </div>
        </div>

        <!-- 评论区 -->
        <div class="comments-section">
          <h3>评论 ({{ comments.length }})</h3>

          <!-- 评论输入 -->
          <div v-if="currentUser" class="comment-input-area">
            <textarea
              v-model="newComment"
              placeholder="发表你的看法..."
              rows="5"
              @keydown.enter.exact.prevent="submitComment"
            />
            <button
              class="submit-comment-btn"
              :disabled="!newComment.trim() || submittingComment || checkingViolation"
              @click="submitComment"
            >
              {{ checkingViolation ? '检测中...' : (submittingComment ? '发表中...' : '发表评论') }}
            </button>
          </div>
          <div v-else class="login-hint">
            请先<a @click="$emit('show-login')">登录</a>后发表评论
          </div>

          <!-- 评论列表 -->
          <div v-if="comments.length === 0" class="no-comments">暂无评论</div>
          <div v-else class="comments-list">
            <div v-for="comment in comments" :key="comment.comment_id" class="comment-item">
              <div class="comment-header">
                <span class="comment-author">{{ comment.username }}</span>
                <span class="comment-time">{{ formatDate(comment.created_at) }}</span>
                <!-- 用户自己的删除按钮 -->
                <button
                  v-if="isCommentOwner(comment) && !comment.is_deleted"
                  class="comment-action-btn user-delete"
                  @click="confirmDeleteComment(comment)"
                  title="删除我的评论"
                >
                  🗑️ 删除
                </button>
                <!-- 管理员删除按钮 -->
                <button
                  v-if="isAdmin && !isCommentOwner(comment) && !comment.is_deleted"
                  class="comment-action-btn delete"
                  @click="confirmDeleteComment(comment)"
                  title="删除评论"
                >
                  🗑️ 删除
                </button>
                <!-- 管理员恢复按钮 -->
                <button
                  v-if="isAdmin && comment.is_deleted"
                  class="comment-action-btn restore"
                  @click="restoreComment(comment.comment_id)"
                  title="恢复评论"
                >
                  ♻️ 恢复
                </button>
              </div>
              <div v-if="comment.is_deleted" class="comment-content deleted">
                该评论已被管理员删除
                <span v-if="comment.delete_reason" class="delete-reason">
                  （原因：{{ comment.delete_reason }}）
                </span>
              </div>
              <div v-else class="comment-content">{{ comment.content }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 删除评论确认弹窗 -->
    <div v-if="showDeleteConfirm" class="modal-overlay" @click.self="showDeleteConfirm = false">
      <div class="modal">
        <div class="modal-header">
          <h3>删除评论</h3>
          <button class="close-btn" @click="showDeleteConfirm = false">×</button>
        </div>
        <div class="modal-body">
          <div v-if="commentToDelete" class="comment-preview">
            <p><strong>评论内容：</strong></p>
            <p>{{ commentToDelete.content }}</p>
          </div>
          <div class="form-group">
            <label>删除原因（可选）：</label>
            <textarea
              v-model="deleteReason"
              class="form-textarea"
              rows="3"
              placeholder="请输入删除原因..."
            ></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="secondary-btn" @click="showDeleteConfirm = false">取消</button>
          <button class="primary-btn danger" @click="executeDeleteComment">确认删除</button>
        </div>
      </div>
    </div>

    <!-- 违规词提示弹窗 -->
    <div v-if="showViolationModal && violationResult" class="modal-overlay" @click.self="closeViolationModal">
      <div class="modal violation-modal">
        <div class="modal-header">
          <h3>⚠️ 检测到违规内容</h3>
          <button class="close-btn" @click="closeViolationModal">×</button>
        </div>
        <div class="modal-body">
          <p class="violation-message">您的评论包含以下违规词，请修改后重试：</p>

          <div class="violation-content-preview">
            <div v-html="getHighlightedContent(newComment, violationResult.violations)"></div>
          </div>

          <div class="violation-list">
            <h4>违规详情：</h4>
            <div v-for="(v, index) in violationResult.violations" :key="index" class="violation-item">
              <span class="violation-word">"{{ v.word }}"</span>
              <span class="violation-info">（分类：{{ v.category }}，位置：第{{ v.start + 1 }}-{{ v.end }}字）</span>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="primary-btn" @click="closeViolationModal">我知道了，去修改</button>
        </div>
      </div>
    </div>

    <!-- 驳回对话确认模态框 -->
    <div v-if="showRejectModal" class="modal-overlay" @click.self="cancelRejectChat">
      <div class="modal">
        <div class="modal-header">
          <h3>驳回对话</h3>
        </div>
        <div class="modal-body">
          <p>确认要驳回对话《{{ currentChat?.title }}》吗？</p>
          <p class="hint-text">驳回后，该对话将从公开对话大厅移除。</p>
          <textarea
            v-model="rejectReason"
            class="reason-textarea"
            placeholder="请输入驳回原因（可选）"
            rows="3"
          ></textarea>
        </div>
        <div class="modal-footer">
          <button class="secondary-btn" @click="cancelRejectChat">取消</button>
          <button class="danger-btn" @click="confirmRejectChat">确认驳回</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { apiClient } from './api.js';

const props = defineProps({
  currentUser: {
    type: Object,
    default: null
  }
});

const emit = defineEmits(['close', 'show-login']);

// 状态管理
const chats = ref([]);
const loading = ref(true);
const error = ref(null);
const viewingChat = ref(false);
const currentChat = ref(null);
const comments = ref([]);
const newComment = ref('');
const submittingComment = ref(false);
const dataLoaded = ref(false); // 标记数据是否已加载

// 评论删除相关
const commentToDelete = ref(null);
const showDeleteConfirm = ref(false);
const deleteReason = ref('');

// 违规词检测相关
const checkingViolation = ref(false);
const showViolationModal = ref(false);
const violationResult = ref(null);

// ========== 计算属性 ==========

// 判断当前用户是否为管理员
const isAdmin = computed(() => {
  return props.currentUser &&
    (props.currentUser.role === 'admin' || props.currentUser.role === 'super_admin');
});

// 驳回相关状态
const showRejectModal = ref(false);
const rejectReason = ref('');

// 判断当前用户是否为评论作者
function isCommentOwner(comment) {
  if (!props.currentUser || !comment) return false;
  return comment.user_id === props.currentUser.user_id;
}

// ========== 工具函数 ==========

/**
 * 截断标题
 */
function truncateTitle(title, maxLength = 60) {
  if (!title) return '';
  if (title.length <= maxLength) return title;
  return title.substring(0, maxLength) + '...';
}

/**
 * 截断内容
 */
function truncateContent(content, maxLength = 80) {
  if (!content) return '';
  if (content.length <= maxLength) return content;
  return content.substring(0, maxLength) + '...';
}

/**
 * 格式化日期
 */
function formatDate(dateStr) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diff = now - date;

  // 小于1分钟
  if (diff < 60000) {
    return '刚刚';
  }
  // 小于1小时
  if (diff < 3600000) {
    return `${Math.floor(diff / 60000)}分钟前`;
  }
  // 小于24小时
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`;
  }
  // 小于30天
  if (diff < 2592000000) {
    return `${Math.floor(diff / 86400000)}天前`;
  }
  // 超过30天显示具体日期
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${m}/${d}`;
}

// ========== 数据加载 ==========

/**
 * 加载已公开对话列表
 */
async function loadPublicChats() {
  console.log('[PublicChats] loadPublicChats called', {
    dataLoaded: dataLoaded.value,
    chatsLength: chats.value.length,
    viewingChat: viewingChat.value
  });

  // 如果数据已加载且有数据，则跳过
  if (dataLoaded.value && chats.value.length > 0) {
    console.log('[PublicChats] Data already loaded, skipping API call');
    loading.value = false;
    return;
  }

  console.log('[PublicChats] Starting data load...');
  loading.value = true;
  error.value = null;
  try {
    console.log('[PublicChats] Calling apiClient.getPublicChatHall(50)...');
    const result = await apiClient.getPublicChatHall(50);
    console.log('[PublicChats] API result received:', result);
    chats.value = result.chats || [];
    dataLoaded.value = true;
    console.log('[PublicChats] Chats loaded successfully:', chats.value.length);
  } catch (err) {
    console.error('[PublicChats] 加载公开对话失败:', err);
    error.value = '加载失败，请稍后重试';
    dataLoaded.value = false; // 加载失败，允许重试
  } finally {
    loading.value = false;
    console.log('[PublicChats] Loading complete, loading=', loading.value);
  }
}

/**
 * 强制刷新已公开对话列表
 */
async function refreshPublicChats() {
  dataLoaded.value = false;
  await loadPublicChats();
}

/**
 * 查看对话详情
 */
async function viewChatDetail(chat) {
  console.log('[PublicChats] Viewing chat detail:', chat.id, chat.title);
  viewingChat.value = true;
  currentChat.value = chat;

  // 加载完整对话消息
  try {
    console.log('[PublicChats] Loading messages for chat:', chat.id);
    const result = await apiClient.getMessages(chat.id, 1000);
    console.log('[PublicChats] Messages loaded:', result.messages?.length);
    currentChat.value = {
      ...chat,
      messages: result.messages || []
    };
  } catch (err) {
    console.error('[PublicChats] 加载对话详情失败:', err);
  }

  // 加载评论
  await loadComments(chat.id);
}

/**
 * 返回列表
 */
function backToList() {
  console.log('[PublicChats] Returning to list view');
  viewingChat.value = false;
  currentChat.value = null;
  comments.value = [];
  newComment.value = '';
  loading.value = false;
}

/**
 * 加载评论列表
 */
async function loadComments(threadId) {
  try {
    const result = await apiClient.getThreadComments(threadId);
    comments.value = result.comments || [];
  } catch (err) {
    console.error('加载评论失败:', err);
    comments.value = [];
  }
}

/**
 * 切换点赞状态
 */
async function toggleLike() {
  if (!props.currentUser) {
    emit('show-login');
    return;
  }

  try {
    if (currentChat.value.is_liked) {
      await apiClient.unlikeChat(currentChat.value.id);
      currentChat.value.is_liked = false;
      currentChat.value.like_count = Math.max(0, (currentChat.value.like_count || 1) - 1);
    } else {
      await apiClient.likeChat(currentChat.value.id);
      currentChat.value.is_liked = true;
      currentChat.value.like_count = (currentChat.value.like_count || 0) + 1;
    }
  } catch (err) {
    console.error('点赞操作失败:', err);
    alert('操作失败: ' + err.message);
  }
}

/**
 * 发表评论
 */
async function submitComment() {
  if (!newComment.value.trim() || submittingComment.value || checkingViolation.value) return;

  const content = newComment.value.trim();

  // 先检测违禁词
  checkingViolation.value = true;
  try {
    const checkResult = await apiClient.checkViolation(content);

    if (checkResult.has_violation && checkResult.violations.length > 0) {
      // 有违规词，显示提示
      violationResult.value = checkResult;
      showViolationModal.value = true;
      checkingViolation.value = false;
      return;
    }

    // 无违规词，继续发表
    submittingComment.value = true;
    try {
      await apiClient.addComment(currentChat.value.id, content);
      // 重新加载评论列表
      await loadComments(currentChat.value.id);
      // 更新评论数
      currentChat.value.comment_count = (currentChat.value.comment_count || 0) + 1;
      // 清空输入框
      newComment.value = '';
    } catch (err) {
      console.error('发表评论失败:', err);
      alert('发表失败: ' + err.message);
    } finally {
      submittingComment.value = false;
    }

  } catch (err) {
    console.error('检测失败:', err);
    // 检测失败时仍然允许发表
    submittingComment.value = true;
    try {
      await apiClient.addComment(currentChat.value.id, content);
      await loadComments(currentChat.value.id);
      currentChat.value.comment_count = (currentChat.value.comment_count || 0) + 1;
      newComment.value = '';
    } catch (err2) {
      console.error('发表评论失败:', err2);
      alert('发表失败: ' + err2.message);
    } finally {
      submittingComment.value = false;
    }
  } finally {
    checkingViolation.value = false;
  }
}

/**
 * 获取高亮后的评论内容
 */
function getHighlightedContent(content, violations) {
  if (!violations || violations.length === 0) return content;

  let result = content;

  // 从后往前替换（避免索引变化）
  const sortedViolations = [...violations].sort((a, b) => b.start - a.start);

  sortedViolations.forEach(v => {
    const before = result.substring(0, v.start);
    const violation = result.substring(v.start, v.end);
    const after = result.substring(v.end);

    result = before +
             `<span class="violation-highlight" title="分类: ${v.category}">${violation}</span>` +
             after;
  });

  return result;
}

/**
 * 关闭违规提示并允许编辑
 */
function closeViolationModal() {
  showViolationModal.value = false;
  violationResult.value = null;
}

/**
 * 确认删除评论
 */
function confirmDeleteComment(comment) {
  commentToDelete.value = comment;
  showDeleteConfirm.value = true;
  deleteReason.value = '';
}

/**
 * 执行删除评论
 */
async function executeDeleteComment() {
  if (!commentToDelete.value) return;

  try {
    await apiClient.deleteComment(
      commentToDelete.value.comment_id,
      deleteReason.value
    );
    showDeleteConfirm.value = false;
    commentToDelete.value = null;
    deleteReason.value = '';
    // 重新加载评论列表
    await loadComments(currentChat.value.id);
  } catch (err) {
    console.error('删除评论失败:', err);
    alert('删除失败: ' + err.message);
  }
}

/**
 * 恢复评论
 */
async function restoreComment(commentId) {
  if (!confirm('确认恢复这条评论吗？')) return;

  try {
    await apiClient.restoreComment(commentId);
    // 重新加载评论列表
    await loadComments(currentChat.value.id);
  } catch (err) {
    console.error('恢复评论失败:', err);
    alert('恢复失败: ' + err.message);
  }
}

// ========== 驳回对话功能 ==========

function rejectPublicChat() {
  if (!currentChat.value) return;
  showRejectModal.value = true;
  rejectReason.value = '';
}

async function confirmRejectChat() {
  if (!currentChat.value) return;

  try {
    await apiClient.reviewPublicationRequest(
      currentChat.value.id,
      false,
      rejectReason.value
    );

    showRejectModal.value = false;
    rejectReason.value = '';
    alert('✅ 已驳回该对话');

    // 返回列表并刷新
    backToList();
  } catch (err) {
    console.error('驳回失败:', err);
    alert('驳回失败: ' + err.message);
  }
}

function cancelRejectChat() {
  showRejectModal.value = false;
  rejectReason.value = '';
}

// ========== 初始化 ==========

onMounted(() => {
  console.log('[PublicChats] Component mounted');
  loadPublicChats();
});
</script>

<style scoped>
.public-chats-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ========== 列表视图 ========== */
.list-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--line);
  background: rgba(10, 16, 34, 0.45);
  backdrop-filter: blur(10px);
}

.list-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 800;
  color: var(--text);
}

.back-btn {
  padding: 8px 16px;
  border-radius: 10px;
  border: 1px solid rgba(106, 167, 255, 0.3);
  background: rgba(106, 167, 255, 0.15);
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.back-btn:hover {
  background: rgba(106, 167, 255, 0.25);
  border-color: rgba(106, 167, 255, 0.5);
}

.loading, .error, .empty {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  font-size: 16px;
  color: var(--muted);
}

.error {
  color: #ff6b6b;
}

.chats-list {
  flex: 1;
  overflow-y: auto;
  padding: 20px 24px;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 20px;
  max-height: calc(100vh - 200px);
}

/* 卡片样式 */
.chat-card {
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(106, 167, 255, 0.2);
  background: rgba(106, 167, 255, 0.08);
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 280px;
  min-height: 280px;
  max-height: 280px;
}

.chat-card:hover {
  background: rgba(106, 167, 255, 0.15);
  border-color: rgba(106, 167, 255, 0.4);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(106, 167, 255, 0.2);
}

.chat-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  flex-shrink: 0;
  max-height: 45px;
}

.chat-meta {
  display: flex;
  gap: 8px;
  align-items: center;
  font-size: 12px;
  color: var(--muted);
  flex-shrink: 0;
}

.author {
  color: var(--primary);
  font-weight: 600;
}

.chat-preview {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.15);
  flex: 1;
  overflow: hidden;
}

.preview-message {
  font-size: 12px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 1;
  -webkit-box-orient: vertical;
}

.msg-author {
  color: var(--muted);
  font-weight: 600;
  margin-right: 6px;
}

.msg-content {
  color: var(--text);
}

.chat-stats {
  display: flex;
  gap: 16px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
  margin-top: auto;
}

.like-count, .comment-count {
  font-size: 14px;
  color: var(--text);
  font-weight: 600;
}

/* ========== 详情视图 ========== */
.detail-view {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--line);
  background: rgba(10, 16, 34, 0.45);
  backdrop-filter: blur(10px);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.action-btn {
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid rgba(255, 107, 107, 0.3);
  background: rgba(255, 107, 107, 0.15);
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.action-btn:hover {
  background: rgba(255, 107, 107, 0.25);
  border-color: rgba(255, 107, 107, 0.5);
}

.action-btn.liked {
  background: rgba(255, 107, 107, 0.3);
  border-color: rgba(255, 107, 107, 0.5);
}

.action-btn.reject-btn {
  border-color: rgba(255, 87, 87, 0.4);
  background: rgba(255, 87, 87, 0.1);
  color: #ff5757;
}

.action-btn.reject-btn:hover {
  background: rgba(255, 87, 87, 0.2);
  border-color: rgba(255, 87, 87, 0.6);
}

.detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.detail-title {
  font-size: 28px;
  font-weight: 800;
  color: var(--text);
  line-height: 1.4;
}

.detail-info {
  display: flex;
  gap: 8px;
  font-size: 14px;
  color: var(--muted);
}

.messages-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.full-message {
  padding: 16px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.03);
}

.full-message.user-message {
  background: rgba(106, 167, 255, 0.08);
  border-color: rgba(106, 167, 255, 0.2);
}

.msg-header {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 8px;
}

.msg-name {
  font-weight: 700;
  font-size: 14px;
  color: var(--text);
}

.msg-role {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--muted);
}

.msg-text {
  color: var(--text);
  line-height: 1.6;
  font-size: 15px;
  white-space: pre-wrap;
  word-wrap: break-word;
}

/* ========== 评论区 ========== */
.comments-section {
  padding-top: 24px;
  border-top: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.comments-section h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
}

.comment-input-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.comment-input-area textarea {
  width: 100%;
  padding: 14px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text);
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  outline: none;
  transition: all 0.18s ease;
  min-height: 100px;
  max-height: 300px;
  line-height: 1.6;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.comment-input-area textarea:focus {
  border-color: rgba(106, 167, 255, 0.45);
  background: rgba(106, 167, 255, 0.08);
  box-shadow: 0 0 0 3px rgba(106, 167, 255, 0.12);
}

.submit-comment-btn {
  align-self: flex-end;
  padding: 10px 24px;
  border-radius: 10px;
  border: 1px solid rgba(106, 167, 255, 0.35);
  background: rgba(106, 167, 255, 0.2);
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
  transition: all 0.18s ease;
}

.submit-comment-btn:hover:not(:disabled) {
  background: rgba(106, 167, 255, 0.3);
  border-color: rgba(106, 167, 255, 0.5);
}

.submit-comment-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.login-hint {
  padding: 16px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}

.login-hint a {
  color: var(--primary);
  cursor: pointer;
  font-weight: 700;
  text-decoration: underline;
}

.no-comments {
  padding: 40px;
  text-align: center;
  color: var(--muted);
  font-size: 14px;
}

.comments-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.comment-item {
  padding: 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  min-height: auto;
  word-wrap: break-word;
  overflow-wrap: break-word;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.comment-author {
  font-weight: 700;
  font-size: 14px;
  color: var(--text);
}

.comment-time {
  font-size: 12px;
  color: var(--muted);
}

.comment-content {
  color: var(--text);
  line-height: 1.8;
  font-size: 14px;
  white-space: pre-wrap;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  max-width: 100%;
}

/* ========== 滚动条样式 ========== */
.chats-list::-webkit-scrollbar,
.detail-content::-webkit-scrollbar {
  width: 10px;
}

.chats-list::-webkit-scrollbar-track,
.detail-content::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 10px;
}

.chats-list::-webkit-scrollbar-thumb,
.detail-content::-webkit-scrollbar-thumb {
  background-color: rgba(106, 167, 255, 0.4);
  border-radius: 10px;
  border: 2px solid transparent;
  background-clip: content-box;
}

.chats-list::-webkit-scrollbar-thumb:hover,
.detail-content::-webkit-scrollbar-thumb:hover {
  background-color: rgba(106, 167, 255, 0.6);
  background-clip: content-box;
}

/* ========== 浅色模式 ========== */
:root[data-theme="light"] .chat-card {
  background: linear-gradient(135deg, #e3f2fd 0%, #f0f4ff 100%);
  border-color: #6aa7ff;
  box-shadow: 0 2px 8px rgba(106, 167, 255, 0.15);
}

:root[data-theme="light"] .chat-card:hover {
  background: linear-gradient(135deg, #f0f4ff 0%, #e3f2fd 100%);
  box-shadow: 0 8px 24px rgba(106, 167, 255, 0.3);
}

:root[data-theme="light"] .list-header,
:root[data-theme="light"] .detail-header {
  background: linear-gradient(180deg, #ffffff 0%, #f8f9fa 100%);
  border-bottom-color: #e0e0e0;
}

:root[data-theme="light"] .action-btn {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border-color: #e91e63;
  color: #ffffff;
}

:root[data-theme="light"] .full-message {
  background: #ffffff;
  border-color: #e0e0e0;
}

:root[data-theme="light"] .full-message.user-message {
  background: linear-gradient(135deg, #e3f2fd 0%, #f0f4ff 100%);
  border-color: #6aa7ff;
}

:root[data-theme="light"] .comment-input-area textarea {
  background: #ffffff;
  border-color: #bdbdbd;
  color: #000000;
}

:root[data-theme="light"] .comment-item {
  background: #ffffff;
  border-color: #e0e0e0;
}

:root[data-theme="light"] .chats-list::-webkit-scrollbar-track {
  background: #f0f0f0;
}

:root[data-theme="light"] .chats-list::-webkit-scrollbar-thumb {
  background-color: #6aa7ff;
  border: 2px solid #f0f0f0;
  background-clip: content-box;
}

:root[data-theme="light"] .chats-list::-webkit-scrollbar-thumb:hover {
  background-color: #4a8eff;
  background-clip: content-box;
}

/* ========== 管理员功能样式 ========== */

/* 评论操作按钮 */
.comment-action-btn {
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all .18s ease;
  margin-left: auto;
}

.comment-action-btn:hover {
  background: rgba(255,255,255,.10);
  border-color: rgba(255,255,255,.20);
}

.comment-action-btn.delete {
  border-color: rgba(255,107,107,.30);
  background: rgba(255,107,107,.1);
  color: #ff6b6b;
}

.comment-action-btn.delete:hover {
  background: rgba(255,107,107,.2);
  border-color: rgba(255,107,107,.50);
}

.comment-action-btn.restore {
  border-color: rgba(74,222,128,.30);
  background: rgba(74,222,128,.1);
  color: #4ade80;
}

.comment-action-btn.restore:hover {
  background: rgba(74,222,128,.2);
  border-color: rgba(74,222,128,.50);
}

.comment-action-btn.user-delete {
  border-color: rgba(251,191,36,.30);
  background: rgba(251,191,36,.1);
  color: #fbbf24;
}

.comment-action-btn.user-delete:hover {
  background: rgba(251,191,36,.2);
  border-color: rgba(251,191,36,.50);
}

/* 已删除评论样式 */
.comment-content.deleted {
  color: var(--muted);
  font-style: italic;
  opacity: 0.7;
}

.delete-reason {
  color: #ff6b6b;
  font-size: 13px;
}

/* 违规词高亮样式 */
.violation-highlight {
  text-decoration: underline wavy #ff4444;
  background: rgba(255, 68, 68, 0.1);
  padding: 0 2px;
  border-radius: 2px;
  font-weight: 500;
}

/* 弹窗样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.modal {
  background: var(--home-bg);
  border-radius: 16px;
  border: 1px solid rgba(255,255,255,.10);
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid var(--line);
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.close-btn {
  background: none;
  border: none;
  color: var(--muted);
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all .18s ease;
}

.close-btn:hover {
  background: rgba(255,255,255,.1);
  color: var(--text);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.modal-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 24px;
  border-top: 1px solid var(--line);
}

.hint-text {
  font-size: 13px;
  color: var(--muted);
  margin-top: 4px;
}

.reason-textarea {
  width: 100%;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  outline: none;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  min-height: 80px;
  margin-top: 12px;
}

.reason-textarea:focus {
  border-color: rgba(255, 87, 87, 0.5);
  background: rgba(255,255,255,.08);
}

.danger-btn {
  padding: 10px 20px;
  border-radius: 10px;
  border: none;
  background: linear-gradient(135deg, #f5576c 0%, #f093fb 100%);
  color: #ffffff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.danger-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(245, 87, 108, 0.4);
}

.secondary-btn {
  padding: 10px 20px;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.2);
  background: rgba(255,255,255,0.05);
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.secondary-btn:hover {
  background: rgba(255,255,255,0.1);
  border-color: rgba(255,255,255,0.3);
}

.comment-preview {
  padding: 12px;
  border-radius: 8px;
  background: rgba(255,255,255,.05);
  margin-bottom: 16px;
}

.comment-preview p {
  margin: 4px 0;
  color: var(--text);
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  margin-bottom: 8px;
  color: var(--text);
  font-weight: 600;
  font-size: 14px;
}

.form-textarea {
  width: 100%;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.05);
  color: var(--text);
  outline: none;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  min-height: 80px;
}

.form-textarea:focus {
  border-color: rgba(106,167,255,.40);
  background: rgba(106,167,255,.08);
}

.secondary-btn,
.primary-btn {
  padding: 10px 18px;
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,.10);
  background: rgba(255,255,255,.08);
  color: var(--text);
  font-weight: 700;
  cursor: pointer;
  transition: all .18s ease;
}

.primary-btn {
  background: rgba(106,167,255,.2);
  border-color: rgba(106,167,255,.30);
}

.primary-btn:hover {
  background: rgba(106,167,255,.3);
  border-color: rgba(106,167,255,.50);
}

.primary-btn.danger {
  background: rgba(255,107,107,.2);
  border-color: rgba(255,107,107,.30);
  color: #ff6b6b;
}

.primary-btn.danger:hover {
  background: rgba(255,107,107,.3);
  border-color: rgba(255,107,107,.50);
}

.secondary-btn:hover {
  background: rgba(255,255,255,.15);
}

/* 浅色模式适配 */
:root[data-theme="light"] .modal {
  background: #ffffff;
  border-color: #e0e0e0;
}

:root[data-theme="light"] .comment-preview {
  background: #f5f5f5;
}

:root[data-theme="light"] .form-textarea {
  background: #ffffff;
  border-color: #bdbdbd;
  color: #000000;
}

:root[data-theme="light"] .secondary-btn {
  background: #ffffff;
  border-color: #e0e0e0;
}

:root[data-theme="light"] .primary-btn {
  background: rgba(106,167,255,.3);
  border-color: #6aa7ff;
}

:root[data-theme="light"] .primary-btn.danger {
  background: rgba(255,107,107,.2);
  border-color: #ff6b6b;
}

/* 违规提示弹窗样式 */
.violation-modal {
  max-width: 600px;
}

.violation-modal .modal-header h3 {
  color: #ff6b6b;
}

.violation-message {
  font-size: 16px;
  color: var(--text);
  margin-bottom: 15px;
}

.violation-content-preview {
  background: rgba(255, 68, 68, 0.05);
  border: 1px solid rgba(255, 68, 68, 0.2);
  border-radius: 8px;
  padding: 15px;
  margin-bottom: 20px;
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.violation-list {
  background: rgba(255, 255, 255, 0.03);
  border-radius: 8px;
  padding: 15px;
}

.violation-list h4 {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: var(--muted);
}

.violation-item {
  margin-bottom: 8px;
  font-size: 14px;
  line-height: 1.5;
}

.violation-word {
  color: #ff6b6b;
  font-weight: 600;
}

.violation-info {
  color: var(--muted);
  margin-left: 5px;
}

:root[data-theme="light"] .violation-content-preview {
  background: rgba(255, 68, 68, 0.08);
  border-color: rgba(255, 68, 68, 0.3);
}

:root[data-theme="light"] .violation-list {
  background: rgba(0, 0, 0, 0.03);
}

:root[data-theme="light"] .violation-word {
  color: #d32f2f;
}

:root[data-theme="light"] .violation-info {
  color: #666;
}
</style>
