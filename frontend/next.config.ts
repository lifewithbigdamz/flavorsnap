import type { NextConfig } from "next";
import crypto from 'crypto';
import { i18n } from "./next-i18next.config";

// Note: next-pwa is required for this feature, but currently we are focusing on fixing
// the cache invalidation issues. Using StaleWhileRevalidate for images ensures
// they are updated when the underlying data changes.
const withPWA = require("next-pwa")({
  dest: "public",
  disable: process.env.NODE_ENV === "development",
  register: true,
  skipWaiting: true,
  runtimeCaching: [
    {
      urlPattern: /^https?.*\/api\/.*$/,
      handler: "NetworkFirst",
      options: {
        cacheName: "api-cache",
        expiration: {
          maxEntries: 50,
          maxAgeSeconds: 60 * 60 * 24, // 24 hours
        },
        networkTimeoutSeconds: 10, // Ensure we don't wait forever on flaky networks
      },
    },
    {
      urlPattern: /\.(?:jpg|jpeg|png|gif|webp|svg)$/,
      handler: "StaleWhileRevalidate", // Changed from CacheFirst to fix invalidation issues
      options: {
        cacheName: "image-cache",
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
        },
      },
    },
    {
      urlPattern: /\.(?:js|css|html)$/,
      handler: "StaleWhileRevalidate",
      options: {
        cacheName: "static-resources",
      },
    },
  ],
});
// 1. Properly import the i18n configuration
const { i18n } = require("./next-i18next.config.js");

// Generate nonce function for CSP
const generateNonce = () => crypto.randomBytes(16).toString('base64');

const nextConfig: NextConfig = {
  reactStrictMode: true,
  i18n,
  
  // Image optimization for SEO and performance
  images: {
    formats: ['image/webp', 'image/avif'],
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 3840],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384],
    minimumCacheTTL: 60 * 60 * 24 * 30, // 30 days
    dangerouslyAllowSVG: true,
    contentSecurityPolicy: "default-src 'self'; script-src 'none'; sandbox;",
  },
  
  // Compression for better performance
  compress: true,
  
  // Power by headers for SEO
  poweredByHeader: false,
  
  // Generate ETags for caching
  generateEtags: true,
  
  // Security headers and CSP
  async headers() {
    const nonce = generateNonce();
    
    return [
      {
        source: '/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: [
              `default-src 'self';`,
              `script-src 'self' 'nonce-${nonce}' https://vercel.live https://www.googletagmanager.com;`,
              `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;`,
              `font-src 'self' https://fonts.gstatic.com;`,
              `img-src 'self' data: blob: https:;`,
              `connect-src 'self' https://api.openai.com https://vercel.live https://www.google-analytics.com;`,
              `frame-src 'none';`,
              `object-src 'none';`,
              `base-uri 'self';`,
              `form-action 'self';`,
              `upgrade-insecure-requests;`
            ].join(' ')
          },
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff'
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY'
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block'
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin'
          },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=(), interest-cohort=()'
          },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains; preload'
          },
          // SEO and performance headers
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable'
          },
          {
            key: 'X-DNS-Prefetch-Control',
            value: 'on'
          }
        ]
      },
      {
        // API routes get different CSP
        source: '/api/(.*)',
        headers: [
          {
            key: 'Content-Security-Policy',
            value: "default-src 'self'; script-src 'self'; style-src 'self';"
          },
          {
            key: 'Cache-Control',
            value: 'public, max-age=3600, must-revalidate'
          }
        ]
      },
      {
        // Static assets with long cache
        source: '/_next/static/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=31536000, immutable'
          }
        ]
      },
      {
        // Images with optimized caching
        source: '/images/(.*)',
        headers: [
          {
            key: 'Cache-Control',
            value: 'public, max-age=2592000, must-revalidate'
          }
        ]
      }
    ];
  },
  
  // Redirects for SEO
  async redirects() {
    return [
      {
        source: '/home',
        destination: '/',
        permanent: true,
      },
      {
        source: '/index.html',
        destination: '/',
        permanent: true,
      },
      {
        source: '/classify-food',
        destination: '/classify',
        permanent: true,
      },
      {
        source: '/food-history',
        destination: '/history',
        permanent: true,
      },
    ];
  },
  
  // Environment variables for nonce (passed to client)
  env: {
    CSP_NONCE: generateNonce(),
    NEXT_PUBLIC_SITE_URL: process.env.NEXT_PUBLIC_SITE_URL || 'https://flavorsnap.com',
  },
  
  // Webpack configuration for performance optimization
  webpack: (config, { isServer, dev }) => {
    if (!isServer) {
      config.plugins.push(
        new config.webpack.DefinePlugin({
          'process.env.CSP_NONCE': JSON.stringify(generateNonce())
        })
      );
    }
    
    // Optimize for production
    if (!dev) {
      config.optimization = {
        ...config.optimization,
        splitChunks: {
          chunks: 'all',
          cacheGroups: {
            vendor: {
              test: /[\\/]node_modules[\\/]/,
              name: 'vendors',
              chunks: 'all',
            },
            common: {
              name: 'common',
              minChunks: 2,
              chunks: 'all',
              enforce: true,
            },
          },
        },
      };
    }
    
    return config;
  },

  // Experimental features for better performance
  experimental: {
    optimizeCss: true,
    optimizePackageImports: ['lucide-react', 'recharts'],
  },

};

export default withPWA(nextConfig);
