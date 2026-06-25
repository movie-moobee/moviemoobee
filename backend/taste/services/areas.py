"""미탐색·안전 영역 감지 (F-MAP-03).

- 안전 근접도: 사용자가 본 영화 '집합'에 가까운 미관람 영화 = '취향 봉우리 주변'.
  점수 = 미관람 영화에서 가장 가까운 본 영화 K편(SAFE_KNN_K)까지의 평균 거리(작을수록 안전).
  ※ 사용자 단일 좌표(평균점)는 폐기됨 — 다봉 취향에선 봉우리들의 평균이 빈 '골짜기'에 떨어져
    엉뚱한 장르를 추천한다(A-08). 모든 로직(추천·지도·친구비교)이 본 영화 '집합' 기반.
    (이 detect_areas 안전은 2D 폴백이고, 1순위는 recommend.safe_by_liked — 좋아한 영화별 고차원 kNN.)
  근접 척도는 2D 좌표 거리(유클리드). 코사인이 아닌 이유: 좌표 원점(0,0)은 임의값이라
  '원점 기준 각도'가 취향을 못 나타낸다(검증 A-06). (좌표는 앵커 대륙 지도 — A-14.)
- 미탐색: 시청 분포 KDE 저밀도 영역.
  ※ KDE는 본 영화를 '전부'(싫어요 포함) 학습한다 — 싫어한 구역도 '가봤음(고밀도)'으로 잡혀
    미탐색에서 빠진다(CLAUDE.md: 싫어요는 탐색밀도+제외로 처리). 안전 중심은 좋아요만 가중 → 비대칭은 의도.
  ※ 지도 밝기(F-MAP-01)도 같은 KDE를 쓰지만 대상(본 영화)·정규화가 달라 3.3에서 별도 함수로 뺀다.
    (관심사 분리: detect_areas 는 '추천 후보' 산출만 책임진다.)
"""
import heapq
import json
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.stats import gaussian_kde

from movies.models import Movie

# 앵커(장르 대륙) 위치 — build_coords가 생성·커밋(anchors.json). 미탐색 대륙 분산에 쓴다(A-15).
_ANCHORS_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "anchors.json"
# 안전 추천용 고차원 벡터 — build_coords가 생성(gitignore). 없으면 safe_by_liked는 None → 옛 2D 폴백.
_SAFE_VECTORS_PATH = Path(__file__).resolve().parents[1] / "artifacts" / "safe_vectors.npz"
UNEXPLORED_PER_CONTINENT = 2   # 미탐색: 대륙당 저밀도 N편(가까운 미탐색 대륙부터 채움). 5대륙×2=10.
EXPLORED_GENRE_MIN = 4         # 본 영화 ≥N편인 장르는 '점유'로 보고 미탐색 대륙서 제외(액션팬에 액션 안 나옴).
UNEXPLORED_MIN_VOTE = 6.0      # 대륙 안 선별 시 평점 하한 — 무명·저질 컷(저밀도만 보면 변두리 잡영화가 옴).
LIKE_NEUTRAL = 3.0             # 좋아요 기준점(별점>3=좋아함). 안전·취향요약 공통. weight = max(rating-3, 0).

KDE_BW = "scott"       # 적응형 대역폭(Scott): h = σ·n^(-1/(d+4)) — 본 영화 수·퍼짐에 자동 적응.
                       # 고정 0.3은 Scott보다 좁아 꼬리 언더플로(demo_c 밀도 e-14) → 밝기 정규화 깨짐. A-06.

KDE_MIN_SAMPLES = 3     # gaussian_kde 수학 하한: 2D는 표본수>차원수(n>2). 미만이면 즉시 실패.
                        # ※ 3개여도 공선이면 여전히 특이하면 → 아래  catch LinAlgError 로 잡을 수 있음.
                        # 호출부가 MAP_MIN_WATCHED(5)로 이미 막으므로 실서비스 경로에선 안 터짐 — 방어용(belt-and-suspenders).

MAP_MIN_WATCHED = 5     # 제품 정책: 지도·추천 공통으로 의미 있으려면 필요한 최소 시청 수(=온보딩 1.2 최소치).
                        # 미만이면 지도·추천 모두 차단(경고 오버레이). ★게이트 로직은 detect_areas 가 아니라
                        #   기능 진입 직전 단일 체크(공통 헬퍼/권한)에서 — 미만이면 detect_areas 호출 자체를 스킵.
                        #   (삭제로 5편 밑으로 내려가는 케이스 대비 — A-06 '알려진 한계' 참고)
                        # ⚠ 온보딩(B)과 같은 값이어야 함 — 추후 단일 출처로 공유.

SAFE_KNN_K = 3          # 안전 추천 kNN 이웃 수: 미관람→본 영화 최근접 K편 평균 거리로 점수.
                        # K=1은 외톨이 본 영화 1편 옆도 추천하지만, K=3은 본 영화가 '몰린' 봉우리를
                        # 우선해 더 안정적(검증 A-08). MAP_MIN_WATCHED(5)≥K라 항상 충족.


_MOVIES_CACHE = None    # (ids, titles, coords) 메모리 캐시. 좌표는 전역 고정(불변식)이라 1회 로드 후 재사용.


def _all_movies():
    """좌표 있는 전체 영화 → (ids, titles, coords(N,2), votes(N,)).
    좌표는 전역 고정(F-MAP 불변식)이라 메모리 캐시 — re-bake(build_coords) 시 clear_movies_cache()로 무효화."""
    global _MOVIES_CACHE
    if _MOVIES_CACHE is None:
        rows = list(
            Movie.objects.filter(map_x__isnull=False, map_y__isnull=False)
            .values_list("id", "title", "map_x", "map_y", "vote_average")
        )
        ids = [r[0] for r in rows]
        titles = [r[1] for r in rows]
        coords = np.array([[r[2], r[3]] for r in rows], dtype=float)
        votes = np.array([r[4] if r[4] is not None else 0.0 for r in rows], dtype=float)
        _MOVIES_CACHE = (ids, titles, coords, votes)
    return _MOVIES_CACHE


def clear_movies_cache():
    """_all_movies()·앵커·안전벡터 캐시 무효화. re-bake(build_coords) 후·테스트에서 호출."""
    global _MOVIES_CACHE, _ANCHORS_CACHE, _SAFE_VEC_CACHE
    _MOVIES_CACHE = None
    _ANCHORS_CACHE = None
    _SAFE_VEC_CACHE = None


def _watched(user):
    """사용자가 본·좌표 있는 영화 → (watched_ids set, coords(M,2)). 쿼리 1번."""
    rows = list(user.watch_records.filter(
        movie__map_x__isnull=False, movie__map_y__isnull=False
    ).values_list("movie_id", "movie__map_x", "movie__map_y"))
    ids = {r[0] for r in rows}
    coords = np.array([[r[1], r[2]] for r in rows], dtype=float)
    return ids, coords


def kde_density(watched_coords, query_coords):
    """watched_coords(M,2) 분포로 KDE 학습 후 query_coords(N,2)의 밀도(N,)를 반환.
    시청<KDE_MIN_SAMPLES 이거나 공선 등 특이행렬이면 None.
    (순수 함수 — 좌표 배열만 받는다. 지도 밝기(3.3)에서도 재사용.)"""
    if len(watched_coords) < KDE_MIN_SAMPLES:
        return None
    try:
        kde = gaussian_kde(watched_coords.T, bw_method=KDE_BW)
    except np.linalg.LinAlgError:   # 한 점에 몰림·공선 등
        return None
    return kde(query_coords.T)


def detect_areas(user, safe_top=10, unexplored_top=10, reachable_band=(30, 70)):
    """미관람 영화의 안전(본 영화 kNN 근접) Top N·미탐색(저밀도) Top N 산출.

    - 반환 enough: 시청 수가 MAP_MIN_WATCHED 이상인가(지도·추천 제공 가능 여부).
      False면 safe/unexplored 는 빈 리스트 — 소비처는 경고 오버레이를 띄운다.

    - 진짜 차단(호출 자체 스킵)은 진입부의 공유 게이트 책임 — 여기 가드는 belt-and-suspenders.

    - reachable_band=(lo,hi): 미탐색은 '도달 가능한' 저밀도만. 본 영화 kNN 거리 분위수
      [lo,hi] 밴드 안에서만 최저 밀도를 고른다. <lo=이미 탐색권(봉우리 코앞),
      >hi=도달 불가/취향 무관(변두리 허공) → 중간 밴드 = '갈 만한데 안 가본 곳'(4.2).
      미관람이 없으면(knn None) 밴드 적용 불가 → 절대 최저 밀도로 폴백.
    """
    watched_ids, watched_coords = _watched(user)

    # 정책 게이트: <MAP_MIN_WATCHED 편이면 지도·추천 미제공(빈 결과). 무거운 _all_movies 전에 차단.
    if len(watched_coords) < MAP_MIN_WATCHED:
        return {"safe": [], "unexplored": [], "enough": False}

    ids, titles, coords, _votes = _all_movies()

    # 추천 후보는 미관람뿐 → 거리·KDE 모두 미관람 부분집합에서만 계산(불필요 연산 제거).
    unwatched = [i for i, mid in enumerate(ids) if mid not in watched_ids]
    uw_coords = coords[unwatched]                          # (U,2)

    # 안전·미탐색 공용: 본 영화 '집합'과의 kNN(K=SAFE_KNN_K) 거리 — 미관람마다 최근접 K편 평균.
    # 무게중심 1점이 아니라 본 영화들 자체를 기준 삼아 다봉 취향의 '골짜기' 오추천을 막는다(A-08).
    knn = None
    if len(unwatched):
        d_watched = np.linalg.norm(                           # (U, M) 미관람×본영화 거리
            uw_coords[:, None, :] - watched_coords[None, :, :], axis=2)
        k = min(SAFE_KNN_K, watched_coords.shape[0])
        knn = np.sort(d_watched, axis=1)[:, :k].mean(axis=1)  # (U,) 작을수록 취향 봉우리에 가까움

    # 안전: kNN 거리 최소 Top N. coord는 후속 MMR 다양성 계산용(응답엔 노출 안 됨).
    safe = []
    if knn is not None:
        order = heapq.nsmallest(safe_top, range(len(unwatched)), key=lambda j: knn[j])
        safe = [{"movie_id": ids[unwatched[j]], "title": titles[unwatched[j]],
                 "distance": float(knn[j]),
                 "coord": (float(uw_coords[j][0]), float(uw_coords[j][1]))} for j in order]

    # 미탐색: kNN 도달가능 밴드 안에서 KDE 밀도 최저 Top N.
    # 밴드 기준도 kNN 거리(본 영화 봉우리 근접도) — 무게중심 골짜기 문제를 미탐색에서도 제거(A-09). knn 없으면 전체.
    unexplored = []
    density = kde_density(watched_coords, uw_coords)         # 미관람만 평가 (None 또는 (U,))
    if density is not None:
        candidates = range(len(unwatched))
        if knn is not None and reachable_band is not None:
            lo, hi = np.percentile(knn, reachable_band)
            candidates = [j for j in range(len(unwatched)) if lo <= knn[j] <= hi]
        order = heapq.nsmallest(unexplored_top, candidates, key=lambda j: density[j])
        unexplored = [{"movie_id": ids[unwatched[j]], "title": titles[unwatched[j]],
                       "density": float(density[j]),
                       "coord": (float(uw_coords[j][0]), float(uw_coords[j][1]))} for j in order]

    return {
        "safe": safe,
        "unexplored": unexplored,
        "enough": True,
    }


_ANCHORS_CACHE = None   # (pos(G,2), names) 메모리 캐시. 좌표와 함께 전역 고정.


def _anchors():
    """앵커 (pos(G,2) ndarray, names) 로드·캐시. 파일 없으면 (빈 배열, [])."""
    global _ANCHORS_CACHE
    if _ANCHORS_CACHE is None:
        try:
            data = json.loads(_ANCHORS_PATH.read_text(encoding="utf-8"))
            _ANCHORS_CACHE = (np.array([[a["x"], a["y"]] for a in data], dtype=float),
                              [a["name"] for a in data])
        except FileNotFoundError:
            _ANCHORS_CACHE = (np.empty((0, 2)), [])
    return _ANCHORS_CACHE


def unexplored_by_continent(user, n=10, per_continent=UNEXPLORED_PER_CONTINENT):
    """미탐색 추천 — '안 가본 장르 대륙'으로 분산해 n편 선별 (A-15).

    왜: 단일 도달밴드의 최저밀도만 뽑으면 한 대륙(골짜기)에 수렴해 한 장르만 주르륵 나온다
    (옛 좌표 범죄 일색 → 앵커 좌표 전쟁 일색, 구조적 문제는 동일 — A-13). 앵커 좌표는 장르로
    구조화돼 있으니 '대륙' 단위로 퍼뜨려 다양성을 구조적으로 보장한다.

    방법: 미관람 영화를 최근접 앵커(대륙)로 분류 → 사용자가 이미 점유한 대륙(본 영화의 대륙)
    제외(코미디팬에 코미디를 '발견'으로 추천하는 오류 차단) → 사용자 좌표에 가까운 미탐색
    대륙부터 대륙당 저밀도 per_continent편씩, n편 찰 때까지(얇은 대륙이면 다음 대륙서 보충).

    반환: detect_areas 미탐색과 같은 형식 [{movie_id, title, density, coord, continent}]. 빈 리스트면
    호출부가 폴백(앵커 미생성·미관람<게이트 등)."""
    anchor_pos, anchor_names = _anchors()
    watched_ids, watched_coords = _watched(user)
    if not len(anchor_pos) or len(watched_coords) < MAP_MIN_WATCHED:
        return []

    ids, _titles, coords, votes = _all_movies()
    unwatched = [i for i, mid in enumerate(ids)
                 if mid not in watched_ids and votes[i] >= UNEXPLORED_MIN_VOTE]   # 평점 하한
    if not unwatched:
        return []
    uw_coords = coords[unwatched]                       # (U,2)
    density = kde_density(watched_coords, uw_coords)    # (U,) 또는 None
    if density is None:
        return []

    def nearest(c):                                     # 좌표 → 최근접 앵커 인덱스
        return int(((anchor_pos[:, 0] - c[0]) ** 2 + (anchor_pos[:, 1] - c[1]) ** 2).argmin())

    # 점유 대륙 = '많이 본' 장르(빈도 ≥ EXPLORED_GENRE_MIN)만 제외. 기하(최근접 앵커) 제외는
    # 폐기했다 — 1편만 본 장르(애니 1편)까지 대륙 통째로 죽여 저밀도 미탐색을 막아 필터버블을
    # 오히려 강화했다. '많이 가본 곳'은 KDE 밀도가 이미 거른다(빈도 제외는 home 장르 안전핀).
    gcount = Counter(Movie.objects.filter(id__in=watched_ids)
                     .values_list("genres__name", flat=True))                     # M2M 1조인 = 장르빈도
    explored_genres = {g for g, c in gcount.items() if g and c >= EXPLORED_GENRE_MIN}
    by_cont = {}                                        # 대륙 → [unwatched 내 인덱스 j]
    for j, gi in enumerate(unwatched):
        ai = nearest(coords[gi])
        if anchor_names[ai] not in explored_genres:
            by_cont.setdefault(ai, []).append(j)

    # 가까운 미탐색 대륙 우선 = 도달 가능 우선. 본 영화 '집합' 최근접 거리로 잰다(A-08 원칙 —
    # 모든 추천은 점 하나가 아니라 본 영화 집합 기반). 각 대륙 = 그 앵커에서 가장 가까운 본 영화까지 거리로 정렬.
    cand = sorted(by_cont, key=lambda ai: float(
        np.min(np.sum((watched_coords - anchor_pos[ai]) ** 2, axis=1))))
    for ai in cand:                                     # 대륙 안은 저밀도(=덜 가본) 우선
        by_cont[ai].sort(key=lambda j: density[j])

    selected = []
    for ai in cand:                                     # 가까운 대륙부터 per_continent씩
        if len(selected) >= n:
            break
        for j in by_cont[ai][:per_continent]:
            gi = unwatched[j]
            selected.append({"movie_id": ids[gi], "title": _titles[gi],
                             "density": float(density[j]),
                             "coord": (float(uw_coords[j][0]), float(uw_coords[j][1])),
                             "continent": anchor_names[ai]})
    # If fewer than n items were selected because there are not enough
    # candidate continents, relax the per-continent cap in round-robin order.
    # The first pass keeps diversity; this pass fills the rail.
    extra_rank = per_continent
    while len(selected) < n:
        added = False
        for ai in cand:
            if len(selected) >= n:
                break
            if len(by_cont[ai]) <= extra_rank:
                continue
            j = by_cont[ai][extra_rank]
            gi = unwatched[j]
            selected.append({"movie_id": ids[gi], "title": _titles[gi],
                             "density": float(density[j]),
                             "coord": (float(uw_coords[j][0]), float(uw_coords[j][1])),
                             "continent": anchor_names[ai]})
            added = True
        if not added:
            break
        extra_rank += 1
    return selected[:n]


_SAFE_VEC_CACHE = None   # (id→row dict, vecs(N,D), ids(N,)) 또는 (None,None,None) = 산출물 없음.


def _safe_vectors():
    """안전 고차원 임베딩 (id→row, vecs, ids 배열) 로드·캐시. 파일 없으면 (None,None,None)."""
    global _SAFE_VEC_CACHE
    if _SAFE_VEC_CACHE is None:
        try:
            data = np.load(_SAFE_VECTORS_PATH)
            ids = data["ids"]
            _SAFE_VEC_CACHE = ({int(mid): i for i, mid in enumerate(ids)}, data["vecs"], ids)
        except FileNotFoundError:
            _SAFE_VEC_CACHE = (None, None, None)
    return _SAFE_VEC_CACHE


def safe_by_liked(user, n=10):
    """안전 추천 — 좋아한 영화 '각각'의 고차원 최근접 미관람을 라운드로빈으로 n편 (A-15).

    원칙: 무게중심/평균점이 아니라 본(좋아한) 영화 '집합'에 kNN(A-08 — 무게중심은 다봉 취향서
    골짜기에 빠져 버린 개념). 단 가장 빽빽한 한 봉우리가 최근접 N편을 독점해(고차원도 동일 —
    A-14 실험1) kNN-to-집합만으론 한 장르만 나온다. 그래서 좋아한 영화마다 자기 최근접을 한 편씩
    번갈아(라운드로빈) 가져와 여러 봉우리를 고르게 커버한다 — 좋아한 SF가 많으면 SF가 비례해서 더
    나온다. 각 추천은 '좋아한 특정 영화의 최근접 미관람'으로 추적된다(centroid 없음).

    2D 대신 고차원(safe_vectors)을 쓰는 이유: 2D는 같은 장르를 한 점에 뭉개(붕괴) 후보가 클론이
    된다. 반환은 detect_areas 안전과 같은 [{movie_id, distance}] (distance=1−코사인). 산출물 없거나
    매칭 본 영화가 없으면 None → 호출부가 옛 2D 안전으로 폴백."""
    id2row, vecs, all_ids = _safe_vectors()
    if vecs is None:
        return None
    rows = list(user.watch_records.values_list("movie_id", "rating"))
    if len(rows) < MAP_MIN_WATCHED:
        return None
    watched_ids = {mid for mid, _ in rows}
    # '좋아한'(>3) 본 영화 기준. 없으면 본 영화 전체로 폴백(사용자 좌표 계산과 같은 비대칭).
    liked = [mid for mid, r in rows if r is not None and float(r) > LIKE_NEUTRAL and mid in id2row]
    if not liked:
        liked = [mid for mid, _ in rows if mid in id2row]
    cand = np.array([i for i, mid in enumerate(all_ids) if int(mid) not in watched_ids])
    if not liked or not len(cand):
        return None
    cv = vecs[cand]                                          # (C, D) 후보 벡터
    # 좋아한 영화별 후보 순위(코사인 유사도 desc) — ranked[i] = vecs 행 인덱스 배열.
    ranked = [cand[np.argsort(-(cv @ vecs[id2row[mid]]))] for mid in liked]

    selected, taken = [], set()
    r = 0
    while len(selected) < n and r < len(cand):
        for lst, src in zip(ranked, liked):                 # 좋아한 영화마다 r번째 최근접 한 편씩
            if len(selected) >= n:
                break
            row = lst[r]
            cid = int(all_ids[row])
            if cid in taken:
                continue
            selected.append({"movie_id": cid, "distance": float(1.0 - vecs[row] @ vecs[id2row[src]])})
            taken.add(cid)
        r += 1
    return selected[:n]
