import { Pending } from "@/components/admin/Pending";

export default function ConsoleSafetyPage() {
  return (
    <Pending
      title="안전"
      describe="안전 신호(safety_flags)와 보류된 편지를 전역으로 보고 해소해요. (교사 검토 03과 모델 공유)"
      endpoint="GET /admin/safety-flags"
    />
  );
}
