"""미탐색·안전 영역 감지 (F-MAP-03).

- 안전 근접도: 사용자가 본 영화 '집합'에 가까운 미관람 영화 = '취향 봉우리 주변'.
  점수 = 미관람 영화에서 가장 가까운 본 영화 K편(SAFE_KNN_K)까지의 평균 거리(작을수록 안전).
  ※ 예전엔 무게중심(별점 가중) 1점 거리를 썼으나, 다봉 취향에선 봉우리들의 평균이 빈
    '골짜기'에 떨어져 엉뚱한 장르를 추천하는 결함이 있었다 → 본 영화 집합 kNN으로 교체(검증 A-08).
    user.coord(무게중심)는 지도 표시·친구 비교용으로 유지하되, 안전 추천 점수엔 더는 안 쓴다.
  근접 척도는 UMAP 2D 좌표 거리(유클리드). 코사인이 아닌 이유: UMAP 원점(0,0)은 임의값이라
  '원점 기준 각도'가 취향을 못 나타낸다(검증 A-06). (UMAP은 국소 거리를 잘 보존 → 유클리드 적합.)
- 미탐색: 시청 분포 KDE 저밀도 영역.
  ※ KDE는 본 영화를 '전부'(싫어요 포함) 학습한다 — 싫어한 구역도 '가봤음(고밀도)'으로 잡혀
    미탐색에서 빠진다(CLAUDE.md: 싫어요는 탐색밀도+제외로 처리). 안전 중심은 좋아요만 가중 → 비대칭은 의도.
  ※ 지도 밝기(F-MAP-01)도 같은 KDE를 쓰지만 대상(본 영화)·정규화가 달라 3.3에서 별도 함수로 뺀다.
    (관심사 분리: detect_areas 는 '추천 후보' 산출만 책임진다.)
"""
import heapq

import numpy as np
from scipy.stats import gaussian_kde

from movies.models import Movie

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
    """좌표 있는 전체 영화 → (ids, titles, coords(N,2)).
    좌표는 전역 고정(F-MAP 불변식)이라 메모리 캐시 — re-bake(build_coords) 시 clear_movies_cache()로 무효화."""
    global _MOVIES_CACHE
    if _MOVIES_CACHE is None:
        rows = list(
            Movie.objects.filter(umap_x__isnull=False, umap_y__isnull=False)
            .values_list("id", "title", "umap_x", "umap_y")
        )
        ids = [r[0] for r in rows]
        titles = [r[1] for r in rows]
        coords = np.array([[r[2], r[3]] for r in rows], dtype=float)
        _MOVIES_CACHE = (ids, titles, coords)
    return _MOVIES_CACHE


def clear_movies_cache():
    """_all_movies() 좌표 캐시 무효화. re-bake(build_coords) 후·테스트에서 호출."""
    global _MOVIES_CACHE
    _MOVIES_CACHE = None


def _watched(user):
    """사용자가 본·좌표 있는 영화 → (watched_ids set, coords(M,2)). 쿼리 1번."""
    rows = list(user.watch_records.filter(
        movie__umap_x__isnull=False, movie__umap_y__isnull=False
    ).values_list("movie_id", "movie__umap_x", "movie__umap_y"))
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
      
    - user.coord_x/y 는 별점 변경 시 signals→recompute_user_coord 로 갱신되는 '캐시'다
      (조회마다 재계산 금지 — F-MAP-00 불변식). 여기선 그 캐시를 읽기만 한다.
      
    - 진짜 차단(호출 자체 스킵)은 진입부의 공유 게이트 책임 — 여기 가드는 belt-and-suspenders.
    
    - reachable_band=(lo,hi): 미탐색은 '도달 가능한' 저밀도만. 본 영화 kNN 거리 분위수
      [lo,hi] 밴드 안에서만 최저 밀도를 고른다. <lo=이미 탐색권(봉우리 코앞),
      >hi=도달 불가/취향 무관(변두리 허공) → 중간 밴드 = '갈 만한데 안 가본 곳'(4.2).
      미관람이 없으면(knn None) 밴드 적용 불가 → 절대 최저 밀도로 폴백.
    """
    watched_ids, watched_coords = _watched(user)
    
    # 정책 게이트: <MAP_MIN_WATCHED 편이면 지도·추천 미제공(빈 결과). 무거운 _all_movies 전에 차단.
    if len(watched_coords) < MAP_MIN_WATCHED:
        return {"user_coord": None, "safe": [], "unexplored": [], "enough": False}

    ids, titles, coords = _all_movies()
    user_coord = (
        np.array([user.coord_x, user.coord_y], dtype=float)  # shape (2,)
        if user.coord_x is not None else None
    )

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
        "user_coord": None if user_coord is None else (float(user_coord[0]), float(user_coord[1])),
        "safe": safe,
        "unexplored": unexplored,
        "enough": True,
    }
