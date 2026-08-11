import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Salarium — Autonomous Equity Research",
    short_name: "Salarium",
    description:
      "Open-source systematic equity research with walk-forward models, covariance-aware portfolio construction, and governed risk controls.",
    start_url: "/",
    display: "standalone",
    background_color: "#000000",
    theme_color: "#000000",
    icons: [
      {
        src: "/salarium-mark.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
    ],
  };
}
