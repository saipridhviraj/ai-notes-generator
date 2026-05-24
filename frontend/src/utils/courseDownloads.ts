import { getCourseStatus, getResult } from "../api/client";
import { downloadTextFile } from "./download";

export async function downloadCourseDayNotes(
  courseId: string,
  day: number,
  which: "student" | "tutor" | "both"
): Promise<void> {
  const status = await getCourseStatus(courseId);
  const sessionId = status.day_sessions[String(day)];
  if (!sessionId) return;

  const result = await getResult(sessionId);
  const dayLabel = String(day).padStart(2, "0");

  if (which === "student" || which === "both") {
    const name = result.student_file ?? `day_${dayLabel}_student_notes.md`;
    const body = result.student_markdown ?? "";
    if (body) downloadTextFile(name, body);
  }
  if (which === "tutor" || which === "both") {
    const name = result.tutor_file ?? `day_${dayLabel}_tutor_notes.md`;
    const body = result.tutor_markdown ?? "";
    if (body) downloadTextFile(name, body);
  }
}

export async function downloadAllCourseDays(
  courseId: string,
  which: "student" | "tutor" | "both"
): Promise<void> {
  const status = await getCourseStatus(courseId);
  const days = [...status.days_completed].sort((a, b) => a - b);
  for (const day of days) {
    await downloadCourseDayNotes(courseId, day, which);
  }
}

export async function downloadLatestCourseDay(
  courseId: string,
  which: "student" | "tutor" | "both"
): Promise<void> {
  const status = await getCourseStatus(courseId);
  const days = [...status.days_completed].sort((a, b) => a - b);
  if (days.length === 0) return;
  await downloadCourseDayNotes(courseId, days[days.length - 1], which);
}
