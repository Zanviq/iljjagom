import { BackupPanel } from "@/components/admin/BackupPanel";

export default function ConsoleBackupPage() {
  return (
    <div>
      <p className="ijg-eyebrow mb-4 text-ink-3">
        백업 / 복원 · JSON 내보내기·복원 (복원은 확인·감사)
      </p>
      <BackupPanel />
    </div>
  );
}
