import "@/styles/globals.css";
import type { AppProps } from "next/app";
import ErrorBoundary from "@/components/ErrorBoundary";
import { ThemeProvider } from "@/components/ThemeProvider";
import NotificationSystem from "@/components/NotificationSystem";
import { appWithTranslation } from 'next-i18next';

// reportWebVitals can be imported from a utils file if you have one
// import { reportWebVitals } from '@/utils/web-vitals';

function App({ Component, pageProps }: AppProps) {
  return (
    <ThemeProvider>
      <ErrorBoundary>
        <Component {...pageProps} />
        <NotificationSystem />
      </ErrorBoundary>
    </ThemeProvider>
  );
}

export default appWithTranslation(App);