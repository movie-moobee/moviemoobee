# A-04 · 영화+좌표 fixture (페어 공유용 시드)

- 날짜 / 일정ID / 담당: 2026-06-07 · 0.5 후속(시드) · 개발자 A(김호준)
- 브랜치 / 커밋: `chore/data-movies-fixture` · (커밋 예정)
- 한 줄 요약: 좌표까지 채워진 영화 데이터를 Django fixture로 덤프해, 페어가 **TMDB 키·ML 스택 없이 `loaddata` 한 줄**로 동일 데이터를 확보하게 한다.

## 만진 파일 (폴더/파일 — 역할)
- `backend/movies/fixtures/movies.json` *(신규, 575K)* — `Genre`(19) + `Keyword`(2205) + `Movie`(299, umap_x/y 포함) 덤프. Django 기본 fixture 경로(`<app>/fixtures/`)라 `loaddata movies`로 로드됨.
- `README.md` — "4) 데이터" 단계를 (A) 빠른 시작(loaddata) / (B) 직접 생성(import_movies·build_coords) 두 갈래로 정리.

## 어떻게 / 왜
- **왜 fixture?** 영화·좌표 데이터는 각자 로컬 DB(도커 볼륨)에만 있어 git으로 공유 안 됨. fixture로 떠두면 페어는 파이프라인을 안 돌려도 됨.
  - 페어 면제 항목: **TMDB API 키 불필요, 무거운 ML 스택(umap 등) 설치 불필요, import_movies/build_coords 실행 불필요.**
- **생성**: `dumpdata movies.Genre movies.Keyword movies.Movie --indent 2 -o movies/fixtures/movies.json`
  - **순서 중요**: Genre·Keyword를 Movie보다 먼저 덤프 → `loaddata`가 M2M(movie_genres/keywords) 참조 전에 부모를 먼저 적재.
  - **인코딩**: Windows 기본(cp949)으로 덤프하면 한글이 깨질 수 있어 `PYTHONUTF8=1`로 UTF-8 강제.
  - WatchRecord(시청기록)는 **제외** — 사용자 데이터라 fixture 아님(데모 데이터는 seed_demo 담당).
- **DB는 여전히 필요**: fixture는 데이터일 뿐, 적재할 PostgreSQL은 있어야 함 → 페어도 Docker(또는 로컬 Postgres)는 필요.

## 기능 동작 (흐름)
```
[개발자 A] dumpdata → movies.json (git 커밋)
        ↓ pull
[페어] migrate → loaddata movies → 영화 299편 + 전역 좌표 확보 (ML/TMDB 불필요)
```

## 검증
- 덤프 결과: 총 2523객체 (genre 19 / keyword 2205 / movie 299), **299편 전부 좌표 보유**, 한글 정상(`옵세션` 등).
- 라운드트립: `loaddata movies` → "Installed 2523 object(s)" 성공.
- `.gitignore`에 안 걸림(추적 가능), 파일 575K.

## 배운 점 · 주의
- dumpdata `-o`는 Windows에서 cp949로 열려 한글이 깨질 수 있다 → `PYTHONUTF8=1` 필수.
- 좌표가 바뀌면(build_coords 재실행 등) fixture도 다시 떠야 일치. 단, **build_coords 재실행은 전역 좌표를 바꾸므로 신중히**(불변식).
- 다음 작업: **seed_demo(데모 유저·별점·친구) + 3.1 사용자 좌표 계산·캐싱 API**.
