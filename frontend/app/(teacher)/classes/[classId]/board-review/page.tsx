import { BoardReview } from "@/components/teacher/BoardReview";
import { TeacherHeader } from "@/components/teacher/TeacherHeader";

export default async function BoardReviewPage({
  params,
}: {
  params: Promise<{ classId: string }>;
}) {
  const { classId } = await params;

  return (
    <div>
      <TeacherHeader
        title="발표 승인"
        sub="학생이 발표한 이야기를 확인하고 학급에 공개해요."
      />
      <BoardReview classId={classId} />
    </div>
  );
}
