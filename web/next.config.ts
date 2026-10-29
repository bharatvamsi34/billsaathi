import type { NextConfig } from "next";

// Static export: the site is plain files on Azure Static Web Apps; everything live comes
// from the BillSaathi API (NEXT_PUBLIC_API_BASE).
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;
