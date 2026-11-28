/** @type {import('next').NextConfig} */
const config = {
  async rewrites() {
    return [{
      source: "/context-runner/:path*",
      destination: "http://127.0.0.1:39913/:path*",
    }];
  },
};
export default config;
