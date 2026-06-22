<script setup>
// 프로필 수정 (와이어프레임 09 / F-AUTH-04·05).
// 사진(파일 업로드)·닉네임 / 비밀번호 변경 / 계정 삭제(Hard, 2차 확인).
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  getMe,
  updateProfile,
  changePassword,
  deleteAccount,
} from "@/api/auth";
import ConfirmDialog from "@/components/ConfirmDialog.vue";

const router = useRouter();

// 프로필(사진·닉네임)
const nickname = ref("");
const currentImageUrl = ref(null); // 기존 사진 URL
const imageFile = ref(null); // 새로 고른 파일
const preview = ref(null); // 새 파일 미리보기
const savingProfile = ref(false);
const profileMsg = ref("");

// 비밀번호
const oldPw = ref("");
const newPw1 = ref("");
const newPw2 = ref("");
const savingPw = ref(false);
const pwMsg = ref("");

// 계정 삭제
const showDelete = ref(false);
const deleting = ref(false);

onMounted(async () => {
  const me = await getMe();
  nickname.value = me.nickname || "";
  currentImageUrl.value = me.profile_image_url;
});

function onPickImage(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  imageFile.value = file;
  preview.value = URL.createObjectURL(file);
}

async function saveProfile() {
  if (savingProfile.value) return;
  savingProfile.value = true;
  profileMsg.value = "";
  try {
    const updated = await updateProfile({
      nickname: nickname.value.trim(),
      imageFile: imageFile.value,
    });
    currentImageUrl.value = updated.profile_image_url;
    imageFile.value = null;
    preview.value = null;
    profileMsg.value = "저장되었습니다.";
  } catch (err) {
    profileMsg.value =
      err?.response?.data?.nickname?.[0] || "저장에 실패했습니다.";
  } finally {
    savingProfile.value = false;
  }
}

async function savePassword() {
  if (savingPw.value) return;
  pwMsg.value = "";
  if (newPw1.value !== newPw2.value) {
    pwMsg.value = "새 비밀번호가 일치하지 않습니다.";
    return;
  }
  savingPw.value = true;
  try {
    await changePassword({
      old_password: oldPw.value,
      new_password1: newPw1.value,
      new_password2: newPw2.value,
    });
    oldPw.value = newPw1.value = newPw2.value = "";
    pwMsg.value = "비밀번호가 변경되었습니다.";
  } catch (err) {
    const d = err?.response?.data;
    pwMsg.value =
      d?.old_password?.[0] || d?.new_password2?.[0] || "변경에 실패했습니다.";
  } finally {
    savingPw.value = false;
  }
}

async function confirmDelete() {
  deleting.value = true;
  try {
    await deleteAccount();
    router.push("/login");
  } catch {
    deleting.value = false;
    showDelete.value = false;
  }
}
</script>

<template>
  <div class="edit">
    <h1 class="page-title">
      프로필 수정
    </h1>

    <!-- 사진 -->
    <div class="photo">
      <img
        v-if="preview || currentImageUrl"
        :src="preview || currentImageUrl"
        alt="프로필"
        class="photo__img"
      >
      <div
        v-else
        class="photo__img photo__img--empty"
      >
        {{ (nickname || "?").charAt(0) }}
      </div>
      <label class="photo__btn">
        사진 등록 / 수정
        <input
          type="file"
          accept="image/*"
          hidden
          @change="onPickImage"
        >
      </label>
      <span class="hint">선택</span>
    </div>

    <!-- 닉네임 -->
    <section class="block">
      <h2 class="block__title">
        닉네임 변경
      </h2>
      <input
        v-model="nickname"
        class="input"
        type="text"
        placeholder="닉네임"
      >
      <div class="row">
        <button
          class="btn btn--primary"
          type="button"
          :disabled="savingProfile"
          @click="saveProfile"
        >
          {{ savingProfile ? "저장 중…" : "저장" }}
        </button>
        <button
          class="btn btn--ghost"
          type="button"
          @click="router.push({ name: 'profile' })"
        >
          취소
        </button>
      </div>
      <p
        v-if="profileMsg"
        class="formmsg"
      >
        {{ profileMsg }}
      </p>
    </section>

    <!-- 비밀번호 -->
    <section class="block">
      <h2 class="block__title">
        비밀번호 변경
      </h2>
      <input
        v-model="oldPw"
        class="input"
        type="password"
        placeholder="현재 비밀번호"
      >
      <input
        v-model="newPw1"
        class="input"
        type="password"
        placeholder="새 비밀번호"
      >
      <input
        v-model="newPw2"
        class="input"
        type="password"
        placeholder="새 비밀번호 확인"
      >
      <div class="row">
        <button
          class="btn btn--primary"
          type="button"
          :disabled="savingPw || !oldPw || !newPw1"
          @click="savePassword"
        >
          {{ savingPw ? "변경 중…" : "비밀번호 변경" }}
        </button>
      </div>
      <p
        v-if="pwMsg"
        class="formmsg"
      >
        {{ pwMsg }}
      </p>
    </section>

    <!-- 계정 삭제 -->
    <section class="block">
      <h2 class="block__title">
        계정
      </h2>
      <button
        class="btn btn--danger"
        type="button"
        @click="showDelete = true"
      >
        계정 삭제
      </button>
    </section>

    <ConfirmDialog
      v-if="showDelete"
      title="계정을 삭제할까요?"
      message="계정과 모든 시청기록·리뷰가 영구 삭제됩니다. 복구할 수 없습니다."
      confirm-label="삭제"
      danger
      :busy="deleting"
      @confirm="confirmDelete"
      @cancel="showDelete = false"
    />
  </div>
</template>

<style scoped>
.edit {
  max-width: 480px;
  margin: 0 auto;
  padding: 28px 24px 60px;
}
.page-title {
  font-size: 20px;
  font-weight: 700;
  text-align: center;
  margin: 0 0 28px;
}
/* 사진 */
.photo {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  margin-bottom: 28px;
}
.photo__img {
  width: 84px;
  height: 84px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--surface-2);
}
.photo__img--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  font-weight: 700;
  color: var(--text-muted);
}
.photo__btn {
  font-size: 13px;
  color: var(--text);
  padding: 7px 14px;
  background: var(--surface-2);
  border: 1px solid var(--border-hover);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.hint {
  font-size: 12px;
  color: var(--text-muted);
}
/* 블록 */
.block {
  margin-top: 28px;
}
.block__title {
  font-size: 14px;
  font-weight: 700;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
  margin: 0 0 14px;
}
.input {
  width: 100%;
  box-sizing: border-box;
  font-family: var(--font);
  font-size: 14px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
}
.input:focus {
  outline: none;
  border-color: var(--gold);
}
.row {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.btn {
  font-family: var(--font);
  font-size: 14px;
  padding: 10px 18px;
  border: 0;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.btn--primary {
  background: var(--gold);
  color: #1a1206;
  font-weight: 600;
}
.btn--ghost {
  background: transparent;
  color: var(--text);
  border: 1px solid var(--border-hover);
}
.btn--danger {
  background: transparent;
  color: var(--danger);
  border: 1px solid var(--danger);
}
.formmsg {
  font-size: 13px;
  color: var(--text-muted);
  margin: 10px 0 0;
}
</style>
