<script setup>
// 회원가입 4단계 위저드 (F-AUTH-01)
import { ref, computed, watch, nextTick, onMounted } from "vue";
import { useRouter } from "vue-router";
import { register, checkAvailability } from "@/api/auth";

const router = useRouter();

const STEPS = ["기본 정보", "비밀번호 설정", "비밀번호 확인", "완료"];
const step = ref(1); // 1~4

const email = ref("");
const nickname = ref("");
const password1 = ref("");
const password2 = ref("");
const error = ref("");
const submitting = ref(false);
const checking = ref(false); // 1단계 중복검사 진행 중

// 각 스텝의 첫 입력칸 — 스텝 전환 시 자동 포커스(칸 클릭 없이 바로 입력)
const emailInput = ref(null);
const nicknameInput = ref(null);
const pw1Input = ref(null);
const pw2Input = ref(null);

function focusStep(s) {
  const target = { 1: emailInput, 2: pw1Input, 3: pw2Input }[s];
  nextTick(() => target?.value?.focus());
}
onMounted(() => focusStep(1));
watch(step, (s) => focusStep(s));

const emailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value));
// 8자 이상 + 영문/숫자/특수문자 포함
const pwValid = computed(() =>
  /^(?=.*[A-Za-z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$/.test(password1.value),
);

async function next() {
  error.value = "";
  if (step.value === 1) {
    if (!emailValid.value) return (error.value = "올바른 이메일 형식을 입력하세요.");
    if (!nickname.value.trim()) return (error.value = "닉네임을 입력하세요.");
    // 비번까지 가기 전에, 1단계에서 이메일·닉네임 중복을 바로 확인 (F-AUTH-01)
    checking.value = true;
    try {
      const { email_taken, nickname_taken } = await checkAvailability({
        email: email.value,
        nickname: nickname.value.trim(),
      });
      if (email_taken) return (error.value = "이미 가입된 이메일입니다.");
      if (nickname_taken) return (error.value = "이미 사용 중인 닉네임입니다.");
    } catch {
      return (error.value = "중복 확인에 실패했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      checking.value = false;
    }
  }
  if (step.value === 2) {
    if (!pwValid.value)
      return (error.value = "8자 이상, 영문·숫자·특수문자를 포함해야 합니다.");
  }
  step.value += 1;
}

async function submit() {
  error.value = "";
  if (password2.value !== password1.value)
    return (error.value = "비밀번호가 일치하지 않습니다.");

  submitting.value = true;
  try {
    await register({
      email: email.value,
      password1: password1.value,
      password2: password2.value,
      nickname: nickname.value.trim(),
    });
    step.value = 4; // 완료
  } catch (e) {
    const d = e.response?.data || {};
    if (d.email) {
      error.value = `이메일: ${d.email[0]}`;
      step.value = 1;
    } else if (d.nickname) {
      error.value = d.nickname[0];
      step.value = 1;
    } else if (d.password1) {
      error.value = d.password1[0];
      step.value = 2;
    } else {
      error.value = "회원가입에 실패했습니다. 입력값을 확인하세요.";
    }
  } finally {
    submitting.value = false;
  }
}

function prev() {
  error.value = "";
  if (step.value > 1) step.value -= 1;
}

function start() {
  router.push("/onboarding");
}
</script>

<template>
  <div class="join">
    <div class="join__logo">
      MOVIE MOOBEE
    </div>

    <div class="join__head">
      <div class="join__count">
        {{ String(step).padStart(2, "0") }} / 04
      </div>
      <h1 class="join__title">
        Join Movie Moobee
      </h1>
      <p class="join__sub">
        취향 지도를 만들기 위한 첫 번째 기록을 시작하세요.
      </p>
    </div>

    <!-- 스텝퍼 -->
    <ol class="stepper">
      <li
        v-for="(label, i) in STEPS"
        :key="label"
        :class="['stepper__item', { on: step === i + 1, done: step > i + 1 }]"
      >
        <span class="stepper__dot">{{ i + 1 }}</span>
        <span class="stepper__label">{{ label }}</span>
      </li>
    </ol>

    <div class="join__body">
      <!-- 1. 기본 정보 -->
      <form
        v-if="step === 1"
        class="block"
        @submit.prevent="next"
      >
        <label
          class="lbl"
          for="r-email"
        >이메일</label>
        <input
          id="r-email"
          ref="emailInput"
          v-model="email"
          type="email"
          class="box-input"
          placeholder="이메일 주소를 입력하세요"
          @keydown.enter.prevent="nicknameInput?.focus()"
        >
        <label
          class="lbl"
          for="r-nick"
        >닉네임</label>
        <input
          id="r-nick"
          ref="nicknameInput"
          v-model="nickname"
          type="text"
          class="box-input"
          placeholder="닉네임을 입력하세요"
        >
        <p
          v-if="error"
          class="error"
        >
          {{ error }}
        </p>
        <button
          class="btn-dark"
          type="submit"
          :disabled="checking"
        >
          {{ checking ? "확인 중…" : "다음" }}
        </button>
      </form>

      <!-- 2. 비밀번호 -->
      <form
        v-else-if="step === 2"
        class="block"
        @submit.prevent="next"
      >
        <label
          class="lbl"
          for="r-pw"
        >비밀번호</label>
        <input
          id="r-pw"
          ref="pw1Input"
          v-model="password1"
          type="password"
          class="box-input"
          placeholder="비밀번호를 입력하세요"
          autocomplete="new-password"
        >
        <p class="hint">
          8자 이상, 영문/숫자/특수문자를 포함해주세요.
        </p>
        <p
          v-if="error"
          class="error"
        >
          {{ error }}
        </p>
        <div class="btn-row">
          <button
            class="btn-ghost"
            type="button"
            @click="prev"
          >
            이전
          </button>
          <button
            class="btn-dark"
            type="submit"
          >
            다음
          </button>
        </div>
      </form>

      <!-- 3. 비밀번호 확인 -->
      <form
        v-else-if="step === 3"
        class="block"
        @submit.prevent="submit"
      >
        <label
          class="lbl"
          for="r-pw2"
        >비밀번호 확인</label>
        <input
          id="r-pw2"
          ref="pw2Input"
          v-model="password2"
          type="password"
          class="box-input"
          placeholder="비밀번호를 다시 입력하세요"
          autocomplete="new-password"
        >
        <p
          v-if="error"
          class="error"
        >
          {{ error }}
        </p>
        <div class="btn-row">
          <button
            class="btn-ghost"
            type="button"
            :disabled="submitting"
            @click="prev"
          >
            이전
          </button>
          <button
            class="btn-dark"
            type="submit"
            :disabled="submitting"
          >
            {{ submitting ? "처리 중…" : "다음" }}
          </button>
        </div>
      </form>

      <!-- 4. 완료 -->
      <div
        v-else
        class="block done-block"
      >
        <div class="check">
          ✓
        </div>
        <h2 class="done-title">
          회원가입이 완료되었습니다!
        </h2>
        <p class="done-sub">
          Movie Moobee에서 당신의 취향을 발견하고, 새로운 이야기를 시작해보세요.
        </p>
        <button
          class="btn-dark"
          type="button"
          @click="start"
        >
          시작하기
        </button>
      </div>
    </div>

    <p
      v-if="step < 4"
      class="switch"
    >
      이미 계정이 있으신가요?
      <RouterLink to="/login">
        로그인
      </RouterLink>
    </p>
  </div>
</template>

<style scoped>
.join {
  min-height: 100vh;
  background: #f0eee9;
  color: #1a1a1a;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 20px 64px;
}
.join__logo {
  font-size: 18px;
  letter-spacing: 0.28em;
  font-weight: 500;
  margin-bottom: 56px;
}
.join__head {
  text-align: center;
  margin-bottom: 40px;
}
.join__count {
  font-size: 13px;
  letter-spacing: 0.1em;
  color: #6b6b6b;
}
.join__title {
  font-family: Georgia, "Times New Roman", serif;
  font-weight: 400;
  font-size: 40px;
  margin: 12px 0 10px;
}
.join__sub {
  font-size: 14px;
  color: #6b6b6b;
  margin: 0;
}
/* 스텝퍼 */
.stepper {
  display: flex;
  align-items: flex-start;
  gap: 0;
  list-style: none;
  padding: 0;
  margin: 0 0 48px;
  width: 100%;
  max-width: 560px;
}
.stepper__item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  position: relative;
  color: #a8a49c;
}
.stepper__item:not(:last-child)::after {
  content: "";
  position: absolute;
  top: 17px;
  left: 50%;
  width: 100%;
  height: 1px;
  background: #d3cfc6;
}
.stepper__item.on::after,
.stepper__item.done::after {
  background: #1a1a1a;
}
.stepper__dot {
  position: relative;
  z-index: 1;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  border: 1px solid #d3cfc6;
  background: #f0eee9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
}
.stepper__item.on .stepper__dot,
.stepper__item.done .stepper__dot {
  background: #111;
  color: #f0eee9;
  border-color: #111;
}
.stepper__label {
  font-size: 13px;
}
.stepper__item.on .stepper__label {
  color: #1a1a1a;
  font-weight: 600;
}
/* 입력 블록 */
.join__body {
  width: 100%;
  max-width: 600px;
}
.block {
  display: flex;
  flex-direction: column;
}
.lbl {
  font-size: 14px;
  font-weight: 600;
  margin: 22px 0 10px;
}
.box-input {
  width: 100%;
  padding: 16px;
  background: #f5f3ef;
  border: 1px solid #d3cfc6;
  border-radius: 2px;
  font-size: 15px;
  font-family: var(--font);
  color: #1a1a1a;
}
.box-input::placeholder {
  color: #a8a49c;
}
.box-input:focus {
  outline: none;
  border-color: #1a1a1a;
}
.hint {
  font-size: 13px;
  color: #8a857c;
  margin: 10px 2px 0;
}
.error {
  font-size: 13px;
  color: #b3261e;
  margin: 14px 2px 0;
}
.btn-dark {
  width: 100%;
  margin-top: 40px;
  padding: 18px;
  background: #111;
  color: #f0eee9;
  border: none;
  font-size: 15px;
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
/* 이전/다음 한 줄 배치 */
.btn-row {
  display: flex;
  gap: 12px;
  margin-top: 40px;
}
.btn-row .btn-dark {
  flex: 1;
  margin-top: 0;
}
.btn-ghost {
  padding: 18px 28px;
  background: transparent;
  color: #1a1a1a;
  border: 1px solid #d3cfc6;
  font-size: 15px;
  font-family: var(--font);
  cursor: pointer;
  transition: border-color 0.15s;
}
.btn-ghost:hover:not(:disabled) {
  border-color: #1a1a1a;
}
.btn-ghost:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
/* 완료 */
.done-block {
  align-items: center;
  text-align: center;
}
.check {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  border: 1.5px solid #1a1a1a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  margin: 8px 0 28px;
}
.done-title {
  font-size: 26px;
  font-weight: 600;
  margin: 0 0 14px;
}
.done-sub {
  font-size: 14px;
  color: #6b6b6b;
  margin: 0 0 8px;
}
.switch {
  margin-top: 40px;
  font-size: 13px;
  color: #6b6b6b;
}
.switch a {
  color: #1a1a1a;
  text-decoration: underline;
  text-underline-offset: 3px;
}
</style>
