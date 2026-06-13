from django.db.models import Q
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from movies.models import Movie
from movies.serializers import MovieDetailSerializer, MovieListSerializer
from movies.services.tmdb import TMDBClient


class MovieListView(ListAPIView):
    # TODO: 인증 후 IsAuthenticated로 변경 (1.1)
    permission_classes = [AllowAny]
    serializer_class = MovieListSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search", "").strip()
        qs = Movie.objects.all()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(original_title__icontains=search))
        else:
            qs = qs.order_by("-vote_count")
        return qs


class MovieDetailView(RetrieveAPIView):
    # TODO: 인증 후 IsAuthenticated로 변경 (1.1)
    permission_classes = [AllowAny]
    serializer_class = MovieDetailSerializer
    queryset = Movie.objects.prefetch_related("genres")


class MovieExtrasView(APIView):
    # TODO: 인증 후 IsAuthenticated로 변경 (1.1)
    permission_classes = [AllowAny]

    def get(self, request, pk):
        movie = Movie.objects.filter(pk=pk).first()
        if not movie:
            return Response({"detail": "Not found."}, status=404)

        client = TMDBClient()
        ott = client.fetch_watch_providers(movie.tmdb_id)
        trailer = client.fetch_videos(movie.tmdb_id)

        return Response({"ott": ott, "trailer": trailer})
