import type { NextConfig } from "next";

const backendApiUrl = process.env.BACKEND_API_URL ?? "http://127.0.0.1:8000/api/v1";
const frontendRoot = process.cwd();

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  outputFileTracingRoot: frontendRoot,
  turbopack: {
    root: frontendRoot,
  },
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${backendApiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
