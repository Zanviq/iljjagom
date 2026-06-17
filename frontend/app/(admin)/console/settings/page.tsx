import { Pending } from "@/components/admin/Pending";

export default function ConsoleSettingsPage() {
  return (
    <Pending
      title="설정"
      describe="역할별 Gemini 모델·런타임 수치(rate limit·ReAct·알림주기)·환경변수 존재여부. 시크릿 값은 노출/저장하지 않아요."
      endpoint="GET/PUT /admin/settings"
    />
  );
}
