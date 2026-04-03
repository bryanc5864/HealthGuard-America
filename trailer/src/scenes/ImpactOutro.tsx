import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  Sequence,
} from "remotion";
import { Audio, whoosh, ding } from "../utils/sfx";
import { display, body } from "../utils/fonts";
import { c, moduleColors } from "../utils/colors";

const moduleNames = ["PriceVision", "DrugWatch", "FoodScore", "RuralAccess", "ChronicCare"];

export const ImpactOutro: React.FC = () => {
  const frame = useCurrentFrame();

  // 5 color bars converge from edges
  const barPositions = [
    { from: { x: -1920, y: 200 }, angle: 0 },
    { from: { x: 1920, y: 300 }, angle: 0 },
    { from: { x: -1920, y: 400 }, angle: 0 },
    { from: { x: 1920, y: 500 }, angle: 0 },
    { from: { x: -1920, y: 600 }, angle: 0 },
  ];

  const barsConverged = frame > 25;

  // Shield emerges from convergence
  const shieldScale = interpolate(frame, [25, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const shieldOpacity = interpolate(frame, [25, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Title
  const titleOpacity = interpolate(frame, [38, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleY = interpolate(frame, [38, 50], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // "Make America Healthy Again" typewriter
  const mahaText = "Make America Healthy Again";
  const mahaChars = Math.floor(
    interpolate(frame, [52, 75], [0, mahaText.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );

  // Module color dots
  const dotsStart = 78;

  // "Five Modules" tagline
  const taglineOpacity = interpolate(frame, [90, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Final shield glow pulse
  const finalGlow = interpolate(
    frame,
    [100, 110, 120],
    [0.2, 0.5, 0.3],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // Fade to black
  const fadeToBlack = interpolate(frame, [115, 130], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: c.primary900 }}>
      {/* SFX */}
      <Sequence from={0}><Audio src={whoosh} volume={0.4} /></Sequence>
      <Sequence from={10}><Audio src={whoosh} volume={0.35} /></Sequence>
      <Sequence from={25}><Audio src={ding} volume={0.45} /></Sequence>

      {/* Converging color bars */}
      {barPositions.map((bar, i) => {
        const x = interpolate(frame, [i * 3, i * 3 + 18], [bar.from.x, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });
        // After converging, bars fade out
        const barOpacity = interpolate(frame, [i * 3, i * 3 + 10, 28, 35], [0, 0.6, 0.6, 0], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              top: bar.from.y - 4,
              left: 0,
              right: 0,
              height: 8,
              background: moduleColors[i],
              opacity: barOpacity,
              transform: `translateX(${x}px)`,
              boxShadow: `0 0 30px ${moduleColors[i]}60`,
            }}
          />
        );
      })}

      {/* Center glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 42%, rgba(42,80,128,${finalGlow}) 0%, transparent 45%)`,
        }}
      />

      {/* Main content */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {/* Shield */}
        <div
          style={{
            opacity: shieldOpacity,
            transform: `scale(${shieldScale})`,
            marginBottom: 20,
          }}
        >
          <svg width="80" height="94" viewBox="0 0 120 140" fill="none">
            <path
              d="M60 5L10 30V65C10 100 35 130 60 138C85 130 110 100 110 65V30L60 5Z"
              fill="url(#sg3)"
              stroke={c.primary400}
              strokeWidth="2"
            />
            <path
              d="M45 70L55 80L78 55"
              stroke="white"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <defs>
              <linearGradient id="sg3" x1="60" y1="0" x2="60" y2="140">
                <stop offset="0%" stopColor={c.primary600} />
                <stop offset="100%" stopColor={c.primary900} />
              </linearGradient>
            </defs>
          </svg>
        </div>

        {/* Title */}
        <div style={{ opacity: titleOpacity, transform: `translateY(${titleY}px)` }}>
          <span style={{ fontFamily: display, fontSize: 72, fontWeight: 800, color: c.white, letterSpacing: "-0.03em" }}>
            Health
          </span>
          <span style={{ fontFamily: display, fontSize: 72, fontWeight: 800, color: c.primary400, letterSpacing: "-0.03em" }}>
            Guard
          </span>
          <span style={{ fontFamily: display, fontSize: 72, fontWeight: 700, color: c.neutral400, letterSpacing: "-0.03em", marginLeft: 16 }}>
            America
          </span>
        </div>

        {/* MAHA typewriter */}
        <div style={{ marginTop: 16, height: 40 }}>
          <span
            style={{
              fontFamily: body,
              fontSize: 28,
              color: "rgba(255,255,255,0.55)",
              fontWeight: 400,
            }}
          >
            {mahaText.slice(0, mahaChars)}
          </span>
          {frame >= 52 && frame < 80 && Math.floor(frame / 7) % 2 === 0 && (
            <span
              style={{
                display: "inline-block",
                width: 3,
                height: 24,
                background: c.primary400,
                marginLeft: 2,
                verticalAlign: "middle",
              }}
            />
          )}
        </div>

        {/* Module dots with labels */}
        <div
          style={{
            display: "flex",
            gap: 24,
            marginTop: 36,
          }}
        >
          {moduleColors.map((color, i) => {
            const dotDelay = dotsStart + i * 4;
            const dotScale = interpolate(frame, [dotDelay, dotDelay + 8], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
              easing: Easing.out(Easing.cubic),
            });
            const dotOpacity = interpolate(frame, [dotDelay, dotDelay + 6], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            return (
              <div
                key={i}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 8,
                  opacity: dotOpacity,
                  transform: `scale(${dotScale})`,
                }}
              >
                <div
                  style={{
                    width: 14,
                    height: 14,
                    borderRadius: "50%",
                    background: color,
                    boxShadow: `0 0 14px ${color}80`,
                  }}
                />
                <span
                  style={{
                    fontFamily: body,
                    fontSize: 10,
                    color: "rgba(255,255,255,0.35)",
                    fontWeight: 600,
                    letterSpacing: "0.04em",
                  }}
                >
                  {moduleNames[i]}
                </span>
              </div>
            );
          })}
        </div>

        {/* Final tagline */}
        <div style={{ opacity: taglineOpacity, marginTop: 40 }}>
          <span
            style={{
              fontFamily: body,
              fontSize: 18,
              color: "rgba(255,255,255,0.3)",
              fontWeight: 600,
              letterSpacing: "0.12em",
              textTransform: "uppercase",
            }}
          >
            Five Modules. One Mission. Your Health.
          </span>
        </div>
      </AbsoluteFill>

      {/* Bottom accent line */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 4,
          background: `linear-gradient(90deg, ${c.secondary700}, ${c.white}, ${c.primary600})`,
          opacity: interpolate(frame, [80, 95], [0, 0.5], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }),
        }}
      />

      {/* Fade to black overlay */}
      <AbsoluteFill style={{ background: "#000", opacity: fadeToBlack }} />
    </AbsoluteFill>
  );
};
