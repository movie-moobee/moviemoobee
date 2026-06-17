<script setup>
// 내 프로필 (F-AUTH-03 로그아웃만 구현 · 04 프로필수정/05 계정삭제는 TODO)
import { ref } from "vue";
import { useRouter } from "vue-router";
import { logout } from "@/api/auth";

const router = useRouter();
const loggingOut = ref(false);

async function onLogout() {
  loggingOut.value = true;
  try {
    await logout();
  } finally {
    router.push("/login");
  }
}
</script>

<template>
  <section class="profile">
    <h1>내 프로필</h1>
    <!-- TODO: 프로필 수정(F-AUTH-04) · 계정 삭제(F-AUTH-05) -->
    <button
      class="logout"
      type="button"
      :disabled="loggingOut"
      @click="onLogout"
    >
      {{ loggingOut ? "로그아웃 중…" : "로그아웃" }}
    </button>
  </section>
</template>

<style scoped>
.profile {
  padding: 24px;
}
.logout {
  margin-top: 16px;
  padding: 10px 18px;
  background: transparent;
  color: var(--text);
  border: 0.5px solid var(--border-hover);
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 14px;
  cursor: pointer;
}
.logout:hover:not(:disabled) {
  background: var(--surface-2);
}
.logout:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
