import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  Img,
  staticFile,
  Sequence,
} from "remotion";
import { Audio, ding } from "../utils/sfx";
import { display, body } from "../utils/fonts";
import { c } from "../utils/colors";

export const HeroReveal: React.FC = () => {
  const frame = useCurrentFrame();

  // Shield stroke draw (SVG dashoffset animation)
  const shieldDraw = interpolate(frame, [5, 35], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const shieldScale = interpolate(frame, [5, 35], [0.7, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const shieldOpacity = interpolate(frame, [5, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Checkmark appears after shield
  const checkDraw = interpolate(frame, [30, 45], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Title typewriter
  const titleText = "HealthGuard";
  const titleChars = Math.floor(
    interpolate(frame, [35, 60], [0, titleText.length], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );
  const showCursor = frame >= 35 && frame < 70 && Math.floor(frame / 8) % 2 === 0;

  // "America" gradient text
  const americaOpacity = interpolate(frame, [58, 70], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const americaY = interpolate(frame, [58, 70], [15, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Tagline
  const taglineOpacity = interpolate(frame, [70, 85], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Background glow pulse
  const glowRadius = interpolate(frame, [30, 60], [0, 45], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Flag parallax (moves slowly)
  const flagX = interpolate(frame, [0, 120], [20, -20], {
    extrapolateRight: "clamp",
  });

  // Bottom accent line draws
  const lineWidth = interpolate(frame, [45, 80], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Fade out
  const fadeOut = interpolate(frame, [85, 100], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ background: c.primary900, opacity: fadeOut }}>
      {/* SFX */}
      <Sequence from={30}><Audio src={ding} volume={0.4} /></Sequence>

      {/* Animated flag background with parallax */}
      <AbsoluteFill
        style={{
          opacity: 0.06,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          transform: `translateX(${flagX}px)`,
        }}
      >
        <Img
          src={staticFile("images/flag.png")}
          style={{ width: 1600, objectFit: "contain", filter: "grayscale(0.4)" }}
        />
      </AbsoluteFill>

      {/* Radial glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 50% 42%, rgba(42,80,128,0.25) 0%, transparent ${glowRadius}%)`,
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
        {/* Shield with stroke animation */}
        <div style={{ transform: `scale(${shieldScale})`, opacity: shieldOpacity, marginBottom: 24 }}>
          <svg width="100" height="118" viewBox="0 0 120 140" fill="none">
            <path
              d="M60 5L10 30V65C10 100 35 130 60 138C85 130 110 100 110 65V30L60 5Z"
              fill={`rgba(42,80,128,${interpolate(frame, [20, 35], [0, 0.9], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })})`}
              stroke={c.primary400}
              strokeWidth="2.5"
              strokeDasharray="400"
              strokeDashoffset={shieldDraw * 400}
            />
            <path
              d="M45 70L55 80L78 55"
              stroke="white"
              strokeWidth="5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="60"
              strokeDashoffset={checkDraw * 60}
            />
          </svg>
        </div>

        {/* Title with typewriter */}
        <div style={{ display: "flex", alignItems: "baseline", gap: 0 }}>
          <span
            style={{
              fontFamily: display,
              fontSize: 88,
              fontWeight: 800,
              color: c.white,
              letterSpacing: "-0.03em",
              lineHeight: 1,
            }}
          >
            {titleText.slice(0, titleChars)}
          </span>
          {showCursor && (
            <span
              style={{
                display: "inline-block",
                width: 4,
                height: 72,
                background: c.primary400,
                marginLeft: 2,
                borderRadius: 2,
              }}
            />
          )}
        </div>

        {/* "America" with gradient */}
        <div
          style={{
            opacity: americaOpacity,
            transform: `translateY(${americaY}px)`,
            marginTop: 4,
          }}
        >
          <span
            style={{
              fontFamily: display,
              fontSize: 88,
              fontWeight: 800,
              letterSpacing: "-0.03em",
              lineHeight: 1,
              background: `linear-gradient(135deg, ${c.secondary500} 20%, ${c.secondary600} 80%)`,
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            America
          </span>
        </div>

        {/* Tagline */}
        <div style={{ opacity: taglineOpacity, marginTop: 24 }}>
          <span
            style={{
              fontFamily: body,
              fontSize: 24,
              color: "rgba(255,255,255,0.5)",
              fontWeight: 400,
              letterSpacing: "0.01em",
            }}
          >
            Healthcare transparency and analytics platform
          </span>
        </div>
      </AbsoluteFill>

      {/* Bottom accent line: red-white-blue */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: `${lineWidth}%`,
          height: 4,
          background: `linear-gradient(90deg, ${c.secondary700}, ${c.white}, ${c.primary600})`,
          opacity: 0.7,
        }}
      />
    </AbsoluteFill>
  );
};
