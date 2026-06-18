/**
 * Avatar — 이니셜 기반 신원 칩(new-design_version2 core/Avatar).
 * name/seed 해시로 색을 결정적으로 선택. 원형이 아닌 라운드 정사각(동화 모티프).
 */
const SIZES: Record<string, number> = { sm: 28, md: 40, lg: 56 };
const PALETTES: [string, string][] = [
  ["#f0a858", "#a85d18"],
  ["#8bba9c", "#3d684f"],
  ["#828ce6", "#353f9e"],
  ["#3dd6c4", "#0f8576"],
  ["#ecb24a", "#ac7613"],
  ["#e0857e", "#b5342a"],
];

function hashIndex(str = ""): number {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) | 0;
  return Math.abs(h) % PALETTES.length;
}

export function Avatar({
  name = "",
  seed,
  size = "md",
  src,
  style,
  ...rest
}: {
  name?: string;
  seed?: string;
  size?: "sm" | "md" | "lg" | number;
  src?: string;
  style?: React.CSSProperties;
} & Omit<React.HTMLAttributes<HTMLSpanElement>, "color">) {
  const px = typeof size === "number" ? size : SIZES[size] || 40;
  const [bg, fg] = PALETTES[hashIndex(seed || name)];
  const initial = (name.trim()[0] || "?").toUpperCase();
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: px,
        height: px,
        flex: "none",
        borderRadius: Math.round(px * 0.32),
        background: src ? "var(--surface-inset)" : bg,
        color: fg,
        fontFamily: "var(--font-serif)",
        fontWeight: "var(--weight-semibold)",
        fontSize: px * 0.42,
        lineHeight: 1,
        overflow: "hidden",
        userSelect: "none",
        ...style,
      }}
      {...rest}
    >
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt={name}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        initial
      )}
    </span>
  );
}
