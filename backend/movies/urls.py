from django.urls import path

from movies.views import MovieDetailView, MovieExtrasView, MovieListView

urlpatterns = [
    path("", MovieListView.as_view(), name="movie-list"),
    path("<int:pk>/", MovieDetailView.as_view(), name="movie-detail"),
    path("<int:pk>/extras/", MovieExtrasView.as_view(), name="movie-extras"),
]
