import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Card } from "../components/Card";

describe("Card Component", () => {
  it("renders title, subtitle, and body children", () => {
    render(
      <Card title="Repository Overview" subtitle="Detailed statistics">
        <p>Active code metrics</p>
      </Card>
    );

    expect(screen.getByText("Repository Overview")).toBeInTheDocument();
    expect(screen.getByText("Detailed statistics")).toBeInTheDocument();
    expect(screen.getByText("Active code metrics")).toBeInTheDocument();
  });

  it("renders header action when provided", () => {
    render(
      <Card title="Security" action={<button>Action</button>}>
        <div>Card body</div>
      </Card>
    );

    expect(screen.getByRole("button", { name: /action/i })).toBeInTheDocument();
  });
});
