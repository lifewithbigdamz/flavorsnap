import React, { useEffect, useRef, useState } from "react";
import { api } from "@/utils/api";
import { storage } from "@/utils/storage";
import { ErrorMessage } from "@/components/ErrorMessage";
import { useTranslation } from "next-i18next";
import { serverSideTranslations } from "next-i18next/serverSideTranslations";
import type { GetStaticProps } from "next";
import LanguageSwitcher from "@/components/LanguageSwitcher";
import { useKeyboardShortcuts } from "@/utils/useKeyboardShortcuts";
import { exportToCSV, exportToJSON } from "@/utils/exportUtils";
import { ClassificationResult, HistoryEntry, AppError } from "@/types";

const HISTORY_KEY = "classification_history";
const MAX_HISTORY_ITEMS = 50;

export default function Classify() {
  const { t } = useTranslation("common");
  const [image, setImage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<AppError | null>(null);
  const [classification, setClassification] = useState<ClassificationResult | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Load history from local storage on mount
  useEffect(() => {
    const savedHistory = storage.get<HistoryEntry[]>(HISTORY_KEY, []);
    setHistory(savedHistory);
  }, []);

  // Save history whenever it changes
  useEffect(() => {
    if (history.length > 0) {
      storage.set(HISTORY_KEY, history.slice(0, MAX_HISTORY_ITEMS));
    }
  }, [history]);

  const handleReset = () => {
    setImage(null);
    setClassification(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      // Validate file size (e.g., 10MB limit)
      if (file.size > 10 * 1024 * 1024) {
        setError({
          message: t('error_file_too_large', 'File is too large. Max size is 10MB.'),
          code: 'FILE_TOO_LARGE'
        });
        return;
      }

      const imageUrl = URL.createObjectURL(file);
      setImage(imageUrl);
      setError(null);
      setClassification(null);
    }
  };

  const handleClassify = async () => {
    if (!image) return;

    setLoading(true);
    setError(null);

    // Announce to screen readers that classification is starting
    const announcement = document.getElementById('classification-announcement');
    if (announcement) {
      announcement.textContent = t('classifying');
    }

    try {
      const response = await api.post<ClassificationResult>('/api/classify', {
        image: image
      }, {
        retries: 2,
        retryDelay: 1000
      });

      if (response.error) {
        setError({
          message: response.error,
          status: response.status
        });
      } else if (response.data) {
        const result = response.data;
        setClassification(result);
        
        // Add to history
        const newEntry: HistoryEntry = {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          ...result
        };
        
        setHistory(prev => [newEntry, ...prev].slice(0, MAX_HISTORY_ITEMS));
      }
    } catch (err: any) {
      setError({
        message: t('error_classify_retry'),
        details: err
      });
      console.error('Classification error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenPicker = () => {
    fileInputRef.current?.click();
  };

  const handleExportJSON = () => {
    exportToJSON(history, "flavorsnap_history");
  };

  const handleExportCSV = () => {
    exportToCSV(history, "flavorsnap_history");
  };

  const clearHistory = () => {
    if (confirm(t("confirm_clear_history", "Are you sure you want to clear your classification history?"))) {
      setHistory([]);
      storage.remove(HISTORY_KEY);
    }
  };

  useKeyboardShortcuts([
    { key: 'o', action: handleOpenPicker },
    { key: 'c', action: () => image && !loading && handleClassify() },
    { key: 'r', action: handleReset },
    { key: 'Escape', action: handleReset },
  ]);

  return (
    <div className="min-h-screen flex flex-col items-center p-4 md:p-8 bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      <div className="w-full max-w-6xl flex justify-end mb-4">
        <LanguageSwitcher />
      </div>

      <header className="text-center mb-8 md:mb-12">
        <h1 className="text-4xl md:text-6xl font-black mb-4 text-transparent bg-clip-text bg-gradient-to-r from-indigo-500 to-emerald-500 leading-tight">
          {t("app_title")}
        </h1>
        <p className="text-gray-600 dark:text-gray-400 text-sm md:text-lg max-w-sm md:max-w-xl mx-auto">
          {t("shortcut_hint", "Press 'O' for camera, 'C' to classify, 'R' to reset")}
        </p>
      </header>

      {/* Main Action Area */}
      <div className="w-full max-w-4xl flex flex-col items-center">
        {/* Screen reader announcements */}
        <div id="classification-announcement" role="status" aria-live="polite" className="sr-only" />
        <div id="error-announcement" role="alert" aria-live="assertive" className="sr-only" />

        <input
          type="file"
          accept="image/*"
          capture="environment"
          ref={fileInputRef}
          onChange={handleImageChange}
          className="hidden"
          aria-label={t("select_image_file")}
        />

        {!image && (
          <button
            onClick={handleOpenPicker}
            className="group relative bg-indigo-600 text-white px-10 py-8 md:px-16 md:py-12 rounded-[2.5rem] shadow-2xl hover:bg-indigo-700 active:scale-95 transition-all focus:outline-none focus:ring-4 focus:ring-indigo-500/50 flex flex-col items-center gap-4 animate-pulse-slow"
          >
            <div className="w-16 h-16 md:w-24 md:h-24 bg-indigo-500 rounded-full flex items-center justify-center shadow-inner mb-2">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 md:h-14 md:w-14" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <span className="text-xl md:text-3xl font-black tracking-tight">{t("open_camera")}</span>
            <div className="flex gap-2">
              <kbd className="hidden sm:inline-block px-3 py-1 text-xs bg-indigo-500/50 rounded border border-indigo-400/50 backdrop-blur-sm">O</kbd>
            </div>
          </button>
        )}

        {error && (
          <div className="w-full mb-8 mt-4 max-w-md animate-shake">
            <ErrorMessage
              error={error}
              onRetry={() => handleClassify()}
              onDismiss={() => setError(null)}
              variant="inline"
            />
          </div>
        )}

        {image && (
          <div className="w-full space-y-8 animate-fade-in" role="region" aria-label={t("image_preview")}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start">
              <div className="relative group overflow-hidden rounded-[2rem] shadow-2xl border-8 border-white dark:border-gray-800 transition-transform hover:scale-[1.02] duration-500">
                <img
                  src={image}
                  alt={t("preview_alt")}
                  className="w-full h-auto object-cover max-h-80 md:max-h-[500px]"
                />
                <button
                  onClick={handleReset}
                  className="absolute top-4 right-4 bg-black/40 backdrop-blur-xl text-white p-3 rounded-full hover:bg-red-500 transition-all focus:outline-none shadow-lg active:scale-90"
                  title={t("clear_image", "Clear (R)")}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>

              <div className="flex flex-col gap-6">
                <button
                  onClick={handleClassify}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-4 bg-emerald-600 text-white px-8 py-6 md:py-10 rounded-[2rem] shadow-2xl hover:bg-emerald-700 disabled:bg-gray-400 transition-all active:scale-95 text-2xl font-black group"
                >
                  {loading ? (
                    <div className="flex items-center gap-3">
                      <div className="animate-spin h-7 w-7 border-4 border-white border-t-transparent rounded-full" />
                      <span>{t('classifying')}</span>
                    </div>
                  ) : (
                    <>
                      <span>{t('classify_food')}</span>
                      <kbd className="hidden sm:inline-block px-3 py-1 text-sm bg-emerald-500/50 rounded border border-emerald-400 uppercase">C</kbd>
                    </>
                  )}
                </button>

                {classification && (
                  <div className="p-8 bg-white dark:bg-gray-800/80 backdrop-blur-md rounded-[2rem] shadow-2xl border border-emerald-100/50 dark:border-emerald-900/20 animate-scale-in">
                    <h3 className="text-2xl font-black text-gray-900 dark:text-white mb-6 flex items-center gap-3">
                      <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center text-white text-sm">✓</div>
                      {t('classification_result')}
                    </h3>
                    <div className="space-y-6">
                      <div className="bg-emerald-50/50 dark:bg-emerald-900/10 p-6 rounded-3xl flex justify-between items-center border border-emerald-100/30 dark:border-emerald-800/20">
                        <div>
                          <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-black uppercase tracking-[0.2em] mb-1">{t("result_label", "Prediction")}</p>
                          <p className="text-3xl font-black text-indigo-900 dark:text-indigo-100">{classification.food}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-black uppercase tracking-[0.2em] mb-1">{t("result_confidence", "Confidence")}</p>
                          <p className="text-3xl font-black text-emerald-600 dark:text-emerald-400">{(classification.confidence * 100).toFixed(1)}%</p>
                        </div>
                      </div>
                      {classification.calories && (
                        <div className="text-center p-4 bg-orange-50/50 dark:bg-orange-900/10 rounded-2xl border border-orange-100/30 dark:border-orange-800/20">
                          <p className="text-sm text-gray-600 dark:text-gray-400 font-bold">
                            🔥 {t("estimated_calories", "Estimated Calories")}: <span className="text-orange-600 dark:text-orange-400 font-black text-xl ml-1">{classification.calories} kcal</span>
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* History Section */}
      <section className="w-full max-w-6xl mt-20 md:mt-32 pb-20">
        <div className="flex flex-col md:flex-row justify-between items-end mb-10 gap-6">
          <div className="space-y-2">
            <h2 className="text-4xl md:text-5xl font-black text-gray-900 dark:text-white flex items-center gap-4">
              {t("history", "History")}
              <span className="text-lg bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 font-black py-1 px-4 rounded-full">{history.length}</span>
            </h2>
            <p className="text-gray-500 dark:text-gray-400 font-medium">
              {t("history_subtitle", "Your recent food captures and insights")}
            </p>
          </div>

          {history.length > 0 && (
            <div className="flex items-center gap-3">
              <div className="flex p-1 bg-white dark:bg-gray-800 rounded-2xl shadow-sm border border-gray-100 dark:border-gray-700">
                <button
                  onClick={handleExportJSON}
                  className="px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-xl text-sm font-bold text-gray-600 dark:text-gray-300 transition-all"
                >
                  JSON
                </button>
                <button
                  onClick={handleExportCSV}
                  className="px-4 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 rounded-xl text-sm font-bold text-gray-600 dark:text-gray-300 transition-all"
                >
                  CSV
                </button>
              </div>
              <button
                onClick={clearHistory}
                className="bg-red-50 dark:bg-red-900/10 text-red-500 hover:bg-red-500 hover:text-white p-3.5 rounded-2xl transition-all shadow-sm border border-red-100 dark:border-red-900/20"
                title={t("clear_history", "Clear History")}
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            </div>
          )}
        </div>

        {history.length === 0 ? (
          <div className="bg-white dark:bg-gray-800/40 rounded-[3rem] py-24 text-center border-4 border-dashed border-gray-100 dark:border-gray-800 animate-pulse-slow">
            <div className="w-20 h-20 bg-gray-50 dark:bg-gray-800 rounded-full flex items-center justify-center mx-auto mb-6">
              <svg xmlns="http://www.w3.org/2000/svg" className="h-10 w-10 text-gray-300 dark:text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </div>
            <p className="text-gray-400 dark:text-gray-500 text-xl font-bold">
              {t("no_history_yet", "Your food snapshots will appear here")}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
            {history.map((entry) => (
              <div
                key={entry.id}
                className="bg-white dark:bg-gray-800 p-6 rounded-[2rem] shadow-xl border border-gray-50 dark:border-gray-700/50 hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 group"
              >
                <div className="flex justify-between items-start mb-6">
                  <span className="bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 text-[10px] font-black px-3 py-1.5 rounded-xl uppercase tracking-widest">
                    {new Date(entry.id).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  </span>
                  <div className="flex items-center gap-1.5 bg-emerald-50 dark:bg-emerald-900/30 px-2 py-1 rounded-lg">
                    <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
                    <span className="text-emerald-600 dark:text-emerald-400 font-black text-xs">{(entry.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
                <h4 className="text-2xl font-black text-gray-900 dark:text-white capitalize mb-2 line-clamp-1 group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">{entry.food}</h4>
                {entry.calories && (
                  <p className="text-sm text-gray-400 dark:text-gray-500 font-bold flex items-center gap-1.5">
                    <span className="text-orange-500">🔥</span> {entry.calories} kcal
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

export const getStaticProps: GetStaticProps = async ({ locale }) => ({
  props: {
    ...(await serverSideTranslations(locale ?? "en", ["common"])),
  },
});