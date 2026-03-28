import { ApiErrorResponse } from "../types";

interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
  progress?: number; // Progress percentage (0-100)
  cached?: boolean; // Whether response came from cache
}

interface ApiOptions extends RequestInit {
  retries?: number;
  retryDelay?: number;
  skipCache?: boolean; // Skip cache for this request
}

interface CacheEntry<T = any> {
  data: T;
  timestamp: number;
  ttl: number;
}

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: ApiErrorResponse,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

// Cache configuration
const CACHE_CONFIG = {
  defaultTTL: 60 * 60 * 1000, // 1 hour in milliseconds
  maxEntries: 100, // Maximum cache entries
  storageKey: 'flavorsnap_api_cache',
};

// In-memory cache for faster access
let memoryCache: Map<string, CacheEntry> = new Map();

// Load cache from localStorage on module load
const loadCacheFromStorage = () => {
  try {
    const stored = localStorage.getItem(CACHE_CONFIG.storageKey);
    if (stored) {
      const parsed = JSON.parse(stored);
      memoryCache = new Map(Object.entries(parsed));
      // Clean expired entries
      cleanExpiredCache();
    }
  } catch (error) {
    console.warn('Failed to load cache from localStorage:', error);
  }
};

// Save cache to localStorage
const saveCacheToStorage = () => {
  try {
    const cacheObject = Object.fromEntries(memoryCache);
    localStorage.setItem(CACHE_CONFIG.storageKey, JSON.stringify(cacheObject));
  } catch (error) {
    console.warn('Failed to save cache to localStorage:', error);
  }
};

// Clean expired cache entries
const cleanExpiredCache = () => {
  const now = Date.now();
  const expiredKeys: string[] = [];

  for (const [key, entry] of memoryCache.entries()) {
    if (now > entry.timestamp + entry.ttl) {
      expiredKeys.push(key);
    }
  }

  expiredKeys.forEach(key => memoryCache.delete(key));

  if (expiredKeys.length > 0) {
    console.log(`Cleaned ${expiredKeys.length} expired cache entries`);
    saveCacheToStorage();
  }
};

// Generate cache key from image data
const generateCacheKey = (imageData: ArrayBuffer | string): string => {
  if (typeof imageData === 'string') {
    // If it's already a hash, use it directly
    return `img_${imageData}`;
  }

  // Generate hash from ArrayBuffer
  const hashBuffer = crypto.subtle.digestSync('SHA-256', imageData);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return `img_${hashHex}`;
};

// Get cached response
const getCachedResponse = <T>(cacheKey: string): ApiResponse<T> | null => {
  const entry = memoryCache.get(cacheKey);
  if (!entry) return null;

  const now = Date.now();
  if (now > entry.timestamp + entry.ttl) {
    memoryCache.delete(cacheKey);
    saveCacheToStorage();
    return null;
  }

  console.log(`Cache hit for key: ${cacheKey.substring(0, 12)}...`);
  return {
    data: entry.data,
    status: 200,
    cached: true
  };
};

// Cache response
const cacheResponse = <T>(cacheKey: string, data: T, ttl?: number) => {
  const entry: CacheEntry<T> = {
    data,
    timestamp: Date.now(),
    ttl: ttl || CACHE_CONFIG.defaultTTL
  };

  // Enforce max entries limit (simple LRU-like behavior)
  if (memoryCache.size >= CACHE_CONFIG.maxEntries) {
    const firstKey = memoryCache.keys().next().value;
    memoryCache.delete(firstKey);
  }

  memoryCache.set(cacheKey, entry);
  saveCacheToStorage();
  console.log(`Cached response for key: ${cacheKey.substring(0, 12)}...`);
};

// Initialize cache
loadCacheFromStorage();

// Clean cache periodically
setInterval(cleanExpiredCache, 5 * 60 * 1000); // Every 5 minutes

const apiRequest = async <T = any>(
  url: string,
  options: ApiOptions = {},
  onProgress?: (progress: number) => void, // Progress callback
): Promise<ApiResponse<T>> => {
  const { retries = 3, retryDelay = 1000, skipCache = false, ...fetchOptions } = options;

  let lastError: Error | null = null;

  // Check cache for prediction requests with image data
  if (!skipCache && url.includes('/predict') && fetchOptions.body instanceof FormData) {
    try {
      // Extract image data from FormData for hashing
      const imageFile = fetchOptions.body.get('image') as File;
      if (imageFile) {
        const imageData = await imageFile.arrayBuffer();
        const cacheKey = generateCacheKey(imageData);

        // Check for cached response
        const cachedResponse = getCachedResponse<T>(cacheKey);
        if (cachedResponse) {
          return cachedResponse;
        }
      }
    } catch (error) {
      console.warn('Cache check failed:', error);
    }
  }

  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const isFormData = typeof FormData !== "undefined" && fetchOptions.body instanceof FormData;
      const defaultHeaders: Record<string, string> = isFormData ? {} : { "Content-Type": "application/json" };

      // Track upload progress for FormData
      if (isFormData && onProgress && fetchOptions.body instanceof FormData) {
        const xhr = new XMLHttpRequest();

        return new Promise((resolve, reject) => {
          xhr.open(fetchOptions.method || 'POST', url);

          // Set headers
          Object.entries(defaultHeaders).forEach(([key, value]) => {
            if (value) xhr.setRequestHeader(key, value);
          });

          // Progress tracking
          xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable && onProgress) {
              const progress = Math.round((e.loaded / e.total) * 100);
              onProgress(progress);
            }
          });

          xhr.onload = () => {
            if (xhr.status >= 200 && xhr.status < 300) {
              try {
                const data = JSON.parse(xhr.responseText);

                // Cache successful prediction responses
                if (url.includes('/predict') && fetchOptions.body instanceof FormData) {
                  try {
                    const imageFile = fetchOptions.body.get('image') as File;
                    if (imageFile) {
                      imageFile.arrayBuffer().then(imageData => {
                        const cacheKey = generateCacheKey(imageData);
                        cacheResponse(cacheKey, data);
                      });
                    }
                  } catch (cacheError) {
                    console.warn('Failed to cache response:', cacheError);
                  }
                }

                resolve({ data, status: xhr.status, cached: false });
              } catch {
                resolve({ data: undefined, status: xhr.status, cached: false });
              }
            } else {
              try {
                const data = JSON.parse(xhr.responseText);
                reject(new ApiError(data.error || `HTTP ${xhr.status}`, xhr.status, data));
              } catch {
                reject(new ApiError(`HTTP ${xhr.status}`, xhr.status));
              }
            }
          };

          xhr.onerror = () => reject(new ApiError('Network error', 0));

          // Send FormData directly
          xhr.send(fetchOptions.body as XMLHttpRequestBodyInit);
        });
      }

      const response = await fetch(url, {
        ...fetchOptions,
        headers: {
          ...defaultHeaders,
          ...(fetchOptions.headers as Record<string, string>),
        },
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const errorMessage =
          (data as ApiErrorResponse)?.error || (data as ApiErrorResponse)?.message || `HTTP ${response.status}`;
        throw new ApiError(errorMessage, response.status, data);
      }

      // Cache successful prediction responses
      if (url.includes('/predict') && !skipCache) {
        try {
          // For fetch requests, we can't easily get the image data for hashing
          // The server-side caching will handle this case
        } catch (cacheError) {
          console.warn('Failed to cache response:', cacheError);
        }
      }

      return {
        data: data as T,
        status: response.status,
        cached: false
      };
    } catch (error) {
      lastError =
        error instanceof Error ? error : new Error("Unknown error occurred");

      // Don't retry on client errors (4xx) except for 429 (rate limit)
      if (
        lastError instanceof ApiError &&
        lastError.status >= 400 &&
        lastError.status < 500 &&
        lastError.status !== 429
      ) {
        break;
      }

      // If this is the last attempt, don't wait
      if (attempt < retries) {
        await sleep(retryDelay * Math.pow(2, attempt)); // Exponential backoff
      }
    }
  }

  return {
    error: lastError?.message || "Request failed",
    status: lastError instanceof ApiError ? lastError.status : 500,
    cached: false
  };
};

// API methods with error handling
export const api = {
  get: <T = any>(url: string, options?: ApiOptions) =>
    apiRequest<T>(url, { method: "GET", ...options }),

  post: <T = any>(url: string, data?: any, options?: ApiOptions, onProgress?: (progress: number) => void) =>
    apiRequest<T>(url, {
      method: "POST",
      body: (typeof FormData !== "undefined" && data instanceof FormData) ? data : (data ? JSON.stringify(data) : undefined),
      ...options,
    }, onProgress),

  put: <T = any>(url: string, data?: any, options?: ApiOptions, onProgress?: (progress: number) => void) =>
    apiRequest<T>(url, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
      ...options,
    }, onProgress),

  delete: <T = any>(url: string, options?: ApiOptions) =>
    apiRequest<T>(url, { method: "DELETE", ...options }),

  // Cache management methods
  cache: {
    clear: () => {
      memoryCache.clear();
      localStorage.removeItem(CACHE_CONFIG.storageKey);
      console.log('Cache cleared');
    },

    getStats: () => {
      cleanExpiredCache();
      return {
        entries: memoryCache.size,
        maxEntries: CACHE_CONFIG.maxEntries,
        defaultTTL: CACHE_CONFIG.defaultTTL
      };
    },

    setTTL: (ttlMs: number) => {
      CACHE_CONFIG.defaultTTL = ttlMs;
      console.log(`Cache TTL set to ${ttlMs}ms`);
    }
  }
};

export { ApiError };
export type { ApiResponse };
