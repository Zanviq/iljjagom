"use client";

import { useState } from "react";

import { ConfirmModal } from "@/components/admin/ConfirmModal";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorText } from "@/components/ui/ErrorText";
import { Select } from "@/components/ui/Select";
import { Textarea } from "@/components/ui/Textarea";
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
    <div className="flex flex-col gap-8">
      <Card padding="lg">
        <h2 className="text-[length:var(--text-md)] font-extrabold text-ink">
          내보내기
        </h2>
        <p className="mt-1 text-[length:var(--text-sm)] text-ink-2">
          전체 데이터를 JSON 파일로 내려받아요.
        </p>
        {exportError && <ErrorText className="mt-2">{exportError}</ErrorText>}
        <Button
          onClick={() => void doExport()}
          disabled={exporting}
          loading={exporting}
          icon="download"
          className="mt-3"
        >
          {exporting ? "내보내는 중…" : "JSON 내보내기"}
        </Button>
      </Card>

      <Card padding="lg">
        <h2 className="text-[length:var(--text-md)] font-extrabold text-ink">복원</h2>
        <p className="mt-1 text-[length:var(--text-sm)] text-ink-2">
          백업 JSON을 붙여넣어 복원해요. <strong>위험 작업</strong>이에요.
        </p>
        <Textarea
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            setResult(null);
          }}
          rows={5}
          spellCheck={false}
          placeholder='{"tables": { ... }}'
          className="mt-3"
          style={{ fontFamily: "var(--font-mono)", fontSize: 13 }}
        />
        <div className="mt-3 flex items-center gap-2">
          <Select
            value={mode}
            onChange={(e) => setMode(e.target.value as "merge" | "overwrite")}
            options={[
              { value: "merge", label: "병합(merge)" },
              { value: "overwrite", label: "덮어쓰기(overwrite)" },
            ]}
            style={{ width: "auto" }}
          />
          <Button
            variant="danger"
            onClick={() => setConfirm(true)}
            disabled={!text.trim()}
            className="flex-none"
          >
            복원 실행
          </Button>
        </div>
        {importError && <ErrorText className="mt-2">{importError}</ErrorText>}
        {result && (
          <p
            className="mt-3 text-[length:var(--text-sm)] font-bold"
            style={{ color: "var(--success-text)" }}
          >
            복원됨:{" "}
            {Object.entries(result)
              .map(([t, n]) => `${t} ${n}`)
              .join(", ")}
          </p>
        )}
      </Card>

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
