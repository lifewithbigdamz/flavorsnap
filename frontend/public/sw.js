const CACHE_NAME = 'flavorsnap-v2';
const STATIC_CACHE_NAME = 'flavorsnap-static-v2';
const DYNAMIC_CACHE_NAME = 'flavorsnap-dynamic-v2';
const ANALYTICS_CACHE_NAME = 'flavorsnap-analytics-v2';
const IMAGE_CACHE_NAME = 'flavorsnap-images-v2';

// Files to cache for offline functionality
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.json',
  '/_next/static/css/app/layout.css',
  '/_next/static/chunks/webpack.js',
  '/_next/static/chunks/framework.js',
  '/_next/static/chunks/main.js',
  '/_next/static/chunks/pages/_app.js',
  '/_next/static/chunks/pages/_error.js',
  '/_next/static/chunks/pages/index.js',
  '/images/hero_img.png',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png',
  '/icons/icon-72x72.png',
  '/icons/icon-96x96.png',
  '/icons/icon-128x128.png',
  '/icons/icon-144x144.png',
  '/icons/icon-152x152.png'
];

// API endpoints that can be cached
const CACHEABLE_APIS = [
  '/api/classify',
  '/api/food-classes',
  '/api/projects',
  '/api/community/forums',
  '/api/community/threads'
];

// Cache strategies
const CACHE_STRATEGIES = {
  CACHE_FIRST: 'cache-first',
  NETWORK_FIRST: 'network-first',
  STALE_WHILE_REVALIDATE: 'stale-while-revalidate',
  CACHE_ONLY: 'cache-only',
  NETWORK_ONLY: 'network-only'
};

// Background sync queue
let backgroundSyncQueue = [];
let offlineAnalytics = [];

// Performance monitoring
const performanceMetrics = {
  cacheHits: 0,
  cacheMisses: 0,
  networkRequests: 0,
  offlineRequests: 0,
  averageResponseTime: 0,
  totalResponseTime: 0,
  requestCount: 0
};

// Install event - cache static assets and initialize caches
self.addEventListener('install', (event) => {
  console.log('Service Worker: Installing...');
  
  event.waitUntil(
    Promise.all([
      // Cache static assets
      caches.open(STATIC_CACHE_NAME)
        .then((cache) => {
          console.log('Service Worker: Caching static assets');
          return cache.addAll(STATIC_ASSETS);
        }),
      // Initialize other caches
      caches.open(DYNAMIC_CACHE_NAME),
      caches.open(ANALYTICS_CACHE_NAME),
      caches.open(IMAGE_CACHE_NAME),
      // Preload critical APIs
      preloadCriticalData()
    ])
      .then(() => {
        console.log('Service Worker: Installation complete');
        return self.skipWaiting();
      })
      .catch((error) => {
        console.error('Service Worker: Installation failed:', error);
      })
  );
});

// Preload critical data for better offline experience
async function preloadCriticalData() {
  try {
    const cache = await caches.open(DYNAMIC_CACHE_NAME);
    const criticalApis = ['/api/food-classes'];
    
    for (const api of criticalApis) {
      try {
        const response = await fetch(api);
        if (response.ok) {
          cache.put(api, response);
        }
      } catch (error) {
        console.log(`Failed to preload ${api}:`, error);
      }
    }
  } catch (error) {
    console.error('Error preloading critical data:', error);
  }
}

// Activate event - clean up old caches and claim clients
self.addEventListener('activate', (event) => {
  console.log('Service Worker: Activating...');
  
  event.waitUntil(
    Promise.all([
      // Clean up old caches
      caches.keys()
        .then((cacheNames) => {
          return Promise.all(
            cacheNames.map((cacheName) => {
              const currentCaches = [STATIC_CACHE_NAME, DYNAMIC_CACHE_NAME, ANALYTICS_CACHE_NAME, IMAGE_CACHE_NAME];
              if (!currentCaches.includes(cacheName)) {
                console.log('Service Worker: Deleting old cache:', cacheName);
                return caches.delete(cacheName);
              }
            })
          );
        }),
      // Claim all clients
      self.clients.claim(),
      // Initialize background sync
      initializeBackgroundSync()
    ])
      .then(() => {
        console.log('Service Worker: Activation complete');
        // Notify all clients about the update
        return self.clients.matchAll()
          .then(clients => {
            clients.forEach(client => {
              client.postMessage({
                type: 'SW_UPDATED',
                msg: 'Service Worker updated'
              });
            });
          });
      })
  );
});

// Initialize background sync
async function initializeBackgroundSync() {
  try {
    // Load any queued background sync operations
    const storedQueue = await getStoredBackgroundSyncQueue();
    backgroundSyncQueue = storedQueue || [];
    
    // Load offline analytics
    const storedAnalytics = await getStoredOfflineAnalytics();
    offlineAnalytics = storedAnalytics || [];
    
    console.log(`Background sync initialized with ${backgroundSyncQueue.length} queued operations`);
  } catch (error) {
    console.error('Error initializing background sync:', error);
  }
}

// Fetch event - advanced caching strategies
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  const startTime = performance.now();
  
  // Handle POST requests for offline queuing
  if (request.method === 'POST') {
    event.respondWith(handlePostRequest(request));
    return;
  }
  
  // Handle API requests with intelligent caching
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(handleApiRequest(request, startTime));
    return;
  }
  
  // Handle image requests with specialized caching
  if (url.pathname.match(/\.(jpg|jpeg|png|gif|webp|svg)$/i)) {
    event.respondWith(handleImageRequest(request, startTime));
    return;
  }
  
  // Handle static assets
  if (STATIC_ASSETS.some(asset => url.pathname === asset || url.pathname.includes(asset))) {
    event.respondWith(handleStaticRequest(request, startTime));
    return;
  }
  
  // Handle navigation requests (SPA routing)
  if (request.mode === 'navigate') {
    event.respondWith(handleNavigationRequest(request, startTime));
    return;
  }
  
  // Default: network first with cache fallback
  event.respondWith(handleDefaultRequest(request, startTime));
});

// Handle POST requests with offline queuing
async function handlePostRequest(request) {
  const url = new URL(request.url);
  
  try {
    // Try network first
    const response = await fetch(request.clone());
    updatePerformanceMetrics('network', performance.now());
    return response;
  } catch (error) {
    console.log('Service Worker: POST request failed, queuing for background sync:', request.url);
    
    // Queue the request for background sync
    await queueBackgroundSync({
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      body: await request.text(),
      timestamp: Date.now()
    });
    
    // Return appropriate response
    if (url.pathname.startsWith('/api/')) {
      return new Response(JSON.stringify({
        error: 'You are currently offline. Your request has been saved and will be sent when you are back online.',
        offline: true,
        queued: true
      }), {
        status: 202, // Accepted
        statusText: 'Accepted - Queued for background sync',
        headers: {
          'Content-Type': 'application/json'
        }
      });
    }
    
    throw error;
  }
}

// Handle API requests with intelligent caching
async function handleApiRequest(request, startTime) {
  const url = new URL(request.url);
  const strategy = getCacheStrategy(url.pathname);
  
  try {
    let response;
    
    switch (strategy) {
      case CACHE_STRATEGIES.CACHE_FIRST:
        response = await cacheFirst(request, DYNAMIC_CACHE_NAME);
        break;
      case CACHE_STRATEGIES.NETWORK_FIRST:
        response = await networkFirst(request, DYNAMIC_CACHE_NAME);
        break;
      case CACHE_STRATEGIES.STALE_WHILE_REVALIDATE:
        response = await staleWhileRevalidate(request, DYNAMIC_CACHE_NAME);
        break;
      default:
        response = await networkFirst(request, DYNAMIC_CACHE_NAME);
    }
    
    updatePerformanceMetrics('cache', startTime);
    return response;
  } catch (error) {
    updatePerformanceMetrics('offline', startTime);
    console.log('Service Worker: API request failed, trying cache:', request.url);
    
    // Try to serve from cache regardless of strategy
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Enhanced offline fallbacks
    return getOfflineResponse(url.pathname);
  }
}

// Handle image requests with specialized caching
async function handleImageRequest(request, startTime) {
  try {
    const response = await cacheFirst(request, IMAGE_CACHE_NAME);
    updatePerformanceMetrics('cache', startTime);
    return response;
  } catch (error) {
    updatePerformanceMetrics('offline', startTime);
    
    // Return placeholder image
    return new Response(
      `<svg width="200" height="200" xmlns="http://www.w3.org/2000/svg">
        <rect width="100%" height="100%" fill="#f3f4f6"/>
        <text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="#6b7280" font-family="sans-serif">
          Image unavailable offline
        </text>
      </svg>`,
      {
        status: 200,
        headers: {
          'Content-Type': 'image/svg+xml',
          'Cache-Control': 'no-cache'
        }
      }
    );
  }
}

// Handle static asset requests
async function handleStaticRequest(request, startTime) {
  try {
    const response = await cacheFirst(request, STATIC_CACHE_NAME);
    updatePerformanceMetrics('cache', startTime);
    return response;
  } catch (error) {
    updatePerformanceMetrics('offline', startTime);
    console.log('Service Worker: Static asset request failed:', request.url);
    throw error;
  }
}

// Handle navigation requests (SPA routing)
async function handleNavigationRequest(request, startTime) {
  try {
    const response = await networkFirst(request, STATIC_CACHE_NAME);
    updatePerformanceMetrics('network', startTime);
    return response;
  } catch (error) {
    updatePerformanceMetrics('offline', startTime);
    console.log('Service Worker: Navigation request failed, serving cached index:', request.url);
    
    const cachedResponse = await caches.match('/');
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Enhanced offline page
    return getOfflinePage();
  }
}

// Handle default requests
async function handleDefaultRequest(request, startTime) {
  try {
    const response = await staleWhileRevalidate(request, DYNAMIC_CACHE_NAME);
    updatePerformanceMetrics('cache', startTime);
    return response;
  } catch (error) {
    updatePerformanceMetrics('offline', startTime);
    const cachedResponse = await caches.match(request);
    return cachedResponse || getOfflineResponse(request.url);
  }
}

// Cache strategy implementations
async function cacheFirst(request, cacheName) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    // Update cache in background
    fetch(request).then(response => {
      if (response.ok) {
        caches.open(cacheName).then(cache => cache.put(request, response));
      }
    }).catch(() => {}); // Ignore network errors
    return cachedResponse;
  }
  
  const networkResponse = await fetch(request);
  if (networkResponse.ok) {
    const cache = await caches.open(cacheName);
    cache.put(request, networkResponse.clone());
  }
  return networkResponse;
}

async function networkFirst(request, cacheName) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(cacheName);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    throw error;
  }
}

async function staleWhileRevalidate(request, cacheName) {
  const cachedResponse = await caches.match(request);
  const networkPromise = fetch(request).then(response => {
    if (response.ok) {
      return caches.open(cacheName).then(cache => {
        cache.put(request, response.clone());
        return response;
      });
    }
    return response;
  }).catch(() => cachedResponse);
  
  return cachedResponse || networkPromise;
}

// Determine cache strategy based on URL
function getCacheStrategy(pathname) {
  if (pathname.includes('/classify') || pathname.includes('/upload')) {
    return CACHE_STRATEGIES.NETWORK_FIRST;
  }
  if (pathname.includes('/food-classes') || pathname.includes('/projects')) {
    return CACHE_STRATEGIES.STALE_WHILE_REVALIDATE;
  }
  if (pathname.includes('/community/forums') || pathname.includes('/community/threads')) {
    return CACHE_STRATEGIES.CACHE_FIRST;
  }
  return CACHE_STRATEGIES.NETWORK_FIRST;
}

// Enhanced offline responses
function getOfflineResponse(pathname) {
  if (pathname.includes('/classify')) {
    return new Response(JSON.stringify({
      error: 'Classification service is unavailable offline',
      offline: true,
      cached: false,
      suggestions: ['Please check your internet connection and try again']
    }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  if (pathname.includes('/food-classes')) {
    return new Response(JSON.stringify({
      data: ['apple', 'banana', 'orange', 'grape', 'strawberry'],
      offline: true,
      cached: true,
      message: 'Showing cached food classes'
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  }
  
  return new Response(JSON.stringify({
    error: 'You are currently offline. Please check your internet connection.',
    offline: true
  }), {
    status: 503,
    headers: { 'Content-Type': 'application/json' }
  });
}

// Enhanced offline page
function getOfflinePage() {
  return new Response(`
    <!DOCTYPE html>
    <html>
      <head>
        <title>FlavorSnap - Offline</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                  margin: 0; padding: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                  color: white; min-height: 100vh; display: flex; align-items: center; }
          .container { max-width: 500px; margin: 0 auto; padding: 40px 20px; text-align: center; }
          .icon { width: 80px; height: 80px; margin: 0 auto 30px; display: block; animation: pulse 2s infinite; }
          h1 { font-size: 2.5em; margin-bottom: 20px; font-weight: 700; }
          p { font-size: 1.1em; margin-bottom: 30px; line-height: 1.6; opacity: 0.9; }
          .button { display: inline-block; padding: 15px 30px; 
                   background: rgba(255, 255, 255, 0.2); color: white; border: 2px solid rgba(255, 255, 255, 0.3); 
                   border-radius: 50px; text-decoration: none; font-weight: 600; 
                   backdrop-filter: blur(10px); transition: all 0.3s ease; }
          .button:hover { background: rgba(255, 255, 255, 0.3); transform: translateY(-2px); }
          .features { margin-top: 40px; display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
          .feature { padding: 20px; background: rgba(255, 255, 255, 0.1); border-radius: 15px; }
          @keyframes pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.05); } }
        </style>
      </head>
      <body>
        <div class="container">
          <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"/>
          </svg>
          <h1>You're Offline</h1>
          <p>FlavorSnap is currently unavailable because you're offline. Your actions will be synced when you reconnect.</p>
          <button class="button" onclick="window.location.reload()">Try Again</button>
          
          <div class="features">
            <div class="feature">
              <h3>📸 Offline Capture</h3>
              <p>Photos are saved locally</p>
            </div>
            <div class="feature">
              <h3>🔄 Auto Sync</h3>
              <p>Syncs when online</p>
            </div>
            <div class="feature">
              <h3>💾 Local Cache</h3>
              <p>Recent data available</p>
            </div>
            <div class="feature">
              <h3>⚡ Fast Loading</h3>
              <p>Optimized performance</p>
            </div>
          </div>
        </div>
      </body>
    </html>
  `, {
    status: 200,
    headers: { 'Content-Type': 'text/html' }
  });
}

// Performance monitoring
function updatePerformanceMetrics(type, startTime) {
  const responseTime = performance.now() - startTime;
  performanceMetrics.requestCount++;
  performanceMetrics.totalResponseTime += responseTime;
  performanceMetrics.averageResponseTime = performanceMetrics.totalResponseTime / performanceMetrics.requestCount;
  
  switch (type) {
    case 'cache':
      performanceMetrics.cacheHits++;
      break;
    case 'network':
      performanceMetrics.networkRequests++;
      break;
    case 'offline':
      performanceMetrics.offlineRequests++;
      break;
  }
  
  // Store analytics periodically
  if (performanceMetrics.requestCount % 10 === 0) {
    storeOfflineAnalytics();
  }
}

// Background sync queue management
async function queueBackgroundSync(request) {
  backgroundSyncQueue.push(request);
  await storeBackgroundSyncQueue();
  
  // Register for background sync if available
  if ('serviceWorker' in navigator && 'sync' in window.ServiceWorker.prototype) {
    try {
      await self.registration.sync.register('background-sync-queue');
    } catch (error) {
      console.log('Background sync registration failed:', error);
    }
  }
}

// Storage utilities
async function storeBackgroundSyncQueue() {
  try {
    const cache = await caches.open(ANALYTICS_CACHE_NAME);
    await cache.put('background-sync-queue', new Response(JSON.stringify(backgroundSyncQueue)));
  } catch (error) {
    console.error('Error storing background sync queue:', error);
  }
}

async function getStoredBackgroundSyncQueue() {
  try {
    const cache = await caches.open(ANALYTICS_CACHE_NAME);
    const response = await cache.match('background-sync-queue');
    if (response) {
      return await response.json();
    }
  } catch (error) {
    console.error('Error retrieving background sync queue:', error);
  }
  return null;
}

async function storeOfflineAnalytics() {
  try {
    const analyticsData = {
      metrics: performanceMetrics,
      timestamp: Date.now(),
      offlineActions: offlineAnalytics
    };
    
    const cache = await caches.open(ANALYTICS_CACHE_NAME);
    await cache.put('offline-analytics', new Response(JSON.stringify(analyticsData)));
  } catch (error) {
    console.error('Error storing offline analytics:', error);
  }
}

async function getStoredOfflineAnalytics() {
  try {
    const cache = await caches.open(ANALYTICS_CACHE_NAME);
    const response = await cache.match('offline-analytics');
    if (response) {
      return await response.json();
    }
  } catch (error) {
    console.error('Error retrieving offline analytics:', error);
  }
  return null;
}

// Enhanced push notification handling
self.addEventListener('push', (event) => {
  console.log('Service Worker: Push received');
  
  let pushData;
  try {
    pushData = event.data.json();
  } catch (error) {
    pushData = {
      title: 'FlavorSnap',
      body: event.data ? event.data.text() : 'New notification available',
      icon: '/icons/icon-192x192.png'
    };
  }
  
  const options = {
    body: pushData.body || 'New update available',
    icon: pushData.icon || '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      ...pushData.data,
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View Details',
        icon: '/icons/icon-96x96.png'
      },
      {
        action: 'dismiss',
        title: 'Dismiss',
        icon: '/icons/icon-96x96.png'
      }
    ],
    requireInteraction: pushData.important || false,
    silent: pushData.silent || false,
    tag: pushData.tag || 'default'
  };
  
  event.waitUntil(
    self.registration.showNotification(pushData.title || 'FlavorSnap', options)
      .then(() => {
        // Log notification for analytics
        offlineAnalytics.push({
          type: 'push_received',
          title: pushData.title,
          timestamp: Date.now()
        });
        storeOfflineAnalytics();
      })
  );
});

// Enhanced notification click handling
self.addEventListener('notificationclick', (event) => {
  console.log('Service Worker: Notification click received');
  
  event.notification.close();
  
  const notificationData = event.notification.data || {};
  
  // Log notification interaction for analytics
  offlineAnalytics.push({
    type: 'notification_clicked',
    action: event.action,
    data: notificationData,
    timestamp: Date.now()
  });
  storeOfflineAnalytics();
  
  if (event.action === 'explore' || event.action === 'view') {
    event.waitUntil(
      clients.matchAll({ type: 'window' })
        .then(clientList => {
          // Focus existing window if available
          for (const client of clientList) {
            if (client.url === self.location.origin && 'focus' in client) {
              return client.focus();
            }
          }
          // Open new window
          if (clients.openWindow) {
            return clients.openWindow(notificationData.url || '/');
          }
        })
    );
  } else if (event.action === 'dismiss') {
    // Just close the notification
  } else {
    // Default action - open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Advanced background sync
self.addEventListener('sync', (event) => {
  console.log('Service Worker: Background sync triggered', event.tag);
  
  if (event.tag === 'background-sync-queue') {
    event.waitUntil(processBackgroundSyncQueue());
  } else if (event.tag === 'background-sync-analytics') {
    event.waitUntil(syncOfflineAnalytics());
  } else if (event.tag === 'background-sync-classification') {
    event.waitUntil(syncClassificationRequests());
  }
});

async function processBackgroundSyncQueue() {
  if (backgroundSyncQueue.length === 0) {
    console.log('No items in background sync queue');
    return;
  }
  
  console.log(`Processing ${backgroundSyncQueue.length} background sync items`);
  
  for (const item of backgroundSyncQueue) {
    try {
      const response = await fetch(item.url, {
        method: item.method,
        headers: item.headers,
        body: item.body
      });
      
      if (response.ok) {
        console.log('Background sync successful for:', item.url);
        // Remove from queue
        backgroundSyncQueue = backgroundSyncQueue.filter(i => i !== item);
        
        // Notify client of successful sync
        notifyClient('sync-success', { url: item.url, timestamp: Date.now() });
      } else {
        console.error('Background sync failed for:', item.url, response.status);
      }
    } catch (error) {
      console.error('Background sync error for:', item.url, error);
    }
  }
  
  await storeBackgroundSyncQueue();
}

async function syncOfflineAnalytics() {
  if (offlineAnalytics.length === 0) {
    return;
  }
  
  try {
    const response = await fetch('/api/analytics/offline', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        analytics: offlineAnalytics,
        metrics: performanceMetrics
      })
    });
    
    if (response.ok) {
      console.log('Offline analytics synced successfully');
      offlineAnalytics = [];
      await storeOfflineAnalytics();
    }
  } catch (error) {
    console.error('Failed to sync offline analytics:', error);
  }
}

async function syncClassificationRequests() {
  // Handle offline classification requests
  const classificationQueue = backgroundSyncQueue.filter(item => 
    item.url.includes('/classify') || item.url.includes('/upload')
  );
  
  for (const request of classificationQueue) {
    try {
      const response = await fetch(request.url, {
        method: request.method,
        headers: request.headers,
        body: request.body
      });
      
      if (response.ok) {
        const result = await response.json();
        
        // Notify client of classification result
        notifyClient('classification-complete', {
          requestId: request.timestamp,
          result: result
        });
        
        // Remove from queue
        backgroundSyncQueue = backgroundSyncQueue.filter(item => item !== request);
      }
    } catch (error) {
      console.error('Failed to sync classification request:', error);
    }
  }
  
  await storeBackgroundSyncQueue();
}

// Client communication
function notifyClient(type, data) {
  self.clients.matchAll().then(clients => {
    clients.forEach(client => {
      client.postMessage({
        type: type,
        data: data,
        timestamp: Date.now()
      });
    });
  });
}

// Handle client messages
self.addEventListener('message', (event) => {
  const { type, data } = event.data;
  
  switch (type) {
    case 'GET_PERFORMANCE_METRICS':
      event.ports[0].postMessage({
        type: 'PERFORMANCE_METRICS',
        data: performanceMetrics
      });
      break;
      
    case 'CLEAR_CACHE':
      clearAllCaches().then(() => {
        event.ports[0].postMessage({
          type: 'CACHE_CLEARED'
        });
      });
      break;
      
    case 'FORCE_SYNC':
      processBackgroundSyncQueue().then(() => {
        event.ports[0].postMessage({
          type: 'SYNC_COMPLETED'
        });
      });
      break;
      
    case 'UPDATE_CACHE_STRATEGY':
      // Update cache strategies based on client preferences
      console.log('Cache strategy update requested:', data);
      break;
      
    default:
      console.log('Unknown message type:', type);
  }
});

// Cache management utilities
async function clearAllCaches() {
  try {
    const cacheNames = await caches.keys();
    await Promise.all(
      cacheNames.map(cacheName => caches.delete(cacheName))
    );
    
    // Reset performance metrics
    performanceMetrics = {
      cacheHits: 0,
      cacheMisses: 0,
      networkRequests: 0,
      offlineRequests: 0,
      averageResponseTime: 0,
      totalResponseTime: 0,
      requestCount: 0
    };
    
    console.log('All caches cleared');
  } catch (error) {
    console.error('Error clearing caches:', error);
  }
}

// Periodic cleanup
async function performPeriodicCleanup() {
  try {
    // Clean up old analytics data
    const cache = await caches.open(ANALYTICS_CACHE_NAME);
    const analyticsResponse = await cache.match('offline-analytics');
    
    if (analyticsResponse) {
      const analytics = await analyticsResponse.json();
      const oneWeekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
      
      // Keep only recent analytics
      analytics.offlineActions = analytics.offlineActions.filter(
        action => action.timestamp > oneWeekAgo
      );
      
      await cache.put('offline-analytics', new Response(JSON.stringify(analytics)));
    }
    
    // Clean up old image cache entries (keep last 50)
    const imageCache = await caches.open(IMAGE_CACHE_NAME);
    const imageRequests = await imageCache.keys();
    
    if (imageRequests.length > 50) {
      const oldRequests = imageRequests.slice(0, imageRequests.length - 50);
      await Promise.all(oldRequests.map(request => imageCache.delete(request)));
    }
    
    console.log('Periodic cleanup completed');
  } catch (error) {
    console.error('Error during periodic cleanup:', error);
  }
}

// Register periodic sync if available
if ('periodicSync' in self.registration) {
  self.addEventListener('periodicsync', (event) => {
    if (event.tag === 'periodic-cleanup') {
      event.waitUntil(performPeriodicCleanup());
    }
  });
}

// Network status monitoring
self.addEventListener('online', () => {
  console.log('Service Worker: Client is online');
  notifyClient('online', { timestamp: Date.now() });
  
  // Trigger background sync when coming online
  if (backgroundSyncQueue.length > 0) {
    processBackgroundSyncQueue();
  }
});

self.addEventListener('offline', () => {
  console.log('Service Worker: Client is offline');
  notifyClient('offline', { timestamp: Date.now() });
});

// Performance monitoring
self.addEventListener('online', () => {
  // Sync performance metrics when coming online
  if (performanceMetrics.requestCount > 0) {
    syncOfflineAnalytics();
  }
});

// Handle navigation requests (SPA routing)
async function handleNavigationRequest(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch (error) {
    console.log('Service Worker: Navigation request failed, serving cached index:', request.url);
    const cachedResponse = await caches.match('/');
    if (cachedResponse) {
      return cachedResponse;
    }
    
    // Fallback offline page
    return new Response(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>FlavorSnap - Offline</title>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; 
                    margin: 0; padding: 0; background: #f3f4f6; color: #1f2937; }
            .container { max-width: 400px; margin: 100px auto; padding: 20px; 
                       background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
            .icon { width: 64px; height: 64px; margin: 0 auto 20px; display: block; }
            h1 { text-align: center; margin-bottom: 10px; color: #ffa500; }
            p { text-align: center; margin-bottom: 20px; line-height: 1.5; }
            .button { display: block; width: 100%; padding: 12px; 
                     background: #ffa500; color: white; border: none; border-radius: 6px; 
                     text-align: center; text-decoration: none; font-weight: 500; }
            .button:hover { background: #e59400; }
          </style>
        </head>
        <body>
          <div class="container">
            <svg class="icon" viewBox="0 0 24 24" fill="none" stroke="#ffa500" stroke-width="2">
              <path d="M18.364 5.636l-3.536 3.536m0 5.656l3.536 3.536M9.172 9.172L5.636 5.636m3.536 9.192l-3.536 3.536M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-5 0a4 4 0 11-8 0 4 4 0 018 0z"/>
            </svg>
            <h1>You're Offline</h1>
            <p>FlavorSnap is currently unavailable because you're offline. Please check your internet connection and try again.</p>
            <button class="button" onclick="window.location.reload()">Try Again</button>
          </div>
        </body>
      </html>
    `, {
      status: 200,
      statusText: 'OK',
      headers: {
        'Content-Type': 'text/html'
      }
    });
  }
}

// Push notification event
self.addEventListener('push', (event) => {
  console.log('Service Worker: Push received');
  
  const options = {
    body: event.data ? event.data.text() : 'New classification result available',
    icon: '/icons/icon-192x192.png',
    badge: '/icons/icon-72x72.png',
    vibrate: [100, 50, 100],
    data: {
      dateOfArrival: Date.now(),
      primaryKey: 1
    },
    actions: [
      {
        action: 'explore',
        title: 'View Result',
        icon: '/icons/icon-96x96.png'
      },
      {
        action: 'close',
        title: 'Close',
        icon: '/icons/icon-96x96.png'
      }
    ]
  };
  
  event.waitUntil(
    self.registration.showNotification('FlavorSnap', options)
  );
});

// Notification click event
self.addEventListener('notificationclick', (event) => {
  console.log('Service Worker: Notification click received');
  
  event.notification.close();
  
  if (event.action === 'explore') {
    event.waitUntil(
      clients.openWindow('/')
    );
  } else if (event.action === 'close') {
    // Just close the notification
  } else {
    // Default action - open the app
    event.waitUntil(
      clients.openWindow('/')
    );
  }
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('Service Worker: Background sync triggered');
  
  if (event.tag === 'background-sync-classification') {
    event.waitUntil(doBackgroundSync());
  }
});

async function doBackgroundSync() {
  // Handle offline classification requests that were queued
  try {
    // This would sync any queued classification requests
    console.log('Service Worker: Performing background sync');
  } catch (error) {
    console.error('Service Worker: Background sync failed:', error);
  }
}
