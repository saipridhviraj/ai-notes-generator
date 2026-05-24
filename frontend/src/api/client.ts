import axios from "axios";

export const API_BASE = import.meta.env.VITE_API_URL ?? "";

// Resolved at runtime from /app-config — use getApiKey() in raw fetch() calls.
let _resolvedApiKey = import.meta.env.VITE_API_KEY ?? "";
export const getApiKey = () => _resolvedApiKey;

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

// Fetch the API key from the backend once and inject it into all future requests.
// This avoids baking the key into the Docker image at build time.
(async () => {
  try {
    const res = await axios.get<{ api_key: string }>(`${API_BASE}/app-config`);
    const key = res.data.api_key;
    if (key) {
      _resolvedApiKey = key;
      apiClient.defaults.headers.common["X-API-Key"] = key;
    }
  } catch {
    // Running locally without APP_API_KEY set — auth is disabled, carry on.
  }
})();

// ── Types ──────────────────────────────────────────────────────────────────

export interface GenerateResponse {
  session_id: string;
  status: string;
  message: string;
}

export interface StatusResponse {
  session_id: string;
  status: "running" | "awaiting_tutor" | "completed" | "failed" | "max_retries_reached" | "rejected" | "cancelled";
  current_node: string | null;
  node_label: string | null;
  active_persona: string | null;
  active_persona_icon: string | null;
  active_persona_blurb: string | null;
  elapsed_seconds: number;
  progress_percent: number;
  progress_step: number;
  progress_total: number;
  pipeline_steps: Array<{
    id: string;
    label: string;
    persona: string;
    persona_icon: string;
    state: "done" | "active" | "pending" | "skipped";
  }>;
  node_artifacts: NodeArtifactItem[];
  retry_count: number;
  tutor_question: string | null;
  output_files: string[];
  errors: string[];
  node_phase?: "starting" | "streaming" | null;
  status_detail?: string | null;
  evaluation_passed?: boolean | null;
  diagram_issue_count?: number;
  chat_history?: ChatMessage[];
  job_alive?: boolean | null;
  interrupted?: boolean;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  ts: number;
}

export interface SessionSummary {
  session_id: string;
  topic: string;
  status: string;
  start_time: number;
  has_notes: boolean;
  output_files: string[];
  chat_count: number;
  student_filename?: string | null;
  tutor_filename?: string | null;
}

export interface NodeArtifactItem {
  node_id: string;
  label: string;
  persona_icon: string;
  state: "done" | "active" | "pending" | "skipped";
  format: "markdown" | "json" | "text";
  available: boolean;
  char_count: number;
  preview: string | null;
  suggested_diagram_count?: number | null;
}

export interface NodeArtifactResponse {
  node_id: string;
  label: string;
  persona_icon: string;
  format: "markdown" | "json" | "text";
  content: string;
  char_count: number;
  suggested_diagrams?: string[] | null;
}

export interface TutorRespondRequest {
  approved: boolean;
  feedback: string;
  response_to: "plan_verification" | "error_clarification";
}

export interface ResultResponse {
  session_id: string;
  status: string;
  topic: string | null;
  student_file: string | null;
  tutor_file: string | null;
  student_markdown: string | null;
  tutor_markdown: string | null;
  evaluation_score: { student: number; tutor: number } | null;
  retry_count: number;
  used_web_search: boolean;
  summary: string | null;
}

// ── API functions ──────────────────────────────────────────────────────────

export async function startGeneration(topic: string, sessionId?: string): Promise<GenerateResponse> {
  const res = await apiClient.post<GenerateResponse>("/generate", {
    topic,
    session_id: sessionId ?? null,
  });
  return res.data;
}

export async function getStatus(sessionId: string): Promise<StatusResponse> {
  const res = await apiClient.get<StatusResponse>(`/status/${sessionId}`);
  return res.data;
}

export async function getNodeArtifact(
  sessionId: string,
  nodeId: string
): Promise<NodeArtifactResponse> {
  const res = await apiClient.get<NodeArtifactResponse>(
    `/artifacts/${sessionId}/${nodeId}`
  );
  return res.data;
}

export async function tutorRespond(
  sessionId: string,
  payload: TutorRespondRequest
): Promise<void> {
  await apiClient.post(`/tutor/respond/${sessionId}`, payload);
}

export async function cancelGeneration(sessionId: string): Promise<void> {
  await apiClient.post(`/cancel/${sessionId}`);
}

export async function restartGeneration(sessionId: string): Promise<void> {
  await apiClient.post(`/restart/${sessionId}`);
}

export type ResumeFromNode =
  | "research"
  | "student_notes"
  | "tutor_notes"
  | "evaluator"
  | "gap_bridger"
  | "mermaid_repair";

export async function resumeFromNode(
  sessionId: string,
  fromNode: ResumeFromNode
): Promise<{ session_id: string; from_node: string; status: string; message: string }> {
  const res = await apiClient.post(`/resume/${sessionId}`, { from_node: fromNode });
  return res.data;
}

export async function getResult(sessionId: string): Promise<ResultResponse> {
  const res = await apiClient.get<ResultResponse>(`/result/${sessionId}`);
  return res.data;
}

export async function listSessions(limit = 40): Promise<{ sessions: SessionSummary[] }> {
  const res = await apiClient.get<{ sessions: SessionSummary[] }>(`/sessions?limit=${limit}`);
  return res.data;
}

export async function sendSessionChat(
  sessionId: string,
  message: string
): Promise<{
  session_id: string;
  message: string;
  status: string;
  output_files: string[];
  chat_history: ChatMessage[];
}> {
  const res = await apiClient.post(`/sessions/${sessionId}/chat`, { message });
  return res.data;
}

export async function clearSessionChat(sessionId: string): Promise<{
  session_id: string;
  message: string;
  chat_history: ChatMessage[];
}> {
  const res = await apiClient.delete(`/sessions/${sessionId}/chat`);
  return res.data;
}

export async function deleteSession(sessionId: string): Promise<{ session_id: string; message: string }> {
  const res = await apiClient.delete(`/sessions/${sessionId}`);
  return res.data;
}

export async function deleteAllSessions(): Promise<{ deleted_count: number; message: string }> {
  const res = await apiClient.delete("/sessions");
  return res.data;
}

// ── Course (multi-day syllabus) ─────────────────────────────────────────────

export interface CourseSummary {
  course_id: string;
  course_name: string;
  status: string;
  start_time: number;
  total_days: number;
  days_completed_count: number;
  has_notes: boolean;
  chat_count: number;
}

export interface CoursePlanRequest {
  course_name: string;
  syllabus: string;
  total_days?: number;
  hours_per_day?: number;
  checkpoint_every?: number;
  programming_languages?: string[];
}

export interface CoursePlanResponse {
  course_id: string;
  status: string;
  course_name: string;
  total_days: number;
  output_root: string;
  days: Array<{ day: number; title: string; topic: string; duration_minutes: number }>;
  message: string;
}

export async function startCoursePlan(body: CoursePlanRequest): Promise<CoursePlanResponse> {
  const res = await apiClient.post<CoursePlanResponse>("/course/plan", body);
  return res.data;
}

export async function listCourses(limit = 50): Promise<{ courses: CourseSummary[] }> {
  const res = await apiClient.get<{ courses: CourseSummary[] }>("/course/courses", {
    params: { limit },
  });
  return res.data;
}

export async function respondCoursePlan(courseId: string, approved: boolean, feedback = ""): Promise<void> {
  await apiClient.post(`/course/${courseId}/plan/respond`, { approved, feedback });
}

export async function respondCourseCheckpoint(courseId: string, approved: boolean, feedback = ""): Promise<void> {
  await apiClient.post(`/course/${courseId}/checkpoint/respond`, { approved, feedback });
}

export interface CourseStatusResponse {
  course_id: string;
  status: string;
  course_name: string;
  total_days: number;
  days_completed: number[];
  next_day: number;
  progress_percent: number;
  output_root: string;
  checkpoint_every: number;
  hours_per_day: number;
  plan_days: Array<{
    day: number;
    title: string;
    topic: string;
    duration_minutes: number;
  }>;
  current_generating_day: number | null;
  current_day_title: string | null;
  current_session_id: string | null;
  checkpoint_message: string | null;
  plan_summary: string | null;
  day_outputs: Record<string, string[]>;
  day_sessions: Record<string, string>;
  errors: string[];
  batch_active?: boolean | null;
  interrupted?: boolean;
}

export async function cancelCourse(courseId: string): Promise<void> {
  await apiClient.post(`/course/${courseId}/cancel`);
}

export async function resumeCourseBatch(courseId: string): Promise<void> {
  await apiClient.post(`/course/${courseId}/resume-batch`);
}

export async function retryCourseDay(courseId: string, day?: number): Promise<void> {
  await apiClient.post(`/course/${courseId}/retry-day`, { day: day ?? null });
}

export async function deleteCourse(courseId: string): Promise<void> {
  await apiClient.delete(`/course/${courseId}`);
}

export async function deleteAllCourses(): Promise<{ message: string }> {
  const res = await apiClient.delete("/course/courses");
  return res.data;
}

export async function getCourseStatus(courseId: string): Promise<CourseStatusResponse> {
  const res = await apiClient.get<CourseStatusResponse>(`/course/${courseId}/status`);
  return res.data;
}
