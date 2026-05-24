/** Mirror of utils/node_personas.py — keep in sync for live stream labels. */
export const NODE_PERSONAS: Record<
  string,
  { name: string; icon: string; task: string }
> = {
  planner: { name: "Curriculum Planner", icon: "📋", task: "Plan curriculum" },
  consult_tutor: { name: "Tutor Liaison", icon: "🤝", task: "Tutor review" },
  research: { name: "Research Analyst", icon: "🔍", task: "Research topic" },
  student_notes: { name: "Student Notes Writer", icon: "📘", task: "Write student notes" },
  tutor_notes: { name: "Tutor Guide Writer", icon: "📗", task: "Write tutor guide" },
  evaluator: { name: "Quality Evaluator", icon: "⭐", task: "Evaluate quality" },
  gap_bridger: { name: "Content Specialist", icon: "🔧", task: "Fill content gaps" },
  final_response: { name: "Publishing Assistant", icon: "💾", task: "Save & finish" },
};

export function personaForNode(nodeId: string | null) {
  if (!nodeId) return null;
  return NODE_PERSONAS[nodeId] ?? {
    name: nodeId.replace(/_/g, " "),
    icon: "🤖",
    task: nodeId.replace(/_/g, " "),
  };
}
