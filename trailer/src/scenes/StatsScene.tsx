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

interface StatItem {
  value: string;
  label: string;
  color: string;
}

const stats: StatItem[] = [
  { value: "30M+", label: "Price Records", color: "#f59e0b" },
  { value: "5,400+", label: "Hospitals", color: "#ef4444" },
  { value: "50K+", label: "Foods Analyzed", color: "#22c55e" },
  { value: "3,142", label: "Counties Mapped", color: "#8b5cf6" },
];

export const StatsScene: React.FC = () => {
  const frame = useCurrentFrame();

  // Scene fade in
  const fadeIn = interpolate(frame, [0, 12], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Header
  const headerOpacity = interpolate(frame, [5, 18], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const headerY = interpolate(frame, [5, 18], [30, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  // Fade out
  const fadeOut = interpolate(frame, [95, 120], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background:
          "linear-gradient(135deg, #0a0e1a 0%, #0f1629 50%, #0a0e1a 100%)",
        opacity: fadeIn * fadeOut,
      }}
    >
      {/* Background grid effect */}
      <AbsoluteFill
        style={{
          backgroundImage:
            "linear-gradient(rgba(37,99,235,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(37,99,235,0.05) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
        }}
      />

      {/* Center glow */}
      <AbsoluteFill
        style={{
          background:
            "radial-gradient(circle at 50% 50%, rgba(37,99,235,0.1) 0%, transparent 50%)",
        }}
      />

      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: 80,
        }}
      >
        {/* Header */}
        <div
          style={{
            opacity: headerOpacity,
            transform: `translateY(${headerY}px)`,
            marginBottom: 70,
            textAlign: "center",
          }}
        >
          <h2
            style={{
              fontFamily: display,
              fontSize: 56,
              fontWeight: 800,
              color: "white",
              margin: 0,
            }}
          >
            Real Data. Real{" "}
            <span style={{ color: "#2563eb" }}>Impact.</span>
          </h2>
        </div>

        {/* Stats grid */}
        <div
          style={{
            display: "flex",
            gap: 50,
            justifyContent: "center",
            width: "100%",
          }}
        >
          {stats.map((stat, i) => {
            const delay = 15 + i * 10;
            const scale = interpolate(
              frame,
              [delay, delay + 15],
              [0.6, 1],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.cubic),
              }
            );
            const opacity = interpolate(
              frame,
              [delay, delay + 12],
              [0, 1],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }
            );

            return (
              <div
                key={i}
                style={{
                  opacity,
                  transform: `scale(${scale})`,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  background: "rgba(255,255,255,0.03)",
                  borderRadius: 20,
                  padding: "50px 45px",
                  minWidth: 240,
                  border: `1px solid ${stat.color}25`,
                  position: "relative",
                  overflow: "hidden",
                }}
              >
                {/* Top color accent */}
                <div
                  style={{
                    position: "absolute",
                    top: 0,
                    left: 0,
                    right: 0,
                    height: 4,
                    background: stat.color,
                  }}
                />
                <div
                  style={{
                    fontFamily: display,
                    fontSize: 72,
                    fontWeight: 800,
                    color: stat.color,
                    lineHeight: 1,
                    marginBottom: 12,
                  }}
                >
                  {stat.value}
                </div>
                <div
                  style={{
                    fontFamily: body,
                    fontSize: 20,
                    color: "#94a3b8",
                    fontWeight: 600,
                    letterSpacing: "1px",
                    textTransform: "uppercase",
                  }}
                >
                  {stat.label}
                </div>
              </div>
            );
          })}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
