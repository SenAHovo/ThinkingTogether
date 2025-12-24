<template>
  <App v-if="currentView === 'app'" @switch-to-admin="switchToAdmin" />
  <Admin v-else @back="goBack" />
</template>

<script setup>
import { ref, onMounted } from 'vue';
import App from './App.vue';
import Admin from './Admin.vue';

const currentView = ref('app');

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
  currentView.value = 'admin';
  window.location.hash = 'admin';
}

function goBack() {
  currentView.value = 'app';
  window.location.hash = '';
}
</script>
