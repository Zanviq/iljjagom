"use client";

import { useState } from "react";

import { ConfirmModal } from "@/components/admin/ConfirmModal";
import { buttonClass } from "@/components/ui/Button";
import { ErrorText } from "@/components/ui/ErrorText";
import { ApiError, backupExport, backupImport } from "@/lib/api";
import { getClientAccessToken } from "@/lib/auth/client";

/** 데이터 백업/복원(추가기능 06). 내보내기=JSON 다운로드, 복원=확인 후 적용(위험). */
export function BackupPanel() {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);

  const [text, setText] = useState("");
  const [mode, setMode] = useState<"merge" | "overwrite">("merge");
  const [confirm, setConfirm] = useState(false);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, number> | null>(null);

  async function doExport() {
    setExporting(true);
    setExportError(null);
    try {
      const token = await getClientAccessToken();
      const data = await backupExport(token, null);
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `iljjagom-backup-${data.exportedAt ?? "export"}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setExportError(e instanceof ApiError ? e.message : "내보내지 못했어요.");
    } finally {
      setExporting(false);
    }
  }

  async function doImport() {
    let parsed: { tables: Record<string, unknown[]> };
    try {
      const obj = JSON.parse(text);
      parsed = { tables: obj.tables ?? obj };
    } catch {
      setImportError("JSON 형식이 올바르지 않아요.");
      setConfirm(false);
      return;
    }
    setImporting(true);
    setImportError(null);
    try {
      const token = await getClientAccessToken();
      const res = await backupImport(token, { mode, tables: parsed.tables });
      setResult(res.imported);
      setConfirm(false);
    } catch (e) {
      setImportError(e instanceof ApiError ? e.message : "복원하지 못했어요.");
    } finally {
      setImporting(false);
    }
  }

  return (
    <div className="space-y-8">
      <section className="rounded-card bg-surface p-5 ring-1 ring-border">
        <h2 className="text-lg font-bold">내보내기</h2>
        <p className="mt-1 text-sm text-muted">
          전체 데이터를 JSON 파일로 내려받아요.
        </p>
        {exportError && <ErrorText className="mt-2">{exportError}</ErrorText>}
        <button
          onClick={() => void doExport()}
          disabled={exporting}
          className={buttonClass("primary", "md", "mt-3")}
        >
          {exporting ? "내보내는 중…" : "JSON 내보내기"}
        </button>
      </section>

      <section className="rounded-card bg-surface p-5 ring-1 ring-border">
        <h2 className="text-lg font-bold">복원</h2>
        <p className="mt-1 text-sm text-muted">
          백업 JSON을 붙여넣어 복원해요. <strong>위험 작업</strong>이에요.
        </p>
        <textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setResult(null);
          }}
          rows={5}
          spellCheck={false}
          placeholder='{"tables": { ... }}'
          className="mt-3 w-full rounded-xl border-2 border-border bg-background p-3 font-mono text-sm"
        />
        <div className="mt-3 flex items-center gap-2">
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as "merge" | "overwrite")}
            className="rounded-lg border-2 border-border bg-background px-2 py-1.5 text-sm font-bold"
          >
            <option value="merge">병합(merge)</option>
            <option value="overwrite">덮어쓰기(overwrite)</option>
          </select>
          <button
            onClick={() => setConfirm(true)}
            disabled={!text.trim()}
            className={buttonClass("danger", "md")}
          >
            복원 실행
          </button>
        </div>
        {importError && <ErrorText className="mt-2">{importError}</ErrorText>}
        {result && (
          <p className="mt-3 text-sm font-bold text-success-strong">
            복원됨: {Object.entries(result).map(([t, n]) => `${t} ${n}`).join(", ")}
          </p>
        )}
      </section>

      {confirm && (
        <ConfirmModal
          title="복원 실행"
          body={
            <p>
              {mode === "overwrite" ? "덮어쓰기" : "병합"} 모드로 데이터를
              복원할까요? 되돌릴 수 없어요.
            </p>
          }
          confirmLabel="복원"
          pending={importing}
          onConfirm={() => void doImport()}
          onCancel={() => setConfirm(false)}
        />
      )}
    </div>
  );
}
