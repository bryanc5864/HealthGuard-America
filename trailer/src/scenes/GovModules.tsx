import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  Sequence,
} from "remotion";
import { Audio, whoosh, ding } from "../utils/sfx";
import { display, body, mono } from "../utils/fonts";
import { c } from "../utils/colors";

// Simulated county dots for the map
const countyDots: Array<{ x: number; y: number; delay: number }> = [];
for (let i = 0; i < 80; i++) {
  countyDots.push({
    x: 120 + Math.random() * 700,
    y: 60 + Math.random() * 380,
    delay: Math.random() * 25,
  });
}

// Disease bars for ChronicCare dashboard
const diseases = [
  { name: "Diabetes", pct: 12.4, color: c.chroniccare },
  { name: "Obesity", pct: 34.2, color: c.drugwatch },
  { name: "Heart Disease", pct: 6.8, color: c.error },
  { name: "High BP", pct: 32.1, color: c.pricevision },
  { name: "COPD", pct: 7.3, color: c.ruralaccess },
  { name: "Depression", pct: 20.4, color: c.info },
];

export const GovModules: React.FC = () => {
  const frame = useCurrentFrame();

  // Dark theme shift
  const shiftOpacity = interpolate(frame, [0, 10], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Split screen reveal
  const splitReveal = interpolate(frame, [5, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Map dots light up in wave
  const getMapDotOpacity = (delay: number) => {
    return interpolate(frame, [10 + delay, 15 + delay], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  };
  const getMapDotScale = (delay: number) => {
    return interpolate(frame, [10 + delay, 15 + delay], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
  };

  // Disease bars animate
  const getDiseaseBarWidth = (i: number) => {
    const delay = 20 + i * 5;
    return interpolate(frame, [delay, delay + 15], [0, 100], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
  };

  // Stat pulse-in
  const getStatAnim = (delay: number) => {
    const scale = interpolate(frame, [delay, delay + 10], [0.5, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    const opacity = interpolate(frame, [delay, delay + 8], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return { scale, opacity };
  };

  // Fade out
  const fadeOut = interpolate(frame, [80, 95], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(135deg, ${c.primary900}, #0d1527)`,
        opacity: shiftOpacity * fadeOut,
      }}
    >
      {/* SFX */}
      <Sequence from={0}><Audio src={whoosh} volume={0.35} /></Sequence>
      <Sequence from={50}><Audio src={ding} volume={0.3} /></Sequence>
      <Sequence from={60}><Audio src={ding} volume={0.25} /></Sequence>

      {/* Government navbar */}
      <div
        style={{
          height: 48,
          background: `linear-gradient(135deg, ${c.primary900}, #1a3553)`,
          borderBottom: `2px solid ${c.secondary700}`,
          display: "flex",
          alignItems: "center",
          padding: "0 40px",
          gap: 8,
        }}
      >
        <span style={{ fontSize: 16, marginRight: 4 }}>🛡️</span>
        <span style={{ fontFamily: display, fontSize: 15, fontWeight: 700, color: c.white, letterSpacing: "-0.02em" }}>
          HealthGuard America
        </span>
        <span style={{ fontFamily: body, fontSize: 11, color: "rgba(255,255,255,0.4)", marginLeft: 8 }}>
          GOVERNMENT PORTAL
        </span>
        <div style={{ marginLeft: "auto", display: "flex", gap: 6 }}>
          {["RuralAccess", "ChronicCare"].map((m) => (
            <span
              key={m}
              style={{
                padding: "5px 12px",
                borderRadius: 8,
                background: "rgba(255,255,255,0.08)",
                fontFamily: body,
                fontSize: 12,
                color: "rgba(255,255,255,0.8)",
                fontWeight: 500,
              }}
            >
              {m}
            </span>
          ))}
        </div>
      </div>

      {/* Split screen content */}
      <div style={{ display: "flex", flex: 1, height: "calc(100% - 48px)" }}>
        {/* LEFT: RuralAccess Map */}
        <div
          style={{
            flex: 1,
            padding: 32,
            opacity: splitReveal,
            borderRight: `1px solid rgba(255,255,255,0.06)`,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: `${c.ruralaccess}20`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>
              🗺️
            </div>
            <div>
              <div style={{ fontFamily: display, fontSize: 18, fontWeight: 700, color: c.white }}>RuralAccess</div>
              <div style={{ fontFamily: body, fontSize: 11, color: "rgba(255,255,255,0.45)" }}>Healthcare Shortage Mapping</div>
            </div>
          </div>

          {/* Simulated map */}
          <div
            style={{
              background: "rgba(255,255,255,0.03)",
              borderRadius: 14,
              border: "1px solid rgba(255,255,255,0.06)",
              height: 440,
              position: "relative",
              overflow: "hidden",
            }}
          >
            {/* US outline approximation */}
            <div style={{ position: "absolute", inset: 0, opacity: 0.08 }}>
              <svg viewBox="0 0 960 600" width="100%" height="100%">
                <rect x="100" y="80" width="760" height="400" rx="20" fill="none" stroke="white" strokeWidth="1" />
              </svg>
            </div>

            {/* County dots lighting up */}
            {countyDots.map((dot, i) => {
              const dotOpacity = getMapDotOpacity(dot.delay);
              const dotScale = getMapDotScale(dot.delay);
              const pulsePhase = (frame + i * 3) % 40;
              const pulse = pulsePhase < 20 ? 1 : 0.6;
              return (
                <div
                  key={i}
                  style={{
                    position: "absolute",
                    left: dot.x,
                    top: dot.y,
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: c.ruralaccess,
                    opacity: dotOpacity * pulse,
                    transform: `scale(${dotScale})`,
                    boxShadow: `0 0 6px ${c.ruralaccess}80`,
                  }}
                />
              );
            })}

            {/* Legend */}
            <div
              style={{
                position: "absolute",
                bottom: 16,
                left: 16,
                padding: "8px 14px",
                borderRadius: 8,
                background: "rgba(0,0,0,0.6)",
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: c.ruralaccess }} />
              <span style={{ fontFamily: body, fontSize: 10, color: "rgba(255,255,255,0.7)" }}>
                Healthcare Shortage Area
              </span>
            </div>
          </div>

          {/* Stats below map */}
          <div style={{ display: "flex", gap: 16, marginTop: 16 }}>
            {[
              { val: "14,631", label: "HPSA Designations" },
              { val: "2,833", label: "Counties Affected" },
            ].map((s, i) => {
              const anim = getStatAnim(50 + i * 8);
              return (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    padding: "12px 16px",
                    borderRadius: 10,
                    background: "rgba(255,255,255,0.04)",
                    border: `1px solid ${c.ruralaccess}25`,
                    borderLeft: `3px solid ${c.ruralaccess}`,
                    opacity: anim.opacity,
                    transform: `scale(${anim.scale})`,
                  }}
                >
                  <div style={{ fontFamily: display, fontSize: 22, fontWeight: 800, color: c.ruralaccess }}>{s.val}</div>
                  <div style={{ fontFamily: body, fontSize: 10, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>{s.label}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* RIGHT: ChronicCare Dashboard */}
        <div style={{ flex: 1, padding: 32, opacity: splitReveal }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <div style={{ width: 36, height: 36, borderRadius: 8, background: `${c.chroniccare}20`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>
              ❤️
            </div>
            <div>
              <div style={{ fontFamily: display, fontSize: 18, fontWeight: 700, color: c.white }}>ChronicCare</div>
              <div style={{ fontFamily: body, fontSize: 11, color: "rgba(255,255,255,0.45)" }}>Disease Prediction & Analytics</div>
            </div>
          </div>

          {/* Disease prevalence bars */}
          <div
            style={{
              background: "rgba(255,255,255,0.03)",
              borderRadius: 14,
              border: "1px solid rgba(255,255,255,0.06)",
              padding: 20,
            }}
          >
            <div style={{ fontFamily: body, fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.6)", marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.06em" }}>
              County Disease Prevalence (%)
            </div>
            {diseases.map((d, i) => (
              <div key={i} style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontFamily: body, fontSize: 12, fontWeight: 500, color: "rgba(255,255,255,0.7)" }}>{d.name}</span>
                  <span style={{ fontFamily: mono, fontSize: 11, color: d.color }}>{d.pct}%</span>
                </div>
                <div style={{ height: 18, background: "rgba(255,255,255,0.06)", borderRadius: 4, overflow: "hidden" }}>
                  <div
                    style={{
                      width: `${(getDiseaseBarWidth(i) / 100) * d.pct * (100 / 40)}%`,
                      maxWidth: "100%",
                      height: "100%",
                      background: d.color,
                      borderRadius: 4,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Accuracy + intervention stats */}
          <div style={{ display: "flex", gap: 16, marginTop: 16 }}>
            {[
              { val: "93.9%", label: "Prediction Accuracy", color: c.chroniccare },
              { val: "2,956", label: "Counties Analyzed", color: c.chroniccare },
            ].map((s, i) => {
              const anim = getStatAnim(60 + i * 8);
              return (
                <div
                  key={i}
                  style={{
                    flex: 1,
                    padding: "12px 16px",
                    borderRadius: 10,
                    background: "rgba(255,255,255,0.04)",
                    border: `1px solid ${c.chroniccare}25`,
                    borderLeft: `3px solid ${c.chroniccare}`,
                    opacity: anim.opacity,
                    transform: `scale(${anim.scale})`,
                  }}
                >
                  <div style={{ fontFamily: display, fontSize: 22, fontWeight: 800, color: c.chroniccare }}>{s.val}</div>
                  <div style={{ fontFamily: body, fontSize: 10, color: "rgba(255,255,255,0.45)", textTransform: "uppercase", letterSpacing: "0.06em", fontWeight: 600 }}>{s.label}</div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
