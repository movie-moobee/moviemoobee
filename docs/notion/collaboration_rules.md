# 무비무비 협업 규칙 — 그라운드룰 · GitHub Flow · 커밋 컨벤션

> 기획 12–13단계 · 2인 협업 · GitHub Flow + Conventional Commits + MR 필수(상대 1명 승인)
> 노션에 붙여넣어 팀 위키로 사용하세요. (이미지: `무비무비_깃헙플로우.png`)

---

## 1. 그라운드룰

### 1.1 소통 · 진행 관리
- 작업 시작 시 노션 일정표 상태를 **진행중**, MR 머지 시 **완료** 체크.
- 매일 비동기 싱크: **어제 한 일 / 오늘 할 일 / 막힌 점** 짧게 남기기.
- 주 1회 마일스톤(M1~M4) 점검으로 일정·분담 재조정.
- **30분 룰**: 같은 문제로 30분 이상 막히면 혼자 끌지 말고 바로 공유.
- 응답 약속: 평일 반나절 내 멘션·리뷰 요청에 반응.

### 1.2 코드 · 작업
- **수직 분담 존중** (A=지도·추천 / B=인증·콘텐츠·소셜). 상대 영역 수정은 사전 한마디 + MR.
- **공통 영역**(공통 셸·라우팅·DB 스키마·환경설정) 변경은 반드시 **MR + 상대 승인**. ← 충돌·장애 주원인.
- `main` 직접 push 금지 — 모든 변경은 브랜치 → MR.
- `.env`·API 키 등 시크릿은 **절대 커밋 금지**(.gitignore). TMDB 키는 별도 채널 공유.
- 중요한 결정은 노션에 기록(구두로 끝내지 않기).

### 1.3 태도
- 리뷰는 **코드**를 향한다. 사람 비난 금지, 제안은 이유와 함께.
- 지적은 **must**(꼭)와 **nit**(취향·제안)을 구분 표시.
- 일정 지연·분담 변경은 최대한 일찍 공유.
- "먼저 동작하게" 한 뒤 개선. 막히면 임시방편이라도 공유 후 함께 다듬기.

---

## 2. GitHub Flow

`main` 보호 + 기능별 브랜치 + MR(상대 1명 승인) → **Squash & Merge**. `main`은 항상 배포(시연) 가능 상태 유지.

### 2.1 작업 흐름 (6단계)
1. **브랜치 생성** — `git checkout main && git pull && git checkout -b feat/map-user-coord`
2. **작업 + 커밋** — Conventional Commits 형식, 작게 자주.
3. **push & MR** — push 후 MR 오픈(템플릿 작성, self-review 먼저).
4. **코드 리뷰** — 상대 1명 승인 + 파이프라인 통과. 변경 요청 오면 2번으로.
5. **Squash & Merge** — 승인 후 작성자가 squash 병합.
6. **브랜치 삭제** — 병합 브랜치 삭제, 각자 `main` pull 로 최신화.

### 2.2 브랜치 네이밍
> 기능 작업은 **기능 명세서 ID**를 붙인다: `<type>/<기능ID>-<요약>`. 공통 작업은 도메인 scope.

| 용도 | 형식 | 예시 |
|---|---|---|
| 기능 | `<type>/<기능ID>-<요약>` | `feat/MAP-00-user-coord` |
| 버그 | `fix/<기능ID>-<요약>` | `fix/WAT-01-rating-required` |
| 공통/잡일(ID 없음) | `<type>/<도메인>-<요약>` | `chore/infra-gitlab-ci` |
| 문서 | `docs/<요약>` | `docs/readme-setup` |
| (선택) 이슈연결 | MR 본문에 `Closes #번호` | `feat/REC-02-kde-region` |

### 2.3 MR 규칙
- 작게 자주(리뷰 가능한 크기). 큰 기능은 단계로 쪼개기.
- MR 제목 = 커밋 컨벤션 형식: `feat(MAP-00): 사용자 좌표 계산`.
- 본문은 MR 템플릿(아래 부록 A) 채우기.
- 올리기 전 self-review 로 diff 확인.

### 2.4 리뷰 · 머지 규칙
- **상대 1명 approve 필수** → 있어야 머지 가능.
- 리뷰 요청은 평일 24시간 내 확인.
- approve 후 **MR 작성자가 직접 Squash & Merge**.
- `main` 충돌은 **브랜치 주인이** 최신화해 해결.
- 미해결 스레드(thread)는 머지 전 모두 resolve.

### 2.5 main 보호 설정 (GitLab → Settings → Repository · Merge requests)
- [ ] Protected branches: `main` 의 'Allowed to push and merge' 비우기 → 직접 push 금지(MR로만)
- [ ] Merge request approvals: 필요한 승인 수 = **1**
- [ ] All threads must be resolved (모든 스레드 해결 후 머지)
- [ ] (선택) Pipelines must succeed (CI 연결 시)
- [ ] Allowed to force push 끄기 · `main` 삭제 금지

---

## 3. 커밋 컨벤션 (Conventional Commits)

```
type(scope): subject

[본문 — 무엇을 왜 (선택)]

[footer — BREAKING CHANGE / Closes #이슈 (선택)]
```

### 3.1 type
| type | 의미 |
|---|---|
| feat | 새 기능 |
| fix | 버그 수정 |
| docs | 문서 |
| style | 포맷·세미콜론 등(동작 변화 없음) |
| refactor | 리팩터링(기능 변화 없음) |
| perf | 성능 개선 |
| test | 테스트 추가·수정 |
| chore | 설정·빌드·잡일 |
| build | 빌드 시스템·의존성 |
| ci | CI 설정 |

### 3.2 scope = 기능 ID (핵심)
> scope에 **기능 명세서 ID**를 그대로 적으면 명세서 ↔ 브랜치 ↔ 커밋 ↔ MR이 한 줄로 꿰인다.

| 기능 ID | 영역 |
|---|---|
| AUTH-01~05 | 인증·계정(회원가입/로그인/로그아웃/프로필/탈퇴) |
| ONB-01 | 온보딩 영화 등록 |
| MOV-01~04 | 영화 검색·상세·OTT·리뷰 |
| WAT-01~04 | 시청 등록·별점·목록·삭제 |
| MAP-00~05 | 사용자 좌표·취향 지도·지도 탐색 |
| REC-01~03 | 추천(안전·미탐색·오늘의 추천) |
| FRD-01~06 | 친구·취향 비교·같이 볼 영화 |

공통 작업(특정 기능 ID 없음)은 **도메인 scope**:

| 공통 scope | 영역 |
|---|---|
| model | Django 모델·마이그레이션 |
| api | DRF 공통(시리얼라이저·라우터·인증 등) |
| ui | 프론트 공통 셸·라우팅·디자인 |
| infra | 설정·env·CI·의존성 |

### 3.3 subject 규칙
- 한글/영문 허용, 50자 내외, **끝에 마침표 없음**.
- 명령형·요약형('추가', '수정', '구현').
- 모호한 `update`, `수정함` 지양.

### 3.4 본문 · footer
- 본문: 왜 바꿨는지 필요 시 한두 줄.
- 이슈 연결: footer 에 `Closes #12` → 머지 시 이슈 자동 종료.
- 호환성 깨짐: `BREAKING CHANGE: ...` 명시.

### 3.5 예시
| 커밋 메시지 | 설명 |
|---|---|
| `feat(MAP-00): 별점 가중 사용자 좌표 계산 추가` | 기능 ID 사용 |
| `fix(WAT-01): 별점 미입력 시에도 저장되던 버그 수정` | 버그 |
| `feat(REC-02): KDE 기반 미탐색 추천 API 구현` | 기능 ID 사용 |
| `chore(model): movies 좌표 컬럼 마이그레이션 추가` | 공통 → 도메인 scope |
| `refactor(FRD-02): 친구 요청 상태 처리 분리` | 리팩터링 |
| `docs: README에 로컬 실행 방법 추가` | 문서 |

---

## 부록

### A. MR 템플릿 — `.gitlab/merge_request_templates/Default.md`
```markdown
## 무엇을 / 왜
- 

## 변경 사항
- 

## 스크린샷 (UI 변경 시)

## 테스트 / 확인
- [ ] 로컬에서 동작 확인
- [ ] 기존 기능 깨지지 않음

## 관련
- Closes #
```

### B. 커밋·MR 전 체크리스트
- [ ] `main` 에서 분기했는가
- [ ] 커밋 메시지가 Conventional 형식인가
- [ ] `.env`·시크릿이 포함되지 않았는가
- [ ] 로컬에서 동작을 확인했는가
- [ ] MR 이 리뷰 가능한 크기인가

### C. `.gitignore` 핵심
```
.env  .env.*
node_modules/
dist/  build/
.DS_Store
*.log
*.local
```
