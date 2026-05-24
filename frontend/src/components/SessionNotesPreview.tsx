import { useQuery } from "@tanstack/react-query";
import { getResult } from "../api/client";
import { NotesPreviewPanel } from "./NotesPreviewPanel";

interface Props {
  sessionId: string;
  enabled: boolean;
}

export function SessionNotesPreview({ sessionId, enabled }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["result", sessionId],
    queryFn: () => getResult(sessionId),
    enabled,
    staleTime: Infinity,
  });

  if (!enabled) return null;
  if (isLoading) {
    return (
      <p className="text-sm text-slate-400" role="status">
        Loading notes preview…
      </p>
    );
  }
  if (error) {
    return (
      <p className="text-sm text-red-400" role="alert">
        Could not load notes preview.
      </p>
    );
  }
  if (!data) return null;

  return <NotesPreviewPanel result={data} />;
}
