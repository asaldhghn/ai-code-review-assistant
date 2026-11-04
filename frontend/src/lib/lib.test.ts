import { describe, expect, it } from "vitest";
import { countBySeverity, filterFindings, languageFromFilename, locationOf, NO_FILTERS } from "./findings";
import { review } from "../test/fixtures";

const { findings } = review();

describe("filterFindings", () => {
  it("returns everything with no filters", () => {
    expect(filterFindings(findings, NO_FILTERS)).toHaveLength(3);
  });
  it("filters by severity, by reviewer, and by both", () => {
    expect(filterFindings(findings, { severity: "critical", reviewer: "all" }).map((f) => f.id)).toEqual(["S1"]);
    expect(filterFindings(findings, { severity: "all", reviewer: "maintainability" }).map((f) => f.id)).toEqual(["M1", "M2"]);
    expect(filterFindings(findings, { severity: "critical", reviewer: "maintainability" })).toEqual([]);
  });
});

describe("helpers", () => {
  it("counts by severity within a reviewer", () => {
    expect(countBySeverity(findings, "maintainability")).toEqual({ critical: 0, warn: 1, info: 1 });
  });
  it("formats locations with and without a line", () => {
    expect(locationOf({ path: "a.py", line: 4 })).toBe("a.py:4");
    expect(locationOf({ path: "a.py", line: null })).toBe("a.py");
  });
  it("detects language from file names", () => {
    expect(languageFromFilename("app.TSX")).toBe("typescript");
    expect(languageFromFilename("notes.unknown")).toBeNull();
  });
});
