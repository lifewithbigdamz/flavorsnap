import { Html, Head, Main, NextScript } from "next/document";
import type { DocumentProps } from "next/document";

const rtlLocales = ["ar"];

export default function Document(props: DocumentProps) {
  const locale = props.__NEXT_DATA__?.locale || "en";
  const dir = rtlLocales.includes(locale) ? "rtl" : "ltr";

  // Generate nonce for CSP
  const nonce = process.env.NODE_ENV === 'production' 
    ? 'GENERATE_SECURE_NONCE_HERE' 
    : 'development-nonce';

  return (
    <Html lang={locale} dir={dir}>
      <Head>
        {/* Content Security Policy */}
        <meta
          httpEquiv="Content-Security-Policy"
          content={`
            default-src 'self';
            script-src 'self' 'nonce-${nonce}' https://vercel.live;
            style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
            font-src 'self' https://fonts.gstatic.com;
            img-src 'self' data: blob: https:;
            connect-src 'self' https://api.openai.com https://vercel.live;
            frame-src 'none';
            object-src 'none';
            base-uri 'self';
            form-action 'self';
            upgrade-insecure-requests;
          `.replace(/\s+/g, ' ').trim()}
        />
        
        {/* Additional Security Headers */}
        <meta httpEquiv="X-Content-Type-Options" content="nosniff" />
        <meta httpEquiv="X-Frame-Options" content="DENY" />
        <meta httpEquiv="X-XSS-Protection" content="1; mode=block" />
        <meta httpEquiv="Referrer-Policy" content="strict-origin-when-cross-origin" />
        <meta httpEquiv="Permissions-Policy" content="camera=(), microphone=(), geolocation=()" />
        
        {/* Preconnect for external domains */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </Head>
      <body className="antialiased">
        <div id="skip-to-content">
          <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-blue-600 text-white px-4 py-2 rounded-md z-50">
            Skip to main content
          </a>
        </div>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
