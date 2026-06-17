import { Pending } from "@/components/admin/Pending";

export default function ConsoleBackupPage() {
  return (
    <Pending
      title="백업 / 복원"
      describe="Supabase 데이터를 범위 선택해 내보내고(JSON), 업로드로 복원해요. 복원은 위험 작업이라 확인·감사 기록됩니다."
      endpoint="POST /admin/backup/export|import"
    />
  );
}
