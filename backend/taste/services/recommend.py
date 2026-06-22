"""추천 (F-REC). 안전=본 영화 kNN 근접 Top N, 미탐색=KDE 저밀도(kNN 도달가능 밴드).

흐름: detect_areas 가 안전·미탐색 '후보 풀'(40)을 산출 → MMR 로 다양성 고려해 10편 선별
→ 영화 메타(포스터·연도·평점) 보강. kNN/KDE가 한 봉우리에 뭉치는 걸 MMR이 펼친다(A-09).
"""
import random

import numpy as np
from django.utils import timezone

from movies.models import Movie
from movies.serializers import MovieListSerializer

from .areas import detect_areas

SAFE_POOL = 40           # MMR 후보 풀 크기(키워도 추천 다양성 불변 — 검증 A-09). 40으로 충분.
UNEXPLORED_POOL = 40
MMR_LAMBDA_SAFE = 0.7    # 안전: 적합도 우선(신선함은 미탐색 담당) + 같은 봉우리 프랜차이즈 중복만 제거.
MMR_LAMBDA_UNEXPLORED = 0.5  # 미탐색: 발견 다양성 위해 더 펼침. (둘 다 검증 A-09, 소프트값)
DAILY_PICK_MIN_VOTE = 7.0   # '오늘의 추천' 후보 최소 평점.


def get_recommendations(user, safe_n=10, unexplored_n=10):
    """안전·미탐색 추천(MMR 선별 + 영화 메타) + 오늘의 추천. enough=False면 빈 리스트 그대로."""
    result = detect_areas(user, safe_top=SAFE_POOL, unexplored_top=UNEXPLORED_POOL)
    if result["enough"]:
        safe = mmr_select(result["safe"], "distance", MMR_LAMBDA_SAFE, safe_n)
        unexplored = mmr_select(result["unexplored"], "density", MMR_LAMBDA_UNEXPLORED, unexplored_n)
        result["safe"] = _enrich(safe, "distance")
        result["unexplored"] = _enrich(unexplored, "density")
        result["today"] = daily_pick(user)
    return result


def daily_pick(user):
    """오늘의 추천: 안 본 영화 중 평점 ≥ DAILY_PICK_MIN_VOTE 에서 '하루 한 편' 랜덤.
    날짜를 시드로 써서(유저+날짜) 같은 날엔 고정(새로고침해도 동일), 자정 지나면 바뀐다.
    추천 엔진(KDE)과 무관한 단순 발견용 — 후보가 없으면 None."""
    watched_ids = user.watch_records.values_list("movie_id", flat=True)
    qs = (Movie.objects
          .filter(vote_average__gte=DAILY_PICK_MIN_VOTE)
          .exclude(id__in=watched_ids)
          .order_by("id"))                 # 시드 인덱스가 일관되도록 안정 정렬
    n = qs.count()
    if not n:
        return None
    seed = f"{user.id}-{timezone.localdate().isoformat()}"   # 유저+날짜 → 하루 단위 고정
    movie = qs[random.Random(seed).randrange(n)]
    return MovieListSerializer(movie).data


def mmr_select(items, score_key, lam, n):
    """후보 풀에서 MMR로 n개 선별. 관련성(score_key, 낮을수록 좋음)과 다양성(이미 뽑힌 것과의
    UMAP 좌표 거리)을 λ로 절충: 점수 = λ·적합도 − (1−λ)·근접도. 풀 내 [0,1] 정규화."""
    if len(items) <= n:
        return items
    coords = np.array([it["coord"] for it in items], dtype=float)    # (P,2)
    score = np.array([it[score_key] for it in items], dtype=float)   # 낮을수록 관련성↑
    rel = (score.max() - score) / (score.max() - score.min() + 1e-9)  # [0,1], 1=best
    D = np.linalg.norm(coords[:, None, :] - coords[None, :, :], axis=2)
    off = D[~np.eye(len(items), dtype=bool)]
    sim = (D.max() - D) / (D.max() - off.min() + 1e-9)                # [0,1], 1=가장 겹침
    sel = [int(np.argmax(rel))]                                       # 1픽=가장 적합
    rest = [i for i in range(len(items)) if i != sel[0]]
    while len(sel) < n and rest:
        best, bj = -1e9, None
        for j in rest:
            s = lam * rel[j] - (1 - lam) * sim[j, sel].max()         # 이미 뽑힌 것과 가장 겹치면 감점
            if s > best:
                best, bj = s, j
        sel.append(bj); rest.remove(bj)
    return [items[i] for i in sel]


def _enrich(items, score_key):
    """[{movie_id, score, ...}] → [MovieList 필드 + score]. 선별 순서 보존(coord는 버려짐)."""
    movies = Movie.objects.in_bulk([it["movie_id"] for it in items])
    out = []
    for it in items:
        movie = movies.get(it["movie_id"])
        if movie is None:
            continue
        data = MovieListSerializer(movie).data
        data[score_key] = it[score_key]
        out.append(data)
    return out
