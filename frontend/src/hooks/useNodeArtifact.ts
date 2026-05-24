import { useCallback, useEffect, useState } from "react";
import { getNodeArtifact, type NodeArtifactItem, type NodeArtifactResponse } from "../api/client";

export function useNodeArtifact(sessionId: string, nodeId: string | null, available: boolean) {
  const [artifact, setArtifact] = useState<NodeArtifactResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!sessionId || !nodeId || !available) {
      setArtifact(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await getNodeArtifact(sessionId, nodeId);
      setArtifact(data);
    } catch {
      setError("Could not load node output.");
      setArtifact(null);
    } finally {
      setLoading(false);
    }
  }, [sessionId, nodeId, available]);

  useEffect(() => {
    load();
  }, [load]);

  return { artifact, loading, error, reload: load };
}

export type { NodeArtifactItem };
