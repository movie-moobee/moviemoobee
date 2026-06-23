"""추천 (F-REC). 안전=본 영화 kNN 근접 Top N, 미탐색=안 가본 장르 대륙으로 분산한 저밀도.

흐름: detect_areas 가 안전 후보 풀(40)을 산출 → MMR 로 같은 봉우리 프랜차이즈 중복만 제거해 10편.
미탐색은 unexplored_by_continent 가 대륙별로 퍼뜨려 10편(A-15). 영화 메타(포스터·연도·평점) 보강.

미탐색이 MMR(좌표만 다양화)이 아니라 대륙 분산인 이유: 단일 도달밴드 최저밀도는 한 대륙(골짜기)에
수렴해 한 장르만 나온다(A-13). 앵커 좌표는 장르로 구조화돼 대륙 단위 분산이 다양성을 구조적으로 보장.
"""
import random

import numpy as np
from django.utils import timezone

from movies.models import Movie
from movies.serializers import MovieListSerializer

from .areas import detect_areas, safe_by_liked, unexplored_by_continent

SAFE_POOL = 40           # 폴백 MMR 후보 풀 크기(키워도 추천 다양성 불변 — 검증 A-09). 40으로 충분.
MMR_LAMBDA_SAFE = 0.7    # 폴백 안전: 적합도 우선 + 같은 봉우리 프랜차이즈 중복만 제거.
DAILY_PICK_MIN_VOTE = 7.0   # '오늘의 추천' 후보 최소 평점.


def get_recommendations(user, safe_n=10, unexplored_n=10):
    """안전(좋아한 영화별 고차원 kNN 라운드로빈)·미탐색(대륙 분산) 추천 + 영화 메타 + 오늘의 추천.

    안전은 safe_by_liked(고차원)가 1순위 — 2D 붕괴로 안전 10편이 클론이 되고 한 봉우리만 나오는
    문제를 좋아한 영화별 kNN 라운드로빈으로 해소(A-15, 무게중심 없이 A-08 원칙 유지). 고차원
    산출물(safe_vectors)이 없으면 옛 2D 안전(detect_areas + MMR)으로 폴백. enough=False면 빈 리스트."""
    result = detect_areas(user, safe_top=SAFE_POOL, unexplored_top=0)
    if result["enough"]:
        safe = safe_by_liked(user, safe_n)
        if safe is None:                 # 고차원 산출물 없음 → 옛 2D 안전
            safe = mmr_select(result["safe"], "distance", MMR_LAMBDA_SAFE, safe_n)
        result["safe"] = _enrich(safe, "distance")
        result["unexplored"] = _enrich(unexplored_by_continent(user, unexplored_n), "density")
        result["today"] = daily_pick(user)
    return result


def daily_pick(user):
    """오늘의 추천: 안 본 영화 중 평점 ≥ DAILY_PICK_MIN_VOTE 에서 '하루 한 편'.
    같은 날엔 고정(새로고침·영화 추가에도 불변), 자정 지나면 바뀐다.
    추천 엔진(KDE)과 무관한 단순 발견용 — 후보가 없으면 None.

    ※ 당첨작은 '추첨번호 최소' 영화 — 번호를 (날짜·유저·영화id)만으로 정해 후보 수·순서와
      무관하게 한다. 위치 인덱스(randrange(n))로 뽑으면 영화를 1편 추가(=후보에서 제외)할 때마다
      n과 인덱스가 밀려 당첨작이 바뀌는 버그가 있었다 — 모집단이 흔들려도 각 영화 번호는 불변이라
      당첨작 자신을 보기 전까진 하루 종일 고정된다."""
    day = timezone.localdate().isoformat()                  # 유저+날짜 → 하루 단위 고정
    watched_ids = set(user.watch_records.values_list("movie_id", flat=True))
    eligible = list(
        Movie.objects.filter(vote_average__gte=DAILY_PICK_MIN_VOTE)
        .exclude(id__in=watched_ids).values_list("id", flat=True)
    )
    if not eligible:
        return None
    pick_id = min(eligible, key=lambda mid: random.Random(f"{day}-{user.id}-{mid}").random())
    return MovieListSerializer(Movie.objects.get(id=pick_id)).data


def mmr_select(items, score_key, lam, n):
    """후보 풀에서 MMR로 n개 선별. 관련성(score_key, 낮을수록 좋음)과 다양성(이미 뽑힌 것과의
    2D 좌표 거리)을 λ로 절충: 점수 = λ·적합도 − (1−λ)·근접도. 풀 내 [0,1] 정규화."""
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
        if "continent" in it:           # 미탐색: 어느 장르 대륙에서 왔는지(프론트 라벨용)
            data["continent"] = it["continent"]
        out.append(data)
    return out
