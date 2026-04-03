import React from "react";
import { c } from "../utils/colors";
import { display, body } from "../utils/fonts";

export const Navbar: React.FC<{
  activeModule?: string;
}> = ({ activeModule }) => {
  const navItems = [
    { label: "Home", icon: "⌂" },
    { label: "PriceVision", icon: "$", color: c.pricevision },
    { label: "DrugWatch", icon: "💊", color: c.drugwatch },
    { label: "FoodScore", icon: "🧺", color: c.foodscore },
    { label: "Gov Portal", icon: "🏛️", color: c.primary600 },
  ];

  return (
    <div
      style={{
        height: 60,
        background: "rgba(255,255,255,0.95)",
        borderBottom: `1px solid ${c.neutral200}`,
        display: "flex",
        alignItems: "center",
        padding: "0 32px",
        gap: 8,
        flexShrink: 0,
      }}
    >
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: 32 }}>
        <span style={{ fontSize: 18, color: c.primary600 }}>🛡️</span>
        <span
          style={{
            fontFamily: display,
            fontSize: 17,
            fontWeight: 700,
            color: c.primary800,
            letterSpacing: "-0.03em",
          }}
        >
          HealthGuard America
        </span>
      </div>

      {/* Nav items */}
      {navItems.map((item) => {
        const isActive = item.label === activeModule;
        return (
          <div
            key={item.label}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              padding: "8px 14px",
              borderRadius: 10,
              background: isActive ? c.primary50 : "transparent",
              fontFamily: body,
              fontSize: 13,
              fontWeight: isActive ? 600 : 500,
              color: isActive ? c.primary700 : c.neutral600,
            }}
          >
            <span style={{ fontSize: 13, opacity: 0.85 }}>{item.icon}</span>
            {item.label}
          </div>
        );
      })}
    </div>
  );
};
