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

const problems = [
  { text: "Hospital prices vary 8.3x for the same procedure", icon: "🏥" },
  { text: "Americans pay 2-3x more for drugs than other nations", icon: "💊" },
  { text: "70% of grocery products are ultra-processed", icon: "🛒" },
];

export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Scene fade in
  const fadeIn = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Headline
  const headlineY = interpolate(frame, [5, 25], [40, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const headlineOpacity = interpolate(frame, [5, 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Scene fade out
  const fadeOut = interpolate(frame, [95, 120], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(135deg, #0a0e1a 0%, #111936 50%, #0a0e1a 100%)",
        opacity: fadeIn * fadeOut,
      }}
    >
      {/* Red accent glow */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(ellipse at 50% 30%, rgba(185, 28, 28, 0.12) 0%, transparent 60%)",
        }}
      />

      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: 100,
        }}
      >
        {/* Headline */}
        <div
          style={{
            transform: `translateY(${headlineY}px)`,
            opacity: headlineOpacity,
            marginBottom: 60,
          }}
        >
          <h2
            style={{
              fontFamily: display,
              fontSize: 64,
              fontWeight: 800,
              color: "white",
              margin: 0,
              textAlign: "center",
              lineHeight: 1.2,
            }}
          >
            Healthcare data is{" "}
            <span style={{ color: "#ef4444" }}>broken</span>
          </h2>
        </div>

        {/* Problem items */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 28,
            width: "100%",
            maxWidth: 900,
          }}
        >
          {problems.map((problem, i) => {
            const delay = 25 + i * 18;
            const itemOpacity = interpolate(
              frame,
              [delay, delay + 15],
              [0, 1],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }
            );
            const itemX = interpolate(
              frame,
              [delay, delay + 15],
              [-40, 0],
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
                  opacity: itemOpacity,
                  transform: `translateX(${itemX}px)`,
                  display: "flex",
                  alignItems: "center",
                  gap: 24,
                  background: "rgba(255,255,255,0.04)",
                  borderRadius: 16,
                  padding: "22px 36px",
                  borderLeft: "4px solid #ef4444",
                }}
              >
                <span style={{ fontSize: 40 }}>{problem.icon}</span>
                <span
                  style={{
                    fontFamily: body,
                    fontSize: 28,
                    color: "#e2e8f0",
                    fontWeight: 400,
                  }}
                >
                  {problem.text}
                </span>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
