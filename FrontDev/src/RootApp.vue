<template>
  <App v-if="currentView === 'app'" @switch-to-admin="switchToAdmin" />
  <Admin v-else :currentUser="currentUser" @back="goBack" />
</template>

<script setup>
import { ref, onMounted } from 'vue';
import App from './App.vue';
import Admin from './Admin.vue';
import { getUser } from './api.js';

const currentView = ref('app');
const currentUser = ref(getUser()); // 获取当前登录用户信息

onMounted(() => {
  const hash = window.location.hash.slice(1);
  if (hash === 'admin') {
    currentView.value = 'admin';
  }

  window.addEventListener('hashchange', () => {
    const newHash = window.location.hash.slice(1);
    currentView.value = newHash === 'admin' ? 'admin' : 'app';
  });
});

function switchToAdmin() {
  // 更新当前用户信息
  currentUser.value = getUser();

  // 检查用户权限
  if (!currentUser.value) {
    alert('请先登录');
    return;
  }

  const role = currentUser.value.role || 'user';
  if (role === 'guest' || role === 'user') {
    alert('您没有权限访问管理后台');
    return;
  }

  // 管理员和超级管理员可以进入
  currentView.value = 'admin';
  window.location.hash = 'admin';
}

function goBack() {
  currentView.value = 'app';
  window.location.hash = '';
}
</script>
