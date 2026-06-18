"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorText } from "@/components/ui/ErrorText";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
import { cn } from "@/lib/cn";
import {
  ApiError,
  createNotification,
  markNotificationRead,
} from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { AppNotification, NotificationLevel, Role } from "@/lib/types";

const LEVELS: NotificationLevel[] = ["info", "warn", "error"];
const TARGETS = ["broadcast", "role", "user"] as const;
type Target = (typeof TARGETS)[number];
const TARGET_LABEL: Record<Target, string> = {
  broadcast: "전체",
  role: "역할",
  user: "사용자",
};
const LEVEL_TONE: Record<NotificationLevel, BadgeTone> = {
  info: "neutral",
  warn: "warning",
  error: "danger",
};

export function NotificationsPanel({
  notifications,
}: {
  notifications: AppNotification[];
}) {
  const router = useRouter();
  const [target, setTarget] = useState<Target>("broadcast");
  const [role, setRole] = useState<Role>("teacher");
  const [userId, setUserId] = useState("");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [level, setLevel] = useState<NotificationLevel>("info");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send() {
    if (!title.trim()) return;
    setPending(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      await createNotification(token, {
        title: title.trim(),
        body: body.trim() || undefined,
        level,
        ...(target === "broadcast" ? { isBroadcast: true } : {}),
        ...(target === "role" ? { targetRole: role } : {}),
        ...(target === "user" ? { targetUserId: userId.trim() } : {}),
      });
      setTitle("");
      setBody("");
      router.refresh();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "보내지 못했어요.");
    } finally {
      setPending(false);
    }
  }

  async function read(id: string) {
    try {
      const token = await getClientAccessToken();
      await markNotificationRead(token, id);
      router.refresh();
    } catch {
      // 무시
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <Card padding="lg">
        <h2 className="text-[length:var(--text-md)] font-extrabold text-ink">
          알림 보내기
        </h2>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {TARGETS.map((t) => (
            <button
              key={t}
              onClick={() => setTarget(t)}
              className={cn(
                "rounded-full px-3 py-1 text-[length:var(--text-sm)] font-bold transition",
                target === t
                  ? "bg-primary text-on-primary"
                  : "bg-surface-inset text-ink-2",
              )}
            >
              {TARGET_LABEL[t]}
            </button>
          ))}
          {target === "role" && (
            <Select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              options={[
                { value: "student", label: "학생" },
                { value: "teacher", label: "교사" },
                { value: "admin", label: "관리자" },
              ]}
              style={{ height: "var(--control-h-sm)", width: "auto" }}
            />
          )}
          {target === "user" && (
            <Input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="사용자 ID"
              style={{ height: "var(--control-h-sm)" }}
            />
          )}
          <Select
            value={level}
            onChange={(e) => setLevel(e.target.value as NotificationLevel)}
            options={LEVELS.map((l) => ({ value: l, label: l }))}
            style={{ height: "var(--control-h-sm)", width: "auto" }}
          />
        </div>
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="제목"
          className="mt-3"
        />
        <Textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={2}
          placeholder="내용(선택)"
          className="mt-2"
        />
        {error && <ErrorText className="mt-2">{error}</ErrorText>}
        <Button
          onClick={() => void send()}
          disabled={pending || !title.trim()}
          loading={pending}
          icon="send"
          className="mt-3"
        >
          {pending ? "보내는 중…" : "보내기"}
        </Button>
      </Card>

      <section>
        <h2 className="mb-3 text-[length:var(--text-md)] font-extrabold text-ink">
          수신함
        </h2>
        {notifications.length === 0 ? (
          <EmptyState icon="bell" title="알림이 없어요" />
        ) : (
          <div className="flex flex-col gap-2">
            {notifications.map((n) => (
              <Card key={n.id} padding="md">
                <div className="flex items-start gap-3">
                  <Badge tone={LEVEL_TONE[n.level] ?? "neutral"}>{n.level}</Badge>
                  <div className="flex-1">
                    <p className="font-bold text-ink">{n.title}</p>
                    {n.body && (
                      <p className="text-[length:var(--text-sm)] text-ink-2">
                        {n.body}
                      </p>
                    )}
                  </div>
                  {!n.readAt && (
                    <button
                      onClick={() => void read(n.id)}
                      className="rounded-[var(--radius-input)] px-2 py-1 text-[length:var(--text-sm)] font-bold text-primary-text hover:bg-surface-inset"
                    >
                      읽음
                    </button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
