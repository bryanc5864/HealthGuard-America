import { Composition } from "remotion";
import { HealthGuardTrailer } from "./Trailer";

export const Root: React.FC = () => {
  return (
    <Composition
      id="HealthGuardTrailer"
      component={HealthGuardTrailer}
      durationInFrames={810}
      fps={30}
      width={1920}
      height={1080}
    />
  );
};
