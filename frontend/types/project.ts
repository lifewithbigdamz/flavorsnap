export interface Task {
  id: string;
  title: string;
  description: string;
  status: 'todo' | 'in_progress' | 'completed' | 'blocked';
  priority: 'low' | 'medium' | 'high' | 'critical';
  assignee: string;
  estimatedHours: number;
  actualHours: number;
  dueDate: string;
  dependencies: string[];
  tags: string[];
  createdAt: string;
  updatedAt: string;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  status: 'planning' | 'active' | 'on_hold' | 'completed' | 'cancelled';
  startDate: string;
  endDate: string;
  budget: number;
  team: TeamMember[];
  tasks: Task[];
  progress: number;
  milestones: Milestone[];
}

export interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar: string;
  workload: number;
  skills: string[];
}

export interface Milestone {
  id: string;
  title: string;
  description: string;
  dueDate: string;
  status: 'pending' | 'completed' | 'overdue';
  progress: number;
}

export interface Resource {
  id: string;
  name: string;
  type: 'human' | 'equipment' | 'budget' | 'material';
  allocation: number;
  availability: number;
  cost: number;
}

export interface TimeEntry {
  id: string;
  taskId: string;
  userId: string;
  hours: number;
  description: string;
  date: string;
  billable: boolean;
  createdAt: string;
}
