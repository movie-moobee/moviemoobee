# A-02 · `import_movies` — TMDB 인기 영화 수집·적재

- 날짜 / 일정ID / 담당: 2026-06-07 · 일정 0.5 · 개발자 A
- 브랜치 / 커밋: `feat/data-00-import-movies` · (커밋 예정)
- 한 줄 요약: TMDB에서 **인기 영화**를 받아 `Movie/Genre/Keyword` 테이블에 적재하는 관리 커맨드. 취향 지도의 **원천 데이터**를 만드는 첫 단계(0.5 파이프라인의 전반부).

## 만진 파일 (폴더/파일 — 역할)
- `backend/taste/management/commands/import_movies.py` — 기존 TODO 스텁을 실제 구현으로 교체.
  - 위치 이유: 무거운 데이터 작업은 **관리 커맨드/서비스 계층**에 둔다(CLAUDE.md 규칙 — 뷰에 무거운 연산 금지). `taste`는 개발자 A(지도·추천·데이터)의 앱.
  - 실행법: `python manage.py import_movies --count 300`

## 어떻게 / 왜
- **레퍼런스**: `docs/poc-bundle/poc-a/1_fetch_movies.py`(검증 완료된 PoC)를 **DB 적재 버전으로 이식**. 바퀴 재발명 금지.
- **수집 기준 = TMDB `/movie/popular`**: 인기도(popularity) 내림차순으로 페이지(20편 단위)를 위에서부터 `--count`만큼 채움. 평점/장르균형 같은 다른 기준은 안 씀.
  - popularity는 TMDB가 매일 계산(조회수·투표 증감·watchlist·최근 개봉 가산) → **신작·화제작에 쏠림**(받은 데이터 연도가 죄다 최신인 이유). 지도 다양성이 필요하면 추후 `/discover`·`/top_rated`로 전략 변경 여지 있음.
- **인증이 중요**: `.env`의 `TMDB_API_KEY`는 v3 키(쿼리 `api_key`)가 아니라 **v4 Read Access Token(JWT, `eyJ...`)**. 그래서 PoC와 달리 `Authorization: Bearer <token>` **헤더**로 호출. (안 그러면 401)
- **상세 한 방 호출**: `/movie/{id}?append_to_response=credits,keywords` 로 장르·키워드·감독을 1요청에 받음(요청 수 절약).
- **모델 매핑 주의**: `Movie.director`는 **단일 문자열** 1개 → 감독 리스트 중 **대표 1명**만 저장(임베딩엔 충분).
- **멱등성**: `Movie`는 `tmdb_id` 기준 `update_or_create`, `Genre/Keyword`는 `get_or_create` → **재실행해도 중복이 안 생긴다**(데이터가 각자 로컬에 있어 자주 다시 돌리므로 중요).
- **좌표는 안 건드림**: `umap_x/umap_y`는 여기서 비워 둔다. 좌표는 다음 단계 `build_coords`가 채우는 **전역 고정값**(CLAUDE.md 불변식).
- **콘솔 인코딩**: Windows 콘솔은 cp949라 **이모지를 못 찍어 죽었음** → 출력의 이모지를 제거(`[수집]`/`[완료]` 텍스트). 한글은 cp949에서 OK.
- **장르 없는 영화 제외**: 임베딩(장르 기반)이 불가능하므로 적재 단계에서 거른다(PoC와 동일) → 300 요청 중 299편 적재.

## 기능 동작 (흐름)
```
manage.py import_movies --count N
 └ /movie/popular 페이지 순회로 영화 ID N개 수집(인기순)
     └ 각 ID에 대해 /movie/{id}?append_to_response=credits,keywords
         └ title/overview/release/runtime/vote/language/poster/대표감독/장르/키워드 추출
             └ Movie.update_or_create(tmdb_id) + Genre/Keyword get_or_create + M2M 연결
 (umap_x/y 는 비움 → build_coords 가 채움)
```

## 검증
- 소량(5편) 스모크 → Bearer 인증·적재 정상.
- 본 수집 300편 → **299편 적재**(1편 장르없음 제외), genres=19, keywords=2205.
- DB 인코딩 정상(UTF-8): `옵세션`, `톰 클랜시의 잭 라이언…`, 타밀어 `கர`까지.
- 멱등성: 재실행해도 `movies=299` 그대로(중복 없음).
- 변경 범위: 해당 커맨드 1파일만(외과적).

## 배운 점 · 주의
- TMDB 키 **버전(v3/v4)**에 따라 인증 방식이 다르다 → v4면 Bearer 헤더.
- `requests`는 `requirements-ml.txt`에 선언돼 있음. 이번엔 그것만 설치해 검증, 무거운 ML 스택(numpy/umap 등)은 `build_coords` 때 설치 예정.
- 다음 작업: **`build_coords`** (TF-IDF→UMAP→`umap_x/y` 적재 + 학습 모델 `.pkl` 저장). 좌표는 한 번만 `fit`, 신규 영화는 `transform`만 — 재학습 금지(불변식).
