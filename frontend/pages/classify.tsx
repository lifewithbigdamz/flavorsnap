import { useRouter } from 'next/router';
import { Camera, Upload, Zap, BarChart3 } from 'lucide-react';
import { useEffect, useRef } from 'react';

export default function Classify() {
  const router = useRouter();
  const singleButtonRef = useRef<HTMLButtonElement>(null);
  const batchButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    // Focus management - set initial focus to first option
    singleButtonRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent, action: () => void) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      action();
    }
    
    // Arrow key navigation between options
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      if (document.activeElement === singleButtonRef.current) {
        batchButtonRef.current?.focus();
      }
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      if (document.activeElement === batchButtonRef.current) {
        singleButtonRef.current?.focus();
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 to-blue-50 py-12">
      <div className="max-w-4xl mx-auto px-4">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Choose Classification Mode
          </h1>
          <p className="text-lg text-gray-600">
            Select how you'd like to classify your food images
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8">
          {/* Single Image Classification */}
          <div className="bg-white rounded-xl shadow-lg p-8 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full mb-6">
              <Camera className="w-8 h-8 text-blue-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Single Image
            </h2>
            <p className="text-gray-600 mb-6">
              Upload and classify one image at a time. Perfect for quick predictions and immediate results.
            </p>
            <ul className="space-y-2 mb-6 text-sm text-gray-600">
              <li className="flex items-center">
                <Zap className="w-4 h-4 text-yellow-500 mr-2" />
                Instant results
              </li>
              <li className="flex items-center">
                <Zap className="w-4 h-4 text-yellow-500 mr-2" />
                Detailed confidence scores
              </li>
              <li className="flex items-center">
                <Zap className="w-4 h-4 text-yellow-500 mr-2" />
                Top 3 predictions
              </li>
            </ul>
            <button
              ref={singleButtonRef}
              onClick={() => router.push('/single')}
              onKeyDown={(e) => handleKeyDown(e, () => router.push('/single'))}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition focus:outline-none focus:ring-4 focus:ring-blue-500/50"
              aria-label="Classify single image - Upload and classify one image at a time"
            >
              Classify Single Image
            </button>
          </div>

          {/* Batch Image Classification */}
          <div className="bg-white rounded-xl shadow-lg p-8 hover:shadow-xl transition-shadow">
            <div className="flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-6">
              <Upload className="w-8 h-8 text-green-600" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-4">
              Batch Processing
            </h2>
            <p className="text-gray-600 mb-6">
              Upload and classify multiple images simultaneously. Ideal for large datasets and efficient processing.
            </p>
            <ul className="space-y-2 mb-6 text-sm text-gray-600">
              <li className="flex items-center">
                <BarChart3 className="w-4 h-4 text-green-500 mr-2" />
                Process up to 50 images
              </li>
              <li className="flex items-center">
                <BarChart3 className="w-4 h-4 text-green-500 mr-2" />
                Progress tracking
              </li>
              <li className="flex items-center">
                <BarChart3 className="w-4 h-4 text-green-500 mr-2" />
                Export results (JSON/CSV)
              </li>
            </ul>
            <button
              ref={batchButtonRef}
              onClick={() => router.push('/batch')}
              onKeyDown={(e) => handleKeyDown(e, () => router.push('/batch'))}
              className="w-full bg-green-600 text-white py-3 rounded-lg font-semibold hover:bg-green-700 transition focus:outline-none focus:ring-4 focus:ring-green-500/50"
              aria-label="Start batch processing - Upload and classify multiple images simultaneously"
            >
              Start Batch Processing
            </button>
          </div>
        </div>

        <div className="mt-12 text-center">
          <button
            onClick={() => router.push('/')}
            onKeyDown={(e) => handleKeyDown(e, () => router.push('/'))}
            className="text-gray-600 hover:text-gray-800 focus:outline-none focus:ring-2 focus:ring-gray-500 px-4 py-2 rounded-lg"
            aria-label="Go back to home page"
          >
            ← Back to Home
          </button>
        </div>
      </div>
    </div>
  );
}
