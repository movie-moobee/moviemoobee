from django.urls import path

from movies.views import (
    GenreListView,
    MovieDetailView,
    MovieExtrasView,
    MovieListView,
    MovieReviewsView,
)

urlpatterns = [
    path("", MovieListView.as_view(), name="movie-list"),
    path("genres/", GenreListView.as_view(), name="movie-genres"),
    path("<int:pk>/", MovieDetailView.as_view(), name="movie-detail"),
    path("<int:pk>/extras/", MovieExtrasView.as_view(), name="movie-extras"),
    path("<int:pk>/reviews/", MovieReviewsView.as_view(), name="movie-reviews"),
]
