from django.core.cache import cache
from django.db.models import Count, Q
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from movies.models import Genre, Movie, ReviewComment, ReviewReaction, WatchRecord
from movies.serializers import (
    MovieDetailSerializer,
    MovieListSerializer,
    MovieReviewSerializer,
    ReviewCommentSerializer,
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
        genre_values = p.getlist("genre")
        if not genre_values:
            genre_values = p.getlist("genre[]")
        if not genre_values:
            genre_values = [p.get("genre", "")]
        genres = [g.strip() for value in genre_values for g in value.split(",") if g.strip()]
        if genres:
            for genre in genres:
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
    별점만 남기고 리뷰 없는 기록은 제외. 좋아요/싫어요 집계 포함(F-REV). 로그인 필수."""
    serializer_class = MovieReviewSerializer

    def get_queryset(self):
        return (
            WatchRecord.objects.filter(movie_id=self.kwargs["pk"])
            .exclude(review__isnull=True)
            .exclude(review="")
            .select_related("user")
            .annotate(
                # 반응·댓글 JOIN이 행을 곱하므로 각 집계 distinct 보정
                like_count=Count("reactions", filter=Q(reactions__value=1), distinct=True),
                dislike_count=Count("reactions", filter=Q(reactions__value=-1), distinct=True),
                comment_count=Count("comments", distinct=True),
            )
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        # 내가 이 영화 리뷰들에 한 반응을 1쿼리로 모아 주입 (record_id → value)
        ctx = super().get_serializer_context()
        pairs = ReviewReaction.objects.filter(
            user=self.request.user, record__movie_id=self.kwargs["pk"]
        ).values_list("record_id", "value")
        ctx["my_reactions"] = dict(pairs)
        return ctx


class ReviewReactionView(APIView):
    """리뷰(시청기록) 좋아요/싫어요 (F-REV). 로그인 필수.
    PUT {value: 1|-1} 설정/교체(멱등) · DELETE 취소. 자기 리뷰엔 반응 불가."""

    def _record(self, pk):
        return get_object_or_404(
            WatchRecord.objects.exclude(review__isnull=True).exclude(review=""), pk=pk
        )

    def _counts(self, record):
        agg = record.reactions.aggregate(
            like=Count("id", filter=Q(value=1)),
            dislike=Count("id", filter=Q(value=-1)),
        )
        return {"like_count": agg["like"], "dislike_count": agg["dislike"]}

    def put(self, request, pk):
        record = self._record(pk)
        if record.user_id == request.user.id:
            return Response({"detail": "자기 리뷰에는 반응할 수 없습니다."}, status=403)
        value = request.data.get("value")
        if value not in (1, -1, "1", "-1"):
            return Response({"detail": "value는 1(좋아요) 또는 -1(싫어요)이어야 합니다."}, status=400)
        ReviewReaction.objects.update_or_create(
            record=record, user=request.user, defaults={"value": int(value)}
        )
        return Response({**self._counts(record), "my_reaction": int(value)})

    def delete(self, request, pk):
        record = self._record(pk)
        ReviewReaction.objects.filter(record=record, user=request.user).delete()
        return Response({**self._counts(record), "my_reaction": None})


class ReviewCommentsView(ListCreateAPIView):
    """리뷰 댓글 목록(GET)·작성(POST) (F-REV, 평탄 구조). 오래된 순. 로그인 필수.
    GET  /api/movies/reviews/<pk>/comments/
    POST /api/movies/reviews/<pk>/comments/ {body}"""
    serializer_class = ReviewCommentSerializer

    def _record(self):
        return get_object_or_404(
            WatchRecord.objects.exclude(review__isnull=True).exclude(review=""),
            pk=self.kwargs["pk"],
        )

    def get_queryset(self):
        return ReviewComment.objects.filter(record_id=self.kwargs["pk"]).select_related("user")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, record=self._record())


class ReviewCommentDeleteView(APIView):
    """리뷰 댓글 삭제 (F-REV). 본인 댓글만.
    DELETE /api/movies/comments/<pk>/"""

    def delete(self, request, pk):
        comment = get_object_or_404(ReviewComment, pk=pk, user=request.user)
        comment.delete()
        return Response(status=204)


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
