import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Easing,
  Img,
  staticFile,
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

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Shield / logo scale-in
  const logoScale = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const logoOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Title slide in
  const titleY = interpolate(frame, [15, 40], [60, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const titleOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Subtitle fade in
  const subtitleOpacity = interpolate(frame, [40, 60], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Glow pulse
  const glowIntensity = interpolate(
    frame,
    [0, 60, 120],
    [0, 0.6, 0.3],
    { extrapolateRight: "clamp" }
  );

  // Scene fade out
  const fadeOut = interpolate(frame, [110, 140], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Flag subtle background
  const flagOpacity = interpolate(frame, [0, 30], [0, 0.08], {
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(135deg, #0a0e1a 0%, #111936 40%, #1a1020 70%, #2d1525 100%)",
        opacity: fadeOut,
      }}
    >
      {/* Background flag */}
      <AbsoluteFill
        style={{
          opacity: flagOpacity,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        <Img
          src={staticFile("images/flag.png")}
          style={{
            width: 1400,
            objectFit: "contain",
            filter: "grayscale(0.5)",
          }}
        />
      </AbsoluteFill>

      {/* Radial glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 45%, rgba(37, 99, 235, ${glowIntensity * 0.3}) 0%, transparent 50%)`,
        }}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
        }}
      >
        {/* Shield icon */}
        <div
          style={{
            transform: `scale(${logoScale})`,
            opacity: logoOpacity,
            marginBottom: 30,
          }}
        >
          <svg
            width="120"
            height="140"
            viewBox="0 0 120 140"
            fill="none"
          >
            <path
              d="M60 5L10 30V65C10 100 35 130 60 138C85 130 110 100 110 65V30L60 5Z"
              fill="url(#shieldGrad)"
              stroke="rgba(255,255,255,0.2)"
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
              <linearGradient id="shieldGrad" x1="60" y1="0" x2="60" y2="140">
                <stop offset="0%" stopColor="#2563eb" />
                <stop offset="100%" stopColor="#1a365d" />
              </linearGradient>
            </defs>
          </svg>
        </div>

        {/* Title */}
        <div
          style={{
            transform: `translateY(${titleY}px)`,
            opacity: titleOpacity,
            textAlign: "center",
          }}
        >
          <h1
            style={{
              fontFamily: display,
              fontSize: 90,
              fontWeight: 800,
              color: "white",
              margin: 0,
              letterSpacing: "-2px",
              lineHeight: 1,
            }}
          >
            Health
            <span style={{ color: "#2563eb" }}>Guard</span>
          </h1>
          <div
            style={{
              fontFamily: body,
              fontSize: 28,
              fontWeight: 600,
              color: "#94a3b8",
              marginTop: 8,
              letterSpacing: "6px",
              textTransform: "uppercase",
            }}
          >
            America
          </div>
        </div>

        {/* Subtitle */}
        <div
          style={{
            opacity: subtitleOpacity,
            marginTop: 40,
            textAlign: "center",
          }}
        >
          <p
            style={{
              fontFamily: body,
              fontSize: 26,
              color: "#cbd5e1",
              margin: 0,
              fontWeight: 400,
            }}
          >
            Transparency is the first step toward a healthier nation
          </p>
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
          background: `linear-gradient(90deg, transparent, #2563eb ${interpolate(frame, [30, 80], [0, 50], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })}%, #b91c1c, transparent)`,
          opacity: interpolate(frame, [30, 50], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      />
    </AbsoluteFill>
  );
};
