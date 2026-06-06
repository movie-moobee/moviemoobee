from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "시연용 데모 계정/시청기록/친구 시드 (개발자 A)"
    def handle(self, *args, **opts):
        # TODO: 데모 유저 + 시청기록(별점) + 친구관계 생성
        self.stdout.write("TODO: seed_demo")
