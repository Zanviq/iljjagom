import Link from "next/link";

import { CopyButton } from "@/components/teacher/CopyButton";
import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { buttonClass } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { getClasses } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function TeacherClassesPage() {
  const token = await getAccessToken();
  const { classes } = await getClasses(token);

  return (
    <div>
      <TeacherHeader title="내 학급" sub="학급을 확인하고 학생을 초대해요." />

      {classes.length === 0 ? (
        <EmptyState icon="layout-grid" title="아직 학급이 없어요">
          학급이 만들어지면 여기에 표시돼요.
        </EmptyState>
      ) : (
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(320px,1fr))]">
          {classes.map((c) => (
            <Card
              key={c.id}
              padding="lg"
              style={{ display: "flex", flexDirection: "column", gap: 16 }}
            >
              <div className="flex items-center justify-between">
                <h3 className="text-[length:var(--text-md)] font-extrabold text-ink">
                  {c.name}
                </h3>
                <Badge tone="info" icon="users">
                  {c.studentCount}명
                </Badge>
              </div>

              <div className="flex items-center justify-between rounded-[var(--radius-card)] border border-line bg-surface-inset px-3.5 py-2.5">
                <div>
                  <p
                    className="text-[length:var(--text-2xs)] font-bold text-ink-3"
                    style={{ letterSpacing: ".04em" }}
                  >
                    가입 코드
                  </p>
                  <p
                    className="font-semibold text-ink"
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: 18,
                      letterSpacing: ".05em",
                    }}
                  >
                    {c.code}
                  </p>
                </div>
                <CopyButton value={c.code} />
              </div>

              <div className="flex gap-2.5">
                <Link
                  href={`/classes/${c.id}/prompt`}
                  className={buttonClass("outline", "sm", "flex-1")}
                >
                  <Icon name="file-pen-line" size={16} />
                  발제
                </Link>
                <Link
                  href={`/classes/${c.id}/dashboard`}
                  className={buttonClass("solid", "sm", "flex-1")}
                >
                  <Icon name="chart-no-axes-column" size={16} />
                  대시보드
                </Link>
              </div>
              <Link
                href={`/classes/${c.id}/safety`}
                className={buttonClass("ghost", "sm")}
              >
                <Icon name="shield-check" size={16} />
                안전 검토
              </Link>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
