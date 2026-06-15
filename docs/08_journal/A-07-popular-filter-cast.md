# A-07 · 대중성 필터 카탈로그 재구축 + 배우(cast) 백필 + admin 경량화

- 날짜 / 일정ID / 담당: 2026-06-14 · chore(데이터) · 개발자 A(김호준)
- 브랜치 / 커밋: `chore/data-popular-filter` · (커밋 예정)
- 한 줄 요약: TMDB 수집을 `/movie/popular` → `/discover/movie`(vote_count≥300, 다득표순)로 바꿔 **저득표 잡영화를 걸러 299→4,958편으로 재구축(re-bake)**. 페어가 머지한 `cast` 필드에 **배우 데이터 백필**. 덤으로 admin 편집 페이지 **autocomplete 경량화**.

## 만진 파일
- `backend/taste/management/commands/import_movies.py` (A) — `_discover_ids()`(대중성 필터, B의 `get()`만 사용) + `--min-votes`(300)·`--fresh`·`--count` 기본 5000 + `_save`에 `cast` 저장.
- `backend/movies/fixtures/movies.json` — 4,958편(좌표+cast) 재덤프, 9.5MB.
- `backend/movies/admin.py` (B 파일, A가 도움) — `autocomplete_fields`로 Movie(키워드 14,472)·WatchRecord(영화 FK 4,958) 위젯 경량화.
- *(안 건드림)* `tmdb.py` — discover는 공개 `get()`만 사용. cast 추출(`fetch_detail`)은 페어 MR(`feat/movie-cast-api`)에서 추가됨.

## 어떻게 / 왜
- **왜 discover**: `/movie/popular`는 필터가 없어 vote_count 4표짜리 옛날·외국 영화가 유입. → `/discover/movie?sort_by=vote_count.desc&vote_count.gte=300&include_adult=false`. 결과 최소 **958표**(다득표 상위 5,000편이라 300까지 안 내려감) → 잡영화 0편.
- **re-bake 절차**: `import_movies --fresh`(299 삭제+4,958 적재) → `build_coords`(4,958편 재학습, 피처 차원 896→**9,245**) → `seed_demo`(데모 좌표 재계산) → fixture 덤프.
- **cast 백필**: 페어가 모델·`fetch_detail`·serializer 추가(머지) → A가 `_save`에 `cast` 저장 + **재import(--fresh 없이 → 좌표 보존)**. cast는 좌표 피처가 아니라 re-bake 불필요.
  - ⚠️ `--fresh` 없이 재import할 때 discover를 다시 조회해 경계 영화가 바뀜(드리프트 62편 유입, 좌표 없음) → 삭제로 정리. **교훈: cast만 백필할 땐 기존 영화를 순회하며 갱신하는 게 깔끔**(discover 재조회 금지).
- **admin**: 기본 등록이라 Movie 편집 폼이 키워드 14,472개, WatchRecord가 영화 4,958개를 통째 `<option>`으로 로딩 → 버벅. `autocomplete_fields`(Select2+AJAX)로 선택된 것만 로드.

## 검증
- 카탈로그 **4,958편 전부 좌표 O**, **4,954편 cast O**(4편은 TMDB에 cast 없음), vote_count<300 **0편**.
- cast 예: 인터스텔라 → "매튜 매커너히,앤 해서웨이,마이클 케인,…". 좌표·데모(3명) 보존.
- `detect_areas` 계산 34ms(4,958편에도 빠름). admin 편집 페이지 즉시 로드.
- UMAP 모델 `reducer.embedding_.shape == (4958, 2)` — 4,958편으로 학습된 확증.

## 결정 / 메모
- **편수 5,000**: 런타임 무관(추천 계산 ms·지도는 본 영화+추천만 렌더), 비용은 fixture git 용량(9.5MB)·import 시간(~10분)뿐. 풍부함 위해 채택.
- **검색은 제목만**: 배우/감독 검색은 보류(검색=로컬 DB). cast는 *표시*만(상세 화면, B 영역).
- **카탈로그 동결**: 운영 중 영화 추가는 transform 경로여야 re-bake 없음. 단 transform 커맨드 미구현이라, 등록은 미리 구운 카탈로그 내에서만(검색=로컬 DB) → transform 불필요.
