/**
 * Switch — on/off 토글(new-design_version2 forms/Switch).
 * 관리자 설정·모니터링 플래그. controlled/uncontrolled. 상태는 :checked(CSS).
 */
export function Switch({
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
        <input
          type="checkbox"
          role="switch"
          className="ijg-checkbox-input"
          {...rest}
        />
        <span className="ijg-switch-track" aria-hidden>
          <span className="ijg-switch-knob" />
        </span>
      </span>
      {label && (
        <span style={{ fontSize: "var(--text-base)", color: "var(--text-1)" }}>{label}</span>
      )}
    </label>
  );
}
