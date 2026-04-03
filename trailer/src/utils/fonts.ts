import { loadFont as loadSora } from "@remotion/google-fonts/Sora";
import { loadFont as loadDMSans } from "@remotion/google-fonts/DMSans";
import { loadFont as loadJetBrains } from "@remotion/google-fonts/JetBrainsMono";

export const { fontFamily: display } = loadSora("normal", {
  weights: ["600", "700", "800"],
  subsets: ["latin"],
});

export const { fontFamily: body } = loadDMSans("normal", {
  weights: ["400", "500", "600", "700"],
  subsets: ["latin"],
});

export const { fontFamily: mono } = loadJetBrains("normal", {
  weights: ["400", "500"],
  subsets: ["latin"],
});
