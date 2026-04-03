import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  Sequence,
} from "remotion";
import { Audio, pageTurn, mouseClick, ding } from "../utils/sfx";
import { display, body, mono } from "../utils/fonts";
import { c } from "../utils/colors";
import { BrowserChrome } from "../components/BrowserChrome";
import { Navbar } from "../components/Navbar";

export const DrugWatchDemo: React.FC = () => {
  const frame = useCurrentFrame();

  // Browser slide in from right
  const browserX = interpolate(frame, [0, 15], [200, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const browserOpacity = interpolate(frame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Search typing
  const searchText = "Ozempic";
  const typedChars = Math.floor(
    interpolate(frame, [12, 26], [0, searchText.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );

  // US price card
  const usCardY = interpolate(frame, [30, 42], [50, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const usCardOpacity = interpolate(frame, [30, 38], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // AU price card
  const auCardY = interpolate(frame, [40, 52], [50, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const auCardOpacity = interpolate(frame, [40, 48], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Savings badge pops in with scale bounce
  const savingsScale = interpolate(frame, [55, 65], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const savingsOpacity = interpolate(frame, [55, 62], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Bottom ticker scroll
  const tickerX = interpolate(frame, [60, 100], [400, -200], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const tickerOpacity = interpolate(frame, [60, 68], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Camera slow zoom
  const cameraScale = interpolate(frame, [0, 100], [0.88, 0.96], {
    extrapolateRight: "clamp",
  });

  // Fade out
  const fadeOut = interpolate(frame, [88, 100], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: c.neutral900, opacity: fadeOut }}>
      {/* SFX */}
      <Sequence from={0}><Audio src={pageTurn} volume={0.35} /></Sequence>
      <Sequence from={12}><Audio src={mouseClick} volume={0.3} /></Sequence>
      <Sequence from={55}><Audio src={ding} volume={0.4} /></Sequence>

      <AbsoluteFill
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          transform: `scale(${cameraScale}) translateX(${browserX}px)`,
          opacity: browserOpacity,
        }}
      >
        <BrowserChrome accentColor={c.drugwatch} url="healthguard-america.vercel.app/public/drugwatch/compare/semaglutide">
          <Navbar activeModule="DrugWatch" />

          {/* DrugWatch header */}
          <div
            style={{
              background: `linear-gradient(135deg, rgba(107,21,32,0.92), rgba(196,61,78,0.86))`,
              padding: "22px 40px 28px",
            }}
          >
            <div style={{ fontFamily: body, fontSize: 11, color: "rgba(255,255,255,0.5)", marginBottom: 6 }}>
              Home › DrugWatch › Compare
            </div>
            <div style={{ fontFamily: display, fontSize: 26, fontWeight: 800, color: "white" }}>
              🌐 International Price Comparison
            </div>
            <div style={{ fontFamily: body, fontSize: 13, color: "rgba(255,255,255,0.6)", marginTop: 2 }}>
              Compare US prices with international markets
            </div>
          </div>

          {/* Content area */}
          <div style={{ display: "flex", padding: "24px 40px", gap: 24, background: c.neutral50, flex: 1 }}>
            {/* Left: Price by country table */}
            <div style={{ flex: 2 }}>
              {/* Search bar */}
              <div
                style={{
                  background: c.white,
                  borderRadius: 12,
                  border: `1px solid ${c.neutral200}`,
                  padding: "10px 16px",
                  display: "flex",
                  alignItems: "center",
                  marginBottom: 20,
                }}
              >
                <span style={{ marginRight: 8, color: c.neutral400 }}>🔍</span>
                <span style={{ fontFamily: body, fontSize: 14, color: typedChars > 0 ? c.neutral800 : c.neutral400 }}>
                  {typedChars > 0 ? searchText.slice(0, typedChars) : "Search drugs..."}
                </span>
              </div>

              {/* Country price comparison */}
              <div style={{ background: c.white, borderRadius: 14, border: `1px solid ${c.neutral200}`, overflow: "hidden" }}>
                <div style={{ background: c.drugwatchLight, padding: "12px 20px", borderBottom: `1px solid ${c.neutral200}` }}>
                  <span style={{ fontFamily: display, fontSize: 14, fontWeight: 700, color: c.drugwatchDark }}>
                    📋 Price by Country
                  </span>
                </div>

                {/* US Row */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "14px 20px",
                    borderBottom: `1px solid ${c.neutral100}`,
                    background: c.drugwatchLight + "40",
                    opacity: usCardOpacity,
                    transform: `translateY(${usCardY}px)`,
                  }}
                >
                  <span style={{ fontSize: 24, marginRight: 12 }}>🇺🇸</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: body, fontSize: 14, fontWeight: 600, color: c.neutral800 }}>United States</div>
                    <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500 }}>Ozempic (Semaglutide)</div>
                  </div>
                  <div style={{ fontFamily: mono, fontSize: 26, fontWeight: 500, color: c.drugwatch }}>
                    $496.25
                  </div>
                  <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500, marginLeft: 8 }}>/unit</div>
                </div>

                {/* Australia Row */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "14px 20px",
                    background: c.foodscoreLight + "40",
                    opacity: auCardOpacity,
                    transform: `translateY(${auCardY}px)`,
                  }}
                >
                  <span style={{ fontSize: 24, marginRight: 12 }}>🇦🇺</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontFamily: body, fontSize: 14, fontWeight: 600, color: c.neutral800 }}>Australia</div>
                    <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500 }}>Ozempic (Semaglutide)</div>
                  </div>
                  <div style={{ fontFamily: mono, fontSize: 26, fontWeight: 500, color: c.foodscore }}>
                    $72.44
                  </div>
                  <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500, marginLeft: 8 }}>/unit</div>
                  <div
                    style={{
                      marginLeft: 12,
                      padding: "3px 10px",
                      borderRadius: 9999,
                      background: c.foodscoreLight,
                      color: c.foodscoreDark,
                      fontFamily: body,
                      fontSize: 11,
                      fontWeight: 700,
                    }}
                  >
                    −85%
                  </div>
                </div>
              </div>
            </div>

            {/* Right: Savings card */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Savings card */}
              <div
                style={{
                  background: `linear-gradient(135deg, ${c.foodscore}, ${c.foodscoreDark})`,
                  borderRadius: 14,
                  padding: "28px 24px",
                  textAlign: "center",
                  transform: `scale(${savingsScale})`,
                  opacity: savingsOpacity,
                  boxShadow: `0 8px 32px ${c.foodscore}40`,
                }}
              >
                <div style={{ fontFamily: body, fontSize: 12, color: "rgba(255,255,255,0.7)", marginBottom: 4, textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600 }}>
                  Potential Savings
                </div>
                <div style={{ fontFamily: display, fontSize: 42, fontWeight: 800, color: c.white, lineHeight: 1 }}>
                  $423.82
                </div>
                <div style={{ fontFamily: body, fontSize: 12, color: "rgba(255,255,255,0.6)", marginTop: 4 }}>
                  per unit vs US price
                </div>
                <div
                  style={{
                    marginTop: 16,
                    display: "inline-flex",
                    padding: "6px 16px",
                    borderRadius: 9999,
                    background: "rgba(255,255,255,0.2)",
                    fontFamily: display,
                    fontSize: 24,
                    fontWeight: 800,
                    color: c.white,
                  }}
                >
                  85% SAVINGS
                </div>
              </div>

              {/* Drug details card */}
              <div
                style={{
                  background: c.white,
                  borderRadius: 14,
                  border: `1px solid ${c.neutral200}`,
                  padding: 20,
                  opacity: interpolate(frame, [50, 58], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                }}
              >
                <div style={{ fontFamily: display, fontSize: 13, fontWeight: 700, color: c.neutral700, marginBottom: 12 }}>
                  💊 Drug Details
                </div>
                {[
                  { label: "Brand", value: "Ozempic" },
                  { label: "Generic", value: "Semaglutide" },
                  { label: "Spending", value: "$9.19B" },
                ].map((row, i) => (
                  <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: i < 2 ? `1px solid ${c.neutral100}` : "none" }}>
                    <span style={{ fontFamily: body, fontSize: 12, color: c.neutral500 }}>{row.label}</span>
                    <span style={{ fontFamily: body, fontSize: 12, fontWeight: 600, color: c.neutral800 }}>{row.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </BrowserChrome>
      </AbsoluteFill>

      {/* Bottom ticker */}
      <div
        style={{
          position: "absolute",
          bottom: 30,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          opacity: tickerOpacity,
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 32,
            fontFamily: body,
            fontSize: 14,
            fontWeight: 600,
            color: c.neutral400,
            transform: `translateX(${tickerX}px)`,
          }}
        >
          <span>$276B Medicare spending tracked</span>
          <span style={{ color: c.neutral600 }}>•</span>
          <span>500+ high-spend drugs</span>
          <span style={{ color: c.neutral600 }}>•</span>
          <span>US vs Canada vs Australia</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
