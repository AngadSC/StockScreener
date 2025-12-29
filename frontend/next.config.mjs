/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // Allow images from external sources (for stock logos if needed)
  images: {
    domains: ['logo.clearbit.com', 'assets.coingecko.com'],
  },
  
  // API proxy (optional - helps with CORS in development)
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`,
      },
    ];
  },
};

export default nextConfig;
