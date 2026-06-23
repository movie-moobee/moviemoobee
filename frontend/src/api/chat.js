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
  if (!res.ok || !res.body) throw new Error(`chat ${res.status}`);

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
      if (data === "[DONE]") return;
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
}
