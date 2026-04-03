import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  Sequence,
} from "remotion";
import { Audio, shutterModern, uiSwitch, ding } from "../utils/sfx";
import { display, body, mono } from "../utils/fonts";
import { c } from "../utils/colors";
import { BrowserChrome } from "../components/BrowserChrome";
import { Navbar } from "../components/Navbar";

export const FoodScoreDemo: React.FC = () => {
  const frame = useCurrentFrame();

  // Camera zoom through effect (starts zoomed out, pushes in)
  const cameraScale = interpolate(frame, [0, 15, 100], [0.6, 0.9, 0.98], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const cameraOpacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Barcode scan animation: line sweeps
  const scanLineY = interpolate(frame, [12, 30], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scanActive = frame >= 12 && frame <= 30;

  // Bad product card flips in
  const badCardScale = interpolate(frame, [32, 42], [0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const badCardOpacity = interpolate(frame, [32, 38], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const badCardRotate = interpolate(frame, [32, 42], [-5, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Good product card
  const goodCardScale = interpolate(frame, [50, 60], [0.8, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const goodCardOpacity = interpolate(frame, [50, 56], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const goodCardRotate = interpolate(frame, [50, 60], [5, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // NOVA bars animate
  const novaBarWidth = (i: number) => {
    const delay = 65 + i * 5;
    return interpolate(frame, [delay, delay + 12], [0, 100], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
  };

  // Stats overlay
  const statsOpacity = interpolate(frame, [78, 88], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fade out
  const fadeOut = interpolate(frame, [95, 108], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const novaData = [
    { label: "Unprocessed", count: "3,943", pct: 12.5, color: c.foodscore },
    { label: "Culinary", count: "625", pct: 2, color: c.info },
    { label: "Processed", count: "4,825", pct: 15.2, color: c.pricevision },
    { label: "Ultra-Processed", count: "22,277", pct: 70.3, color: c.drugwatch },
  ];

  return (
    <AbsoluteFill style={{ background: c.neutral900, opacity: fadeOut }}>
      {/* SFX */}
      <Sequence from={12}><Audio src={shutterModern} volume={0.35} /></Sequence>
      <Sequence from={32}><Audio src={uiSwitch} volume={0.35} /></Sequence>
      <Sequence from={50}><Audio src={ding} volume={0.35} /></Sequence>

      <AbsoluteFill
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          transform: `scale(${cameraScale})`,
          opacity: cameraOpacity,
        }}
      >
        <BrowserChrome accentColor={c.foodscore} url="healthguard-america.vercel.app/public/foodscore/product">
          <Navbar activeModule="FoodScore" />

          {/* FoodScore header */}
          <div
            style={{
              background: `linear-gradient(135deg, rgba(15,60,32,0.92), rgba(30,168,90,0.86))`,
              padding: "20px 40px 24px",
            }}
          >
            <div style={{ fontFamily: body, fontSize: 11, color: "rgba(255,255,255,0.5)", marginBottom: 6 }}>
              Home › FoodScore › Product Analysis
            </div>
            <div style={{ fontFamily: display, fontSize: 26, fontWeight: 800, color: "white" }}>
              🧺 FoodScore
            </div>
            <div style={{ fontFamily: body, fontSize: 13, color: "rgba(255,255,255,0.6)", marginTop: 2 }}>
              AI-powered health scoring for 50,000+ food products
            </div>
          </div>

          {/* Content */}
          <div style={{ display: "flex", padding: "20px 40px", gap: 24, background: c.neutral50, flex: 1 }}>
            {/* Left: Product cards comparison */}
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
              {/* Scan animation indicator */}
              {scanActive && (
                <div style={{ position: "relative", height: 40, background: c.neutral200, borderRadius: 10, overflow: "hidden" }}>
                  <div
                    style={{
                      position: "absolute",
                      top: `${scanLineY}%`,
                      left: 0,
                      right: 0,
                      height: 3,
                      background: c.foodscore,
                      boxShadow: `0 0 12px ${c.foodscore}`,
                    }}
                  />
                  <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontFamily: mono, fontSize: 12, color: c.neutral500 }}>
                    ▐▐▐ ▌▐▌▐ ▐▐▐▐ ▌▐▌▐ ▐▐▐
                  </div>
                </div>
              )}

              {/* BAD product card */}
              <div
                style={{
                  background: c.white,
                  borderRadius: 14,
                  border: `2px solid ${c.error}30`,
                  padding: 20,
                  opacity: badCardOpacity,
                  transform: `scale(${badCardScale}) rotate(${badCardRotate}deg)`,
                  boxShadow: `0 4px 20px ${c.error}15`,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div>
                    <div style={{ fontFamily: display, fontSize: 16, fontWeight: 700, color: c.neutral800 }}>
                      Wavy Potato Chips, Cheddar & Sour Cream
                    </div>
                    <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500 }}>Spartan</div>
                  </div>
                  {/* NOVA 4 badge */}
                  <div style={{ padding: "4px 12px", borderRadius: 9999, background: c.drugwatchLight, color: c.drugwatchDark, fontFamily: body, fontSize: 12, fontWeight: 700 }}>
                    NOVA 4
                  </div>
                </div>
                {/* Score */}
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      width: 64, height: 64, borderRadius: 12,
                      background: `linear-gradient(135deg, ${c.error}, ${c.drugwatchDark})`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontFamily: display, fontSize: 28, fontWeight: 800, color: c.white,
                    }}
                  >
                    23
                  </div>
                  <div>
                    <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500 }}>MAHA Health Score</div>
                    <div style={{ fontFamily: body, fontSize: 13, fontWeight: 600, color: c.error }}>Poor — Ultra-Processed</div>
                  </div>
                </div>
                {/* Additives */}
                <div style={{ display: "flex", gap: 6, marginTop: 12, flexWrap: "wrap" }}>
                  {["Yellow 6", "Yellow 5", "Red 40", "MSG"].map((a) => (
                    <span key={a} style={{ padding: "3px 8px", borderRadius: 6, background: c.drugwatchLight, color: c.drugwatchDark, fontSize: 10, fontFamily: body, fontWeight: 600 }}>
                      ⚠️ {a}
                    </span>
                  ))}
                </div>
              </div>

              {/* GOOD product card */}
              <div
                style={{
                  background: c.white,
                  borderRadius: 14,
                  border: `2px solid ${c.foodscore}30`,
                  padding: 20,
                  opacity: goodCardOpacity,
                  transform: `scale(${goodCardScale}) rotate(${goodCardRotate}deg)`,
                  boxShadow: `0 4px 20px ${c.foodscore}15`,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
                  <div>
                    <div style={{ fontFamily: display, fontSize: 16, fontWeight: 700, color: c.neutral800 }}>
                      Red Apple Chips
                    </div>
                    <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500 }}>Welch's</div>
                  </div>
                  <div style={{ padding: "4px 12px", borderRadius: 9999, background: c.foodscoreLight, color: c.foodscoreDark, fontFamily: body, fontSize: 12, fontWeight: 700 }}>
                    NOVA 1
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                  <div
                    style={{
                      width: 64, height: 64, borderRadius: 12,
                      background: `linear-gradient(135deg, ${c.foodscore}, ${c.foodscoreDark})`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontFamily: display, fontSize: 28, fontWeight: 800, color: c.white,
                    }}
                  >
                    86
                  </div>
                  <div>
                    <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500 }}>MAHA Health Score</div>
                    <div style={{ fontFamily: body, fontSize: 13, fontWeight: 600, color: c.foodscore }}>Good — Unprocessed</div>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 6, marginTop: 12 }}>
                  <span style={{ padding: "3px 8px", borderRadius: 6, background: c.foodscoreLight, color: c.foodscoreDark, fontSize: 10, fontFamily: body, fontWeight: 600 }}>
                    ✅ No additives
                  </span>
                </div>
              </div>
            </div>

            {/* Right: NOVA classification bars */}
            <div style={{ flex: 1 }}>
              <div style={{ background: c.white, borderRadius: 14, border: `1px solid ${c.neutral200}`, padding: 20 }}>
                <div style={{ fontFamily: display, fontSize: 14, fontWeight: 700, color: c.neutral700, marginBottom: 16 }}>
                  NOVA Food Processing Classification
                </div>
                {novaData.map((nova, i) => (
                  <div key={i} style={{ marginBottom: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontFamily: body, fontSize: 12, fontWeight: 600, color: c.neutral700 }}>
                        {i + 1}. {nova.label}
                      </span>
                      <span style={{ fontFamily: mono, fontSize: 11, color: c.neutral500 }}>
                        {nova.count} ({nova.pct}%)
                      </span>
                    </div>
                    <div style={{ height: 24, background: c.neutral100, borderRadius: 6, overflow: "hidden" }}>
                      <div
                        style={{
                          width: `${novaBarWidth(i) * (nova.pct / 100) * (100 / 70.3)}%`,
                          maxWidth: "100%",
                          height: "100%",
                          background: nova.color,
                          borderRadius: 6,
                          transition: "width 0.1s",
                        }}
                      />
                    </div>
                  </div>
                ))}

                {/* Accuracy badge */}
                <div
                  style={{
                    marginTop: 16,
                    padding: "12px 16px",
                    borderRadius: 10,
                    background: c.foodscoreLight,
                    border: `1px solid ${c.foodscore}30`,
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    opacity: interpolate(frame, [82, 90], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
                  }}
                >
                  <span style={{ fontFamily: display, fontSize: 22, fontWeight: 800, color: c.foodscore }}>96.2%</span>
                  <span style={{ fontFamily: body, fontSize: 12, color: c.foodscoreDark, fontWeight: 500 }}>
                    ML classification accuracy
                  </span>
                </div>
              </div>
            </div>
          </div>
        </BrowserChrome>
      </AbsoluteFill>

      {/* Floating stats */}
      <div
        style={{
          position: "absolute",
          bottom: 30,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "center",
          gap: 24,
          opacity: statsOpacity,
        }}
      >
        {[
          { val: "50K+", label: "Products", color: c.foodscore },
          { val: "96.2%", label: "Accuracy", color: c.foodscore },
          { val: "350", label: "Additives Scored", color: c.foodscore },
        ].map((s, i) => (
          <div
            key={i}
            style={{
              padding: "8px 18px",
              borderRadius: 9999,
              background: `${c.foodscore}12`,
              border: `1px solid ${c.foodscore}35`,
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <span style={{ fontFamily: display, fontSize: 16, fontWeight: 800, color: c.foodscore }}>{s.val}</span>
            <span style={{ fontFamily: body, fontSize: 12, color: c.neutral400, fontWeight: 500 }}>{s.label}</span>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
