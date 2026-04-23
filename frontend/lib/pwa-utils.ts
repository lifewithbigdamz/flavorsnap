export interface BeforeInstallPromptEvent extends Event {
  readonly platforms: string[];
  readonly userChoice: Promise<{
    outcome: 'accepted' | 'dismissed';
    platform: string;
  }>;
  prompt(): Promise<void>;
}

export interface PushSubscriptionOptions {
  userVisibleOnly: boolean;
  applicationServerKey?: ArrayBuffer | string;
}

export interface PerformanceMetrics {
  cacheHits: number;
  cacheMisses: number;
  networkRequests: number;
  offlineRequests: number;
  averageResponseTime: number;
  totalResponseTime: number;
  requestCount: number;
}

export interface OfflineAnalytics {
  type: string;
  timestamp: number;
  data?: any;
}

export interface CacheStrategy {
  name: string;
  pattern: RegExp;
  strategy: 'cache-first' | 'network-first' | 'stale-while-revalidate';
  maxAge: number;
  maxEntries: number;
}

export class PWAManager {
  private static instance: PWAManager;
  private deferredPrompt: BeforeInstallPromptEvent | null = null;
  private swRegistration: ServiceWorkerRegistration | null = null;
  private isInstalled: boolean = false;
  private isOnline: boolean = navigator.onLine;
  private performanceMetrics: PerformanceMetrics = {
    cacheHits: 0,
    cacheMisses: 0,
    networkRequests: 0,
    offlineRequests: 0,
    averageResponseTime: 0,
    totalResponseTime: 0,
    requestCount: 0
  };
  private offlineAnalytics: OfflineAnalytics[] = [];
  private cacheStrategies: CacheStrategy[] = [];
  private messageChannel: MessageChannel | null = null;

  static getInstance(): PWAManager {
    if (!PWAManager.instance) {
      PWAManager.instance = new PWAManager();
    }
    return PWAManager.instance;
  }

  private constructor() {
    this.initializeServiceWorker();
    this.setupInstallPrompt();
    this.setupNetworkListeners();
    this.setupMessageChannel();
    this.initializeCacheStrategies();
  }

  private async initializeServiceWorker() {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      try {
        const registration = await navigator.serviceWorker.register('/sw.js', {
          scope: '/'
        });
        
        this.swRegistration = registration;
        console.log('Service Worker registered successfully:', registration);
        
        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // New version available
                this.notifyUpdateAvailable();
              }
            });
          }
        });

        // Handle controller change (new service worker activated)
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          console.log('Service Worker controller changed, reloading page');
          window.location.reload();
        });

      } catch (error) {
        console.error('Service Worker registration failed:', error);
      }
    }
  }

  private setupInstallPrompt() {
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        this.deferredPrompt = e as BeforeInstallPromptEvent;
        console.log('Install prompt ready');
      });

      window.addEventListener('appinstalled', () => {
        this.isInstalled = true;
        this.deferredPrompt = null;
        console.log('PWA installed successfully');
        this.trackInstallation();
      });
    }
  }

  // Check if app is running in standalone mode
  isStandalone(): boolean {
    if (typeof window === 'undefined') return false;
    
    return (
      window.matchMedia('(display-mode: standalone)').matches ||
      (window.navigator as any).standalone ||
      document.referrer.includes('android-app://')
    );
  }

  // Check if install prompt is available
  canInstall(): boolean {
    return this.deferredPrompt !== null && !this.isInstalled;
  }

  // Show install prompt
  async showInstallPrompt(): Promise<boolean> {
    if (!this.deferredPrompt) {
      console.log('Install prompt not available');
      return false;
    }

    try {
      await this.deferredPrompt.prompt();
      const { outcome } = await this.deferredPrompt.userChoice;
      
      console.log(`Install prompt ${outcome}`);
      this.deferredPrompt = null;
      
      return outcome === 'accepted';
    } catch (error) {
      console.error('Error showing install prompt:', error);
      return false;
    }
  }

  // Request notification permission
  async requestNotificationPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
      console.log('This browser does not support notifications');
      return 'denied';
    }

    if (Notification.permission === 'granted') {
      return 'granted';
    }

    if (Notification.permission === 'denied') {
      return 'denied';
    }

    try {
      const permission = await Notification.requestPermission();
      console.log('Notification permission:', permission);
      return permission;
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      return 'denied';
    }
  }

  // Subscribe to push notifications
  async subscribeToPushNotifications(
    publicVapidKey?: string
  ): Promise<PushSubscription | null> {
    if (!this.swRegistration) {
      console.log('Service Worker not registered');
      return null;
    }

    const permission = await this.requestNotificationPermission();
    if (permission !== 'granted') {
      console.log('Notification permission not granted');
      return null;
    }

    try {
      const subscription = await this.swRegistration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: publicVapidKey ? this.urlBase64ToUint8Array(publicVapidKey) as unknown as BufferSource : undefined
      });

      console.log('Push subscription successful:', subscription);
      return subscription;
    } catch (error) {
      console.error('Push subscription failed:', error);
      return null;
    }
  }

  // Unsubscribe from push notifications
  async unsubscribeFromPushNotifications(): Promise<boolean> {
    if (!this.swRegistration) {
      return false;
    }

    try {
      const subscription = await this.swRegistration.pushManager.getSubscription();
      if (subscription) {
        await subscription.unsubscribe();
        console.log('Unsubscribed from push notifications');
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error unsubscribing from push notifications:', error);
      return false;
    }
  }

  // Show local notification
  async showLocalNotification(
    title: string,
    options: NotificationOptions = {}
  ): Promise<void> {
    const permission = await this.requestNotificationPermission();
    if (permission !== 'granted') {
      console.log('Notification permission not granted');
      return;
    }

    if (this.swRegistration) {
      await this.swRegistration.showNotification(title, {
        icon: '/icons/icon-192x192.png',
        badge: '/icons/icon-72x72.png',
        ...options
      });
    } else {
      new Notification(title, {
        icon: '/icons/icon-192x192.png',
        badge: '/icons/icon-72x72.png',
        ...options
      });
    }
  }

  // Check for updates
  async checkForUpdates(): Promise<boolean> {
    if (!this.swRegistration) {
      return false;
    }

    try {
      await this.swRegistration.update();
      return true;
    } catch (error) {
      console.error('Error checking for updates:', error);
      return false;
    }
  }

  // Get current push subscription
  async getPushSubscription(): Promise<PushSubscription | null> {
    if (!this.swRegistration) {
      return null;
    }

    try {
      return await this.swRegistration.pushManager.getSubscription();
    } catch (error) {
      console.error('Error getting push subscription:', error);
      return null;
    }
  }

  // Register background sync
  async registerBackgroundSync(tag: string): Promise<boolean> {
    if (!this.swRegistration || !('sync' in this.swRegistration)) {
      console.log('Background sync not supported');
      return false;
    }

    try {
      await (this.swRegistration.sync as any).register(tag);
      console.log(`Background sync registered: ${tag}`);
      return true;
    } catch (error: unknown) {
      console.error('Error registering background sync:', error);
      return false;
    }
  }

  // Utility method to convert VAPID key
  private urlBase64ToUint8Array(base64String: string): Uint8Array {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  // Notify user about update availability
  private notifyUpdateAvailable() {
    if (typeof window !== 'undefined') {
      // You can show a custom UI here
      console.log('New version available!');
      
      // Show a simple notification
      this.showLocalNotification('Update Available', {
        body: 'A new version of FlavorSnap is available. Click to update.',
        requireInteraction: true
      });
    }
  }

  // Track installation for analytics
  private trackInstallation() {
    if (typeof window !== 'undefined' && (window as any).gtag) {
      (window as any).gtag('event', 'pwa_installed', {
        event_category: 'PWA',
        event_label: 'FlavorSnap Installed'
      });
    }
  }

  // Get PWA installation status
  getInstallationStatus(): {
    isInstalled: boolean;
    isStandalone: boolean;
    canInstall: boolean;
  } {
    return {
      isInstalled: this.isInstalled,
      isStandalone: this.isStandalone(),
      canInstall: this.canInstall()
    };
  }

  // Advanced PWA features
  private setupNetworkListeners(): void {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        this.isOnline = true;
        this.logOfflineAnalytics('network_status', { status: 'online' });
        console.log('PWA: Network connection restored');
      });

      window.addEventListener('offline', () => {
        this.isOnline = false;
        this.logOfflineAnalytics('network_status', { status: 'offline' });
        console.log('PWA: Network connection lost');
      });
    }
  }

  private setupMessageChannel(): void {
    if (typeof window !== 'undefined' && 'serviceWorker' in navigator) {
      this.messageChannel = new MessageChannel();
      
      this.messageChannel.port1.onmessage = (event) => {
        this.handleServiceWorkerMessage(event.data);
      };

      navigator.serviceWorker.addEventListener('message', (event) => {
        this.handleServiceWorkerMessage(event.data);
      });
    }
  }

  private handleServiceWorkerMessage(data: any): void {
    switch (data.type) {
      case 'SW_UPDATED':
        console.log('PWA: Service Worker updated');
        this.notifyUser('App Updated', 'A new version is available. Refresh to see changes.');
        break;
      case 'online':
        this.isOnline = true;
        console.log('PWA: Back online');
        break;
      case 'offline':
        this.isOnline = false;
        console.log('PWA: Gone offline');
        break;
      case 'sync-success':
        console.log('PWA: Background sync successful', data.data);
        break;
      case 'classification-complete':
        console.log('PWA: Classification completed', data.data);
        break;
      default:
        console.log('PWA: Unknown message from service worker', data);
    }
  }

  private initializeCacheStrategies(): void {
    this.cacheStrategies = [
      {
        name: 'static-assets',
        pattern: /\.(css|js|png|jpg|jpeg|gif|webp|svg|woff|woff2)$/i,
        strategy: 'cache-first',
        maxAge: 30 * 24 * 60 * 60 * 1000, // 30 days
        maxEntries: 100
      },
      {
        name: 'api-calls',
        pattern: /\/api\//i,
        strategy: 'network-first',
        maxAge: 5 * 60 * 1000, // 5 minutes
        maxEntries: 50
      },
      {
        name: 'images',
        pattern: /\.(jpg|jpeg|png|gif|webp)$/i,
        strategy: 'stale-while-revalidate',
        maxAge: 7 * 24 * 60 * 60 * 1000, // 7 days
        maxEntries: 200
      }
    ];
  }

  // Performance monitoring
  getPerformanceMetrics(): PerformanceMetrics {
    return { ...this.performanceMetrics };
  }

  async getPerformanceMetricsFromSW(): Promise<PerformanceMetrics | null> {
    if (!this.swRegistration) return null;

    try {
      const messageChannel = new MessageChannel();
      
      return new Promise((resolve) => {
        messageChannel.port1.onmessage = (event) => {
          if (event.data.type === 'PERFORMANCE_METRICS') {
            resolve(event.data.data);
          } else {
            resolve(null);
          }
        };

        navigator.serviceWorker.controller?.postMessage(
          { type: 'GET_PERFORMANCE_METRICS' },
          [messageChannel.port2]
        );
      });
    } catch (error) {
      console.error('Error getting performance metrics from SW:', error);
      return null;
    }
  }

  // Cache management
  async clearCache(): Promise<boolean> {
    if (!this.swRegistration) return false;

    try {
      const messageChannel = new MessageChannel();
      
      return new Promise((resolve) => {
        messageChannel.port1.onmessage = (event) => {
          resolve(event.data.type === 'CACHE_CLEARED');
        };

        navigator.serviceWorker.controller?.postMessage(
          { type: 'CLEAR_CACHE' },
          [messageChannel.port2]
        );
      });
    } catch (error) {
      console.error('Error clearing cache:', error);
      return false;
    }
  }

  // Background sync
  async forceBackgroundSync(): Promise<boolean> {
    if (!this.swRegistration) return false;

    try {
      const messageChannel = new MessageChannel();
      
      return new Promise((resolve) => {
        messageChannel.port1.onmessage = (event) => {
          resolve(event.data.type === 'SYNC_COMPLETED');
        };

        navigator.serviceWorker.controller?.postMessage(
          { type: 'FORCE_SYNC' },
          [messageChannel.port2]
        );
      });
    } catch (error) {
      console.error('Error forcing background sync:', error);
      return false;
    }
  }

  // Offline analytics
  private logOfflineAnalytics(type: string, data?: any): void {
    this.offlineAnalytics.push({
      type,
      timestamp: Date.now(),
      data
    });

    // Keep only last 1000 entries
    if (this.offlineAnalytics.length > 1000) {
      this.offlineAnalytics = this.offlineAnalytics.slice(-1000);
    }
  }

  getOfflineAnalytics(): OfflineAnalytics[] {
    return [...this.offlineAnalytics];
  }

  // Advanced notification features
  async scheduleNotification(
    title: string,
    options: NotificationOptions & { scheduledTime?: number } = {}
  ): Promise<void> {
    const { scheduledTime, ...notificationOptions } = options;

    if (scheduledTime && scheduledTime > Date.now()) {
      const delay = scheduledTime - Date.now();
      setTimeout(() => {
        this.showLocalNotification(title, notificationOptions);
      }, delay);
    } else {
      await this.showLocalNotification(title, notificationOptions);
    }
  }

  // Cross-browser compatibility
  detectBrowserCapabilities(): {
    serviceWorker: boolean;
    pushNotifications: boolean;
    backgroundSync: boolean;
    periodicSync: boolean;
    notifications: boolean;
    installPrompt: boolean;
    standaloneMode: boolean;
  } {
    return {
      serviceWorker: 'serviceWorker' in navigator,
      pushNotifications: 'PushManager' in window && 'Notification' in window,
      backgroundSync: 'serviceWorker' in navigator && 'sync' in ServiceWorkerRegistration.prototype,
      periodicSync: 'serviceWorker' in navigator && 'periodicSync' in ServiceWorkerRegistration.prototype,
      notifications: 'Notification' in window,
      installPrompt: 'beforeinstallprompt' in window,
      standaloneMode: this.isStandalone()
    };
  }

  // Network status
  getNetworkStatus(): {
    isOnline: boolean;
    connectionType?: string;
    effectiveType?: string;
    downlink?: number;
    rtt?: number;
  } {
    const connection = (navigator as any).connection || (navigator as any).mozConnection || (navigator as any).webkitConnection;
    
    return {
      isOnline: this.isOnline,
      connectionType: connection?.type,
      effectiveType: connection?.effectiveType,
      downlink: connection?.downlink,
      rtt: connection?.rtt
    };
  }

  // Storage management
  async getStorageUsage(): Promise<{
    quota: number;
    usage: number;
    usageDetails: any;
  }> {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      try {
        const estimate = await navigator.storage.estimate();
        return {
          quota: estimate.quota || 0,
          usage: estimate.usage || 0,
          usageDetails: (estimate as any).usageDetails || {}
        };
      } catch (error) {
        console.error('Error getting storage usage:', error);
      }
    }
    
    return { quota: 0, usage: 0, usageDetails: {} };
  }

  async requestPersistentStorage(): Promise<boolean> {
    if ('storage' in navigator && 'persist' in navigator.storage) {
      try {
        const isPersistent = await navigator.storage.persist();
        console.log('Persistent storage granted:', isPersistent);
        return isPersistent;
      } catch (error) {
        console.error('Error requesting persistent storage:', error);
      }
    }
    return false;
  }

  // User engagement tracking
  trackUserEngagement(action: string, data?: any): void {
    this.logOfflineAnalytics('user_engagement', { action, data });
  }

  // App lifecycle
  getAppVisibilityState(): 'visible' | 'hidden' {
    if (typeof document !== 'undefined') {
      return document.visibilityState as 'visible' | 'hidden';
    }
    return 'visible';
  }

  setupVisibilityChangeListener(callback: (isVisible: boolean) => void): () => void {
    if (typeof document !== 'undefined') {
      const handleVisibilityChange = () => {
        callback(document.visibilityState === 'visible');
      };

      document.addEventListener('visibilitychange', handleVisibilityChange);

      // Return cleanup function
      return () => {
        document.removeEventListener('visibilitychange', handleVisibilityChange);
      };
    }
    return () => {};
  }

  // Advanced install features
  async checkInstallEligibility(): Promise<{
    eligible: boolean;
    reasons: string[];
    recommendations: string[];
  }> {
    const capabilities = this.detectBrowserCapabilities();
    const reasons: string[] = [];
    const recommendations: string[] = [];

    if (!capabilities.serviceWorker) {
      reasons.push('Service Worker not supported');
      recommendations.push('Use a modern browser that supports Service Workers');
    }

    if (!capabilities.installPrompt) {
      reasons.push('Install prompt not supported');
      recommendations.push('Try installing from the browser menu');
    }

    if (this.isInstalled) {
      reasons.push('Already installed');
      recommendations.push('App is already installed');
    }

    const eligible = reasons.length === 0 && this.canInstall();

    return {
      eligible,
      reasons,
      recommendations
    };
  }

  // Custom notifications
  private notifyUser(title: string, message: string): void {
    // You can implement a custom notification UI here
    console.log('PWA Notification:', title, message);
    
    // Also show as system notification if permitted
    this.showLocalNotification(title, { body: message });
  }
}

export const pwaManager = PWAManager.getInstance();
