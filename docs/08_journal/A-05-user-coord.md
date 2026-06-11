# A-05 · 사용자 좌표 계산·캐싱 + 시그널 + seed_demo (F-MAP-00)

- 날짜 / 일정ID / 담당: 2026-06-07 · 3.1 (F-MAP-00) · 개발자 A(김호준)
- 브랜치 / 커밋: `feat/MAP-00-user-coord` · (커밋 예정)
- 한 줄 요약: 시청기록(별점)으로 **사용자 좌표 = 별점 가중 평균**을 계산해 `users.coord_x/y`에 캐싱하고, 별점 변경 시 **Signal로 자동 재계산**. 조회 API + 테스트용 seed_demo 포함.

## 만진 파일 (폴더/파일 — 역할)
- `backend/taste/services/coords.py` — `recompute_user_coord(user)` 구현(스텁 → 실제). 좌표 계산·캐싱 로직 한 곳.
- `backend/taste/signals.py` *(신규)* — `movies.WatchRecord` post_save/post_delete 구독 → 해당 유저 좌표 재계산. 핸들러는 taste(A)에 두고 B의 모델만 구독.
- `backend/taste/apps.py` — `ready()`에서 signals import(시그널 등록).
- `backend/taste/views.py` + `urls.py` — `GET /api/taste/me/coord` (IsAuthenticated): 캐시된 내 좌표 반환.
- `backend/taste/management/commands/seed_demo.py` — 데모 유저 3명 + 취향 편향 시청기록 + 친구 1쌍(스텁 → 실제).

## 어떻게 / 왜
- **공식**: `weight = max(rating - 3.0, 0)`. 좌표 = **Σ(w·coord) / Σw** = 선호(3점 초과) 영화의 별점 가중 무게중심. 선호 0편(Σw≈0)이면 **본 영화 단순평균**, 시청 0편이면 null.
  - ⚠️ **수식 변천(2번 리뷰)**: PoC-B 원안 `Σw` 분모 → 음수 가중치에서 부호뒤집힘·발산 → 1차로 `Σ|w|`로 막았으나, **`Σ|w|`도 "비선호를 원점 반대편으로 보내는" 의미 없는 동작**(UMAP 원점은 임의값)이라 결함 잔존. → **최종: 비선호는 중심 계산에서 제외(클램프 `max(·,0)`)**. 싫어요 신호는 추천/KDE에서 처리. (PoC-B가 적어둔 "방법 B: 양수만 사용"과 일치)
  - **DB Aggregate**로 계산(행 미로딩; `Sum/Greatest/Cast`). 루프 버전은 가독성용 주석 보존. numpy 안 씀.
  - **저장은 `type(user).objects.filter(pk=...).update(...)`** — 파생 필드만 원자적 갱신(인스턴스 로드/다른 필드 간섭 없음).
- **캐싱(불변식)**: 조회마다 재계산 금지. `users.coord_x/y/coord_updated_at`에 저장하고, **별점 추가/수정/삭제 때만** 갱신.
- **시그널 위치**: 트리거 대상은 B의 `WatchRecord`지만, 좌표 로직은 A 도메인 → 핸들러를 `taste/signals.py`에 두고 `WatchRecord`만 구독(B 코드 무수정). `apps.ready()`에서 등록.
  - 주의: `bulk_create`는 시그널을 안 쏜다. seed_demo는 의도적으로 개별 `create`로 생성해 시그널 경로까지 검증.
- **API**: 단순 좌표 응답이라 serializer 없이 함수 뷰 + dict Response(단순함 우선). `permission_classes=[IsAuthenticated]`.
- **seed_demo**: 영화 많은 상위 3개 장르를 유저별 주취향으로 배정 → 주취향 10편(별점 3.5~5.0) + 그 외 5편(1.5~3.0). 멱등성(재실행 시 데모 유저 삭제 후 재생성).

## 기능 동작 (흐름)
```
WatchRecord 생성/수정/삭제
  └ post_save / post_delete 시그널
      └ recompute_user_coord(user): 시청영화 좌표 + (rating-3.0) 가중평균
          └ users.coord_x/y/coord_updated_at 캐싱
GET /api/taste/me/coord → 캐시된 좌표 반환 (재계산 안 함)
```

## 검증
- `seed_demo`: 데모 3명 좌표 자동 캐싱(시그널 경유), 장르별로 다른 위치.
- **클램프 동작**: 선호 2편 → 무게중심(midpoint)에 정확히 안착 / **비선호(별점1.0) 추가해도 좌표 불변**(중심에 영향 0) / 선호 0편 → 본 영화 단순평균 / 시청 0편 → null. 전부 기대값과 일치.
- **sanity**: 편향 유저(드라마/스릴러) 좌표가 주취향 군집 중심에 전체중심보다 가까움 ✅. (액션은 중앙·광역 장르라 비교 무의미 — 버그 아님)
- **시그널 edit/delete**: rating 수정·삭제 시 좌표 즉시 변동 확인.
- **API**: 비로그인 403, 인증 200 + 좌표.
- `makemigrations --check` 변경 없음, `ruff` 통과.

## 배운 점 · 주의
- **임베딩 좌표계에서 "밀어내기"는 함정**: 원점이 임의값이라 음수 가중치(Σw·Σ|w| 둘 다)는 의미가 깨진다. 추천계 정석대로 **비선호는 중심에서 제외**하고 추천/KDE에서 다루는 게 안정적. (불변식 `max(rating-3,0)`로 갱신)
- 집계는 가능하면 DB에서(Aggregate) — 행을 파이썬으로 올리지 않음. (단 우리 규모에선 루프도 성능 문제 없음; 정석을 따른 것)
- `save(update_fields=...)`는 다른 필드를 덮어쓰지 않지만(오해 주의), 파생 필드 갱신은 `.filter().update()` 채택. 단 `.update()`는 인메모리 인스턴스를 안 바꾸므로 **계산값을 인스턴스에 직접 동기화**(같은 요청 내 stale read 방지).
- **None 안전**: `rating`은 NOT NULL(스키마)이고 좌표는 not-null 필터 → `Sum/wsum`이 None이 될 수 없음 + 가드(`if not n`, `wsum<0.01`)로 div-by-zero 불가. (Coalesce는 불가능 케이스 방어라 미적용 — 단순함 우선)
- **증분 업데이트 보류**: 클램프·fallback 경계(별점이 3점을 넘나들면 가중치 0↔양수) 때문에 델타 누적은 버그 위험이 커서 전체 재계산 유지(우리 규모엔 1쿼리라 충분).
- **알려진 한계(의도적 보류)**: `recompute_user_coord`에 동시성 락(`select_for_update`)을 안 걸었다. 한 유저가 자기 별점을 *동시에* 변경하는 일은 로컬 시연 범위에서 사실상 없고, coord는 파생값이라 다음 변경 때 자동 복구된다. 멀티유저 동시성 환경이면 `transaction.atomic()+select_for_update()` 추가.
- 인증(dj-rest-auth)이 아직(B의 1.1) → API E2E는 SessionAuth 기준으로만 확인. 토큰 인증 붙으면 그대로 동작(IsAuthenticated는 인증방식 불문).
- 시그널이 B의 WatchRecord를 구독(핸들러는 A 소유) → **B와 공유 필요**.
- **⚠️ 벌크 쓰기 금지 규칙(B 공유)**: `post_save/post_delete`는 `bulk_create()`·`QuerySet.update()`에선 **발동 안 함** → 좌표가 stale. **WatchRecord는 일반 `.save()/.delete()`로만** 쓴다(벌크 필요 시 `recompute_user_coord`를 명시 호출). 참고로 `QuerySet.delete()`는 post_delete를 발동시켜 안전.
- **프로덕션 하드닝 목록(지금은 범위상 보류)**:
  - ① 동기 시그널 → 무거워지면 Celery 등 비동기 큐로(현재는 집계 1쿼리라 가벼움).
  - ③ 비동기로 가면 `transaction.on_commit`으로 커밋 후 실행(동기+같은 트랜잭션인 현재는 불필요 — 자기 트랜잭션 데이터 보이고 롤백도 함께).
  - ④ `created` 분기로 막으면 별점 *수정* 재계산을 놓쳐 **버그** → 채택 안 함. 리뷰-only 수정 비용은 1쿼리라 감수(정밀 제어는 FieldTracker 필요, DRF `save()`는 update_fields가 None이라 가드도 무력).
- 다음: F-MAP-03(미탐색·안전 영역 감지, KDE/코사인) 또는 추천(4.1/4.2).
