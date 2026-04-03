import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  Sequence,
} from "remotion";
import { Audio, whoosh, whip, uiSwitch } from "../utils/sfx";
import { display, body, mono } from "../utils/fonts";
import { c } from "../utils/colors";
import { BrowserChrome } from "../components/BrowserChrome";
import { Navbar } from "../components/Navbar";

// Simulated hospital price cards for the same procedure
const hospitals = [
  { name: "Community Medical Center", state: "FL", gross: "$4,050", cash: "$1,820", fairness: "Overpriced", color: c.error },
  { name: "Southeast Health", state: "AL", gross: "$2,340", cash: "$487", fairness: "Great Deal", color: c.foodscore },
  { name: "Regional Hospital", state: "TX", gross: "$8,920", cash: "$3,150", fairness: "Overpriced", color: c.error },
];

export const PriceProblem: React.FC = () => {
  const frame = useCurrentFrame();

  // Browser zooms in from 0.6 to fill screen
  const browserScale = interpolate(frame, [0, 20], [0.55, 0.88], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const browserOpacity = interpolate(frame, [0, 10], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Cards slide in staggered from bottom
  const getCardAnim = (i: number) => {
    const delay = 18 + i * 10;
    const y = interpolate(frame, [delay, delay + 12], [80, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    const opacity = interpolate(frame, [delay, delay + 8], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return { y, opacity };
  };

  // "8.3x" variance zooms up dramatically
  const varianceStart = 55;
  const varianceScale = interpolate(frame, [varianceStart, varianceStart + 15], [0.3, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const varianceOpacity = interpolate(frame, [varianceStart, varianceStart + 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  // Browser fades as variance takes over
  const browserFadeForVariance = interpolate(frame, [varianceStart - 5, varianceStart + 8], [1, 0.15], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // "What if you could see every price?" text
  const questionOpacity = interpolate(frame, [72, 82], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const questionY = interpolate(frame, [72, 82], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Scene fade out
  const fadeOut = interpolate(frame, [88, 100], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: c.neutral900, opacity: fadeOut }}>
      {/* SFX */}
      <Sequence from={18}><Audio src={whoosh} volume={0.3} /></Sequence>
      <Sequence from={28}><Audio src={whoosh} volume={0.3} /></Sequence>
      <Sequence from={38}><Audio src={whoosh} volume={0.3} /></Sequence>
      <Sequence from={55}><Audio src={whip} volume={0.5} /></Sequence>
      <Sequence from={72}><Audio src={uiSwitch} volume={0.35} /></Sequence>

      {/* Browser with fake PriceVision compare page */}
      <AbsoluteFill
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          transform: `scale(${browserScale})`,
          opacity: browserOpacity * browserFadeForVariance,
        }}
      >
        <BrowserChrome accentColor={c.pricevision} url="healthguard-america.vercel.app/public/pricevision/compare">
          <Navbar activeModule="PriceVision" />
          {/* Page header */}
          <div
            style={{
              background: `linear-gradient(135deg, rgba(100,45,10,0.92), rgba(168,107,10,0.88))`,
              padding: "28px 40px 36px",
            }}
          >
            <div style={{ fontFamily: body, fontSize: 11, color: "rgba(255,255,255,0.5)", marginBottom: 8 }}>
              Home › PriceVision › Compare
            </div>
            <div style={{ fontFamily: display, fontSize: 28, fontWeight: 800, color: "white", letterSpacing: "-0.03em" }}>
              📊 Price Comparison
            </div>
            <div style={{ fontFamily: body, fontSize: 14, color: "rgba(255,255,255,0.6)", marginTop: 4 }}>
              MRI Brain Scan (HCPCS: 70553) — Comparing across hospitals
            </div>
          </div>

          {/* Price comparison cards */}
          <div style={{ padding: "28px 40px", background: c.neutral50 }}>
            <div style={{ display: "flex", gap: 20 }}>
              {hospitals.map((h, i) => {
                const anim = getCardAnim(i);
                return (
                  <div
                    key={i}
                    style={{
                      flex: 1,
                      background: c.white,
                      borderRadius: 14,
                      border: `1px solid ${c.neutral200}`,
                      borderTop: `4px solid ${h.color}`,
                      padding: "20px 24px",
                      transform: `translateY(${anim.y}px)`,
                      opacity: anim.opacity,
                      boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
                    }}
                  >
                    <div style={{ fontFamily: display, fontSize: 15, fontWeight: 700, color: c.neutral800, marginBottom: 4 }}>
                      {h.name}
                    </div>
                    <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500, marginBottom: 16 }}>{h.state}</div>
                    <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
                      Gross Charge
                    </div>
                    <div style={{ fontFamily: mono, fontSize: 28, fontWeight: 500, color: c.neutral800, marginBottom: 8 }}>
                      {h.gross}
                    </div>
                    <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500, textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
                      Cash Price
                    </div>
                    <div style={{ fontFamily: mono, fontSize: 22, fontWeight: 500, color: c.foodscore }}>
                      {h.cash}
                    </div>
                    <div
                      style={{
                        marginTop: 14,
                        display: "inline-flex",
                        padding: "4px 12px",
                        borderRadius: 9999,
                        fontSize: 11,
                        fontWeight: 700,
                        fontFamily: body,
                        background: h.fairness === "Great Deal" ? c.foodscoreLight : c.drugwatchLight,
                        color: h.fairness === "Great Deal" ? c.foodscoreDark : c.drugwatchDark,
                      }}
                    >
                      {h.fairness}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </BrowserChrome>
      </AbsoluteFill>

      {/* "8.3x" dramatic overlay */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          opacity: varianceOpacity,
          transform: `scale(${varianceScale})`,
        }}
      >
        <div
          style={{
            fontFamily: display,
            fontSize: 200,
            fontWeight: 800,
            color: c.pricevision,
            letterSpacing: "-0.04em",
            lineHeight: 1,
            textShadow: `0 0 80px ${c.pricevision}50`,
          }}
        >
          8.3×
        </div>
        <div
          style={{
            fontFamily: body,
            fontSize: 32,
            color: c.neutral400,
            marginTop: 12,
            fontWeight: 500,
          }}
        >
          average price variance for the same procedure
        </div>
      </AbsoluteFill>

      {/* "What if" question */}
      <AbsoluteFill
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "flex-end",
          paddingBottom: 100,
          opacity: questionOpacity,
          transform: `translateY(${questionY}px)`,
        }}
      >
        <div
          style={{
            fontFamily: display,
            fontSize: 36,
            fontWeight: 700,
            color: c.white,
            letterSpacing: "-0.02em",
          }}
        >
          What if you could see <span style={{ color: c.pricevision }}>every price</span>?
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
