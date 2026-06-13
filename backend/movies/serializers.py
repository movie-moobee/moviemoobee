from rest_framework import serializers

from movies.models import Genre, Movie


class MovieListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ["id", "tmdb_id", "title", "release_year", "poster_path", "vote_average"]


class MovieDetailSerializer(serializers.ModelSerializer):
    genres = serializers.SerializerMethodField()

    def get_genres(self, obj):
        return list(obj.genres.values_list("name", flat=True))

    class Meta:
        model = Movie
        fields = [
            "id", "tmdb_id", "title", "release_year", "poster_path", "vote_average",
            "overview", "director", "runtime", "original_language",
            "genres", "umap_x", "umap_y",
        ]
