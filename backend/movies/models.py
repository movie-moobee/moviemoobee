from django.db import models

class Genre(models.Model):
    tmdb_genre_id = models.IntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=50, unique=True)
    def __str__(self): return self.name

class Keyword(models.Model):
    name = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.name

class Movie(models.Model):
    # ERD: movies.  좌표는 전역 고정(개발자 A 파이프라인이 채움; fit 금지, transform 만)
    tmdb_id = models.BigIntegerField(unique=True)
    title = models.CharField(max_length=500)
    original_title = models.CharField(max_length=500, blank=True)
    overview = models.TextField(blank=True)
    release_date = models.DateField(null=True, blank=True)
    release_year = models.IntegerField(null=True, blank=True)
    runtime = models.IntegerField(null=True, blank=True)
    vote_average = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    vote_count = models.IntegerField(null=True, blank=True)
    original_language = models.CharField(max_length=10, blank=True)
    poster_path = models.CharField(max_length=500, blank=True)
    director = models.CharField(max_length=255, blank=True)
    umap_x = models.FloatField(null=True, blank=True)   # 전역 좌표 X
    umap_y = models.FloatField(null=True, blank=True)   # 전역 좌표 Y
    created_at = models.DateTimeField(auto_now_add=True)
    genres = models.ManyToManyField(Genre, related_name="movies", blank=True)
    keywords = models.ManyToManyField(Keyword, related_name="movies", blank=True)
    def __str__(self): return self.title

class WatchRecord(models.Model):
    # ERD: watch_records.  등록=별점 필수(F-WAT-01), 리뷰 선택.
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="watch_records")
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE, related_name="watch_records")
    rating = models.DecimalField(max_digits=2, decimal_places=1)   # 0.5 단위, 필수
    review = models.TextField(blank=True, null=True)               # 선택
    watched_on = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "movie"], name="uniq_user_movie")]
