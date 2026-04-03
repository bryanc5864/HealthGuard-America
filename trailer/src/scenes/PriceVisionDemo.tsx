import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  Sequence,
} from "remotion";
import { Audio, mouseClick, whoosh, ding } from "../utils/sfx";
import { display, body, mono } from "../utils/fonts";
import { c } from "../utils/colors";
import { BrowserChrome } from "../components/BrowserChrome";
import { Navbar } from "../components/Navbar";

const searchText = "MRI Brain";

const results = [
  { name: "Southeast Health Medical Center", loc: "Dothan, AL", code: "70553", cash: "$487", gross: "$2,340" },
  { name: "North Alabama Medical Center", loc: "Florence, AL", code: "70553", cash: "$612", gross: "$3,180" },
  { name: "Marshall Medical Centers", loc: "Boaz, AL", code: "70553", cash: "$945", gross: "$4,050" },
  { name: "Mizell Memorial Hospital", loc: "Opp, AL", code: "70553", cash: "$1,120", gross: "$5,600" },
  { name: "Crenshaw Community Hospital", loc: "Luverne, AL", code: "70553", cash: "$1,450", gross: "$8,920" },
];

export const PriceVisionDemo: React.FC = () => {
  const frame = useCurrentFrame();

  // Browser camera: starts centered, slowly zooms in toward the results
  const cameraScale = interpolate(frame, [0, 100], [0.88, 0.98], {
    extrapolateRight: "clamp",
  });
  const cameraY = interpolate(frame, [30, 100], [0, -40], {
    extrapolateRight: "clamp",
  });

  // Typewriter in search box
  const typedChars = Math.floor(
    interpolate(frame, [8, 28], [0, searchText.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );

  // Result rows slide in staggered from right
  const getRowAnim = (i: number) => {
    const delay = 35 + i * 6;
    const x = interpolate(frame, [delay, delay + 10], [60, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.cubic),
    });
    const opacity = interpolate(frame, [delay, delay + 6], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return { x, opacity };
  };

  // Stat chips fly in from edges
  const statChips = [
    { text: "30M Records", delay: 70, fromX: -200 },
    { text: "5,400 Hospitals", delay: 76, fromX: 200 },
    { text: "50 States", delay: 82, fromX: -200 },
  ];

  // Fade out
  const fadeOut = interpolate(frame, [100, 115], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: c.neutral900, opacity: fadeOut }}>
      {/* SFX */}
      <Sequence from={8}><Audio src={mouseClick} volume={0.3} /></Sequence>
      <Sequence from={35}><Audio src={whoosh} volume={0.25} /></Sequence>
      <Sequence from={70}><Audio src={ding} volume={0.3} /></Sequence>

      <AbsoluteFill
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          transform: `scale(${cameraScale}) translateY(${cameraY}px)`,
        }}
      >
        <BrowserChrome accentColor={c.pricevision} url="healthguard-america.vercel.app/public/pricevision/search?q=MRI+Brain">
          <Navbar activeModule="PriceVision" />

          {/* PriceVision page header */}
          <div
            style={{
              background: `linear-gradient(135deg, rgba(100,45,10,0.92), rgba(168,107,10,0.88))`,
              padding: "22px 40px 28px",
            }}
          >
            <div style={{ fontFamily: body, fontSize: 11, color: "rgba(255,255,255,0.5)", marginBottom: 6 }}>
              Home › PriceVision
            </div>
            <div style={{ fontFamily: display, fontSize: 26, fontWeight: 800, color: "white" }}>
              💰 PriceVision
            </div>
            <div style={{ fontFamily: body, fontSize: 13, color: "rgba(255,255,255,0.6)", marginTop: 2 }}>
              Compare hospital procedure prices across 5,400+ facilities nationwide
            </div>
          </div>

          {/* Stats bar */}
          <div style={{ display: "flex", gap: 16, padding: "16px 40px", background: c.white, borderBottom: `1px solid ${c.neutral200}` }}>
            {[
              { val: "30M", label: "Price Records", color: c.pricevision },
              { val: "5,400", label: "Hospitals", color: c.pricevision },
              { val: "50", label: "States", color: c.pricevision },
              { val: "8.3×", label: "Avg Variance", color: c.error },
            ].map((s, i) => (
              <div key={i} style={{ borderLeft: `3px solid ${s.color}`, paddingLeft: 12 }}>
                <div style={{ fontFamily: display, fontSize: 20, fontWeight: 800, color: s.color }}>{s.val}</div>
                <div style={{ fontFamily: body, fontSize: 10, color: c.neutral500, textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600 }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Search box */}
          <div style={{ padding: "24px 40px", background: c.neutral50 }}>
            <div
              style={{
                maxWidth: 700,
                margin: "0 auto",
                background: c.white,
                borderRadius: 14,
                padding: 24,
                border: `1px solid ${c.neutral200}`,
                boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
              }}
            >
              <div style={{ fontFamily: display, fontSize: 16, fontWeight: 700, color: c.neutral800, marginBottom: 12 }}>
                Search Procedure Prices
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  background: c.neutral50,
                  borderRadius: 10,
                  border: `2px solid ${frame > 8 ? c.primary500 : c.neutral200}`,
                  padding: "10px 16px",
                  transition: "border-color 0.15s",
                }}
              >
                <span style={{ marginRight: 10, color: c.neutral400, fontSize: 16 }}>🔍</span>
                <span style={{ fontFamily: body, fontSize: 15, color: typedChars > 0 ? c.neutral800 : c.neutral400 }}>
                  {typedChars > 0 ? searchText.slice(0, typedChars) : "Search procedures (e.g., MRI, knee replacement...)"}
                </span>
                {frame > 8 && frame < 35 && Math.floor(frame / 6) % 2 === 0 && (
                  <span style={{ display: "inline-block", width: 2, height: 18, background: c.primary500, marginLeft: 1 }} />
                )}
              </div>
              {/* Popular searches */}
              <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
                {["MRI", "CT Scan", "Colonoscopy", "Knee", "X-Ray"].map((tag) => (
                  <span
                    key={tag}
                    style={{
                      padding: "4px 10px",
                      borderRadius: 9999,
                      fontSize: 11,
                      fontWeight: 600,
                      fontFamily: body,
                      background: tag === "MRI" ? c.pricevisionLight : c.neutral100,
                      color: tag === "MRI" ? c.pricevisionDark : c.neutral600,
                      border: `1px solid ${tag === "MRI" ? c.pricevision + "40" : c.neutral200}`,
                    }}
                  >
                    {tag}
                  </span>
                ))}
              </div>
            </div>

            {/* Results table */}
            <div
              style={{
                marginTop: 20,
                background: c.white,
                borderRadius: 14,
                border: `1px solid ${c.neutral200}`,
                overflow: "hidden",
              }}
            >
              {/* Table header */}
              <div
                style={{
                  display: "flex",
                  padding: "10px 24px",
                  background: c.neutral50,
                  borderBottom: `1px solid ${c.neutral100}`,
                  fontFamily: body,
                  fontSize: 10,
                  fontWeight: 700,
                  color: c.neutral500,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                <div style={{ flex: 2 }}>Hospital</div>
                <div style={{ flex: 1, textAlign: "center" }}>Code</div>
                <div style={{ flex: 1, textAlign: "right" }}>Gross Charge</div>
                <div style={{ flex: 1, textAlign: "right" }}>Cash Price</div>
              </div>
              {/* Results */}
              {results.map((r, i) => {
                const anim = getRowAnim(i);
                return (
                  <div
                    key={i}
                    style={{
                      display: "flex",
                      padding: "12px 24px",
                      borderBottom: i < results.length - 1 ? `1px solid ${c.neutral100}` : "none",
                      alignItems: "center",
                      opacity: anim.opacity,
                      transform: `translateX(${anim.x}px)`,
                    }}
                  >
                    <div style={{ flex: 2 }}>
                      <div style={{ fontFamily: body, fontSize: 13, fontWeight: 600, color: c.primary600 }}>{r.name}</div>
                      <div style={{ fontFamily: body, fontSize: 11, color: c.neutral500 }}>{r.loc}</div>
                    </div>
                    <div style={{ flex: 1, textAlign: "center" }}>
                      <span style={{ padding: "2px 8px", borderRadius: 6, background: c.primary50, color: c.primary600, fontSize: 11, fontFamily: mono, fontWeight: 500 }}>
                        {r.code}
                      </span>
                    </div>
                    <div style={{ flex: 1, textAlign: "right", fontFamily: mono, fontSize: 14, color: c.neutral700 }}>
                      {r.gross}
                    </div>
                    <div style={{ flex: 1, textAlign: "right", fontFamily: mono, fontSize: 14, fontWeight: 500, color: c.foodscore }}>
                      {r.cash}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </BrowserChrome>
      </AbsoluteFill>

      {/* Flying stat chips */}
      {statChips.map((chip, i) => {
        const chipX = interpolate(frame, [chip.delay, chip.delay + 12], [chip.fromX, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });
        const chipOpacity = interpolate(frame, [chip.delay, chip.delay + 8], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        const chipY = i === 0 ? 880 : i === 1 ? 920 : 960;

        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: "50%",
              top: chipY,
              transform: `translateX(calc(-50% + ${chipX}px))`,
              opacity: chipOpacity,
              padding: "8px 20px",
              borderRadius: 9999,
              background: `${c.pricevision}15`,
              border: `1px solid ${c.pricevision}40`,
              fontFamily: body,
              fontSize: 14,
              fontWeight: 600,
              color: c.pricevision,
            }}
          >
            {chip.text}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
