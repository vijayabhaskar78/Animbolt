/** @type {import('next').NextConfig} */

// BACKEND_INTERNAL_URL is a server-side-only env var — it is never prefixed with
// NEXT_PUBLIC_, so it is never bundled into client JS or visible in DevTools.
// Set it to the internal address of your API server (e.g. http://api:8000 in Docker,
// or your Railway/Render/EC2 URL in production). Defaults to localhost for local dev.
const BACKEND = process.env.BACKEND_INTERNAL_URL || "http://localhost:8001";

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      { source: "/api/:path*",       destination: `${BACKEND}/api/:path*` },
      { source: "/artifacts/:path*", destination: `${BACKEND}/artifacts/:path*` },
      { source: "/ws/:path*",        destination: `${BACKEND}/ws/:path*` },
    ];
  },
};

export default nextConfig;

