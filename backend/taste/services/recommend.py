"""추천 (F-REC). 안전=좌표 거리 Top N, 미탐색=KDE 저밀도(도달가능 밴드). 이미 본 영화 제외.

detect_areas(areas.py)가 안전·미탐색 후보(movie_id+score)를 한 번에 산출 → 여기선
추천 카드에 필요한 영화 메타(포스터·연도·평점)만 붙여 내려준다(엔드포인트 1개로 통합).
"""
from movies.models import Movie
from movies.serializers import MovieListSerializer

from .areas import detect_areas


def get_recommendations(user, safe_n=10, unexplored_n=10):
    """안전·미탐색 추천을 영화 메타까지 채워 반환. enough=False면 빈 리스트 그대로."""
    result = detect_areas(user, safe_top=safe_n, unexplored_top=unexplored_n)
    if result["enough"]:
        result["safe"] = _enrich(result["safe"], "distance")
        result["unexplored"] = _enrich(result["unexplored"], "density")
    return result


def _enrich(items, score_key):
    """[{movie_id, score}] → [MovieList 필드 + score]. detect_areas 순서(거리/밀도순) 보존."""
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
