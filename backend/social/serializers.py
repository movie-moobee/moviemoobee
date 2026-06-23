from rest_framework import serializers

from accounts.serializers import build_image_url
from .models import Friendship, Notification


class UserCardSerializer(serializers.Serializer):
    """친구 검색 결과 카드 (F-FRD-01). 닉네임·아바타·본 영화 편수 + 나와의 관계상태.

    watch_count 는 뷰에서 annotate(Count("watch_records")) 로 주입.
    relation 은 context["relation_map"][user_id] 에서 조회
    (none / friend / pending_sent / pending_received). 주취향 장르는 추후(F-FRD-05).
    """

    id = serializers.IntegerField()
    nickname = serializers.CharField()
    profile_image_url = serializers.SerializerMethodField()
    watch_count = serializers.IntegerField(read_only=True)
    relation = serializers.SerializerMethodField()

    def get_profile_image_url(self, obj):
        return build_image_url(obj.profile_image, self.context)

    def get_relation(self, obj):
        return self.context.get("relation_map", {}).get(obj.id, "none")


class ReceivedRequestSerializer(serializers.Serializer):
    """받은 친구 요청 카드 (F-FRD-03). friendship id + 요청자(requester) 정보."""

    id = serializers.IntegerField()          # friendship id (수락/거절 대상)
    created_at = serializers.DateTimeField()
    requester = serializers.SerializerMethodField()

    def get_requester(self, obj):
        u = obj.requester
        return {
            "id": u.id,
            "nickname": u.nickname,
            "profile_image_url": build_image_url(u.profile_image, self.context),
            "watch_count": u.watch_records.count(),
        }


class FriendSerializer(serializers.Serializer):
    """친구 목록 카드 (F-FRD-04). 닉네임·아바타·본 영화 편수.
    watch_count 는 뷰에서 annotate(Count("watch_records")) 로 주입."""

    id = serializers.IntegerField()
    nickname = serializers.CharField()
    profile_image_url = serializers.SerializerMethodField()
    watch_count = serializers.IntegerField(read_only=True)

    def get_profile_image_url(self, obj):
        return build_image_url(obj.profile_image, self.context)


class NotificationSerializer(serializers.Serializer):
    """알림 드롭다운 아이템 (F-NTF-01, 와이어프레임 14).

    type: friend_request(요청·수락/거절 버튼 포함) / friend_accept(수락됨).
    actor = 유발한 상대(요청자 또는 수락자). friendship 은 요청 알림의 수락/거절 대상.
    """

    id = serializers.IntegerField()
    type = serializers.CharField()
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    friendship_id = serializers.IntegerField(allow_null=True)  # 요청 알림의 수락/거절 대상 id
    friendship_status = serializers.SerializerMethodField()     # pending|accepted|None(폐기됨)
    actor = serializers.SerializerMethodField()

    def get_friendship_status(self, obj):
        return obj.friendship.status if obj.friendship_id else None

    def get_actor(self, obj):
        u = obj.actor
        return {
            "id": u.id,
            "nickname": u.nickname,
            "profile_image_url": build_image_url(u.profile_image, self.context),
        }


class FriendProfileSerializer(FriendSerializer):
    """친구 프로필 상세 (F-FRD-04, 화면 13 헤더). 목록 카드 + 친구의 시청작 그리드.
    취향 비교 지도(F-FRD-05)·챗봇(5.4)은 추후."""

    watched = serializers.SerializerMethodField()

    def get_watched(self, obj):
        recs = obj.watch_records.select_related("movie").order_by("-created_at")
        return [
            {
                "id": r.movie_id,
                "title": r.movie.title,
                "poster_path": r.movie.poster_path,
                "release_year": r.movie.release_year,
                "rating": float(r.rating),
            }
            for r in recs
        ]
