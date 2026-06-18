import { cn } from "@/lib/cn";
import { Icon } from "./Icon";

/**
 * ChatBubble — AI 기획 대화/우측 AI 채팅의 한 턴(new-design_version2 feedback/ChatBubble).
 * from="ai"=곰 작가(선두 마크 + surface 버블), from="me"=아이(primary, 우측 정렬).
 * streaming=true면 라이브 캐럿(.ijg-caret).
 */
export function ChatBubble({
  from = "ai",
  streaming = false,
  name,
  children,
  style,
  ...rest
}: {
  from?: "ai" | "me";
  streaming?: boolean;
  name?: React.ReactNode;
  children?: React.ReactNode;
  style?: React.CSSProperties;
} & Omit<React.HTMLAttributes<HTMLDivElement>, "color">) {
  const isAi = from === "ai";
  return (
    <div
      style={{
        display: "flex",
        flexDirection: isAi ? "row" : "row-reverse",
        alignItems: "flex-end",
        gap: 10,
        ...style,
      }}
      {...rest}
    >
      {isAi && (
        <span
          aria-hidden
          style={{
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            width: 34,
            height: 34,
            flex: "none",
            borderRadius: "calc(var(--radius-card) * 0.5)",
            background: "var(--primary)",
            color: "var(--on-primary)",
            boxShadow: "var(--elev-sm)",
          }}
        >
          <Icon name="sparkles" size={18} strokeWidth={2.25} />
        </span>
      )}
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 4,
          maxWidth: "78%",
          alignItems: isAi ? "flex-start" : "flex-end",
        }}
      >
        {name && (
          <span
            style={{
              fontSize: "var(--text-2xs)",
              fontWeight: 700,
              color: "var(--text-3)",
              padding: "0 4px",
            }}
          >
            {name}
          </span>
        )}
        <div
          className={cn(streaming && "ijg-caret")}
          style={{
            padding: "11px 15px",
            fontSize: "var(--text-md)",
            lineHeight: "var(--leading-normal)",
            color: isAi ? "var(--text-1)" : "var(--on-primary)",
            background: isAi ? "var(--surface-2)" : "var(--primary)",
            border: isAi ? "var(--border) solid var(--line)" : "none",
            borderRadius: "var(--radius-lg)",
            borderEndStartRadius: isAi ? 4 : "var(--radius-lg)",
            borderEndEndRadius: isAi ? "var(--radius-lg)" : 4,
            boxShadow: "var(--elev-sm)",
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
