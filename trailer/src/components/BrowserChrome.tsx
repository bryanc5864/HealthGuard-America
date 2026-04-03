import React from "react";
import { c } from "../utils/colors";

// Simulated browser window to frame website demos
export const BrowserChrome: React.FC<{
  accentColor?: string;
  url?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ accentColor = c.primary600, url = "healthguard-america.vercel.app", children, style }) => {
  return (
    <div
      style={{
        width: 1680,
        height: 920,
        borderRadius: 16,
        overflow: "hidden",
        boxShadow: "0 20px 80px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.08)",
        display: "flex",
        flexDirection: "column",
        ...style,
      }}
    >
      {/* Title bar */}
      <div
        style={{
          height: 42,
          background: c.neutral800,
          display: "flex",
          alignItems: "center",
          padding: "0 16px",
          gap: 10,
          borderBottom: `2px solid ${accentColor}40`,
          flexShrink: 0,
        }}
      >
        {/* Traffic lights */}
        <div style={{ display: "flex", gap: 7 }}>
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#ff5f57" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#febc2e" }} />
          <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#28c840" }} />
        </div>
        {/* URL bar */}
        <div
          style={{
            flex: 1,
            height: 26,
            background: c.neutral900,
            borderRadius: 6,
            display: "flex",
            alignItems: "center",
            paddingLeft: 12,
            marginLeft: 12,
          }}
        >
          <span style={{ color: "#28c840", fontSize: 11, marginRight: 6 }}>🔒</span>
          <span style={{ color: c.neutral400, fontSize: 12, fontFamily: "system-ui" }}>{url}</span>
        </div>
      </div>
      {/* Content */}
      <div style={{ flex: 1, overflow: "hidden", position: "relative" }}>
        {children}
      </div>
    </div>
  );
};
