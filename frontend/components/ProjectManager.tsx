import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Calendar, Clock, Users, BarChart3, Plus, Edit, Trash2, CheckCircle, AlertCircle } from 'lucide-react';

interface Task {
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

interface Project {
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

interface TeamMember {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar: string;
  workload: number;
  skills: string[];
}

interface Milestone {
  id: string;
  title: string;
  description: string;
  dueDate: string;
  status: 'pending' | 'completed' | 'overdue';
  progress: number;
}

interface Resource {
  id: string;
  name: string;
  type: 'human' | 'equipment' | 'budget' | 'material';
  allocation: number;
  availability: number;
  cost: number;
}

interface TimeEntry {
  id: string;
  taskId: string;
  userId: string;
  hours: number;
  description: string;
  date: string;
  billable: boolean;
}

export default function ProjectManager() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [isLoading, setIsLoading] = useState(false);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showNewTaskModal, setShowNewTaskModal] = useState(false);

  // Project management functions
  const createProject = async (projectData: Partial<Project>) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(projectData)
      });
      const newProject = await response.json();
      setProjects([...projects, newProject]);
      setShowNewProjectModal(false);
    } catch (error) {
      console.error('Error creating project:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateProject = async (projectId: string, updates: Partial<Project>) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      const updatedProject = await response.json();
      setProjects(projects.map(p => p.id === projectId ? updatedProject : p));
      if (selectedProject?.id === projectId) {
        setSelectedProject(updatedProject);
      }
    } catch (error) {
      console.error('Error updating project:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const deleteProject = async (projectId: string) => {
    setIsLoading(true);
    try {
      await fetch(`/api/projects/${projectId}`, { method: 'DELETE' });
      setProjects(projects.filter(p => p.id !== projectId));
      if (selectedProject?.id === projectId) {
        setSelectedProject(null);
      }
    } catch (error) {
      console.error('Error deleting project:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Task management functions
  const createTask = async (taskData: Partial<Task>) => {
    if (!selectedProject) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(taskData)
      });
      const newTask = await response.json();
      const updatedProject = {
        ...selectedProject,
        tasks: [...selectedProject.tasks, newTask]
      };
      setSelectedProject(updatedProject);
      setProjects(projects.map(p => p.id === selectedProject.id ? updatedProject : p));
      setShowNewTaskModal(false);
    } catch (error) {
      console.error('Error creating task:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const updateTask = async (taskId: string, updates: Partial<Task>) => {
    if (!selectedProject) return;
    
    setIsLoading(true);
    try {
      const response = await fetch(`/api/projects/${selectedProject.id}/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      const updatedTask = await response.json();
      const updatedProject = {
        ...selectedProject,
        tasks: selectedProject.tasks.map(t => t.id === taskId ? updatedTask : t)
      };
      setSelectedProject(updatedProject);
      setProjects(projects.map(p => p.id === selectedProject.id ? updatedProject : p));
    } catch (error) {
      console.error('Error updating task:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Time tracking functions
  const logTime = async (timeEntry: Partial<TimeEntry>) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/time-entries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(timeEntry)
      });
      const newEntry = await response.json();
      // Update task actual hours
      if (selectedProject) {
        const task = selectedProject.tasks.find(t => t.id === timeEntry.taskId);
        if (task) {
          await updateTask(task.id, {
            actualHours: task.actualHours + timeEntry.hours
          });
        }
      }
    } catch (error) {
      console.error('Error logging time:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Resource allocation functions
  const allocateResource = async (resourceId: string, allocation: number) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/resources/${resourceId}/allocate`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ allocation })
      });
      const updatedResource = await response.json();
      // Update local state
    } catch (error) {
      console.error('Error allocating resource:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Reporting functions
  const generateReport = async (reportType: string, projectId?: string) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/reports/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type: reportType, projectId })
      });
      const report = await response.json();
      // Handle report download/display
      console.log('Report generated:', report);
    } catch (error) {
      console.error('Error generating report:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Calculate project statistics
  const getProjectStats = (project: Project) => {
    const totalTasks = project.tasks.length;
    const completedTasks = project.tasks.filter(t => t.status === 'completed').length;
    const inProgressTasks = project.tasks.filter(t => t.status === 'in_progress').length;
    const overdueTasks = project.tasks.filter(t => 
      t.status !== 'completed' && new Date(t.dueDate) < new Date()
    ).length;
    const totalEstimatedHours = project.tasks.reduce((sum, t) => sum + t.estimatedHours, 0);
    const totalActualHours = project.tasks.reduce((sum, t) => sum + t.actualHours, 0);

    return {
      totalTasks,
      completedTasks,
      inProgressTasks,
      overdueTasks,
      completionRate: totalTasks > 0 ? (completedTasks / totalTasks) * 100 : 0,
      totalEstimatedHours,
      totalActualHours,
      efficiency: totalEstimatedHours > 0 ? (totalEstimatedHours / totalActualHours) * 100 : 0
    };
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-500';
      case 'in_progress': return 'bg-blue-500';
      case 'active': return 'bg-green-500';
      case 'on_hold': return 'bg-yellow-500';
      case 'blocked': return 'bg-red-500';
      case 'cancelled': return 'bg-red-500';
      default: return 'bg-gray-500';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'critical': return 'bg-red-100 text-red-800 border-red-200';
      case 'high': return 'bg-orange-100 text-orange-800 border-orange-200';
      case 'medium': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'low': return 'bg-green-100 text-green-800 border-green-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Project Management</h1>
        <Button onClick={() => setShowNewProjectModal(true)}>
          <Plus className="w-4 h-4 mr-2" />
          New Project
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Projects List */}
        <div className="lg:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>Projects</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {projects.map(project => {
                const stats = getProjectStats(project);
                return (
                  <div
                    key={project.id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedProject?.id === project.id 
                        ? 'border-blue-500 bg-blue-50' 
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setSelectedProject(project)}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-medium">{project.name}</h3>
                      <Badge className={getStatusColor(project.status)}>
                        {project.status.replace('_', ' ')}
                      </Badge>
                    </div>
                    <Progress value={stats.completionRate} className="mb-2" />
                    <div className="text-xs text-gray-500">
                      {stats.completedTasks}/{stats.totalTasks} tasks
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>
        </div>

        {/* Project Details */}
        <div className="lg:col-span-3">
          {selectedProject ? (
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-6">
                <TabsTrigger value="overview">Overview</TabsTrigger>
                <TabsTrigger value="tasks">Tasks</TabsTrigger>
                <TabsTrigger value="team">Team</TabsTrigger>
                <TabsTrigger value="resources">Resources</TabsTrigger>
                <TabsTrigger value="time">Time Tracking</TabsTrigger>
                <TabsTrigger value="reports">Reports</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="flex justify-between items-center">
                      {selectedProject.name}
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => deleteProject(selectedProject.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-gray-600 mb-4">{selectedProject.description}</p>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                      <div className="text-center">
                        <div className="text-2xl font-bold">{getProjectStats(selectedProject).completionRate.toFixed(0)}%</div>
                        <div className="text-sm text-gray-500">Completion</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{getProjectStats(selectedProject).totalTasks}</div>
                        <div className="text-sm text-gray-500">Total Tasks</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{getProjectStats(selectedProject).overdueTasks}</div>
                        <div className="text-sm text-gray-500">Overdue</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold">{selectedProject.team.length}</div>
                        <div className="text-sm text-gray-500">Team Members</div>
                      </div>
                    </div>

                    <div className="space-y-4">
                      <div>
                        <h4 className="font-medium mb-2">Progress</h4>
                        <Progress value={selectedProject.progress} />
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <h4 className="font-medium mb-2">Timeline</h4>
                          <div className="text-sm text-gray-600">
                            <div>Start: {new Date(selectedProject.startDate).toLocaleDateString()}</div>
                            <div>End: {new Date(selectedProject.endDate).toLocaleDateString()}</div>
                          </div>
                        </div>
                        <div>
                          <h4 className="font-medium mb-2">Budget</h4>
                          <div className="text-sm text-gray-600">
                            ${selectedProject.budget.toLocaleString()}
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Milestones */}
                <Card>
                  <CardHeader>
                    <CardTitle>Milestones</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {selectedProject.milestones.map(milestone => (
                        <div key={milestone.id} className="flex items-center justify-between p-3 border rounded-lg">
                          <div>
                            <h4 className="font-medium">{milestone.title}</h4>
                            <p className="text-sm text-gray-600">{milestone.description}</p>
                            <div className="text-xs text-gray-500 mt-1">
                              Due: {new Date(milestone.dueDate).toLocaleDateString()}
                            </div>
                          </div>
                          <div className="text-right">
                            <Badge className={getStatusColor(milestone.status)}>
                              {milestone.status}
                            </Badge>
                            <div className="mt-2">
                              <Progress value={milestone.progress} className="w-20" />
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="tasks" className="space-y-4">
                <div className="flex justify-between items-center">
                  <h3 className="text-lg font-medium">Tasks</h3>
                  <Button onClick={() => setShowNewTaskModal(true)}>
                    <Plus className="w-4 h-4 mr-2" />
                    Add Task
                  </Button>
                </div>

                <div className="grid gap-3">
                  {selectedProject.tasks.map(task => (
                    <Card key={task.id}>
                      <CardContent className="p-4">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <h4 className="font-medium">{task.title}</h4>
                            <p className="text-sm text-gray-600">{task.description}</p>
                          </div>
                          <Badge className={getPriorityColor(task.priority)}>
                            {task.priority}
                          </Badge>
                        </div>
                        
                        <div className="flex items-center gap-4 text-sm text-gray-500">
                          <div className="flex items-center gap-1">
                            <Users className="w-4 h-4" />
                            {task.assignee}
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="w-4 h-4" />
                            {task.actualHours}h / {task.estimatedHours}h
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="w-4 h-4" />
                            {new Date(task.dueDate).toLocaleDateString()}
                          </div>
                          <Badge className={getStatusColor(task.status)}>
                            {task.status.replace('_', ' ')}
                          </Badge>
                        </div>

                        <div className="mt-3">
                          <Progress 
                            value={task.status === 'completed' ? 100 : task.status === 'in_progress' ? 50 : 0} 
                          />
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </TabsContent>

              <TabsContent value="team" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Team Members</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4">
                      {selectedProject.team.map(member => (
                        <div key={member.id} className="flex items-center justify-between p-4 border rounded-lg">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
                              {member.name.charAt(0)}
                            </div>
                            <div>
                              <h4 className="font-medium">{member.name}</h4>
                              <p className="text-sm text-gray-600">{member.role}</p>
                              <p className="text-xs text-gray-500">{member.email}</p>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm text-gray-600">Workload: {member.workload}%</div>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {member.skills.map(skill => (
                                <Badge key={skill} variant="outline" className="text-xs">
                                  {skill}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="resources" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Resource Allocation</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Resource allocation interface would go here */}
                      <p className="text-gray-600">Resource allocation management interface</p>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="time" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Time Tracking</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {/* Time tracking interface would go here */}
                      <p className="text-gray-600">Time tracking and logging interface</p>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="reports" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Reports & Analytics</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <Button 
                        variant="outline" 
                        onClick={() => generateReport('project_summary', selectedProject.id)}
                      >
                        <BarChart3 className="w-4 h-4 mr-2" />
                        Project Summary
                      </Button>
                      <Button 
                        variant="outline" 
                        onClick={() => generateReport('time_analysis', selectedProject.id)}
                      >
                        <Clock className="w-4 h-4 mr-2" />
                        Time Analysis
                      </Button>
                      <Button 
                        variant="outline" 
                        onClick={() => generateReport('resource_utilization', selectedProject.id)}
                      >
                        <Users className="w-4 h-4 mr-2" />
                        Resources
                      </Button>
                      <Button 
                        variant="outline" 
                        onClick={() => generateReport('progress_report', selectedProject.id)}
                      >
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Progress
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          ) : (
            <Card>
              <CardContent className="p-8 text-center">
                <p className="text-gray-500">Select a project to view details</p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
