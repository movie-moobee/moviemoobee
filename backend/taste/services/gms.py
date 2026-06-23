"""GMS(SSAFY LLM 게이트웨이) 클라이언트 — OpenAI 호환 chat/completions (5.4, 김호준).

엔드포인트만 GMS, 바디·응답은 OpenAI 동일. 키는 settings.GMS_KEY(.env) — 절대 클라이언트 노출 금지.

※ gpt-5-nano는 '추론(reasoning) 모델'이라 reasoning_effort 기본값이면 추론이 출력 토큰을
  전부 먹어 빈 응답(finish_reason=length)이 나온다 — 스모크(gms_smoke)로 확인. 챗봇은 깊은
  추론이 필요 없으므로 reasoning_effort='minimal'로 고정(추론토큰 0, 빠르고 저렴).
"""
import json

import requests
from django.conf import settings

REASONING_EFFORT = "minimal"
MAX_COMPLETION_TOKENS = 900
TIMEOUT = 60


def _headers():
    return {"Authorization": f"Bearer {settings.GMS_KEY}", "Content-Type": "application/json"}


def _body(messages, stream):
    return {
        "model": settings.GMS_MODEL,
        "messages": messages,
        "reasoning_effort": REASONING_EFFORT,
        "max_completion_tokens": MAX_COMPLETION_TOKENS,
        "stream": stream,
    }


def complete(messages):
    """비스트리밍 — 전체 응답 문자열 반환(system 내부용)."""
    r = requests.post(f"{settings.GMS_BASE_URL}/chat/completions",
                      headers=_headers(), json=_body(messages, False), timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def stream(messages):
    """스트리밍 — 콘텐츠 델타를 차례로 yield(유저 응답용). OpenAI SSE(data: {chunk}) 파싱."""
    with requests.post(f"{settings.GMS_BASE_URL}/chat/completions",
                       headers=_headers(), json=_body(messages, True),
                       stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue
            choices = chunk.get("choices") or []
            if choices:
                delta = choices[0].get("delta", {}).get("content")
                if delta:
                    yield delta
