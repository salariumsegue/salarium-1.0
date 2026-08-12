import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Salarium — Autonomous Investment Research",
    short_name: "Salarium",
    description:
      "Systematic equity research from signal to portfolio, with walk-forward validation and governed risk controls.",
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
