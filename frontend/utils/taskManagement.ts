import { Task, Project, TeamMember, TimeEntry, Resource } from '@/types/project';

export interface TaskFilter {
  status?: string[];
  priority?: string[];
  assignee?: string[];
  tags?: string[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  search?: string;
}

export interface TaskSort {
  field: keyof Task;
  direction: 'asc' | 'desc';
}

export interface TaskStatistics {
  totalTasks: number;
  completedTasks: number;
  inProgressTasks: number;
  blockedTasks: number;
  overdueTasks: number;
  completionRate: number;
  averageCompletionTime: number;
  productivityScore: number;
}

export interface GanttChartData {
  tasks: {
    id: string;
    title: string;
    start: Date;
    end: Date;
    progress: number;
    dependencies: string[];
    assignee: string;
    status: string;
  }[];
  milestones: {
    id: string;
    title: string;
    date: Date;
    status: string;
  }[];
}

export interface WorkloadDistribution {
  memberId: string;
  memberName: string;
  totalHours: number;
  allocatedHours: number;
  utilizationRate: number;
  tasks: {
    id: string;
    title: string;
    estimatedHours: number;
    actualHours: number;
    status: string;
  }[];
}

export interface CriticalPath {
  tasks: string[];
  totalDuration: number;
  criticalTasks: {
    id: string;
    title: string;
    duration: number;
    slack: number;
  }[];
}

export class TaskManager {
  private tasks: Task[] = [];
  private projects: Project[] = [];
  private teamMembers: TeamMember[] = [];

  constructor() {
    this.initializeData();
  }

  private initializeData(): void {
    // Initialize with sample data
    this.loadFromStorage();
  }

  private loadFromStorage(): void {
    try {
      const storedTasks = localStorage.getItem('tasks');
      const storedProjects = localStorage.getItem('projects');
      const storedTeamMembers = localStorage.getItem('teamMembers');

      if (storedTasks) this.tasks = JSON.parse(storedTasks);
      if (storedProjects) this.projects = JSON.parse(storedProjects);
      if (storedTeamMembers) this.teamMembers = JSON.parse(storedTeamMembers);
    } catch (error) {
      console.error('Error loading data from storage:', error);
    }
  }

  private saveToStorage(): void {
    try {
      localStorage.setItem('tasks', JSON.stringify(this.tasks));
      localStorage.setItem('projects', JSON.stringify(this.projects));
      localStorage.setItem('teamMembers', JSON.stringify(this.teamMembers));
    } catch (error) {
      console.error('Error saving data to storage:', error);
    }
  }

  // Task Management
  public createTask(taskData: Omit<Task, 'id' | 'createdAt' | 'updatedAt'>): Task {
    const task: Task = {
      ...taskData,
      id: this.generateId('task'),
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString()
    };

    this.tasks.push(task);
    this.saveToStorage();
    return task;
  }

  public updateTask(taskId: string, updates: Partial<Task>): Task | null {
    const taskIndex = this.tasks.findIndex(t => t.id === taskId);
    if (taskIndex === -1) return null;

    this.tasks[taskIndex] = {
      ...this.tasks[taskIndex],
      ...updates,
      updatedAt: new Date().toISOString()
    };

    this.saveToStorage();
    return this.tasks[taskIndex];
  }

  public deleteTask(taskId: string): boolean {
    const initialLength = this.tasks.length;
    this.tasks = this.tasks.filter(t => t.id !== taskId);
    
    if (this.tasks.length < initialLength) {
      this.saveToStorage();
      return true;
    }
    return false;
  }

  public getTask(taskId: string): Task | null {
    return this.tasks.find(t => t.id === taskId) || null;
  }

  public getTasks(filter?: TaskFilter, sort?: TaskSort): Task[] {
    let filteredTasks = [...this.tasks];

    // Apply filters
    if (filter) {
      if (filter.status && filter.status.length > 0) {
        filteredTasks = filteredTasks.filter(t => filter.status!.includes(t.status));
      }
      if (filter.priority && filter.priority.length > 0) {
        filteredTasks = filteredTasks.filter(t => filter.priority!.includes(t.priority));
      }
      if (filter.assignee && filter.assignee.length > 0) {
        filteredTasks = filteredTasks.filter(t => filter.assignee!.includes(t.assignee));
      }
      if (filter.tags && filter.tags.length > 0) {
        filteredTasks = filteredTasks.filter(t => 
          t.tags.some(tag => filter.tags!.includes(tag))
        );
      }
      if (filter.dateRange) {
        filteredTasks = filteredTasks.filter(t => {
          const taskDate = new Date(t.dueDate);
          return taskDate >= filter.dateRange!.start && taskDate <= filter.dateRange!.end;
        });
      }
      if (filter.search) {
        const searchLower = filter.search.toLowerCase();
        filteredTasks = filteredTasks.filter(t =>
          t.title.toLowerCase().includes(searchLower) ||
          t.description.toLowerCase().includes(searchLower)
        );
      }
    }

    // Apply sorting
    if (sort) {
      filteredTasks.sort((a, b) => {
        const aValue = a[sort.field];
        const bValue = b[sort.field];
        
        if (aValue < bValue) return sort.direction === 'asc' ? -1 : 1;
        if (aValue > bValue) return sort.direction === 'asc' ? 1 : -1;
        return 0;
      });
    }

    return filteredTasks;
  }

  // Task Statistics
  public getTaskStatistics(projectId?: string): TaskStatistics {
    const tasks = projectId 
      ? this.tasks.filter(t => this.getProjectTaskIds(projectId).includes(t.id))
      : this.tasks;

    const totalTasks = tasks.length;
    const completedTasks = tasks.filter(t => t.status === 'completed').length;
    const inProgressTasks = tasks.filter(t => t.status === 'in_progress').length;
    const blockedTasks = tasks.filter(t => t.status === 'blocked').length;
    const overdueTasks = tasks.filter(t => 
      t.status !== 'completed' && new Date(t.dueDate) < new Date()
    ).length;

    const completionRate = totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0;
    
    // Calculate average completion time
    const completedTasksWithTime = tasks.filter(t => 
      t.status === 'completed' && t.actualHours > 0
    );
    const averageCompletionTime = completedTasksWithTime.length > 0
      ? completedTasksWithTime.reduce((sum, t) => sum + t.actualHours, 0) / completedTasksWithTime.length
      : 0;

    // Calculate productivity score (completed tasks / total estimated hours)
    const totalEstimatedHours = tasks.reduce((sum, t) => sum + t.estimatedHours, 0);
    const totalActualHours = tasks.reduce((sum, t) => sum + t.actualHours, 0);
    const productivityScore = totalEstimatedHours > 0 
      ? (completedTasks / totalEstimatedHours) * 100 
      : 0;

    return {
      totalTasks,
      completedTasks,
      inProgressTasks,
      blockedTasks,
      overdueTasks,
      completionRate,
      averageCompletionTime,
      productivityScore
    };
  }

  // Dependency Management
  public getTaskDependencies(taskId: string): Task[] {
    const task = this.getTask(taskId);
    if (!task) return [];

    return task.dependencies.map(depId => this.getTask(depId)).filter(Boolean) as Task[];
  }

  public getTaskDependents(taskId: string): Task[] {
    return this.tasks.filter(t => t.dependencies.includes(taskId));
  }

  public canUpdateTaskStatus(taskId: string, newStatus: string): boolean {
    const task = this.getTask(taskId);
    if (!task) return false;

    // Check if all dependencies are completed
    if (newStatus === 'in_progress') {
      const dependencies = this.getTaskDependencies(taskId);
      return dependencies.every(dep => dep.status === 'completed');
    }

    return true;
  }

  // Critical Path Analysis
  public calculateCriticalPath(projectId: string): CriticalPath {
    const projectTasks = this.tasks.filter(t => 
      this.getProjectTaskIds(projectId).includes(t.id)
    );

    // Build dependency graph
    const taskMap = new Map(projectTasks.map(t => [t.id, t]));
    const visited = new Set<string>();
    const criticalTasks: { id: string; title: string; duration: number; slack: number }[] = [];

    // Calculate earliest start times
    const earliestStart = new Map<string, number>();
    projectTasks.forEach(task => {
      if (task.dependencies.length === 0) {
        earliestStart.set(task.id, 0);
      } else {
        const maxDepEnd = Math.max(...task.dependencies.map(depId => {
          const dep = taskMap.get(depId);
          return dep ? (earliestStart.get(depId) || 0) + dep.estimatedHours : 0;
        }));
        earliestStart.set(task.id, maxDepEnd);
      }
    });

    // Calculate latest start times and slack
    const latestStart = new Map<string, number>();
    const projectEnd = Math.max(...projectTasks.map(t => 
      (earliestStart.get(t.id) || 0) + t.estimatedHours
    ));

    projectTasks.forEach(task => {
      const dependents = this.getTaskDependents(task.id);
      if (dependents.length === 0) {
        latestStart.set(task.id, projectEnd - task.estimatedHours);
      } else {
        const minDepStart = Math.min(...dependents.map(dep => 
          latestStart.get(dep.id) || 0
        ));
        latestStart.set(task.id, minDepStart - task.estimatedHours);
      }
    });

    // Identify critical tasks (slack = 0)
    projectTasks.forEach(task => {
      const slack = (latestStart.get(task.id) || 0) - (earliestStart.get(task.id) || 0);
      if (Math.abs(slack) < 0.01) { // Consider floating point precision
        criticalTasks.push({
          id: task.id,
          title: task.title,
          duration: task.estimatedHours,
          slack: 0
        });
      }
    });

    return {
      tasks: criticalTasks.map(t => t.id),
      totalDuration: projectEnd,
      criticalTasks
    };
  }

  // Gantt Chart Data
  public getGanttChartData(projectId: string): GanttChartData {
    const projectTasks = this.tasks.filter(t => 
      this.getProjectTaskIds(projectId).includes(t.id)
    );

    const project = this.projects.find(p => p.id === projectId);
    const milestones = project?.milestones || [];

    return {
      tasks: projectTasks.map(task => ({
        id: task.id,
        title: task.title,
        start: new Date(task.createdAt),
        end: new Date(task.dueDate),
        progress: task.status === 'completed' ? 100 : task.status === 'in_progress' ? 50 : 0,
        dependencies: task.dependencies,
        assignee: task.assignee,
        status: task.status
      })),
      milestones: milestones.map(milestone => ({
        id: milestone.id,
        title: milestone.title,
        date: new Date(milestone.dueDate),
        status: milestone.status
      }))
    };
  }

  // Workload Distribution
  public getWorkloadDistribution(projectId?: string): WorkloadDistribution[] {
    const tasks = projectId 
      ? this.tasks.filter(t => this.getProjectTaskIds(projectId).includes(t.id))
      : this.tasks;

    const workloadMap = new Map<string, WorkloadDistribution>();

    // Calculate workload per team member
    tasks.forEach(task => {
      const member = workloadMap.get(task.assignee);
      if (member) {
        member.totalHours += task.estimatedHours;
        member.tasks.push({
          id: task.id,
          title: task.title,
          estimatedHours: task.estimatedHours,
          actualHours: task.actualHours,
          status: task.status
        });
      } else {
        workloadMap.set(task.assignee, {
          memberId: task.assignee,
          memberName: task.assignee,
          totalHours: task.estimatedHours,
          allocatedHours: 0, // Would be set based on team member capacity
          utilizationRate: 0,
          tasks: [{
            id: task.id,
            title: task.title,
            estimatedHours: task.estimatedHours,
            actualHours: task.actualHours,
            status: task.status
          }]
        });
      }
    });

    // Calculate utilization rates
    workloadMap.forEach((workload, memberId) => {
      const teamMember = this.teamMembers.find(m => m.id === memberId);
      if (teamMember) {
        workload.allocatedHours = teamMember.workload * 40; // Assuming 40-hour work weeks
        workload.utilizationRate = workload.allocatedHours > 0 
          ? (workload.totalHours / workload.allocatedHours) * 100 
          : 0;
      }
    });

    return Array.from(workloadMap.values());
  }

  // Time Tracking
  public logTime(timeEntry: Omit<TimeEntry, 'id' | 'createdAt'>): TimeEntry {
    const entry: TimeEntry = {
      ...timeEntry,
      id: this.generateId('time'),
      createdAt: new Date().toISOString()
    };

    // Update task actual hours
    this.updateTask(timeEntry.taskId, {
      actualHours: (this.getTask(timeEntry.taskId)?.actualHours || 0) + timeEntry.hours
    });

    // Store time entry (in real app, this would go to database)
    const timeEntries = this.getTimeEntries();
    timeEntries.push(entry);
    localStorage.setItem('timeEntries', JSON.stringify(timeEntries));

    return entry;
  }

  public getTimeEntries(taskId?: string, userId?: string): TimeEntry[] {
    try {
      const stored = localStorage.getItem('timeEntries');
      let entries: TimeEntry[] = stored ? JSON.parse(stored) : [];

      if (taskId) {
        entries = entries.filter(e => e.taskId === taskId);
      }
      if (userId) {
        entries = entries.filter(e => e.userId === userId);
      }

      return entries;
    } catch (error) {
      console.error('Error loading time entries:', error);
      return [];
    }
  }

  // Resource Management
  public allocateResource(resourceId: string, allocation: number): boolean {
    // In a real implementation, this would update the database
    console.log(`Allocating resource ${resourceId} with ${allocation}% allocation`);
    return true;
  }

  // Project Helpers
  private getProjectTaskIds(projectId: string): string[] {
    const project = this.projects.find(p => p.id === projectId);
    return project?.tasks.map(t => t.id) || [];
  }

  // Utility Methods
  private generateId(prefix: string): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  public exportTasks(format: 'json' | 'csv' | 'excel'): string {
    const data = this.tasks;
    
    if (format === 'json') {
      return JSON.stringify(data, null, 2);
    }
    
    if (format === 'csv') {
      const headers = ['ID', 'Title', 'Status', 'Priority', 'Assignee', 'Estimated Hours', 'Actual Hours', 'Due Date'];
      const rows = data.map(task => [
        task.id,
        task.title,
        task.status,
        task.priority,
        task.assignee,
        task.estimatedHours,
        task.actualHours,
        task.dueDate
      ]);
      
      return [headers, ...rows].map(row => row.join(',')).join('\n');
    }
    
    // For Excel, would need a library like xlsx
    return JSON.stringify(data, null, 2);
  }

  public importTasks(data: string, format: 'json' | 'csv'): boolean {
    try {
      let importedTasks: any[] = [];
      
      if (format === 'json') {
        importedTasks = JSON.parse(data);
      } else if (format === 'csv') {
        const lines = data.split('\n');
        const headers = lines[0].split(',');
        
        for (let i = 1; i < lines.length; i++) {
          const values = lines[i].split(',');
          const task: any = {};
          
          headers.forEach((header, index) => {
            task[header.toLowerCase().replace(' ', '_')] = values[index];
          });
          
          importedTasks.push(task);
        }
      }
      
      // Validate and add tasks
      importedTasks.forEach(taskData => {
        if (taskData.title && taskData.assignee) {
          this.createTask({
            title: taskData.title,
            description: taskData.description || '',
            status: taskData.status || 'todo',
            priority: taskData.priority || 'medium',
            assignee: taskData.assignee,
            estimatedHours: parseFloat(taskData.estimated_hours) || 0,
            actualHours: parseFloat(taskData.actual_hours) || 0,
            dueDate: taskData.due_date || new Date().toISOString().split('T')[0],
            dependencies: [],
            tags: []
          });
        }
      });
      
      return true;
    } catch (error) {
      console.error('Error importing tasks:', error);
      return false;
    }
  }

  // Notification System
  public getOverdueTasks(): Task[] {
    return this.tasks.filter(task => 
      task.status !== 'completed' && 
      new Date(task.dueDate) < new Date()
    );
  }

  public getUpcomingDeadlines(days: number = 7): Task[] {
    const cutoff = new Date();
    cutoff.setDate(cutoff.getDate() + days);
    
    return this.tasks.filter(task => 
      task.status !== 'completed' && 
      new Date(task.dueDate) <= cutoff &&
      new Date(task.dueDate) >= new Date()
    );
  }

  public getTasksNeedingAttention(): Task[] {
    return this.tasks.filter(task => {
      // Overdue tasks
      if (task.status !== 'completed' && new Date(task.dueDate) < new Date()) {
        return true;
      }
      
      // Tasks with no progress but past halfway point
      const daysSinceCreation = Math.floor(
        (Date.now() - new Date(task.createdAt).getTime()) / (1000 * 60 * 60 * 24)
      );
      const totalDays = Math.floor(
        (new Date(task.dueDate).getTime() - new Date(task.createdAt).getTime()) / (1000 * 60 * 60 * 24)
      );
      
      if (daysSinceCreation > totalDays / 2 && task.status === 'todo') {
        return true;
      }
      
      return false;
    });
  }
}

// Export singleton instance
export const taskManager = new TaskManager();
