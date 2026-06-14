from rest_framework import serializers

from movies.models import Genre, Movie


class MovieListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ["id", "tmdb_id", "title", "release_year", "poster_path", "vote_average"]


class MovieDetailSerializer(serializers.ModelSerializer):
    genres = serializers.SerializerMethodField()
    cast = serializers.SerializerMethodField()

    def get_genres(self, obj):
        return list(obj.genres.values_list("name", flat=True))

    def get_cast(self, obj):
        return [name.strip() for name in obj.cast.split(",") if name.strip()]

    class Meta:
        model = Movie
        fields = [
            "id", "tmdb_id", "title", "release_year", "poster_path", "vote_average",
            "overview", "director", "cast", "runtime", "original_language",
            "genres", "umap_x", "umap_y",
        ]
