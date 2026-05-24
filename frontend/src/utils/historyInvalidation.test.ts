import { describe, it, expect } from "vitest";
import {
  isSessionTerminal,
  isCourseTerminal,
} from "./historyInvalidation";

describe("historyInvalidation", () => {
  it("detects session terminal states", () => {
    expect(isSessionTerminal("completed")).toBe(true);
    expect(isSessionTerminal("running")).toBe(false);
    expect(isSessionTerminal(undefined)).toBe(false);
  });

  it("detects course terminal states", () => {
    expect(isCourseTerminal("completed")).toBe(true);
    expect(isCourseTerminal("paused")).toBe(true);
    expect(isCourseTerminal("generating")).toBe(false);
  });
});
