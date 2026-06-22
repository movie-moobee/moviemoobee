# A-13 · 미탐색 추천 다양화 — 재설계 탐색 (검토/보류)

- 날짜 / 일정ID / 담당: 2026-06-22 · 4.3 후속(A-11 연장) · 김호준
- 상태: **실험·진단 완료, 구현 보류** — 다음 세션(집 PC)에서 방향 결정 후 구현
- 한 줄 요약: 미탐색 추천 rail이 한 장르(범죄/역사) 일색으로 나오는 문제를 실측으로 진단. 풀확대·블렌드MMR·하드캡·밴드스윕을 전부 돌려본 결과, **"거리대 분할(stratified)"만 실효**. 단 먼 거리대는 큰 취향 점프. 구현 여부·튜닝(PER 등) 미결정.

## 문제
- `RecommendView` 미탐색 rail 10편이 **rlaghwns132(블록버스터 취향, 마블·SF·인셉션 등 12편)** 기준 **범죄 10/10·역사 9/10·드라마 9/10** — "다양한 새 취향 발견"이라는 의도와 어긋남(한 장르 주르륵).

## 진단 (실측 데이터)
- 미탐색 후보 풀 장르분포(rlaghwns132): 풀 40→**범죄 40/40**, 80→범죄 63/80, 150→역사72·드라마69·범죄63. **풀을 키워도 후보가 범죄·역사·드라마 계열뿐.**
- 원인: 도달밴드(거리 30~70분위) 안의 "최저 밀도" 지점이 지도상 **한 골짜기(범죄/역사)** 로 수렴. MMR은 **좌표로만** 다양화 → 장르는 단일.
- 비(非)범죄(애니·로맨스 등)는 좌표상 너무 멀어 도달밴드 밖 → 풀 키워도 안 들어옴.

## 용어 정리 (재설계 논의 기준)
- **좌표**: 영화 고정 위치 `(umap_x, umap_y)`. 비슷한 영화끼리 가까움.
- **거리**: 미관람 영화 → 내가 본 영화 중 최근접 3편 평균거리(kNN, k=3, `SAFE_KNN_K`). 작으면 취향 옆, 크면 멀리.
- **밀도(KDE)**: 본 영화로 붐비는 정도. 낮으면 안 가본 곳.
- **도달밴드**: 거리 30~70분위. "너무 가깝지도 멀지도 않은 = 갈 만한" 범위.
- **MMR**: 후보풀에서 `점수 = λ·적합도 − (1−λ)·(기선택과의 유사도)` 로 한 편씩 그리디 선별. (`recommend.py mmr_select`)
- **블렌드**: MMR의 '유사도'를 **좌표거리만 → 좌표+장르겹침(자카드) 섞은 것**. ※ 풀 크기와는 **별개 손잡이**.

## 시도와 결과 (9유저: rlaghwns132 + 장르데모 8)
| 방식 | 효과 |
|---|---|
| **풀 확대**(40→100/150) | 다양한 이웃 가진 유저 약간↑, **rlaghwns132 무효(범죄 그대로)** |
| **블렌드 MMR** | romance 3→8·music 10→14·crime 6→8·horror 7→10 개선, **rlaghwns132 무효(후보가 다 범죄라 뺄 게 없음)** |
| **하드 장르캡**(3/4편) | **역효과** — 범죄·역사·드라마가 같이 붙어다녀 3편에 동시 한도 도달+폴백 → crime 6→5, rlaghwns132 7→5 |
| **밴드 스윕**(30~70→30~90→50~95…) | 밴드 넓히면 **다른 단일 골짜기로 점프**(범죄→전쟁/액션→판타지/코미디), 여전히 한 장르 |
| **거리대 분할(stratified)** | ✅ **전원 다양** — rlaghwns132 범죄독점 깨짐(로맨스·코미디·드라마·판타지·스릴러 혼합), anime 1→10, romance 2→9, crime 4→14 |

## 해법: 거리대 분할 (stratified) — 동작
1. 거리 범위를 **1껍질(30~70)이 아니라 4껍질**로: `30~52 / 52~74 / 74~96 / 96~100` 분위.
2. 각 껍질에서 저밀도 후보를 `detect_areas`(밴드 인자만 교체)로 받음 → 중복 제외 → blend_mmr로 **PER편씩**(`[3,3,2,2]`=10).
3. 4껍질 = 지도 4개 지역 = 여러 장르 → 자연 다양.
- **rlaghwns132 실제 거리대별 선택**(검증):
  - 30~52(가까운): 왓에버웍스·게스후 `[코미디·로맨스]`
  - 52~74(중간): 패스트라이브즈·피아니스트 `[드라마·로맨스]`
  - 74~96(먼): 브루스올마이티·후엠아이 `[판타지·코미디·스릴러]`
  - 96~100(가장 먼): 보이이레이즈드 `[드라마]`
  → 현재였으면 범죄 10편, 분할하면 로맨스·코미디·드라마·판타지·스릴러 혼합.

## 트레이드오프 / 미결정 (다음 세션 결정)
- **먼 껍질 = 큰 취향 점프**(마블팬→로맨스코미디). "전부 도달가능"을 일부 포기하고 "가까운+과감" 혼합. 단 먼 것도 *그 거리대의 저밀도(구조화된 미탐색)* 라 무작위는 아님.
- 단일군집 취향(rlaghwns132·anime·comedy)은 이 방식 아니면 다양화 **본질적 불가**(reachable 범위에 다른 장르가 없음).
- **결정할 것**: ① 거리대 분할 실제 구현 여부, ② `PER`(near:far) 비중(현 3:3:2:2 → 가까운↑=안전 / 먼↑=과감), ③ 구간 개수·경계, ④ blend 적용·비율(좌표:장르), ⑤ **공유엔진**(지도 취향요약·친구추천도 `detect_areas`/MMR 사용)에 일관 적용할지 추천페이지만 할지, ⑥ A-11(2D→고차원)도 같이 볼지(현 보류).

## 프로토타입 코드 (실험용 — 실제 코드 미반영, `recommend.py`에 이식 예정)
```python
import numpy as np
from collections import Counter
from movies.models import Movie
from taste.services.areas import detect_areas

def jaccard(a, b):
    u = len(a | b)
    return len(a & b) / u if u else 0.0

def gset(mid):
    return set(Movie.objects.get(id=mid).genres.values_list("name", flat=True))

def blend_mmr(items, gmap, n=10, lam=0.5, wc=0.5, wg=0.5):
    if len(items) <= n:
        return items
    coords = np.array([it["coord"] for it in items], float)
    dens = np.array([it["density"] for it in items], float)
    rel = (dens.max() - dens) / (dens.max() - dens.min() + 1e-9)
    D = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=2)
    off = D[~np.eye(len(items), dtype=bool)]
    csim = (D.max() - D) / (D.max() - off.min() + 1e-9)
    gs = [gmap[it["movie_id"]] for it in items]
    G = np.array([[jaccard(gs[i], gs[j]) for j in range(len(items))] for i in range(len(items))])
    sim = wc * csim + wg * G
    sel = [int(np.argmax(rel))]
    rest = [i for i in range(len(items)) if i != sel[0]]
    while len(sel) < n and rest:
        best, bj = -1e9, None
        for j in rest:
            s = lam * rel[j] - (1 - lam) * sim[j, sel].max()
            if s > best:
                best, bj = s, j
        sel.append(bj); rest.remove(bj)
    return [items[i] for i in sel]

STRATA = [(30, 52), (52, 74), (74, 96), (96, 100)]
PER = [3, 3, 2, 2]

def stratified(u):
    sel, seen = [], set()
    for (lo, hi), k in zip(STRATA, PER):
        pool = [it for it in detect_areas(u, safe_top=1, unexplored_top=60,
                                          reachable_band=(lo, hi))["unexplored"]
                if it["movie_id"] not in seen]
        gmap = {it["movie_id"]: gset(it["movie_id"]) for it in pool}
        for it in blend_mmr(pool, gmap, k):
            sel.append(it["movie_id"]); seen.add(it["movie_id"])
    return sel
```

## 관련
- [[A-08]](안전 kNN) · [[A-09]](MMR·KDE 2D) · [[A-11]](2D vs 고차원 — 이 논의의 상위) · [[A-12]](취향요약 KDE 미탐색)
