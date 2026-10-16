import { describe, it, expect, beforeEach } from "vitest";
import { getStoredToken, setStoredToken, clearStoredToken } from "../services/apiClient";

describe("apiClient Token Storage", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("stores and retrieves auth token", () => {
    expect(getStoredToken()).toBeNull();
    setStoredToken("sample-jwt-token-xyz");
    expect(getStoredToken()).toBe("sample-jwt-token-xyz");
  });

  it("clears stored token", () => {
    setStoredToken("token-to-delete");
    expect(getStoredToken()).toBe("token-to-delete");
    clearStoredToken();
    expect(getStoredToken()).toBeNull();
  });
});
