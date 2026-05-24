import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { QualityReviewPanel } from "./QualityReviewPanel";

describe("QualityReviewPanel", () => {
  it("shows evaluation passed message", () => {
    render(
      <QualityReviewPanel
        evaluationPassed={true}
        diagramIssueCount={0}
        retryCount={0}
        canRegenerate={false}
        resuming={false}
        onResume={vi.fn()}
      />
    );
    expect(screen.getByText(/Evaluation passed/i)).toBeTruthy();
  });

  it("calls onResume when regenerate clicked", () => {
    const onResume = vi.fn();
    render(
      <QualityReviewPanel
        evaluationPassed={false}
        diagramIssueCount={2}
        retryCount={1}
        canRegenerate={true}
        resuming={false}
        onResume={onResume}
      />
    );
    fireEvent.click(screen.getByText(/Regenerate student notes/i));
    expect(onResume).toHaveBeenCalledWith("student_notes");
  });
});
