"""GMS(gpt-5-nano) 연결·파라미터 탐색용 스모크 (김호준, 5.4 착수 전 검증).

UI 붙이기 전에 ① 키 유효성·잔여 크레딧 ② 최소 호출 응답 포맷 ③ 스트리밍 포맷
④ max_completion_tokens 등 GPT-5 계열 파라미터 수용 여부를 raw 로 확인한다.
실행: python manage.py gms_smoke          (key-info + 최소 호출)
      python manage.py gms_smoke --stream (스트리밍 포맷 확인)
"""
import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "GMS(gpt-5-nano) 연결·응답 포맷 스모크 테스트"

    def add_arguments(self, parser):
        parser.add_argument("--stream", action="store_true", help="스트리밍 응답 포맷 확인")

    def handle(self, *args, **opts):
        if not settings.GMS_KEY:
            self.stderr.write("GMS_KEY 가 비어 있음 — .env 에 GMS_KEY=... 추가 필요")
            return
        headers = {"Authorization": f"Bearer {settings.GMS_KEY}", "Content-Type": "application/json"}

        # ① key-info — 키 유효성·잔여 크레딧
        self.stdout.write("=== key-info ===")
        try:
            r = requests.get("https://gms.ssafy.io/gmsapi/key-info", headers=headers, timeout=20)
            self.stdout.write(f"  status={r.status_code}  {r.text[:300]}")
        except requests.RequestException as e:
            self.stderr.write(f"  key-info 실패: {e}")

        url = f"{settings.GMS_BASE_URL}/chat/completions"
        messages = [
            {"role": "developer", "content": "Answer in Korean. 한 문장으로."},
            {"role": "user", "content": "영화 '인셉션'을 친구와 같이 볼 때 한 줄 추천 멘트를 써줘."},
        ]

        if opts["stream"]:
            # ③ 스트리밍 포맷
            self.stdout.write(f"\n=== stream (model={settings.GMS_MODEL}) ===")
            body = {"model": settings.GMS_MODEL, "messages": messages, "stream": True}
            try:
                with requests.post(url, headers=headers, json=body, stream=True, timeout=60) as r:
                    self.stdout.write(f"  status={r.status_code}")
                    if r.status_code != 200:
                        self.stderr.write(f"  err body: {r.text[:500]}")
                        return
                    for line in r.iter_lines(decode_unicode=True):
                        if line:
                            self.stdout.write(f"  {line[:160]}")
            except requests.RequestException as e:
                self.stderr.write(f"  stream 실패: {e}")
            return

        # ② 최소 호출 — 응답 raw + usage. (파라미터 없이 먼저)
        self.stdout.write(f"\n=== chat (model={settings.GMS_MODEL}, 최소 바디) ===")
        body = {"model": settings.GMS_MODEL, "messages": messages}
        try:
            r = requests.post(url, headers=headers, json=body, timeout=60)
            self.stdout.write(f"  status={r.status_code}")
            if r.status_code != 200:
                self.stderr.write(f"  err body: {r.text[:600]}")
                return
            data = r.json()
            self.stdout.write(f"  content: {data['choices'][0]['message']['content']!r}")
            self.stdout.write(f"  usage: {json.dumps(data.get('usage', {}), ensure_ascii=False)}")
            self.stdout.write(f"  finish_reason: {data['choices'][0].get('finish_reason')}")
        except requests.RequestException as e:
            self.stderr.write(f"  chat 실패: {e}")
            return

        # ④ max_completion_tokens 수용 여부 (GPT-5 계열은 max_tokens 거부 가능)
        self.stdout.write("\n=== chat + max_completion_tokens=200 ===")
        body2 = {"model": settings.GMS_MODEL, "messages": messages, "max_completion_tokens": 200}
        try:
            r = requests.post(url, headers=headers, json=body2, timeout=60)
            self.stdout.write(f"  status={r.status_code}  {'OK' if r.status_code == 200 else r.text[:400]}")
        except requests.RequestException as e:
            self.stderr.write(f"  실패: {e}")
