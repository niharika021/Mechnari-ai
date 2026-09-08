import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Cloud Run runs `node server.js` from this trimmed output rather than
  // `next start` against the full node_modules tree - smaller image, no
  // change to local `npm run dev` / `npm run build`.
  output: "standalone",
};

export default nextConfig;
