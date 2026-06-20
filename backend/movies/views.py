from django.db.models import Q
from rest_framework.generics import (
    ListAPIView,
    ListCreateAPIView,
    RetrieveAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.response import Response
from rest_framework.views import APIView

from movies.models import Movie, WatchRecord
from movies.serializers import (
    MovieDetailSerializer,
    MovieListSerializer,
    WatchRecordSerializer,
)
from movies.services.tmdb import TMDBClient


class MovieListView(ListAPIView):
    # 로그인 필수 (전역 IsAuthenticated 기본값 적용)
    serializer_class = MovieListSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search", "").strip()
        qs = Movie.objects.all()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(original_title__icontains=search))
        else:
            qs = qs.order_by("-vote_count")
        # ?limit=N (온보딩 인기 10편 등). 전체 카탈로그 통째 반환 방지.
        limit = self.request.query_params.get("limit")
        if limit and limit.isdigit():
            qs = qs[: int(limit)]
        return qs


class MovieDetailView(RetrieveAPIView):
    # 로그인 필수 (전역 IsAuthenticated 기본값 적용)
    serializer_class = MovieDetailSerializer
    queryset = Movie.objects.prefetch_related("genres", "keywords")


class MovieExtrasView(APIView):
    # 로그인 필수 (전역 IsAuthenticated 기본값 적용)

    def get(self, request, pk):
        movie = Movie.objects.filter(pk=pk).first()
        if not movie:
            return Response({"detail": "Not found."}, status=404)

        client = TMDBClient()
        ott = client.fetch_watch_providers(movie.tmdb_id)
        trailer = client.fetch_videos(movie.tmdb_id)

        return Response({"ott": ott, "trailer": trailer})


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
