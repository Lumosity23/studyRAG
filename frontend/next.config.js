/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: 'http://localhost:8000/api/v1/:path*', // Proxy vers le backend FastAPI
      },
      {
        source: '/health/:path*',
        destination: 'http://localhost:8000/health/:path*', // Proxy pour health check
      },
    ]
  },
  // Configuration pour augmenter les timeouts
  experimental: {
    proxyTimeout: 120000, // 2 minutes timeout
  },
  // Headers pour éviter les timeouts
  async headers() {
    return [
      {
        source: '/api/v1/:path*',
        headers: [
          {
            key: 'Connection',
            value: 'keep-alive',
          },
          {
            key: 'Keep-Alive',
            value: 'timeout=120',
          },
        ],
      },
    ]
  },
}

module.exports = nextConfig