import type { PlanReply } from "@/lib/types";

/** 기획 중 누적되는 인물 카드 미리보기. */
export function CharacterCard({
  draft,
}: {
  draft: PlanReply["characterDraft"];
}) {
  const hasContent = draft.name || draft.traits.length > 0;
  if (!hasContent) return null;

  return (
    <aside className="rounded-card bg-surface p-5 ring-1 ring-border">
      <h3 className="text-sm font-bold text-muted">우리 주인공</h3>
      <p className="mt-1 text-2xl font-extrabold">
        {draft.name || "이름은 아직 비밀"}
      </p>
      {draft.traits.length > 0 && (
        <ul className="mt-3 flex flex-wrap gap-2">
          {draft.traits.map((t, i) => (
            <li
              key={i}
              className="rounded-full bg-accent/40 px-3 py-1 text-sm font-bold"
            >
              {t}
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
