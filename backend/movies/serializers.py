from decimal import Decimal

from rest_framework import serializers

from movies.models import Genre, Movie, ReviewComment, WatchRecord


class MovieListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = ["id", "tmdb_id", "title", "release_year", "poster_path", "vote_average"]


class MovieDetailSerializer(serializers.ModelSerializer):
    # ⚠️ my_record(요청 유저별)를 포함한다 → 이 응답은 절대 캐싱 금지.
    #    캐싱은 유저 무관 데이터(OTT extras)에만. 메타가 빨라 캐싱 불필요.
    genres = serializers.SerializerMethodField()
    keywords = serializers.SerializerMethodField()
    cast = serializers.SerializerMethodField()
    my_record = serializers.SerializerMethodField()

    def get_genres(self, obj):
        return list(obj.genres.values_list("name", flat=True))

    def get_keywords(self, obj):
        return list(obj.keywords.values_list("name", flat=True))

    def get_cast(self, obj):
        return [name.strip() for name in obj.cast.split(",") if name.strip()]

    def get_my_record(self, obj):
        # 안 본 영화면 None → 프론트가 등록/수정 버튼 분기. (F-WAT-01)
        user = self.context["request"].user
        rec = WatchRecord.objects.filter(user=user, movie=obj).first()
        if not rec:
            return None
        return {
            "id": rec.id,
            "rating": rec.rating,
            "review": rec.review,
            "watched_on": rec.watched_on,
        }

    class Meta:
        model = Movie
        fields = [
            "id", "tmdb_id", "title", "release_year", "poster_path", "vote_average",
            "overview", "director", "cast", "runtime", "original_language",
            "genres", "keywords", "trailer_key", "my_record", "map_x", "map_y",
        ]


class WatchRecordSerializer(serializers.ModelSerializer):
    """시청기록 CRUD (F-WAT-01/03/04 공용, 온보딩 F-ONB-01도 사용).
    rating 필수·0.5단위(F-WAT-02), review·watched_on 선택. user는 요청 토큰에서."""

    # 쓰기: movie는 id로 받음 / 읽기: 카드용 영화 정보 노출
    movie = serializers.PrimaryKeyRelatedField(queryset=Movie.objects.all(), write_only=True)
    movie_detail = MovieListSerializer(source="movie", read_only=True)

    class Meta:
        model = WatchRecord
        fields = ["id", "movie", "movie_detail", "rating", "review", "watched_on", "created_at"]
        read_only_fields = ["id", "created_at"]

    def validate_rating(self, value):
        # 0.5~5.0 범위 + 0.5 단위로 정규화 (round(x*2)/2)
        if value < Decimal("0.5") or value > Decimal("5.0"):
            raise serializers.ValidationError("별점은 0.5에서 5.0 사이여야 합니다.")
        return (value / Decimal("0.5")).quantize(Decimal("1")) * Decimal("0.5")

    def validate(self, attrs):
        # 중복 등록 방지(생성 시에만). 모델 UniqueConstraint를 깔끔한 400으로.
        if self.instance is None:
            user = self.context["request"].user
            if WatchRecord.objects.filter(user=user, movie=attrs["movie"]).exists():
                raise serializers.ValidationError({"movie": "이미 등록한 영화입니다."})
        return attrs


class MovieReviewSerializer(serializers.ModelSerializer):
    """상세의 이용자 리뷰 카드 (F-MOV-04 + F-REV 좋아요/싫어요).
    작성자 닉네임·아바타 + 별점·내용·작성일 + 반응 집계·내 반응·본인여부.

    like_count/dislike_count 는 뷰에서 annotate, my_reaction 은 context['my_reactions'] 주입.
    is_mine 이면 프론트가 반응 버튼을 숨긴다(자기 리뷰엔 반응 불가)."""

    nickname = serializers.CharField(source="user.nickname", read_only=True)
    profile_image_url = serializers.SerializerMethodField()
    like_count = serializers.IntegerField(read_only=True)
    dislike_count = serializers.IntegerField(read_only=True)
    comment_count = serializers.IntegerField(read_only=True)
    my_reaction = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    def get_profile_image_url(self, obj):
        # 프로필 사진(ImageField) → 절대 URL. 없으면 None.
        img = obj.user.profile_image
        if not img:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(img.url) if request else img.url

    def get_my_reaction(self, obj):
        # 내가 이 리뷰에 한 반응(1/-1) 또는 None — 뷰가 1쿼리로 모아 context에 주입
        return self.context.get("my_reactions", {}).get(obj.id)

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and obj.user_id == request.user.id)

    class Meta:
        model = WatchRecord
        fields = [
            "id", "nickname", "profile_image_url", "rating", "review", "created_at",
            "like_count", "dislike_count", "comment_count", "my_reaction", "is_mine",
        ]


class ReviewCommentSerializer(serializers.ModelSerializer):
    """리뷰 댓글 (F-REV, 평탄 구조). 작성자 닉네임·아바타 + 내용·작성일 + 본인여부.
    body 만 쓰기, 나머지는 읽기 전용. user/record 는 뷰에서 주입."""

    nickname = serializers.CharField(source="user.nickname", read_only=True)
    profile_image_url = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    def get_profile_image_url(self, obj):
        img = obj.user.profile_image
        if not img:
            return None
        request = self.context.get("request")
        return request.build_absolute_uri(img.url) if request else img.url

    def get_is_mine(self, obj):
        request = self.context.get("request")
        return bool(request and obj.user_id == request.user.id)

    class Meta:
        model = ReviewComment
        fields = ["id", "nickname", "profile_image_url", "body", "created_at", "is_mine"]
        read_only_fields = ["id", "created_at"]
