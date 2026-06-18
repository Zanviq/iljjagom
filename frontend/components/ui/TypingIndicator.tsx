/**
 * TypingIndicator — AI 응답 대기 표시(회색 문구 + 점 3개 파동).
 * "아직 한 글자도 안 온 대기" 전용 — 실제 본문 스트리밍 캐럿(.ijg-caret)과 구분한다.
 * 곰 작가 기획 대화·총괄 드로어·자유집필 우측 대화 등에서 공통 사용.
 */
export function TypingIndicator({ label = "생각하고 있어요" }: { label?: string }) {
  return (
    <span
      className="ijg-typing"
      role="status"
      aria-live="polite"
      aria-label={`곰 작가가 ${label}`}
    >
      <span style={{ color: "var(--text-3)" }}>{label}</span>
      <span className="ijg-typing-dots" aria-hidden>
        <i style={{ "--i": 0 } as React.CSSProperties} />
        <i style={{ "--i": 1 } as React.CSSProperties} />
        <i style={{ "--i": 2 } as React.CSSProperties} />
      </span>
    </span>
  );
}
