import { describe, expect, it } from "vitest";
import { formatDate, INDIAN_STATES_AND_UTS, TRACKING_STATUS_OPTIONS } from "../lib/format";

describe("format utilities", () => {
  it("handles missing dates truthfully", () => {
    expect(formatDate(null)).toBe("Not fixed");
    expect(formatDate(undefined)).toBe("Not fixed");
  });

  it("includes Indian states and UTs and user-maintained statuses", () => {
    expect(INDIAN_STATES_AND_UTS.length).toBeGreaterThanOrEqual(35);
    expect(TRACKING_STATUS_OPTIONS.map((o) => o.value)).toContain("READY_TO_APPLY");
  });
});
