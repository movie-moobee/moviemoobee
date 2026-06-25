<script setup>
import { computed, onMounted } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'
import { useCurrentUser } from '@/composables/useCurrentUser'
import NotificationBell from '@/components/NotificationBell.vue'

const navItems = [
  { name: 'home',      label: '홈' },
  { name: 'map',       label: '지도' },
  { name: 'movies',    label: '영화' },
  { name: 'recommend', label: '추천' },
  { name: 'friends',   label: '친구' },
]

// 우상단 아바타용 공유 사용자 상태. 레이아웃 마운트(로그인 직후) 시 최신값 로드.
const { user, loadUser } = useCurrentUser()
onMounted(() => loadUser(true))

// 현재 라우트 이름으로 활성 탭 판정(상세/하위 화면도 상위 탭에 매핑).
const route = useRoute()
const ACTIVE_MAP = { 'movie-detail': 'movies', 'friend-compare': 'friends', records: 'map' }
const activeName = computed(() => ACTIVE_MAP[route.name] || route.name)

function initial(nickname) {
  return (nickname || '나').trim().charAt(0).toUpperCase()
}
</script>

<template>
  <div class="flex min-h-screen flex-col bg-ink font-sans text-fg antialiased">
    <!-- ───────── NAV ───────── -->
    <header class="sticky top-0 z-40 border-b border-line bg-ink/70 backdrop-blur-xl">
      <div class="mx-auto flex h-[64px] max-w-[1500px] items-center gap-8 px-6 lg:px-10">
        <!-- brand -->
        <RouterLink
          :to="{ name: 'home' }"
          class="group flex items-center gap-2.5"
        >
          <span class="relative grid h-8 w-8 place-items-center overflow-hidden rounded-md border border-line bg-ink-700">
            <img
              src="/moobee.png"
              alt="무비무비"
              class="h-full w-full object-cover"
            >
          </span>
          <span class="font-display text-[17px] font-semibold tracking-tightest">무비무비</span>
        </RouterLink>

        <!-- center nav -->
        <nav class="hidden flex-1 items-center justify-center gap-1 md:flex">
          <RouterLink
            v-for="item in navItems"
            :key="item.name"
            :to="{ name: item.name }"
            class="rounded-full px-3.5 py-1.5 text-[13.5px] font-medium transition"
            :class="activeName === item.name
              ? 'text-fg bg-white/[0.04] border border-line'
              : 'text-fg-muted hover:text-fg'"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <!-- actions -->
        <div class="ml-auto flex items-center gap-2 md:ml-0">
          <RouterLink
            :to="{ name: 'movies' }"
            class="grid h-9 w-9 place-items-center rounded-full border border-line text-fg-muted transition hover:border-lineHover hover:text-fg"
            aria-label="영화 검색"
          >
            <svg
              viewBox="0 0 24 24"
              class="h-[18px] w-[18px]"
              fill="none"
              stroke="currentColor"
              stroke-width="1.8"
            ><circle
              cx="11"
              cy="11"
              r="7"
            /><path
              d="m20 20-3.2-3.2"
              stroke-linecap="round"
            /></svg>
          </RouterLink>

          <NotificationBell />

          <RouterLink
            :to="{ name: 'profile' }"
            class="grid h-9 w-9 place-items-center overflow-hidden rounded-full border border-line bg-gradient-to-br from-ink-600 to-ink-800 text-[12px] font-semibold text-fg-muted transition hover:border-lineHover"
          >
            <img
              v-if="user?.profile_image_url"
              :src="user.profile_image_url"
              alt="내 프로필"
              class="h-full w-full object-cover"
            >
            <span v-else>{{ initial(user?.nickname) }}</span>
          </RouterLink>
        </div>
      </div>
    </header>

    <main class="flex-1">
      <RouterView />
    </main>

    <!-- ───────── FOOTER ───────── -->
    <footer class="border-t border-line">
      <div class="mx-auto flex max-w-[1500px] flex-wrap items-center justify-between gap-3 px-6 py-7 lg:px-10">
        <span class="font-sans text-[11px] tracking-[0.04em] text-fg-muted">무비무비 — 취향을 별자리로</span>
        <span class="font-mono text-[11px] text-fg-faint">© 2026</span>
      </div>
    </footer>
  </div>
</template>
