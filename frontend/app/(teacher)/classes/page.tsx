import { ClassManager } from "@/components/teacher/ClassManager";
import { TeacherHeader } from "@/components/teacher/TeacherHeader";
import { getClasses } from "@/lib/api";
import { getAccessToken } from "@/lib/auth/server";

export default async function TeacherClassesPage() {
  const token = await getAccessToken();
  const { classes } = await getClasses(token);

  return (
    <div>
      <TeacherHeader title="내 학급" sub="학급을 만들고 학생을 초대해요." />
      <ClassManager initial={classes} />
    </div>
  );
}
