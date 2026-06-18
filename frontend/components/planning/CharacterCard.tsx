import { Avatar } from "@/components/ui/Avatar";
import { Card } from "@/components/ui/Card";
import { Chip } from "@/components/ui/Chip";
import type { PlanReply } from "@/lib/types";

/**
 * 기획 중 누적되는 인물 카드 미리보기(new-design_version2 CharacterPreview).
 * 대화로 주인공이 점점 또렷해진다.
 */
export function CharacterCard({
  draft,
}: {
  draft: PlanReply["characterDraft"];
}) {
  const name = draft.name || "이름은 아직 비밀";
  return (
    <Card tone="primary" padding="lg" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
      <p className="ijg-eyebrow" style={{ color: "var(--primary-text)" }}>
        인물 카드
      </p>
      <div className="flex items-center gap-3.5">
        <Avatar name={draft.name || "?"} size={56} />
        <div>
          <p
            style={{
              fontFamily: "var(--font-serif)",
              fontWeight: 600,
              fontSize: 26,
              color: "var(--text-1)",
            }}
          >
            {name}
          </p>
          <p className="text-[length:var(--text-sm)] text-ink-2">이야기의 주인공</p>
        </div>
      </div>
      {draft.traits.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {draft.traits.map((t, i) => (
            <Chip key={i} selected>
              {t}
            </Chip>
          ))}
        </div>
      )}
      <p
        className="text-[length:var(--text-sm)] text-ink-2"
        style={{ lineHeight: 1.6 }}
      >
        대화를 나눌수록 주인공이 점점 또렷해져요. 준비가 되면 이야기를 시작해요.
      </p>
    </Card>
  );
}
