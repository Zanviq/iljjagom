import { Pending } from "@/components/admin/Pending";

export default function ConsoleSessionsPage() {
  return (
    <Pending
      title="AI 세션 / ReAct 트레이스"
      describe="동작 중·완료된 AI 세션의 역할·모델·스텝·토큰을 실시간/사후로 봐요."
      endpoint="GET /admin/sessions"
    />
  );
}
