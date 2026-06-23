from django.core.cache import cache
from django.db.models import Q
from django.db.models.functions import Lower
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from movies.models import Genre, Movie, WatchRecord
from movies.serializers import (
    MovieDetailSerializer,
    MovieListSerializer,
    MovieReviewSerializer,
    WatchRecordSerializer,
)
from movies.services.tmdb import TMDBClient


class MovieListView(ListAPIView):
    # 로그인 필수 (전역 IsAuthenticated 기본값 적용)
    serializer_class = MovieListSerializer

    def get_queryset(self):
        p = self.request.query_params
        search = p.get("search", "").strip()
        qs = Movie.objects.all()

        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(original_title__icontains=search))

        # 메인 '최근 추가된 영화'(F-MAIN, 김호준) — 검색 없을 때만, 기존 동작 유지
        if not search and p.get("sort") == "recent":
            qs = qs.order_by("-created_at")
            limit = p.get("limit")
            return qs[: int(limit)] if limit and limit.isdigit() else qs

        # --- 검색 페이지 필터 (F-MOV-01, 다중 적용 가능) ---
        genre = p.get("genre", "").strip()
        if genre:
            qs = qs.filter(genres__name=genre)

        language = p.get("language", "").strip()
        if language:
            qs = qs.filter(original_language=language)

        min_rating = p.get("min_rating")
        if min_rating:
            try:
                qs = qs.filter(vote_average__gte=float(min_rating))
            except ValueError:
                pass

        max_rating = p.get("max_rating")
        if max_rating:
            try:
                qs = qs.filter(vote_average__lte=float(max_rating))
            except ValueError:
                pass

        decade = p.get("decade")
        if decade and decade.isdigit():
            d = int(decade)
            qs = qs.filter(release_year__gte=d, release_year__lt=d + 10)

        runtime = p.get("runtime")
        if runtime == "short":
            qs = qs.filter(runtime__lt=90)
        elif runtime == "medium":
            qs = qs.filter(runtime__gte=90, runtime__lte=120)
        elif runtime == "long":
            qs = qs.filter(runtime__gt=120)

        # 정렬: 검색은 제목순(시리즈가 아이언맨→2→3로 묶임), 그 외는 평점 높은순
        if search:
            qs = qs.order_by(Lower("title"))
        else:
            qs = qs.order_by("-vote_average", "-vote_count")
        qs = qs.distinct()

        # 검색 페이지는 전체 반환(평점 높은순 스크롤). limit는 명시될 때만 적용.
        limit = p.get("limit")
        return qs[: int(limit)] if limit and limit.isdigit() else qs


class GenreListView(APIView):
    """검색 필터의 장르 드롭다운용 — 카탈로그에 실제 영화가 있는 장르명만 (F-MOV-01)."""

    def get(self, request):
        names = list(
            Genre.objects.filter(movies__isnull=False)
            .distinct()
            .order_by("name")
            .values_list("name", flat=True)
        )
        return Response(names)


class MovieDetailView(RetrieveAPIView):
    # 로그인 필수 (전역 IsAuthenticated 기본값 적용)
    serializer_class = MovieDetailSerializer
    queryset = Movie.objects.prefetch_related("genres", "keywords")


class MovieExtrasView(APIView):
    # 로그인 필수 (전역 IsAuthenticated 기본값 적용)
    # 예고편은 DB(Movie.trailer_key)로 옮겨 상세 응답에 포함 → 여기선 OTT만.
    # OTT는 자주 바뀌어 DB 저장 대신 6시간 캐싱(영화별, 전 유저 공유).

    OTT_TTL = 60 * 60 * 6  # 6시간

    def get(self, request, pk):
        movie = Movie.objects.filter(pk=pk).first()
        if not movie:
            return Response({"detail": "Not found."}, status=404)

        cache_key = f"ott:{movie.tmdb_id}"
        ott = cache.get(cache_key)
        if ott is None:  # 캐시 미스 → TMDB 실시간 1회, 이후 6시간 재사용
            ott = TMDBClient().fetch_watch_providers(movie.tmdb_id)
            cache.set(cache_key, ott, self.OTT_TTL)

        return Response({"ott": ott})


class MovieReviewsView(ListAPIView):
    """이 영화에 달린 전 유저 리뷰(리뷰 있는 것만), 최신순. (F-MOV-04)
    별점만 남기고 리뷰 없는 기록은 제외. 로그인 필수(전역 기본)."""
    serializer_class = MovieReviewSerializer

    def get_queryset(self):
        return (
            WatchRecord.objects.filter(movie_id=self.kwargs["pk"])
            .exclude(review__isnull=True)
            .exclude(review="")
            .select_related("user")
            .order_by("-created_at")
        )


class WatchRecordListCreateView(ListCreateAPIView):
    """내 시청기록 목록(GET) + 등록(POST). 별점 매겨 담기 = 여기.
    생성·삭제 시 taste 시그널이 사용자 좌표 자동 재계산(F-MAP-00)."""
    serializer_class = WatchRecordSerializer

    def get_queryset(self):
        return (
            WatchRecord.objects.filter(user=self.request.user)
            .select_related("movie")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WatchRecordDetailView(RetrieveUpdateDestroyAPIView):
    """시청기록 수정(PATCH: 별점·리뷰)·삭제(DELETE). 본인 것만."""
    serializer_class = WatchRecordSerializer

    def get_queryset(self):
        return WatchRecord.objects.filter(user=self.request.user).select_related("movie")
