<script setup>
// 프로필 수정 (와이어프레임 09 / F-AUTH-04·05).
// 사진(파일 업로드, 고르면 즉시 저장)·닉네임 / 비밀번호 변경 / 계정 삭제(Hard, 2차 확인).
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  updateProfile,
  uploadAvatar,
  changePassword,
  deleteAccount,
  deleteAvatar,
} from "@/api/auth";
import { useCurrentUser } from "@/composables/useCurrentUser";
import ConfirmDialog from "@/components/ConfirmDialog.vue";

const router = useRouter();
const { user, loadUser, setUser, clearUser } = useCurrentUser();

// 사진 (닉네임과 독립 — 고르면 즉시 저장)
const currentImageUrl = ref(null);
const savingPhoto = ref(false);
const removingPhoto = ref(false);
const photoMsg = ref("");

// 닉네임
const nickname = ref("");
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
  const me = user.value || (await loadUser());
  nickname.value = me?.nickname || "";
  currentImageUrl.value = me?.profile_image_url;
});

// 파일 선택 → 즉시 업로드(닉네임 저장 버튼과 무관)
async function onPickImage(e) {
  const file = e.target.files?.[0];
  e.target.value = ""; // 같은 파일 다시 선택해도 change 발생하도록 초기화
  if (!file || savingPhoto.value) return;
  savingPhoto.value = true;
  photoMsg.value = "";
  try {
    const updated = await uploadAvatar(file);
    currentImageUrl.value = updated.profile_image_url;
    setUser(updated); // 우상단 아바타 즉시 반영
    photoMsg.value = "사진이 변경되었습니다.";
  } catch {
    photoMsg.value = "사진 저장에 실패했습니다.";
  } finally {
    savingPhoto.value = false;
  }
}

async function removePhoto() {
  if (removingPhoto.value) return;
  removingPhoto.value = true;
  photoMsg.value = "";
  try {
    await deleteAvatar();
    currentImageUrl.value = null;
    if (user.value) setUser({ ...user.value, profile_image_url: null });
    photoMsg.value = "사진이 삭제되었습니다.";
  } catch {
    photoMsg.value = "사진 삭제에 실패했습니다.";
  } finally {
    removingPhoto.value = false;
  }
}

// 닉네임만 저장 (사진과 독립)
async function saveProfile() {
  if (savingProfile.value) return;
  savingProfile.value = true;
  profileMsg.value = "";
  try {
    const updated = await updateProfile({ nickname: nickname.value.trim() });
    setUser(updated);
    profileMsg.value = "저장되었습니다.";
  } catch (err) {
    profileMsg.value = err?.response?.data?.nickname?.[0] || "저장에 실패했습니다.";
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
    pwMsg.value = d?.old_password?.[0] || d?.new_password2?.[0] || "변경에 실패했습니다.";
  } finally {
    savingPw.value = false;
  }
}

async function confirmDelete() {
  deleting.value = true;
  try {
    await deleteAccount();
    clearUser();
    router.push("/login");
  } catch {
    deleting.value = false;
    showDelete.value = false;
  }
}
</script>

<template>
  <div class="edit">
    <button
      class="back"
      type="button"
      @click="router.push({ name: 'profile' })"
    >
      ‹ 프로필로 돌아가기
    </button>
    <h1 class="page-title">
      프로필 수정
    </h1>

    <!-- 사진 (고르면 즉시 저장, 닉네임과 독립) -->
    <div class="photo">
      <img
        v-if="currentImageUrl"
        :src="currentImageUrl"
        alt="프로필"
        class="photo__img"
      >
      <div
        v-else
        class="photo__img photo__img--empty"
      >
        {{ (nickname || "?").charAt(0) }}
      </div>
      <div class="photo__actions">
        <label
          class="photo__btn"
          :class="{ 'photo__btn--busy': savingPhoto }"
        >
          {{ savingPhoto ? "저장 중…" : currentImageUrl ? "사진 수정" : "사진 등록" }}
          <input
            type="file"
            accept="image/*"
            hidden
            :disabled="savingPhoto"
            @change="onPickImage"
          >
        </label>
        <button
          v-if="currentImageUrl"
          class="photo__btn photo__btn--remove"
          type="button"
          :disabled="removingPhoto || savingPhoto"
          @click="removePhoto"
        >
          {{ removingPhoto ? "삭제 중…" : "사진 삭제" }}
        </button>
      </div>
      <p
        v-if="photoMsg"
        class="formmsg"
      >
        {{ photoMsg }}
      </p>
    </div>

    <!-- 닉네임 -->
    <section class="block">
      <h2 class="block__title">
        닉네임 변경
      </h2>
      <div class="nick-row">
        <input
          v-model="nickname"
          class="input"
          type="text"
          placeholder="닉네임"
        >
        <button
          class="btn btn--primary"
          type="button"
          :disabled="savingProfile"
          @click="saveProfile"
        >
          {{ savingProfile ? "저장 중…" : "저장" }}
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
  max-width: 640px;
  margin: 0 auto;
  padding: 40px 28px 72px;
}
/* 돌아가기 */
.back {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  margin-bottom: 14px;
  padding: 6px 10px 6px 6px;
  background: none;
  border: none;
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.back:hover {
  color: var(--text);
}
.page-title {
  font-size: 24px;
  font-weight: 700;
  text-align: center;
  margin: 0 0 36px;
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
  width: 108px;
  height: 108px;
  border-radius: 50%;
  object-fit: cover;
  background: var(--surface-2);
}
.photo__img--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  font-weight: 700;
  color: var(--text-muted);
}
.photo__actions {
  display: flex;
  gap: 8px;
}
.photo__btn {
  font-size: 14px;
  color: var(--text);
  padding: 9px 18px;
  background: var(--surface-2);
  border: 1px solid var(--border-hover);
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.photo__btn--busy {
  opacity: 0.5;
  cursor: not-allowed;
}
.photo__btn--remove {
  color: var(--danger);
}
.photo__btn--remove:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
/* 블록 */
.block {
  margin-top: 36px;
}
.block__title {
  font-size: 16px;
  font-weight: 700;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
  margin: 0 0 16px;
}
.input {
  width: 100%;
  box-sizing: border-box;
  font-family: var(--font);
  font-size: 15px;
  padding: 13px 14px;
  margin-bottom: 10px;
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
/* 닉네임: 입력칸 + 저장 버튼 한 줄 */
.nick-row {
  display: flex;
  gap: 8px;
  align-items: stretch;
}
.nick-row .input {
  flex: 1;
  margin-bottom: 0;
}
.nick-row .btn {
  flex-shrink: 0;
}
.btn {
  font-family: var(--font);
  font-size: 15px;
  padding: 12px 24px;
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
