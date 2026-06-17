import { Pending } from "@/components/admin/Pending";

export default function ConsoleMessagesPage() {
  return (
    <Pending
      title="대화 기록"
      describe="기획 인터뷰·편지·튜터 대화를 검색·열람해요. 열람도 감사 기록됩니다(미성년 데이터)."
      endpoint="GET /admin/messages"
    />
  );
}
