import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
} from "remotion";
import { loadFont } from "@remotion/google-fonts/PlusJakartaSans";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";

const { fontFamily: display } = loadFont("normal", {
  weights: ["700", "800"],
  subsets: ["latin"],
});
const { fontFamily: body } = loadInter("normal", {
  weights: ["400", "600"],
  subsets: ["latin"],
});

const moduleColors = ["#f59e0b", "#ef4444", "#22c55e", "#8b5cf6", "#06b6d4"];

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Scene fade in
  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Shield
  const shieldScale = interpolate(frame, [10, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Title
  const titleOpacity = interpolate(frame, [25, 40], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const titleY = interpolate(frame, [25, 40], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Tagline
  const taglineOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Module dots
  const dotsOpacity = interpolate(frame, [55, 70], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // CTA
  const ctaOpacity = interpolate(frame, [70, 85], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const ctaScale = interpolate(frame, [70, 85], [0.9, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Final fade out to black
  const finalFade = interpolate(frame, [120, 140], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Glow pulsing
  const glowPulse = interpolate(
    frame % 60,
    [0, 30, 60],
    [0.15, 0.25, 0.15],
    { extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(135deg, #0a0e1a 0%, #111936 40%, #1a1020 70%, #2d1525 100%)",
        opacity: fadeIn * finalFade,
      }}
    >
      {/* Centered glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 45%, rgba(37,99,235,${glowPulse}) 0%, transparent 45%)`,
        }}
      />

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
            transform: `scale(${shieldScale})`,
            marginBottom: 28,
          }}
        >
          <svg
            width="90"
            height="105"
            viewBox="0 0 120 140"
            fill="none"
          >
            <path
              d="M60 5L10 30V65C10 100 35 130 60 138C85 130 110 100 110 65V30L60 5Z"
              fill="url(#shieldGrad2)"
              stroke="rgba(255,255,255,0.15)"
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
              <linearGradient
                id="shieldGrad2"
                x1="60"
                y1="0"
                x2="60"
                y2="140"
              >
                <stop offset="0%" stopColor="#2563eb" />
                <stop offset="100%" stopColor="#1a365d" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        {/* Title */}
        <div
          style={{
            opacity: titleOpacity,
            transform: `translateY(${titleY}px)`,
          }}
        >
          <h1
            style={{
              fontFamily: display,
              fontSize: 80,
              fontWeight: 800,
              color: "white",
              margin: 0,
              letterSpacing: "-2px",
              textAlign: "center",
            }}
          >
            Health<span style={{ color: "#2563eb" }}>Guard</span>{" "}
            <span style={{ color: "#94a3b8", fontWeight: 700 }}>America</span>
          </h1>
        </div>

        {/* Tagline */}
        <div
          style={{
            opacity: taglineOpacity,
            marginTop: 20,
          }}
        >
          <p
            style={{
              fontFamily: body,
              fontSize: 30,
              color: "#cbd5e1",
              margin: 0,
              fontWeight: 400,
              textAlign: "center",
            }}
          >
            Make America Healthy Again
          </p>
        </div>

        {/* Module color dots */}
        <div
          style={{
            opacity: dotsOpacity,
            display: "flex",
            gap: 16,
            marginTop: 40,
          }}
        >
          {moduleColors.map((color, i) => {
            const dotDelay = 55 + i * 4;
            const dotScale = interpolate(
              frame,
              [dotDelay, dotDelay + 8],
              [0, 1],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.cubic),
              }
            );
            return (
              <div
                key={i}
                style={{
                  width: 14,
                  height: 14,
                  borderRadius: "50%",
                  background: color,
                  transform: `scale(${dotScale})`,
                  boxShadow: `0 0 12px ${color}80`,
                }}
              />
            );
          })}
        </div>

        {/* CTA */}
        <div
          style={{
            opacity: ctaOpacity,
            transform: `scale(${ctaScale})`,
            marginTop: 50,
          }}
        >
          <div
            style={{
              fontFamily: body,
              fontSize: 20,
              color: "#64748b",
              fontWeight: 600,
              letterSpacing: "3px",
              textTransform: "uppercase",
            }}
          >
            Five Modules. One Mission. Your Health.
          </div>
        </div>
      </AbsoluteFill>

      {/* Bottom accent line - red white blue */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 4,
          background:
            "linear-gradient(90deg, #b91c1c, #ffffff, #2563eb)",
          opacity: interpolate(frame, [60, 80], [0, 0.6], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />
    </AbsoluteFill>
  );
};
