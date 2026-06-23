<script setup>
import { onMounted } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useCurrentUser } from '@/composables/useCurrentUser'

const navItems = [
  { name: 'home',    label: '홈' },
  { name: 'map',       label: '지도' },
  { name: 'movies',    label: '영화' },
  { name: 'recommend', label: '추천' },
  { name: 'friends',   label: '친구' },
]

// 우상단 아바타용 공유 사용자 상태. 레이아웃 마운트(로그인 직후) 시 최신값 로드.
const { user, loadUser } = useCurrentUser()
onMounted(() => loadUser(true))

function initial(nickname) {
  return (nickname || '나').trim().charAt(0).toUpperCase()
}
</script>

<template>
  <div class="shell">
    <header class="nav">
      <RouterLink
        :to="{ name: 'home' }"
        class="brand"
      >
        무비무비
      </RouterLink>
      <nav class="links">
        <RouterLink
          v-for="item in navItems"
          :key="item.name"
          :to="{ name: item.name }"
          class="link"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
      <RouterLink
        :to="{ name: 'profile' }"
        class="avatar"
      >
        <img
          v-if="user?.profile_image_url"
          :src="user.profile_image_url"
          alt="내 프로필"
          class="avatar__img"
        >
        <span v-else>{{ initial(user?.nickname) }}</span>
      </RouterLink>
    </header>
    <main class="content">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; display: flex; flex-direction: column; }
.nav {
  display: flex; align-items: center; gap: 18px;
  padding: 12px 24px;
  background: var(--surface-2);
  border-bottom: 0.5px solid var(--border);
}
.brand { font-size: 16px; font-weight: 500; color: var(--gold); letter-spacing: 0.5px; }
.links { display: flex; gap: 16px; flex: 1; }
.link { font-size: 14px; color: var(--text-muted); transition: color 0.15s; }
.link:hover { color: var(--text); }
.link.router-link-exact-active { color: var(--gold); }
.avatar {
  width: 28px; height: 28px; border-radius: 50%;
  background: #2A2F3C; color: var(--text);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px;
  overflow: hidden;
}
.avatar__img { width: 100%; height: 100%; object-fit: cover; }
.content { flex: 1; }
</style>
