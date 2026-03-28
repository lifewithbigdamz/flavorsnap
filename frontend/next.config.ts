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
          }
        ]
      }
    ];
  },
  
  // Environment variables for nonce (passed to client)
  env: {
    CSP_NONCE: generateNonce()
  },
  
  // Webpack configuration to pass nonce to client
  webpack: (config, { isServer }) => {
    if (!isServer) {
      config.plugins.push(
        new config.webpack.DefinePlugin({
          'process.env.CSP_NONCE': JSON.stringify(generateNonce())
        })
      );
    }
    return config;
  }

};

export default withPWA(nextConfig);
