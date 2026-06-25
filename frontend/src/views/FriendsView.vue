<script setup>
// 친구 페이지 (F-FRD-01~04, 와이어프레임 12) — 친구목록·검색·받은요청.
// 탭: 친구 목록(삭제) / 친구 검색(요청) / 받은 요청(수락·거절, 뱃지).
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  searchUsers,
  sendFriendRequest,
  getReceivedRequests,
  acceptFriendRequest,
  rejectFriendRequest,
  getFriends,
  unfriend,
} from "@/api/social";
import ConfirmDialog from "@/components/ConfirmDialog.vue";

const router = useRouter();
const TABS = [
  { key: "list", label: "친구 목록" },
  { key: "search", label: "친구 검색" },
  { key: "received", label: "받은 요청" },
];
const activeTab = ref("list"); // 친구 목록이 기본 탭(와이어프레임 12)

// --- 친구 목록 (F-FRD-04) ---
const friends = ref([]);
const friendsLoading = ref(true);
const friendsError = ref("");
const unfriendTarget = ref(null); // 끊기 확인 대상 친구
const unfriending = ref(false);

async function loadFriends() {
  friendsLoading.value = true;
  try {
    friends.value = await getFriends();
  } catch {
    friendsError.value = "친구 목록을 불러오지 못했습니다.";
  } finally {
    friendsLoading.value = false;
  }
}

function openProfile(friend) {
  router.push({ name: "friend-compare", params: { id: friend.id } });
}

async function confirmUnfriend() {
  if (!unfriendTarget.value || unfriending.value) return;
  unfriending.value = true;
  try {
    await unfriend(unfriendTarget.value.id);
    friends.value = friends.value.filter((u) => u.id !== unfriendTarget.value.id);
    unfriendTarget.value = null;
  } catch {
    friendsError.value = "친구 끊기에 실패했습니다.";
  } finally {
    unfriending.value = false;
  }
}

// --- 친구 검색 ---
const query = ref("");
const results = ref([]);
const searching = ref(false);
const searched = ref(false);
const searchError = ref("");
const sendingId = ref(null); // 요청 전송 중인 대상 id

async function onSearch() {
  if (!query.value.trim()) return;
  searching.value = true;
  searchError.value = "";
  try {
    results.value = await searchUsers(query.value.trim());
    searched.value = true;
  } catch {
    searchError.value = "검색에 실패했습니다.";
  } finally {
    searching.value = false;
  }
}

async function onRequest(user) {
  if (sendingId.value) return;
  sendingId.value = user.id;
  try {
    await sendFriendRequest(user.id);
    user.relation = "pending_sent"; // 카드 즉시 '요청 대기'로
  } catch (e) {
    searchError.value = e?.response?.data?.detail || "요청에 실패했습니다.";
  } finally {
    sendingId.value = null;
  }
}

// --- 받은 요청 ---
const received = ref([]);
const receivedLoading = ref(true);
const respondingId = ref(null);
const receivedError = ref("");
const receivedCount = computed(() => received.value.length);

async function loadReceived() {
  receivedLoading.value = true;
  try {
    received.value = await getReceivedRequests();
  } catch {
    received.value = [];
  } finally {
    receivedLoading.value = false;
  }
}

async function onAccept(reqItem) {
  if (respondingId.value) return;
  respondingId.value = reqItem.id;
  receivedError.value = "";
  try {
    await acceptFriendRequest(reqItem.id);
    received.value = received.value.filter((r) => r.id !== reqItem.id);
    // 검색 결과에 그 사람이 떠 있으면 관계도 갱신
    const u = results.value.find((x) => x.id === reqItem.requester.id);
    if (u) u.relation = "friend";
    loadFriends(); // 친구 목록 탭에 방금 수락한 친구가 바로 보이도록 갱신
  } catch {
    receivedError.value = "수락에 실패했습니다. 잠시 후 다시 시도해주세요.";
  } finally {
    respondingId.value = null;
  }
}

async function onReject(reqItem) {
  if (respondingId.value) return;
  respondingId.value = reqItem.id;
  receivedError.value = "";
  try {
    await rejectFriendRequest(reqItem.id);
    received.value = received.value.filter((r) => r.id !== reqItem.id);
    const u = results.value.find((x) => x.id === reqItem.requester.id);
    if (u) u.relation = "none";
  } catch {
    receivedError.value = "거절에 실패했습니다. 잠시 후 다시 시도해주세요.";
  } finally {
    respondingId.value = null;
  }
}

onMounted(() => {
  loadFriends();
  loadReceived(); // 뱃지 수가 어느 탭에서든 보이도록 미리 로드
});

function initial(nickname) {
  return (nickname || "?").trim().charAt(0).toUpperCase();
}
</script>

<template>
  <div class="mx-auto max-w-[1320px] px-6 pb-28 pt-10 lg:px-10">
    <!-- ───────── PAGE HEADER ───────── -->
    <section class="mb-6">
      <div class="mb-3 flex items-center gap-2.5 font-sans text-[11px] uppercase tracking-[0.14em] text-fg-muted">
        <span class="h-px w-7 bg-gold/60" />친구 · Companions
      </div>
      <h1 class="font-display text-[30px] font-semibold leading-[1.12] tracking-tightest sm:text-[36px]">
        취향이 닮은 사람들과 <span class="text-fg-muted">이어지세요</span>
      </h1>
    </section>

    <!-- ───────── TABS ───────── -->
    <div class="no-bar mb-6 flex items-center gap-1 overflow-x-auto border-b border-line">
      <button
        v-for="t in TABS"
        :key="t.key"
        type="button"
        class="relative shrink-0 px-4 py-2.5 text-[14px] font-semibold transition"
        :class="activeTab === t.key ? 'text-fg' : 'text-fg-muted hover:text-fg'"
        @click="activeTab = t.key"
      >
        {{ t.label }}
        <span
          v-if="t.key === 'received' && receivedCount"
          class="ml-1.5 inline-grid min-w-[18px] place-items-center rounded-full bg-danger px-1.5 text-[11px] font-semibold leading-[16px] text-white"
        >{{ receivedCount }}</span>
        <span
          class="absolute inset-x-3 -bottom-px h-[2px] rounded-full bg-gold"
          :class="{ hidden: activeTab !== t.key }"
        />
      </button>
    </div>

    <!-- ───────── 친구 목록 탭 ───────── -->
    <template v-if="activeTab === 'list'">
      <p
        v-if="friendsError"
        class="py-10 text-center text-[14px] text-danger"
      >
        {{ friendsError }}
      </p>
      <p
        v-if="friendsLoading"
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        불러오는 중…
      </p>
      <p
        v-else-if="friends.length === 0"
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        아직 친구가 없습니다. 친구 검색에서 요청을 보내보세요.
      </p>
      <ul
        v-else
        class="grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2"
      >
        <li
          v-for="u in friends"
          :key="u.id"
          class="flex cursor-pointer items-center gap-3.5 rounded-xl border border-line bg-ink-800 p-3.5 transition hover:border-lineHover"
          @click="openProfile(u)"
        >
          <div class="grid h-[52px] w-[52px] shrink-0 place-items-center overflow-hidden rounded-full border border-line bg-ink-700 text-[20px] font-bold text-fg-muted">
            <img
              v-if="u.profile_image_url"
              :src="u.profile_image_url"
              :alt="u.nickname"
              class="h-full w-full object-cover"
            >
            <span v-else>{{ initial(u.nickname) }}</span>
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-[15px] font-bold text-fg">
              {{ u.nickname }}
            </p>
            <p class="mt-1 text-[12.5px] text-fg-muted">
              본 영화 {{ u.watch_count }}편
            </p>
          </div>
          <div class="flex shrink-0 gap-1.5">
            <button
              type="button"
              class="whitespace-nowrap rounded-lg border border-gold bg-gold px-3.5 py-2 text-[13px] font-semibold text-ink transition hover:bg-gold-soft"
              @click.stop="openProfile(u)"
            >
              취향 비교
            </button>
            <button
              type="button"
              class="whitespace-nowrap rounded-lg border border-line px-3.5 py-2 text-[13px] font-semibold text-danger transition hover:border-danger"
              @click.stop="unfriendTarget = u"
            >
              친구 삭제
            </button>
          </div>
        </li>
      </ul>
    </template>

    <!-- ───────── 친구 검색 탭 ───────── -->
    <template v-else-if="activeTab === 'search'">
      <div class="mb-6 flex gap-2.5">
        <div class="flex flex-1 items-center gap-2.5 rounded-xl border border-line bg-ink-800 px-4 py-2.5 transition focus-within:border-gold">
          <svg
            viewBox="0 0 24 24"
            class="h-[18px] w-[18px] text-fg-faint"
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
          <input
            v-model="query"
            type="text"
            placeholder="닉네임으로 친구 검색"
            class="w-full bg-transparent text-[14px] text-fg placeholder:text-fg-faint focus:outline-none"
            @keyup.enter="onSearch"
          >
        </div>
        <button
          type="button"
          class="shrink-0 rounded-xl bg-gold px-6 text-[14px] font-bold text-ink transition hover:bg-gold-soft"
          @click="onSearch"
        >
          검색
        </button>
      </div>

      <p
        v-if="searchError"
        class="py-10 text-center text-[14px] text-danger"
      >
        {{ searchError }}
      </p>
      <p
        v-else-if="searching"
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        검색 중…
      </p>
      <ul
        v-else-if="results.length"
        class="grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2"
      >
        <li
          v-for="u in results"
          :key="u.id"
          class="flex items-center gap-3.5 rounded-xl border border-line bg-ink-800 p-3.5"
          :class="{ 'border-dashed': u.relation === 'pending_sent' }"
        >
          <div class="grid h-[52px] w-[52px] shrink-0 place-items-center overflow-hidden rounded-full border border-line bg-ink-700 text-[20px] font-bold text-fg-muted">
            <img
              v-if="u.profile_image_url"
              :src="u.profile_image_url"
              :alt="u.nickname"
              class="h-full w-full object-cover"
            >
            <span v-else>{{ initial(u.nickname) }}</span>
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-[15px] font-bold text-fg">
              {{ u.nickname }}
            </p>
            <p class="mt-1 text-[12.5px] text-fg-muted">
              본 영화 {{ u.watch_count }}편
            </p>
          </div>
          <!-- 관계상태별 액션 -->
          <button
            v-if="u.relation === 'none'"
            type="button"
            :disabled="sendingId === u.id"
            class="whitespace-nowrap rounded-lg border border-gold bg-gold px-3.5 py-2 text-[13px] font-semibold text-ink transition hover:bg-gold-soft disabled:cursor-not-allowed disabled:opacity-50"
            @click="onRequest(u)"
          >
            {{ sendingId === u.id ? "요청 중…" : "친구 요청" }}
          </button>
          <span
            v-else-if="u.relation === 'pending_sent'"
            class="cursor-default whitespace-nowrap rounded-lg border border-line px-3.5 py-2 text-[13px] font-semibold text-fg-muted"
          >요청 대기 중</span>
          <button
            v-else-if="u.relation === 'pending_received'"
            type="button"
            class="whitespace-nowrap rounded-lg border border-lineHover px-3.5 py-2 text-[13px] font-semibold text-fg transition hover:bg-white/[0.04]"
            @click="activeTab = 'received'"
          >
            받은 요청 확인
          </button>
          <span
            v-else
            class="cursor-default whitespace-nowrap rounded-lg border border-line px-3.5 py-2 text-[13px] font-semibold text-fg-muted"
          >친구</span>
        </li>
      </ul>
      <p
        v-else-if="searched"
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        검색 결과가 없습니다.
      </p>
      <p
        v-else
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        닉네임으로 친구를 찾아 요청을 보내보세요.
      </p>
    </template>

    <!-- ───────── 받은 요청 탭 ───────── -->
    <template v-else>
      <p
        v-if="receivedError"
        class="py-10 text-center text-[14px] text-danger"
      >
        {{ receivedError }}
      </p>
      <p
        v-if="receivedLoading"
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        불러오는 중…
      </p>
      <p
        v-else-if="received.length === 0"
        class="py-10 text-center text-[14px] text-fg-muted"
      >
        받은 친구 요청이 없습니다.
      </p>
      <ul
        v-else
        class="grid list-none grid-cols-1 gap-3 p-0 sm:grid-cols-2"
      >
        <li
          v-for="r in received"
          :key="r.id"
          class="flex items-center gap-3.5 rounded-xl border border-line bg-ink-800 p-3.5"
        >
          <div class="grid h-[52px] w-[52px] shrink-0 place-items-center overflow-hidden rounded-full border border-line bg-ink-700 text-[20px] font-bold text-fg-muted">
            <img
              v-if="r.requester.profile_image_url"
              :src="r.requester.profile_image_url"
              :alt="r.requester.nickname"
              class="h-full w-full object-cover"
            >
            <span v-else>{{ initial(r.requester.nickname) }}</span>
          </div>
          <div class="min-w-0 flex-1">
            <p class="truncate text-[15px] font-bold text-fg">
              {{ r.requester.nickname }}
            </p>
            <p class="mt-1 text-[12.5px] text-fg-muted">
              본 영화 {{ r.requester.watch_count }}편 · 친구 요청을 보냈어요
            </p>
          </div>
          <div class="flex shrink-0 gap-1.5">
            <button
              type="button"
              :disabled="respondingId === r.id"
              class="whitespace-nowrap rounded-lg border border-gold bg-gold px-3.5 py-2 text-[13px] font-semibold text-ink transition hover:bg-gold-soft disabled:cursor-not-allowed disabled:opacity-50"
              @click="onAccept(r)"
            >
              수락
            </button>
            <button
              type="button"
              :disabled="respondingId === r.id"
              class="whitespace-nowrap rounded-lg border border-line px-3.5 py-2 text-[13px] font-semibold text-fg transition hover:border-lineHover disabled:cursor-not-allowed disabled:opacity-50"
              @click="onReject(r)"
            >
              거절
            </button>
          </div>
        </li>
      </ul>
    </template>

    <!-- 친구 끊기 확인 -->
    <ConfirmDialog
      v-if="unfriendTarget"
      title="친구를 삭제할까요?"
      :message="`'${unfriendTarget.nickname}' 님과 친구를 끊습니다.`"
      confirm-label="친구 삭제"
      cancel-label="취소"
      :danger="true"
      :busy="unfriending"
      @confirm="confirmUnfriend"
      @cancel="unfriendTarget = null"
    />
  </div>
</template>
