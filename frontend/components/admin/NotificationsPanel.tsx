"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { buttonClass } from "@/components/ui/Button";
import { ErrorText } from "@/components/ui/ErrorText";
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
    <div className="space-y-8">
      <section className="rounded-card bg-surface p-5 ring-1 ring-border">
        <h2 className="text-lg font-bold">알림 보내기</h2>
        <div className="mt-3 flex flex-wrap gap-2">
          {TARGETS.map((t) => (
            <button
              key={t}
              onClick={() => setTarget(t)}
              className={`rounded-full px-3 py-1 text-sm font-bold ${
                target === t ? "bg-primary text-primary-foreground" : "bg-black/5"
              }`}
            >
              {TARGET_LABEL[t]}
            </button>
          ))}
          {target === "role" && (
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className="rounded-lg border-2 border-border bg-background px-2 py-1 text-sm"
            >
              <option value="student">학생</option>
              <option value="teacher">교사</option>
              <option value="admin">관리자</option>
            </select>
          )}
          {target === "user" && (
            <input
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="사용자 ID"
              className="rounded-lg border-2 border-border bg-background px-2 py-1 text-sm"
            />
          )}
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value as NotificationLevel)}
            className="rounded-lg border-2 border-border bg-background px-2 py-1 text-sm"
          >
            {LEVELS.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="제목"
          className="mt-3 w-full rounded-xl border-2 border-border bg-background px-4 py-2"
        />
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={2}
          placeholder="내용(선택)"
          className="mt-2 w-full resize-none rounded-xl border-2 border-border bg-background px-4 py-2"
        />
        {error && <ErrorText className="mt-2">{error}</ErrorText>}
        <button
          onClick={() => void send()}
          disabled={pending || !title.trim()}
          className={buttonClass("primary", "md", "mt-3")}
        >
          {pending ? "보내는 중…" : "보내기"}
        </button>
      </section>

      <section>
        <h2 className="mb-3 text-lg font-bold">수신함</h2>
        {notifications.length === 0 ? (
          <p className="rounded-card bg-surface p-5 text-muted ring-1 ring-border">
            알림이 없어요.
          </p>
        ) : (
          <ul className="space-y-2">
            {notifications.map((n) => (
              <li
                key={n.id}
                className="flex items-start gap-3 rounded-card bg-surface p-4 ring-1 ring-border"
              >
                <span
                  className={`mt-0.5 rounded-full px-2 py-0.5 text-xs font-bold ${
                    n.level === "error"
                      ? "bg-danger/10 text-danger"
                      : n.level === "warn"
                        ? "bg-accent/50 text-foreground"
                        : "bg-black/5 text-muted"
                  }`}
                >
                  {n.level}
                </span>
                <div className="flex-1">
                  <p className="font-bold">{n.title}</p>
                  {n.body && <p className="text-sm text-muted">{n.body}</p>}
                </div>
                {!n.readAt && (
                  <button
                    onClick={() => void read(n.id)}
                    className="rounded-lg px-2 py-1 text-sm font-bold text-primary-strong hover:bg-black/5"
                  >
                    읽음
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
