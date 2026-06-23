# A-15 · 추천 재설계 — 미탐색 대륙분산 + 안전 봉우리별 kNN + 무게중심 완전 폐기

- 날짜 / 일정ID / 담당: 2026-06-23 · 4.1~4.3 후속(A-08·A-13·A-14 연장) · 김호준
- 브랜치 / 커밋: `feat/REC-unexplored-continents`
- 한 줄 요약: A-14 앵커 좌표 도입 후 내 계정으로 추천을 점검하다 4가지 결함을 발견·수정. ① 미탐색이 한 장르 일색 → **장르 대륙 분산**, ② 안전 10편이 한 점 클론 → **좋아한 영화별 고차원 kNN(`safe_by_liked`)**, ③ 정보 없는 유령 영화 → **포스터 필수 프룬**, ④ 버렸다던 무게중심이 코드 곳곳에 잔존 → **뿌리째 폐기**.

## 발단
A-14 앵커 좌표로 재bake 후 rlaghwns132(블록버스터 취향)로 추천을 보니: 미탐색이 **전쟁 10/10**(옛 좌표 땐 범죄 일색), 안전 10편이 사실상 같은 SF 영화, 미탐색에 12분짜리 포스터·줄거리 없는 유령(Return)까지. 파다 보니 **A-08에서 "안전 점수만" 뺐던 무게중심이 모델 필드·시그널·지도용으로 남아** 미탐색 정렬·`cluster_safe`로 자꾸 되살아나고 있었다.

## 1. 미탐색 — 장르 대륙 분산
- **진단(실측)**: 앵커 좌표에서도 도달밴드(kNN거리 30~70분위)의 최저밀도가 지도상 한 골짜기로 수렴. 풀을 키워도 한 장르(전쟁/역사 계열)뿐. **단조로움은 좌표·차원 무관**(A-13/A-14 실험1 재확인) — 최대 군집에서 뽑히는 구조라서.
- **해법**: 앵커 좌표가 장르로 구조화된 점을 활용 — 미관람을 최근접 앵커=**대륙**으로 분류 → **많이 본 장르(빈도 ≥ `EXPLORED_GENRE_MIN`=4)** 제외 → 본 영화 **집합 최근접 거리**로 대륙 정렬(가까운=도달가능 우선) → 대륙당 저밀도(KDE) **2편**씩(`UNEXPLORED_PER_CONTINENT`), 평점하한(`UNEXPLORED_MIN_VOTE`=6.0). 5대륙×2=10.
- **시행착오**:
  - 처음엔 **기하 제외**(본 영화 최근접 앵커)도 같이 걸었더니, 1편만 본 장르(애니 1편)가 대륙 통째로 사망 → 저밀도 미탐색을 막아 **오히려 필터버블 강화**. 폐기하고 빈도(≥4) 제외만 남김(많이 가본 곳은 KDE 밀도가 이미 거름).
  - 대륙 정렬 기준을 처음 `user_coord`(무게중심)로 썼다가, 다봉 취향에서 골짜기 함정(A-08)이라 **본 영화 집합 최근접**으로 교정. (이 교정으로 rlaghwns132에 로맨스가 "도달가능"으로 제대로 복귀 — 이터널선샤인을 봤으므로.)
- 결과(9유저 실측): 전원 5대륙 다양, 단일장르 0. 응답에 `continent` 필드 추가(프론트 라벨용).

## 2. 안전 — `safe_by_liked` (좋아한 영화별 고차원 kNN, centroid 없음)
- **진단**: 안전 10편 좌표 최대 상호거리 **0.27**(지도폭 22의 1.2% = 한 점). 좋아한 SF가 2D에서 한 점에 붕괴(collapse) → 그 위 미관람 SF도 클론. + 제일 빽빽한 SF 봉우리만 쓰고 가족(인사이드아웃 ★4.5) 취향 무시.
- **실험**: 고차원 kNN-to-집합(k=1·k=3)도 **SF 10/10** — 단조는 차원 무관 확인. → 봉우리 커버엔 봉우리별 배분 필수.
- **시행착오(중요)**: 처음 `cluster_safe`(좋아한 영화 KMeans 봉우리 → 봉우리별 **centroid** 코사인 kNN)로 다양성은 얻었으나, **centroid(평균점)가 곧 A-08이 버린 개념** — 사용자가 지적("무게중심 자꾸 도입").
- **최종(채택)**: `safe_by_liked` — 좋아한 영화 **각각**의 고차원(`safe_vectors`) 최근접 미관람을 **라운드로빈**으로 수집. 각 추천이 "좋아한 *특정 영화*의 최근접"으로 추적되고 **평균점이 없다**. 좋아한 SF가 많으면 SF가 비례해서 더 나옴.
- 결과: 좌표 상호거리 0.27→**7.18**, SF·가족/애니·MCU **3봉우리** 커버, 봉우리 내부도 정확(닥터스트레인지→토르, 인사이드아웃→곰돌이푸).
- **산출물**: `build_coords`가 거시공간(`x_macro`)을 SVD 48차원 축소·L2정규화해 `safe_vectors.npz`(ids·vecs)로 저장. `coords_model.pkl`처럼 gitignore. **없으면 `cluster`/`centroid` 없이 옛 2D 안전(detect_areas+MMR)으로 우아하게 폴백** → 페어가 rebake 안 해도 안 깨짐.

## 3. 유령 영화 프룬 (포스터 필수)
- 12분·포스터X·줄거리X인 "Return"이 평점필터(vote_avg≥6)를 통과해 미탐색에 떴다.
- **조사**: 줄거리 빈값 42편은 대부분 **정상 외국영화의 한글 줄거리 누락**(이탈리아 코미디 등 90~120분·수천 표), 단편(<40분)도 정상 픽사 단편 → 줄거리·러닝타임 기준은 과배제. **포스터 결측만이 깨끗한 유령 신호**("시각 추천에서 카드도 못 그림").
- **조치**: `prune_catalog`에 `poster_path=""` 영구 규칙 추가. 1편 제거(3745→3744). fixture·좌표 재bake.

## 4. 무게중심(user_coord) 완전 폐기
- A-08에서 "안전 점수에서만" 뺐을 뿐 `users.coord_x/y` 필드·시그널·`my_coord` API·지도 표시용으로 남아, 이번에 미탐색 정렬·`cluster_safe`로 두 번이나 되살아났다. **평균점 1개는 다봉 취향에서 빈 골짜기에 떨어지고, 좌표 원점이 임의값이라 "중심"이 취향을 못 나타낸다**(A-06·A-08). 표시용으로라도 남기면 다시 기어든다 → 뿌리째 제거.
- 제거: `accounts.User`의 `coord_x/coord_y/coord_updated_at`(마이그레이션 0004) · `taste/signals.py` · `taste/services/coords.py`(`recompute_user_coord`) · `apps.ready` 시그널 등록 · `detect_areas`의 user_coord 계산·반환 · `my_coord` 뷰/URL · seed·show 출력 · 프론트 주석. CLAUDE.md 불변식 "어떤 형태로도(점수·표시·캐시필드·API) 재도입 금지"로 재작성(※ CLAUDE.md는 git 미추적 개인파일이라 본 일지가 결정의 기록).
- **친구 비교(5.3) 영향**: per-user 점이 없으니, 두 사람의 **본 영화 집합·KDE 영역을 겹쳐 비교**하는 방식으로 설계해야 한다(점 두 개 비교 ❌). 프로젝트 철학(집합·KDE 기반)과 일치.

## 만진 파일 (폴더/파일 — 역할)
- `backend/taste/services/areas.py` — `unexplored_by_continent`(대륙 분산)·`safe_by_liked`(봉우리별 kNN)·`_anchors`/`_safe_vectors` 캐시·`_all_movies`에 평점 추가·`detect_areas`에서 user_coord 제거
- `backend/taste/services/recommend.py` — 안전=`safe_by_liked` 1순위(폴백 2D)·미탐색=대륙분산·`continent` 필드 보존
- `backend/taste/management/commands/build_coords.py` — `safe_vectors.npz`(SVD 48차원) 산출
- `backend/taste/management/commands/prune_catalog.py` — 포스터 없는 유령 영구 제외
- `backend/accounts/models.py` (+`migrations/0004`) — 좌표 필드 3개 삭제
- 삭제: `backend/taste/services/coords.py` · `backend/taste/signals.py`
- `backend/taste/{apps,views,urls}.py` · seed_demo · seed_genre_demos · show_areas · taste_map.py — user_coord 잔재 제거
- `backend/movies/fixtures/movies.json` · `taste/artifacts/anchors.json` — 3744편 재bake
- `frontend/src/api/taste.js` — 응답 주석 정리 · `.gitignore` — `*.npz`

## 검증
- 9유저 실측: 미탐색 전원 5대륙 다양(단일장르 0), 안전 봉우리 다양(rlaghwns132 모험10·액션7·SF4·가족3·코미디3·애니3·판타지3), 안전 좌표 상호거리 7.18.
- `manage.py check` 통과, 미적용 마이그레이션 0, 응답에 `user_coord` 없음, User 모델에 coord 필드 없음.
- 추천 시각화로 안전 3봉우리·미탐색 5대륙·유령 제거를 눈으로 확인.

## 배운 점 · 주의
- **단조로움은 좌표·차원으로 안 풀린다** — 구조(최대 군집 독점) 문제라 봉우리별/대륙별 **배분**이 본질적 해법.
- **평균점(centroid)은 매칭 기준으로 쓰면 안 된다** — 어떤 형태로든(전역·봉우리별) 다봉 취향에서 골짜기에 빠진다. 모든 매칭은 **집합 기반**. 표시용으로라도 남기면 재도입의 씨앗이 된다 → 개념 자체를 제거.
- **데이터 품질은 좁은 신호로** — 줄거리/러닝타임은 정상 콘텐츠를 대량 오배제. 포스터 결측처럼 오배제 0인 신호만 영구 규칙화.
- 고차원 산출물은 **선택적·폴백 가능**하게 — 없으면 옛 경로로 동작해 페어/타PC가 안 깨지게.

## 관련
- [[A-06]](코사인·원점 기각) · [[A-08]](안전 kNN 집합·무게중심 1차 제거) · [[A-13]](미탐색 다양화 탐색) · [[A-14]](앵커 좌표·고차원 안전 보너스)
