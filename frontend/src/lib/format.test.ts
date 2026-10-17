import { describe, expect, it } from "vitest";
import { STATUSES, STATUS_GROUPS, formatBytes, formatSalary } from "./format";

describe("formatBytes", () => {
  it("picks a sensible unit", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(3 * 1024 * 1024)).toBe("3.0 MB");
  });
});

describe("formatSalary", () => {
  const base = { salary_currency: "USD", salary_period: "year" as const };
  it("formats a range", () => {
    expect(formatSalary({ ...base, salary_min: 100000, salary_max: 150000 })).toContain("–");
  });
  it("is empty when nothing is set", () => {
    expect(formatSalary({ ...base, salary_min: null, salary_max: null })).toBe("");
  });
});

describe("STATUS_GROUPS", () => {
  it("only references known statuses", () => {
    for (const g of STATUS_GROUPS) {
      for (const s of g.statuses ?? []) expect(STATUSES).toContain(s);
    }
  });
});
