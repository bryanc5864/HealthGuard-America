import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  Easing,
  Img,
  staticFile,
  Sequence,
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

interface ModuleData {
  name: string;
  tagline: string;
  stat: string;
  statLabel: string;
  color: string;
  image: string;
  icon: string;
}

const modules: ModuleData[] = [
  {
    name: "PriceVision",
    tagline: "Compare hospital procedure prices across 5,400+ facilities",
    stat: "30M+",
    statLabel: "Price Records",
    color: "#f59e0b",
    image: "images/hospital.jpg",
    icon: "💰",
  },
  {
    name: "DrugWatch",
    tagline: "Compare drug prices: US vs international markets",
    stat: "60-90%",
    statLabel: "Potential Savings",
    color: "#ef4444",
    image: "images/pills.jpg",
    icon: "💊",
  },
  {
    name: "FoodScore",
    tagline: "AI-powered health scoring for 50,000+ food products",
    stat: "96.2%",
    statLabel: "ML Accuracy",
    color: "#22c55e",
    image: "images/food.png",
    icon: "🥗",
  },
  {
    name: "RuralAccess",
    tagline: "Map healthcare shortage areas and access gaps",
    stat: "14,631",
    statLabel: "Shortage Areas",
    color: "#8b5cf6",
    image: "images/rural.jpg",
    icon: "🗺️",
  },
  {
    name: "ChronicCare",
    tagline: "Predict chronic disease patterns across 3,000 counties",
    stat: "93.9%",
    statLabel: "Prediction Accuracy",
    color: "#06b6d4",
    image: "images/chronic.jpg",
    icon: "❤️",
  },
];

const MODULE_DURATION = 54; // frames per module (~1.8s each)

const ModuleCard: React.FC<{ module: ModuleData }> = ({ module }) => {
  const frame = useCurrentFrame();

  // Image zoom
  const imgScale = interpolate(frame, [0, MODULE_DURATION], [1.0, 1.15], {
    extrapolateRight: "clamp",
  });

  // Content slide in
  const contentX = interpolate(frame, [5, 22], [80, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const contentOpacity = interpolate(frame, [5, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Stat counter
  const statScale = interpolate(frame, [15, 30], [0.5, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const statOpacity = interpolate(frame, [15, 28], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Fade out
  const fadeOut = interpolate(frame, [MODULE_DURATION - 10, MODULE_DURATION], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Color bar width
  const barWidth = interpolate(frame, [0, 20], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });

  return (
    <AbsoluteFill style={{ opacity: fadeOut }}>
      {/* Background image */}
      <AbsoluteFill>
        <Img
          src={staticFile(module.image)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${imgScale})`,
            filter: "brightness(0.3)",
          }}
        />
      </AbsoluteFill>

      {/* Gradient overlay */}
      <AbsoluteFill
        style={{
          background: `linear-gradient(90deg, rgba(10,14,26,0.95) 0%, rgba(10,14,26,0.7) 50%, rgba(10,14,26,0.4) 100%)`,
        }}
      />

      {/* Color accent bar at top */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: `${barWidth}%`,
          height: 5,
          background: module.color,
          boxShadow: `0 0 30px ${module.color}60`,
        }}
      />

      {/* Content */}
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          padding: "0 120px",
        }}
      >
        {/* Left - Text */}
        <div
          style={{
            flex: 1,
            opacity: contentOpacity,
            transform: `translateX(${contentX}px)`,
          }}
        >
          {/* Module badge */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 12,
              background: `${module.color}20`,
              border: `1px solid ${module.color}40`,
              borderRadius: 50,
              padding: "10px 24px",
              marginBottom: 24,
            }}
          >
            <span style={{ fontSize: 24 }}>{module.icon}</span>
            <span
              style={{
                fontFamily: body,
                fontSize: 18,
                fontWeight: 600,
                color: module.color,
                letterSpacing: "2px",
                textTransform: "uppercase",
              }}
            >
              {module.name}
            </span>
          </div>

          {/* Tagline */}
          <h2
            style={{
              fontFamily: display,
              fontSize: 52,
              fontWeight: 700,
              color: "white",
              margin: 0,
              lineHeight: 1.2,
              maxWidth: 750,
            }}
          >
            {module.tagline}
          </h2>
        </div>

        {/* Right - Stat */}
        <div
          style={{
            opacity: statOpacity,
            transform: `scale(${statScale})`,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            minWidth: 280,
          }}
        >
          <div
            style={{
              fontFamily: display,
              fontSize: 96,
              fontWeight: 800,
              color: module.color,
              lineHeight: 1,
              textShadow: `0 0 40px ${module.color}40`,
            }}
          >
            {module.stat}
          </div>
          <div
            style={{
              fontFamily: body,
              fontSize: 22,
              color: "#94a3b8",
              fontWeight: 600,
              marginTop: 8,
              letterSpacing: "1px",
              textTransform: "uppercase",
            }}
          >
            {module.statLabel}
          </div>
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const ModulesScene: React.FC = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill>
      {modules.map((module, i) => (
        <Sequence
          key={i}
          from={i * MODULE_DURATION}
          durationInFrames={MODULE_DURATION}
        >
          <ModuleCard module={module} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
