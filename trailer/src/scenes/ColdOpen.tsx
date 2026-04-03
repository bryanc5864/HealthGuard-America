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

// Rapid-fire alarming stat flashes — the crisis
const flashes = [
  { text: "$29,442", sub: "avg hospital charge", color: c.drugwatch },
  { text: "8.3×", sub: "price variance for same procedure", color: c.pricevision },
  { text: "70.3%", sub: "of food is ultra-processed", color: c.error },
  { text: "$496", sub: "Ozempic in the US", color: c.drugwatch },
  { text: "$72", sub: "same drug in Australia", color: c.foodscore },
  { text: "14,631", sub: "healthcare shortage areas", color: c.ruralaccess },
];

export const ColdOpen: React.FC = () => {
  const frame = useCurrentFrame();
  const FLASH_DURATION = 12; // ~0.4s each

  return (
    <AbsoluteFill style={{ background: "#050810" }}>
      {/* SFX */}
      <Sequence from={0}><Audio src={whoosh} volume={0.5} /></Sequence>
      <Sequence from={12}><Audio src={whip} volume={0.4} /></Sequence>
      <Sequence from={24}><Audio src={whoosh} volume={0.5} /></Sequence>
      <Sequence from={36}><Audio src={whip} volume={0.4} /></Sequence>
      <Sequence from={48}><Audio src={whoosh} volume={0.5} /></Sequence>
      <Sequence from={60}><Audio src={uiSwitch} volume={0.4} /></Sequence>

      {/* Flashing stats */}
      {flashes.map((flash, i) => {
        const start = i * FLASH_DURATION;
        const localFrame = frame - start;
        if (localFrame < 0 || localFrame >= FLASH_DURATION) return null;

        // Slam in from scale 2.5 → 1, slight shake
        const scale = interpolate(localFrame, [0, 4], [2.5, 1], {
          extrapolateRight: "clamp",
          easing: Easing.out(Easing.cubic),
        });
        const opacity = interpolate(localFrame, [0, 2, FLASH_DURATION - 3, FLASH_DURATION], [0, 1, 1, 0], {
          extrapolateRight: "clamp",
        });
        const shakeX = localFrame < 5 ? Math.sin(localFrame * 8) * (5 - localFrame) : 0;
        const shakeY = localFrame < 5 ? Math.cos(localFrame * 6) * (5 - localFrame) * 0.5 : 0;

        // Red screen flash
        const screenFlash = interpolate(localFrame, [0, 4], [0.15, 0], {
          extrapolateRight: "clamp",
        });

        return (
          <AbsoluteFill key={i} style={{ opacity }}>
            {/* Screen flash */}
            <AbsoluteFill style={{ background: flash.color, opacity: screenFlash }} />
            {/* Vignette */}
            <AbsoluteFill
              style={{
                background: "radial-gradient(circle, transparent 30%, #050810 75%)",
              }}
            />
            <AbsoluteFill
              style={{
                display: "flex",
                flexDirection: "column",
                justifyContent: "center",
                alignItems: "center",
                transform: `scale(${scale}) translate(${shakeX}px, ${shakeY}px)`,
              }}
            >
              <div
                style={{
                  fontFamily: display,
                  fontSize: 140,
                  fontWeight: 800,
                  color: flash.color,
                  letterSpacing: "-0.04em",
                  lineHeight: 1,
                  textShadow: `0 0 60px ${flash.color}60, 0 0 120px ${flash.color}30`,
                }}
              >
                {flash.text}
              </div>
              <div
                style={{
                  fontFamily: body,
                  fontSize: 28,
                  color: c.neutral400,
                  marginTop: 16,
                  fontWeight: 500,
                  letterSpacing: "0.02em",
                }}
              >
                {flash.sub}
              </div>
            </AbsoluteFill>
          </AbsoluteFill>
        );
      })}

      {/* Scanline effect */}
      <AbsoluteFill
        style={{
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,255,255,0.015) 2px, rgba(255,255,255,0.015) 4px)",
          pointerEvents: "none",
        }}
      />
    </AbsoluteFill>
  );
};
