import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Use 127.0.0.1 explicitly, NOT 'localhost' — Node 18+ resolves
    // 'localhost' to IPv6 ([::1]) first, which uvicorn (IPv4-only by
    // default) refuses, surfacing as HTTP 500 on every /api/* request
    // and a cryptic "Unable to reach the server" on the login form.
    return [
      {
        source: '/api/:path*',
        destination: (process.env.NEXT_PUBLIC_API_URL ?? 'http://127.0.0.1:8000') + '/:path*',
      },
    ];
  },
};

export default nextConfig;
