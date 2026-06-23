from django.urls import path

from movies.views import (
    GenreListView,
    MovieDetailView,
    MovieExtrasView,
    MovieListView,
    MovieReviewsView,
    ReviewCommentDeleteView,
    ReviewCommentsView,
    ReviewReactionView,
)

urlpatterns = [
    path("", MovieListView.as_view(), name="movie-list"),
    path("genres/", GenreListView.as_view(), name="movie-genres"),
    path("<int:pk>/", MovieDetailView.as_view(), name="movie-detail"),
    path("<int:pk>/extras/", MovieExtrasView.as_view(), name="movie-extras"),
    path("<int:pk>/reviews/", MovieReviewsView.as_view(), name="movie-reviews"),
    path("reviews/<int:pk>/reaction/", ReviewReactionView.as_view(), name="review-reaction"),
    path("reviews/<int:pk>/comments/", ReviewCommentsView.as_view(), name="review-comments"),
    path("comments/<int:pk>/", ReviewCommentDeleteView.as_view(), name="review-comment-delete"),
]
