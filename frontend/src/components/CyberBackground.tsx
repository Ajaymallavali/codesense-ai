import React from "react";

export function CyberBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden z-0 select-none">
      {/* Top Edge Neon Laser Horizon Beam */}
      <div className="cyber-beam" />

      {/* Futuristic Cyber Dot & Line Matrix Grid */}
      <div className="absolute inset-0 cyber-grid-bg opacity-70" />

      {/* Floating Ambient Glowing Plasma Orbs */}
      <div
        className="absolute -top-40 right-1/4 h-[500px] w-[500px] rounded-full bg-emerald-500/10 blur-[120px] animate-orb-float-1 will-change-transform"
        style={{ transformOrigin: "center center" }}
      />
      <div
        className="absolute top-1/3 -left-28 h-[450px] w-[450px] rounded-full bg-teal-500/[0.08] blur-[110px] animate-orb-float-2 will-change-transform"
        style={{ transformOrigin: "center center" }}
      />
      <div
        className="absolute -bottom-36 right-1/3 h-[520px] w-[520px] rounded-full bg-emerald-600/[0.07] blur-[130px] animate-orb-float-3 will-change-transform"
        style={{ transformOrigin: "center center" }}
      />

      {/* Subtle Radial Vignette to keep focus centered and text high-contrast */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(8,12,20,0.45)_100%)]" />
    </div>
  );
}
