# 무비무비 기획 문서 (docs)

무비무비(MovieMoobee) 기획·설계 문서 모음. "좋아하는 영화"가 아니라 **"좋아하게 될 영화"** 를 추천 — 취향 지도에서 미탐색 영역을 찾아 필터 버블을 벗어나게 한다.

> 스택: Vue 3 (Composition API) · Django REST Framework · PostgreSQL · 범위: 로컬 시연
> 파일명은 호환성을 위해 영문, 내용은 한글입니다.

## 문서 목록

| # | 파일 | 내용 |
|---|---|---|
| 01 | [01_functional_spec.docx](01_functional_spec.docx) | 기능 명세서 — 화면·기능(기능 ID F-*), 입력/처리/출력/예외, 비기능 요건 |
| 02 | [02_erd.png](02_erd.png) · [.svg](02_erd.svg) · [.dbml](02_erd.dbml) | ERD(8 테이블). DBML은 [dbdiagram.io](https://dbdiagram.io)에 붙여넣어 사용 |
| 03 | [03_wireframe.html](03_wireframe.html) | 와이어프레임 — 화면 01~13(어두운 취향 지도 포함). 브라우저로 열기 |
| 04 | [04_schedule.xlsx](04_schedule.xlsx) · [04_gantt.png](04_gantt.png) | 일정표 — WBS·간트·역할분담, 상태/진행률/리뷰 칸 |
| 05 | [05_collaboration_rules.docx](05_collaboration_rules.docx) | 협업 규칙 — 그라운드룰·GitHub Flow(GitLab)·커밋 컨벤션(기능 ID) |
| 06 | [06_github_flow.png](06_github_flow.png) | GitHub Flow 다이어그램(브랜치→MR→승인→Squash & Merge) |
| 07 | [07_docker_postgres_guide.md](07_docker_postgres_guide.md) | Docker + PostgreSQL 로컬 세팅·트러블슈팅 |

## 노션용 (notion/)
- [schedule.csv](notion/schedule.csv) — 노션 DB로 import (상태·완료·진행률·리뷰)
- [schedule_guide.md](notion/schedule_guide.md) — 일정 임포트 가이드 + 역할 분담
- [collaboration_rules.md](notion/collaboration_rules.md) — 협업 규칙 위키용

## 참고
- 화면·기능은 **01 기능 명세서의 기능 ID(F-*)** 기준. 브랜치·커밋도 이 ID를 사용.
- DB 모델은 **02 ERD** 를 따름.
- 확정본은 `docs/`, 살아있는 작업용(체크·리뷰)은 노션에서 관리.
