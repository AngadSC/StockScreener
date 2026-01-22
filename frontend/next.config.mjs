/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  images: {
    domains: ['logo.clearbit.com', 'assets.coingecko.com'],
  },
  
  async rewrites() {
    // 1. Get the API URL from environment, OR fallback to your Railway URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://stockscreenerapi-production.up.railway.app/api/v1';
    
    // 2. Log it so you can see it in the Vercel Build Logs
    console.log('Using API URL:', apiUrl);

    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;