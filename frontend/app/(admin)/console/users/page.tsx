import { Pending } from "@/components/admin/Pending";

export default function ConsoleUsersPage() {
  return (
    <Pending
      title="사용자 관리"
      describe="역할·학급·권한을 관리해요. 위험 변경은 확인 후 적용됩니다."
      endpoint="GET/PATCH /admin/users"
    />
  );
}
