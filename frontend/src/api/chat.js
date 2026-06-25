// LLM 챗봇 SSE 스트리밍 (5.4). axios는 브라우저 스트리밍이 약해 fetch + ReadableStream 사용.
// streaming TextDecoder 로 멀티바이트(한글) 청크 경계도 안전하게 합친다.
// path 예: "/social/friends/72/cowatch/", "/taste/chat". onDelta(text) 로 토큰을 흘려준다.
export async function streamChat(path, messages, onDelta, signal) {
  const token = localStorage.getItem("token");
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Token ${token}` } : {}),
    },
    body: JSON.stringify({ messages }),
    signal,
  });
  // 일일 한도 초과(429): 본문 detail/사용량을 담아 LIMIT 에러로 던진다(호출측이 카운터·안내 처리).
  if (res.status === 429) {
    let body = {};
    try { body = await res.json(); } catch { /* noop */ }
    const err = new Error(body.detail || "오늘 사용 가능한 횟수를 모두 사용했어요.");
    err.code = "LIMIT";
    if (body.used != null) err.usage = { used: body.used, limit: body.limit };
    throw err;
  }
  if (!res.ok || !res.body) throw new Error(`chat ${res.status}`);

  // 응답 헤더의 잔여 사용량(있으면) — 스트림 끝까지 읽은 뒤 호출측에 반환.
  const usedH = res.headers.get("X-Cowatch-Used");
  const usage = usedH != null ? { used: Number(usedH), limit: Number(res.headers.get("X-Cowatch-Limit")) } : null;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf("\n\n")) >= 0) {     // SSE 이벤트 경계
      const ev = buf.slice(0, i).trim();
      buf = buf.slice(i + 2);
      if (!ev.startsWith("data:")) continue;
      const data = ev.slice(5).trim();
      if (data === "[DONE]") return usage;
      let parsed;
      try {
        parsed = JSON.parse(data);
      } catch {
        continue;   // 깨진/부분 청크는 무시
      }
      if (parsed.error) throw new Error(parsed.error);
      if (parsed.delta) onDelta(parsed.delta);
    }
  }
  return usage;
}
