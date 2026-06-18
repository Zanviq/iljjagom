import { Icon } from "./Icon";

/**
 * Checkbox — 라운드 정사각 박스 + check(new-design_version2 forms/Checkbox).
 * controlled/uncontrolled 모두 지원. 체크 시각은 :checked(CSS)로 반영(universal).
 */
export function Checkbox({
  label,
  style,
  ...rest
}: {
  label?: React.ReactNode;
  style?: React.CSSProperties;
} & React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <label
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 10,
        cursor: rest.disabled ? "not-allowed" : "pointer",
        opacity: rest.disabled ? 0.5 : 1,
        ...style,
      }}
    >
      <span style={{ position: "relative", display: "inline-flex", flex: "none" }}>
        <input type="checkbox" className="ijg-checkbox-input" {...rest} />
        <span className="ijg-checkbox-box" aria-hidden>
          <Icon name="check" size={15} strokeWidth={3} className="ijg-checkbox-mark" />
        </span>
      </span>
      {label && (
        <span style={{ fontSize: "var(--text-base)", color: "var(--text-1)" }}>{label}</span>
      )}
    </label>
  );
}
