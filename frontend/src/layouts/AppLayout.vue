<script setup>
import { RouterLink, RouterView } from 'vue-router'

const navItems = [
  { name: 'home',    label: '홈' },
  { name: 'map',     label: '지도' },
  { name: 'movies',  label: '영화' },
  { name: 'records', label: '기록' },
  { name: 'friends', label: '친구' },
]
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
        나
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
}
.content { flex: 1; }
</style>
