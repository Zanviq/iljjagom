"use client";

import Link from "next/link";
import { useState } from "react";

import { CopyButton } from "@/components/teacher/CopyButton";
import { Badge } from "@/components/ui/Badge";
import { Button, buttonClass } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Icon } from "@/components/ui/Icon";
import { Input } from "@/components/ui/Input";
import {
  ApiError,
  createClass,
  rotateClassCode,
  updateClass,
} from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";
import type { ClassSummary } from "@/lib/types";

/**
 * 교사 학급 관리(04 기능개선 교사/01). 다중 학급 생성·이름 변경·코드 재발급.
 * 미구현 엔드포인트는 안내(graceful). 목록(getClasses)은 기존 라이브.
 */
export function ClassManager({ initial }: { initial: ClassSummary[] }) {
  const [classes, setClasses] = useState<ClassSummary[]>(initial);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    const name = newName.trim();
    if (!name || creating) return;
    setCreating(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      const created = await createClass(token, name);
      setClasses((cs) => [...cs, created]);
      setNewName("");
    } catch (e) {
      setError(friendly(e, "학급을 만들지 못했어요."));
    } finally {
      setCreating(false);
    }
  }

  function onRenamed(updated: ClassSummary) {
    setClasses((cs) => cs.map((c) => (c.id === updated.id ? updated : c)));
  }
  function onRotated(id: string, code: string) {
    setClasses((cs) => cs.map((c) => (c.id === id ? { ...c, code } : c)));
  }

  return (
    <div className="flex flex-col gap-6">
      <Card padding="lg">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void create();
          }}
          className="flex items-end gap-2.5"
        >
          <div className="flex-1">
            <p className="ijg-eyebrow mb-1.5" style={{ color: "var(--primary-text)" }}>
              새 학급 만들기
            </p>
            <Input
              icon="layout-grid"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="예: 3학년 2반 국어"
              aria-label="새 학급 이름"
            />
          </div>
          <Button
            type="submit"
            icon="plus"
            disabled={!newName.trim() || creating}
            loading={creating}
            className="flex-none"
          >
            만들기
          </Button>
        </form>
        {error && (
          <p className="mt-2 text-[length:var(--text-sm)] font-bold" style={{ color: "var(--danger-text)" }}>
            {error}
          </p>
        )}
      </Card>

      {classes.length === 0 ? (
        <EmptyState icon="layout-grid" title="아직 학급이 없어요">
          위에서 학급을 만들어 학생을 초대해요.
        </EmptyState>
      ) : (
        <div className="grid gap-4 [grid-template-columns:repeat(auto-fill,minmax(320px,1fr))]">
          {classes.map((c) => (
            <ClassCard
              key={c.id}
              cls={c}
              onRenamed={onRenamed}
              onRotated={onRotated}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ClassCard({
  cls,
  onRenamed,
  onRotated,
}: {
  cls: ClassSummary;
  onRenamed: (c: ClassSummary) => void;
  onRotated: (id: string, code: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(cls.name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function saveName() {
    const next = name.trim();
    if (!next || busy) return;
    if (next === cls.name) {
      setEditing(false);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      const updated = await updateClass(token, cls.id, next);
      onRenamed(updated);
      setEditing(false);
    } catch (e) {
      setError(friendly(e, "이름을 바꾸지 못했어요."));
    } finally {
      setBusy(false);
    }
  }

  async function rotate() {
    if (busy) return;
    setBusy(true);
    setError(null);
    try {
      const token = await getClientAccessToken();
      const res = await rotateClassCode(token, cls.id);
      onRotated(cls.id, res.code);
    } catch (e) {
      setError(friendly(e, "코드를 재발급하지 못했어요."));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card padding="lg" style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="flex items-center justify-between gap-2">
        {editing ? (
          <div className="flex flex-1 items-center gap-2">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              aria-label="학급 이름"
              className="flex-1"
            />
            <Button size="sm" icon="check" onClick={() => void saveName()} loading={busy} aria-label="저장" />
            <Button
              size="sm"
              variant="ghost"
              icon="x"
              onClick={() => {
                setName(cls.name);
                setEditing(false);
              }}
              aria-label="취소"
            />
          </div>
        ) : (
          <>
            <h3 className="truncate text-[length:var(--text-md)] font-extrabold text-ink">
              {cls.name}
            </h3>
            <div className="flex flex-none items-center gap-2">
              <Badge tone="info" icon="users">
                {cls.studentCount}명
              </Badge>
              <Button
                size="sm"
                variant="ghost"
                icon="pencil"
                onClick={() => setEditing(true)}
                aria-label="이름 변경"
              />
            </div>
          </>
        )}
      </div>

      <div className="flex items-center justify-between rounded-[var(--radius-card)] border border-line bg-surface-inset px-3.5 py-2.5">
        <div>
          <p className="text-[length:var(--text-2xs)] font-bold text-ink-3" style={{ letterSpacing: ".04em" }}>
            가입 코드
          </p>
          <p
            className="font-semibold text-ink"
            style={{ fontFamily: "var(--font-mono)", fontSize: 18, letterSpacing: ".05em" }}
          >
            {cls.code}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <Button
            size="sm"
            variant="ghost"
            icon="refresh-cw"
            onClick={() => void rotate()}
            loading={busy}
            aria-label="코드 재발급"
          />
          <CopyButton value={cls.code} />
        </div>
      </div>

      {error && (
        <p className="text-[length:var(--text-sm)] font-bold" style={{ color: "var(--danger-text)" }}>
          {error}
        </p>
      )}

      <div className="flex gap-2.5">
        <Link href={`/classes/${cls.id}/prompt`} className={buttonClass("outline", "sm", "flex-1")}>
          <Icon name="file-pen-line" size={16} />
          발제
        </Link>
        <Link href={`/classes/${cls.id}/dashboard`} className={buttonClass("solid", "sm", "flex-1")}>
          <Icon name="chart-no-axes-column" size={16} />
          대시보드
        </Link>
      </div>
      <Link href={`/classes/${cls.id}/safety`} className={buttonClass("ghost", "sm")}>
        <Icon name="shield-check" size={16} />
        안전 검토
      </Link>
    </Card>
  );
}

function friendly(e: unknown, fallback: string): string {
  if (e instanceof ApiError) {
    if (e.status === 404 || e.status === 0)
      return "이 기능을 준비하고 있어요. 조금만 기다려 주세요.";
    return e.message;
  }
  return fallback;
}
