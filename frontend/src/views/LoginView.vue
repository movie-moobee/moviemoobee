<script setup>
// 로그인 (F-AUTH-02)
import { ref } from "vue";
import { useRouter } from "vue-router";
import { login } from "@/api/auth";

const router = useRouter();
const email = ref("");
const password = ref("");
const error = ref("");
const loading = ref(false);

async function onSubmit() {
  error.value = "";
  loading.value = true;
  try {
    await login(email.value, password.value);
    router.push("/");
  } catch (e) {
    error.value =
      e.response?.data?.non_field_errors?.[0] ||
      "로그인에 실패했습니다. 이메일과 비밀번호를 확인하세요.";
  } finally {
    loading.value = false;
  }
}
</script>

<template>
  <div class="auth-split">
    <!-- 좌: 시네마 히어로 -->
    <aside class="hero">
      <div class="hero__logo">
        MOVIE MOOBEE
      </div>
      <div class="hero__copy">
        <h1>Discover<br>your next<br>story.</h1>
        <p>영화는 단순한 감상이 아닌,<br>우리를 이해하는 또 다른 언어.</p>
      </div>
      <div class="hero__foot">
        © 2026 Movie Moobee. All rights reserved.
      </div>
    </aside>

    <!-- 우: 로그인 폼 -->
    <main class="panel">
      <form
        class="form"
        @submit.prevent="onSubmit"
      >
        <h2 class="form__title">
          Login to Movie Moobee
        </h2>

        <label
          class="lbl"
          for="login-email"
        >EMAIL</label>
        <input
          id="login-email"
          v-model="email"
          type="email"
          class="line-input"
          placeholder="이메일을 입력하세요"
          autocomplete="email"
          required
        >

        <label
          class="lbl"
          for="login-password"
        >PASSWORD</label>
        <input
          id="login-password"
          v-model="password"
          type="password"
          class="line-input"
          placeholder="비밀번호를 입력하세요"
          autocomplete="current-password"
          required
        >

        <a
          class="forgot"
          href="#"
          @click.prevent
        >비밀번호를 잊으셨나요?</a>

        <p
          v-if="error"
          class="error"
        >
          {{ error }}
        </p>

        <button
          class="btn-dark"
          type="submit"
          :disabled="loading"
        >
          {{ loading ? "로그인 중…" : "LOGIN" }}
        </button>

        <p class="switch">
          아직 계정이 없으신가요?
          <RouterLink to="/signup">
            회원가입
          </RouterLink>
        </p>
      </form>
    </main>
  </div>
</template>

<style scoped>
.auth-split {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #f0eee9;
  color: #1a1a1a;
}
/* 좌측 히어로 */
.hero {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 56px 64px;
  color: #f0eee9;
  background:
    linear-gradient(rgba(8, 8, 10, 0.62), rgba(8, 8, 10, 0.82)),
    radial-gradient(120% 80% at 50% 0%, #2a2a30 0%, #08080a 70%);
}
.hero__logo {
  position: absolute;
  top: 48px;
  left: 64px;
  font-size: 18px;
  letter-spacing: 0.28em;
  font-weight: 500;
}
.hero__copy h1 {
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 400;
  font-size: 64px;
  line-height: 1.05;
  margin: 0 0 28px;
}
.hero__copy p {
  font-size: 16px;
  line-height: 1.7;
  color: rgba(240, 238, 233, 0.72);
  margin: 0;
}
.hero__foot {
  position: absolute;
  bottom: 36px;
  left: 64px;
  font-size: 12px;
  color: rgba(240, 238, 233, 0.4);
}
/* 우측 폼 */
.panel {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}
.form {
  width: 100%;
  max-width: 380px;
}
.form__title {
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 400;
  font-size: 32px;
  margin: 0 0 40px;
}
.lbl {
  display: block;
  font-size: 11px;
  letter-spacing: 0.16em;
  color: #6b6b6b;
  margin: 22px 0 8px;
}
.line-input {
  width: 100%;
  border: none;
  border-bottom: 1px solid #c9c5bd;
  background: transparent;
  padding: 8px 2px;
  font-size: 15px;
  font-family: var(--font);
  color: #1a1a1a;
}
.line-input::placeholder {
  color: #a8a49c;
}
.line-input:focus {
  outline: none;
  border-bottom-color: #1a1a1a;
}
.forgot {
  display: inline-block;
  margin: 18px 0 0;
  font-size: 13px;
  color: #1a1a1a;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.error {
  margin: 16px 0 0;
  font-size: 13px;
  color: #b3261e;
}
.btn-dark {
  width: 100%;
  margin-top: 26px;
  padding: 16px;
  background: #111;
  color: #f0eee9;
  border: none;
  font-size: 14px;
  letter-spacing: 0.16em;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-dark:hover:not(:disabled) {
  background: #000;
}
.btn-dark:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.switch {
  text-align: center;
  margin-top: 28px;
  font-size: 13px;
  color: #6b6b6b;
}
.switch a {
  color: #1a1a1a;
  text-decoration: underline;
  text-underline-offset: 3px;
}
@media (max-width: 860px) {
  .auth-split {
    grid-template-columns: 1fr;
  }
  .hero {
    display: none;
  }
}
</style>
