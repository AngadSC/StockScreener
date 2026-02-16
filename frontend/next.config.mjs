/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  images: {
    domains: ['logo.clearbit.com', 'assets.coingecko.com'],
  },

  async headers() {
    const csp = [
      "default-src 'self'",
      "base-uri 'self'",
      "frame-ancestors 'none'",
      "object-src 'none'",
      "script-src 'self' 'unsafe-inline' https://s3.tradingview.com https://*.tradingview.com",
      "style-src 'self' 'unsafe-inline'",
      "img-src 'self' data: https: https://*.tradingview.com",
      "connect-src 'self' https: wss://*.tradingview.com",
      "frame-src 'self' https://*.tradingview.com",
      "font-src 'self' data:",
      "form-action 'self'",
    ].join('; ');

    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Content-Security-Policy', value: csp },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Strict-Transport-Security', value: 'max-age=31536000; includeSubDomains; preload' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        ],
      },
    ];
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
