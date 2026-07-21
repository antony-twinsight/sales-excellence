import { describe, expect, it } from "vitest";
import { currency } from "./api";

describe("currency", () => {
  it("formats Australian dollars without cents", () => {
    expect(currency(1250000)).toContain("1,250,000");
  });
});
