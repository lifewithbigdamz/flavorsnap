import React, { useMemo } from 'react';
import { useTranslation } from 'next-i18next';
import { ClassificationResult as IClassificationResult } from '../types';

interface ClassificationResultProps {
  result: IClassificationResult;
  loading?: boolean;
}

export function ClassificationResult({ result, loading = false }: ClassificationResultProps) {
  const { t } = useTranslation('common');

  const confidencePercentage = useMemo(() => 
    Math.round(result.confidence * 100), 
    [result.confidence]
  );

  const getConfidenceLevel = (confidence: number) => {
    if (confidence > 0.8) return 'high';
    if (confidence > 0.5) return 'medium';
    return 'low';
  };

  const confidenceLevel = getConfidenceLevel(result.confidence);

  return (
    <div 
      className="w-full bg-white dark:bg-gray-800 rounded-[2rem] shadow-2xl p-6 sm:p-8 border border-gray-100 dark:border-gray-700 animate-scale-in"
      role="region"
      aria-labelledby="result-title"
    >
      <h3 id="result-title" className="text-xl sm:text-2xl font-black text-gray-900 dark:text-white mb-6 flex items-center gap-3">
        <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center text-white text-sm" aria-hidden="true">✓</div>
        {t('classification_result', 'Analysis Results')}
      </h3>

      <div className="space-y-6">
        {/* Main Prediction */}
        <div 
          className="bg-emerald-50/50 dark:bg-emerald-900/10 p-6 rounded-3xl flex flex-col sm:flex-row justify-between items-center border border-emerald-100/30 dark:border-emerald-800/20 gap-4"
          aria-live="polite"
        >
          <div className="text-center sm:text-left">
            <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-black uppercase tracking-[0.2em] mb-1">
              {t('result_label', 'Detected Food')}
            </p>
            <p className="text-3xl sm:text-4xl font-black text-indigo-900 dark:text-indigo-100 capitalize">
              {result.food || result.prediction}
            </p>
          </div>
          
          <div className="text-center sm:text-right">
            <p className="text-[10px] text-emerald-600 dark:text-emerald-400 font-black uppercase tracking-[0.2em] mb-1">
              {t('result_confidence', 'Confidence')}
            </p>
            <div className="flex items-center gap-2 justify-center sm:justify-end">
              <p className={`text-3xl sm:text-4xl font-black ${
                confidenceLevel === 'high' ? 'text-emerald-600' : 
                confidenceLevel === 'medium' ? 'text-orange-500' : 'text-red-500'
              }`}>
                {confidencePercentage}%
              </p>
            </div>
          </div>
        </div>

        {/* Nutritional Insights (Simulated for Now) */}
        {result.calories && (
          <div className="p-4 bg-orange-50/50 dark:bg-orange-900/10 rounded-2xl border border-orange-100/30 dark:border-orange-800/20 flex items-center justify-center gap-3">
            <span className="text-2xl" aria-hidden="true">🔥</span>
            <p className="text-sm sm:text-base text-gray-700 dark:text-gray-300 font-bold">
              {t('estimated_calories', 'Estimated Calories')}: 
              <span className="text-orange-600 dark:text-orange-400 font-black text-xl ml-2">
                {result.calories} kcal
              </span>
            </p>
          </div>
        )}

        {/* Accessibility Announcement for Screen Readers */}
        <div className="sr-only" aria-live="assertive">
          {t('classification_announcement', 'Classification complete. Found {{food}} with {{confidence}}% confidence.', {
            food: result.food || result.prediction,
            confidence: confidencePercentage
          })}
        </div>

        {/* Processing Details */}
        {result.processing_time && (
          <p className="text-[10px] text-gray-400 dark:text-gray-500 text-center uppercase tracking-widest">
            {t('processed_in', 'Processed in {{time}}ms', { time: Math.round(result.processing_time) })}
          </p>
        )}
      </div>
    </div>
  );
}
