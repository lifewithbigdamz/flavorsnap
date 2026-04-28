import { User, Thread, Post, Forum } from '@/types/community';

export interface ModerationAction {
  id: string;
  type: 'delete' | 'edit' | 'lock' | 'pin' | 'ban' | 'warn' | 'approve';
  contentType: 'thread' | 'post' | 'user' | 'forum';
  contentId: string;
  moderatorId: string;
  moderatorName: string;
  reason: string;
  description: string;
  timestamp: string;
  auto: boolean;
  severity: 'low' | 'medium' | 'high' | 'critical';
}

export interface ModerationReport {
  id: string;
  reporterId: string;
  reporterName: string;
  contentType: 'thread' | 'post' | 'user';
  contentId: string;
  reason: string;
  description: string;
  category: 'spam' | 'harassment' | 'inappropriate' | 'off_topic' | 'duplicate' | 'other';
  status: 'pending' | 'reviewed' | 'resolved' | 'dismissed';
  createdAt: string;
  reviewedAt?: string;
  reviewedBy?: string;
  actionTaken?: ModerationAction;
}

export interface ContentFilter {
  id: string;
  name: string;
  type: 'keyword' | 'regex' | 'ml' | 'external';
  pattern: string;
  action: 'flag' | 'block' | 'warn' | 'queue';
  severity: number;
  enabled: boolean;
  category: string;
  description: string;
}

export interface ModerationQueue {
  id: string;
  contentType: 'thread' | 'post' | 'user_registration';
  contentId: string;
  content: any;
  status: 'pending' | 'approved' | 'rejected' | 'flagged';
  flags: ContentFlag[];
  reviewedBy?: string;
  reviewedAt?: string;
  autoApproved: boolean;
  priority: number;
  createdAt: string;
}

export interface ContentFlag {
  type: string;
  severity: number;
  reason: string;
  confidence: number;
  filterId?: string;
  timestamp: string;
}

export interface ModerationStats {
  totalReports: number;
  pendingReports: number;
  resolvedReports: number;
  autoModerated: number;
  manualActions: number;
  averageResponseTime: number;
  topReportCategories: Array<{
    category: string;
    count: number;
  }>;
  moderatorActivity: Array<{
    moderatorId: string;
    moderatorName: string;
    actions: number;
    avgResponseTime: number;
  }>;
}

export class ContentModerator {
  private filters: ContentFilter[] = [];
  private reports: ModerationReport[] = [];
  private actions: ModerationAction[] = [];
  private queue: ModerationQueue[] = [];
  private blockedUsers: Set<string> = new Set();
  private trustedUsers: Set<string> = new Set();
  private warningThreshold: number = 3;
  private autoBanThreshold: number = 5;

  constructor() {
    this.initializeFilters();
    this.loadModerationData();
  }

  private initializeFilters(): void {
    this.filters = [
      {
        id: 'profanity_filter',
        name: 'Profanity Detection',
        type: 'keyword',
        pattern: 'badword1|badword2|badword3',
        action: 'flag',
        severity: 3,
        enabled: true,
        category: 'inappropriate',
        description: 'Detects and flags profanity'
      },
      {
        id: 'spam_filter',
        name: 'Spam Detection',
        type: 'regex',
        pattern: '(buy now|click here|free money|limited offer)',
        action: 'queue',
        severity: 4,
        enabled: true,
        category: 'spam',
        description: 'Detects potential spam content'
      },
      {
        id: 'harassment_filter',
        name: 'Harassment Detection',
        type: 'ml',
        pattern: 'harassment_model',
        action: 'block',
        severity: 5,
        enabled: true,
        category: 'harassment',
        description: 'ML-based harassment detection'
      },
      {
        id: 'link_filter',
        name: 'Suspicious Links',
        type: 'regex',
        pattern: '(bit\\.ly|tinyurl|short\\.link)',
        action: 'queue',
        severity: 2,
        enabled: true,
        category: 'spam',
        description: 'Flags suspicious short links'
      }
    ];
  }

  private loadModerationData(): void {
    try {
      const storedFilters = localStorage.getItem('moderation_filters');
      const storedReports = localStorage.getItem('moderation_reports');
      const storedActions = localStorage.getItem('moderation_actions');
      const storedQueue = localStorage.getItem('moderation_queue');

      if (storedFilters) this.filters = JSON.parse(storedFilters);
      if (storedReports) this.reports = JSON.parse(storedReports);
      if (storedActions) this.actions = JSON.parse(storedActions);
      if (storedQueue) this.queue = JSON.parse(storedQueue);
    } catch (error) {
      console.error('Error loading moderation data:', error);
    }
  }

  private saveModerationData(): void {
    try {
      localStorage.setItem('moderation_filters', JSON.stringify(this.filters));
      localStorage.setItem('moderation_reports', JSON.stringify(this.reports));
      localStorage.setItem('moderation_actions', JSON.stringify(this.actions));
      localStorage.setItem('moderation_queue', JSON.stringify(this.queue));
    } catch (error) {
      console.error('Error saving moderation data:', error);
    }
  }

  // Content Analysis
  public analyzeContent(content: string, contentType: 'thread' | 'post', authorId: string): ContentFlag[] {
    const flags: ContentFlag[] = [];

    // Skip analysis for trusted users
    if (this.trustedUsers.has(authorId)) {
      return flags;
    }

    // Check if user is blocked
    if (this.blockedUsers.has(authorId)) {
      flags.push({
        type: 'blocked_user',
        severity: 10,
        reason: 'User is blocked from posting',
        confidence: 1.0,
        timestamp: new Date().toISOString()
      });
      return flags;
    }

    // Run content through filters
    for (const filter of this.filters.filter(f => f.enabled)) {
      const flag = this.runFilter(filter, content);
      if (flag) {
        flags.push(flag);
      }
    }

    // Check for duplicate content
    if (this.isDuplicateContent(content)) {
      flags.push({
        type: 'duplicate',
        severity: 2,
        reason: 'Potential duplicate content',
        confidence: 0.7,
        timestamp: new Date().toISOString()
      });
    }

    // Check user reputation
    const userWarnings = this.getUserWarnings(authorId);
    if (userWarnings >= this.warningThreshold) {
      flags.push({
        type: 'high_risk_user',
        severity: 6,
        reason: `User has ${userWarnings} warnings`,
        confidence: 0.8,
        timestamp: new Date().toISOString()
      });
    }

    return flags;
  }

  private runFilter(filter: ContentFilter, content: string): ContentFlag | null {
    try {
      let matches = false;
      let confidence = 0.5;

      switch (filter.type) {
        case 'keyword':
          const keywords = filter.pattern.split('|');
          matches = keywords.some(keyword => 
            content.toLowerCase().includes(keyword.toLowerCase())
          );
          confidence = matches ? 0.9 : 0;
          break;

        case 'regex':
          const regex = new RegExp(filter.pattern, 'i');
          matches = regex.test(content);
          confidence = matches ? 0.8 : 0;
          break;

        case 'ml':
          // In a real implementation, this would call an ML service
          matches = this.simulateMLDetection(filter.pattern, content);
          confidence = matches ? 0.7 : 0;
          break;

        case 'external':
          // In a real implementation, this would call an external API
          matches = this.simulateExternalCheck(content);
          confidence = matches ? 0.6 : 0;
          break;
      }

      if (matches && confidence > 0.5) {
        return {
          type: filter.category,
          severity: filter.severity,
          reason: `Matched ${filter.name}: ${filter.description}`,
          confidence,
          filterId: filter.id,
          timestamp: new Date().toISOString()
        };
      }

      return null;
    } catch (error) {
      console.error('Error running filter:', error);
      return null;
    }
  }

  private simulateMLDetection(model: string, content: string): boolean {
    // Simulate ML detection (in real implementation, would call actual ML model)
    const suspiciousPatterns = ['hate', 'kill', 'harm', 'violence'];
    return suspiciousPatterns.some(pattern => 
      content.toLowerCase().includes(pattern)
    );
  }

  private simulateExternalCheck(content: string): boolean {
    // Simulate external API check (in real implementation, would call external service)
    return content.length > 1000; // Example: very long content might be spam
  }

  private isDuplicateContent(content: string): boolean {
    // In a real implementation, this would check against database
    const existingContent = localStorage.getItem('recent_posts') || '[]';
    const posts = JSON.parse(existingContent);
    
    return posts.some((post: string) => 
      this.calculateSimilarity(content, post) > 0.8
    );
  }

  private calculateSimilarity(str1: string, str2: string): number {
    // Simple similarity calculation (in real implementation, would use more sophisticated algorithm)
    const longer = str1.length > str2.length ? str1 : str2;
    const shorter = str1.length > str2.length ? str2 : str1;
    
    if (longer.length === 0) return 1.0;
    
    const editDistance = this.levenshteinDistance(longer, shorter);
    return (longer.length - editDistance) / longer.length;
  }

  private levenshteinDistance(str1: string, str2: string): number {
    const matrix = [];
    
    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i];
    }
    
    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j;
    }
    
    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }
    
    return matrix[str2.length][str1.length];
  }

  // Queue Management
  public addToQueue(content: any, contentType: 'thread' | 'post' | 'user_registration', authorId: string): void {
    const flags = this.analyzeContent(content.content || content.bio || '', contentType, authorId);
    
    const queueItem: ModerationQueue = {
      id: this.generateId('queue'),
      contentType,
      contentId: content.id || this.generateId('temp'),
      content,
      status: flags.length > 0 ? 'flagged' : 'pending',
      flags,
      autoApproved: flags.length === 0,
      priority: this.calculatePriority(flags, authorId),
      createdAt: new Date().toISOString()
    };

    this.queue.push(queueItem);
    this.saveModerationData();

    // Auto-approve if no flags and user is trusted
    if (flags.length === 0 && this.trustedUsers.has(authorId)) {
      this.approveQueueItem(queueItem.id, 'system');
    }
  }

  private calculatePriority(flags: ContentFlag[], authorId: string): number {
    if (flags.length === 0) return 1;

    const maxSeverity = Math.max(...flags.map(f => f.severity));
    const userWarnings = this.getUserWarnings(authorId);
    
    return maxSeverity + userWarnings;
  }

  private getUserWarnings(authorId: string): number {
    return this.actions.filter(action => 
      action.contentType === 'user' && 
      action.contentId === authorId && 
      action.type === 'warn'
    ).length;
  }

  // Report Management
  public createReport(report: Omit<ModerationReport, 'id' | 'status' | 'createdAt'>): ModerationReport {
    const newReport: ModerationReport = {
      ...report,
      id: this.generateId('report'),
      status: 'pending',
      createdAt: new Date().toISOString()
    };

    this.reports.push(newReport);
    this.saveModerationData();

    // Auto-review if high severity
    const contentFlags = this.analyzeContent('', report.contentType as 'thread' | 'post', report.contentId);
    if (contentFlags.some(f => f.severity >= 5)) {
      this.reviewReport(newReport.id, 'system', 'auto_high_severity');
    }

    return newReport;
  }

  public getReports(status?: string, category?: string): ModerationReport[] {
    let filtered = [...this.reports];

    if (status) {
      filtered = filtered.filter(r => r.status === status);
    }

    if (category) {
      filtered = filtered.filter(r => r.category === category);
    }

    return filtered.sort((a, b) => 
      new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
    );
  }

  public reviewReport(reportId: string, reviewerId: string, action: string): void {
    const report = this.reports.find(r => r.id === reportId);
    if (!report) return;

    report.status = 'reviewed';
    report.reviewedAt = new Date().toISOString();
    report.reviewedBy = reviewerId;

    // Create moderation action
    const moderationAction: ModerationAction = {
      id: this.generateId('action'),
      type: this.getActionType(action),
      contentType: report.contentType,
      contentId: report.contentId,
      moderatorId: reviewerId,
      moderatorName: 'Moderator', // Would fetch from user data
      reason: report.reason,
      description: `Reviewed report: ${report.description}`,
      timestamp: new Date().toISOString(),
      auto: reviewerId === 'system',
      severity: this.getActionSeverity(action)
    };

    this.actions.push(moderationAction);
    this.saveModerationData();
  }

  private getActionType(action: string): ModerationAction['type'] {
    switch (action) {
      case 'delete': return 'delete';
      case 'edit': return 'edit';
      case 'lock': return 'lock';
      case 'pin': return 'pin';
      case 'ban': return 'ban';
      case 'warn': return 'warn';
      case 'approve': return 'approve';
      default: return 'warn';
    }
  }

  private getActionSeverity(action: string): ModerationAction['severity'] {
    switch (action) {
      case 'delete': return 'medium';
      case 'lock': return 'medium';
      case 'ban': return 'critical';
      case 'warn': return 'low';
      case 'approve': return 'low';
      default: return 'medium';
    }
  }

  // Queue Management
  public getQueue(status?: string): ModerationQueue[] {
    let filtered = [...this.queue];

    if (status) {
      filtered = filtered.filter(q => q.status === status);
    }

    return filtered.sort((a, b) => b.priority - a.priority);
  }

  public approveQueueItem(queueId: string, reviewerId: string): void {
    const queueItem = this.queue.find(q => q.id === queueId);
    if (!queueItem) return;

    queueItem.status = 'approved';
    queueItem.reviewedBy = reviewerId;
    queueItem.reviewedAt = new Date().toISOString();

    this.saveModerationData();
  }

  public rejectQueueItem(queueId: string, reviewerId: string, reason: string): void {
    const queueItem = this.queue.find(q => q.id === queueId);
    if (!queueItem) return;

    queueItem.status = 'rejected';
    queueItem.reviewedBy = reviewerId;
    queueItem.reviewedAt = new Date().toISOString();

    // Create moderation action
    const action: ModerationAction = {
      id: this.generateId('action'),
      type: 'delete',
      contentType: queueItem.contentType,
      contentId: queueItem.contentId,
      moderatorId: reviewerId,
      moderatorName: 'Moderator',
      reason: 'Rejected from moderation queue',
      description: reason,
      timestamp: new Date().toISOString(),
      auto: false,
      severity: 'medium'
    };

    this.actions.push(action);
    this.saveModerationData();
  }

  // User Management
  public warnUser(userId: string, moderatorId: string, reason: string): void {
    const action: ModerationAction = {
      id: this.generateId('action'),
      type: 'warn',
      contentType: 'user',
      contentId: userId,
      moderatorId,
      moderatorName: 'Moderator',
      reason: 'User warning',
      description: reason,
      timestamp: new Date().toISOString(),
      auto: false,
      severity: 'low'
    };

    this.actions.push(action);

    // Check if user should be auto-banned
    const warnings = this.getUserWarnings(userId);
    if (warnings >= this.autoBanThreshold) {
      this.banUser(userId, moderatorId, 'Automatic ban due to excessive warnings');
    }

    this.saveModerationData();
  }

  public banUser(userId: string, moderatorId: string, reason: string): void {
    this.blockedUsers.add(userId);

    const action: ModerationAction = {
      id: this.generateId('action'),
      type: 'ban',
      contentType: 'user',
      contentId: userId,
      moderatorId,
      moderatorName: 'Moderator',
      reason: 'User banned',
      description: reason,
      timestamp: new Date().toISOString(),
      auto: false,
      severity: 'critical'
    };

    this.actions.push(action);
    this.saveModerationData();
  }

  public unbanUser(userId: string, moderatorId: string): void {
    this.blockedUsers.delete(userId);

    const action: ModerationAction = {
      id: this.generateId('action'),
      type: 'approve',
      contentType: 'user',
      contentId: userId,
      moderatorId,
      moderatorName: 'Moderator',
      reason: 'User unbanned',
      description: 'User has been unbanned',
      timestamp: new Date().toISOString(),
      auto: false,
      severity: 'low'
    };

    this.actions.push(action);
    this.saveModerationData();
  }

  public addTrustedUser(userId: string): void {
    this.trustedUsers.add(userId);
    localStorage.setItem('trusted_users', JSON.stringify([...this.trustedUsers]));
  }

  public removeTrustedUser(userId: string): void {
    this.trustedUsers.delete(userId);
    localStorage.setItem('trusted_users', JSON.stringify([...this.trustedUsers]));
  }

  // Filter Management
  public addFilter(filter: Omit<ContentFilter, 'id'>): ContentFilter {
    const newFilter: ContentFilter = {
      ...filter,
      id: this.generateId('filter')
    };

    this.filters.push(newFilter);
    this.saveModerationData();
    return newFilter;
  }

  public updateFilter(filterId: string, updates: Partial<ContentFilter>): boolean {
    const filterIndex = this.filters.findIndex(f => f.id === filterId);
    if (filterIndex === -1) return false;

    this.filters[filterIndex] = { ...this.filters[filterIndex], ...updates };
    this.saveModerationData();
    return true;
  }

  public deleteFilter(filterId: string): boolean {
    const initialLength = this.filters.length;
    this.filters = this.filters.filter(f => f.id !== filterId);
    
    if (this.filters.length < initialLength) {
      this.saveModerationData();
      return true;
    }
    return false;
  }

  public getFilters(): ContentFilter[] {
    return [...this.filters];
  }

  // Analytics
  public getModerationStats(): ModerationStats {
    const pendingReports = this.reports.filter(r => r.status === 'pending').length;
    const resolvedReports = this.reports.filter(r => r.status === 'resolved').length;
    const autoModerated = this.actions.filter(a => a.auto).length;
    const manualActions = this.actions.filter(a => !a.auto).length;

    // Calculate average response time
    const reviewedReports = this.reports.filter(r => r.reviewedAt);
    const avgResponseTime = reviewedReports.length > 0 
      ? reviewedReports.reduce((sum, r) => {
          const responseTime = new Date(r.reviewedAt!).getTime() - new Date(r.createdAt).getTime();
          return sum + responseTime;
        }, 0) / reviewedReports.length / (1000 * 60) // Convert to minutes
      : 0;

    // Top report categories
    const categoryCounts = this.reports.reduce((acc, r) => {
      acc[r.category] = (acc[r.category] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const topReportCategories = Object.entries(categoryCounts)
      .map(([category, count]) => ({ category, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);

    // Moderator activity
    const moderatorActivity = this.actions.reduce((acc, action) => {
      const existing = acc.find(m => m.moderatorId === action.moderatorId);
      if (existing) {
        existing.actions++;
      } else {
        acc.push({
          moderatorId: action.moderatorId,
          moderatorName: action.moderatorName,
          actions: 1,
          avgResponseTime: 0
        });
      }
      return acc;
    }, [] as ModerationStats['moderatorActivity']);

    return {
      totalReports: this.reports.length,
      pendingReports,
      resolvedReports,
      autoModerated,
      manualActions,
      averageResponseTime: avgResponseTime,
      topReportCategories,
      moderatorActivity
    };
  }

  // Utility Methods
  private generateId(prefix: string): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public isUserBlocked(userId: string): boolean {
    return this.blockedUsers.has(userId);
  }

  public isUserTrusted(userId: string): boolean {
    return this.trustedUsers.has(userId);
  }

  public getBlockedUsers(): string[] {
    return [...this.blockedUsers];
  }

  public getTrustedUsers(): string[] {
    return [...this.trustedUsers];
  }

  public exportModerationData(): string {
    return JSON.stringify({
      filters: this.filters,
      reports: this.reports,
      actions: this.actions,
      queue: this.queue,
      blockedUsers: [...this.blockedUsers],
      trustedUsers: [...this.trustedUsers]
    }, null, 2);
  }

  public importModerationData(data: string): boolean {
    try {
      const imported = JSON.parse(data);
      
      if (imported.filters) this.filters = imported.filters;
      if (imported.reports) this.reports = imported.reports;
      if (imported.actions) this.actions = imported.actions;
      if (imported.queue) this.queue = imported.queue;
      if (imported.blockedUsers) this.blockedUsers = new Set(imported.blockedUsers);
      if (imported.trustedUsers) this.trustedUsers = new Set(imported.trustedUsers);

      this.saveModerationData();
      return true;
    } catch (error) {
      console.error('Error importing moderation data:', error);
      return false;
    }
  }
}

// Export singleton instance
export const contentModerator = new ContentModerator();
