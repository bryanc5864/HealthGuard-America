import { AbsoluteFill, Sequence } from "remotion";
import { ColdOpen } from "./scenes/ColdOpen";
import { HeroReveal } from "./scenes/HeroReveal";
import { PriceProblem } from "./scenes/PriceProblem";
import { PriceVisionDemo } from "./scenes/PriceVisionDemo";
import { DrugWatchDemo } from "./scenes/DrugWatchDemo";
import { FoodScoreDemo } from "./scenes/FoodScoreDemo";
import { GovModules } from "./scenes/GovModules";
import { ImpactOutro } from "./scenes/ImpactOutro";

// 750 frames @ 30fps = 25 seconds
//
// Scene timeline:
//   ColdOpen:       0–75    (2.5s)  Rapid alarming stat flashes
//   HeroReveal:     70–170  (3.3s)  Shield draw, typewriter title, glow
//   PriceProblem:   165–270 (3.5s)  Browser with price cards, 8.3x slam
//   PriceVisionDemo:265–380 (3.8s)  Search typing, results cascade, stats fly
//   DrugWatchDemo:  375–480 (3.5s)  Ozempic comparison, 85% savings badge
//   FoodScoreDemo:  475–585 (3.7s)  Barcode scan, product cards, NOVA bars
//   GovModules:     580–680 (3.3s)  Split: RuralAccess map + ChronicCare bars
//   ImpactOutro:    675–810 (4.5s)  Color bars converge, logo, MAHA, fade

export const HealthGuardTrailer: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#050810" }}>
      <Sequence from={0} durationInFrames={80}>
        <ColdOpen />
      </Sequence>

      <Sequence from={70} durationInFrames={105}>
        <HeroReveal />
      </Sequence>

      <Sequence from={165} durationInFrames={110}>
        <PriceProblem />
      </Sequence>

      <Sequence from={265} durationInFrames={120}>
        <PriceVisionDemo />
      </Sequence>

      <Sequence from={375} durationInFrames={110}>
        <DrugWatchDemo />
      </Sequence>

      <Sequence from={475} durationInFrames={115}>
        <FoodScoreDemo />
      </Sequence>

      <Sequence from={580} durationInFrames={105}>
        <GovModules />
      </Sequence>

      <Sequence from={675} durationInFrames={135}>
        <ImpactOutro />
      </Sequence>
    </AbsoluteFill>
  );
};
