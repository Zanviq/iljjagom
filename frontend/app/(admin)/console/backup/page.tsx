import { BackupPanel } from "@/components/admin/BackupPanel";

export default function ConsoleBackupPage() {
  return (
    <div>
      <h1 className="text-3xl font-extrabold">백업 / 복원</h1>
      <p className="mt-1 text-muted">
        데이터를 JSON으로 내보내고, 업로드로 복원해요. 복원은 확인·감사됩니다.
      </p>
      <div className="mt-6">
        <BackupPanel />
      </div>
    </div>
  );
}
