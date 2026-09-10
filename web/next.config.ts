import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Turbopack keeps a filesystem cache for the dev server so a restart does
    // not recompile everything. The e2e stack switches it off: its container
    // is thrown away with the stack, so the hundreds of megabytes it writes
    // are never read again — and the write itself stalls the dev server for
    // tens of seconds in the middle of the browser suite.
    turbopackFileSystemCacheForDev: process.env.DEV_FILESYSTEM_CACHE !== "0",
  },
};

export default nextConfig;
