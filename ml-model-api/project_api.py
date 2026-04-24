from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date
import json

router = APIRouter(prefix="/api/projects", tags=["projects"])

# Pydantic models for request/response
class TaskBase(BaseModel):
    title: str
    description: str
    status: str = "todo"
    priority: str = "medium"
    assignee: str
    estimated_hours: float
    due_date: date
    dependencies: List[str] = []
    tags: List[str] = []

class TaskCreate(TaskBase):
    project_id: str

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    estimated_hours: Optional[float] = None
    actual_hours: Optional[float] = None
    due_date: Optional[date] = None
    dependencies: Optional[List[str]] = None
    tags: Optional[List[str]] = None

class TaskResponse(TaskBase):
    id: str
    actual_hours: float = 0.0
    created_at: datetime
    updated_at: datetime

class TeamMemberBase(BaseModel):
    name: str
    email: str
    role: str
    avatar: str = ""
    workload: float = 0.0
    skills: List[str] = []

class TeamMemberCreate(TeamMemberBase):
    project_id: str

class TeamMemberResponse(TeamMemberBase):
    id: str

class MilestoneBase(BaseModel):
    title: str
    description: str
    due_date: date
    status: str = "pending"
    progress: float = 0.0

class MilestoneCreate(MilestoneBase):
    project_id: str

class MilestoneResponse(MilestoneBase):
    id: str

class ProjectBase(BaseModel):
    name: str
    description: str
    status: str = "planning"
    start_date: date
    end_date: date
    budget: float = 0.0

class ProjectCreate(ProjectBase):
    pass

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    budget: Optional[float] = None
    progress: Optional[float] = None

class ProjectResponse(ProjectBase):
    id: str
    progress: float = 0.0
    created_at: datetime
    updated_at: datetime
    team: List[TeamMemberResponse] = []
    tasks: List[TaskResponse] = []
    milestones: List[MilestoneResponse] = []

class ResourceBase(BaseModel):
    name: str
    type: str  # human, equipment, budget, material
    allocation: float = 0.0
    availability: float = 100.0
    cost: float = 0.0

class ResourceCreate(ResourceBase):
    project_id: str

class ResourceResponse(ResourceBase):
    id: str

class TimeEntryBase(BaseModel):
    task_id: str
    user_id: str
    hours: float
    description: str
    date: date
    billable: bool = True

class TimeEntryCreate(TimeEntryBase):
    pass

class TimeEntryResponse(TimeEntryBase):
    id: str
    created_at: datetime

# Database dependency
def get_db():
    # This would be replaced with actual database session
    pass

# Project endpoints
@router.post("/", response_model=ProjectResponse)
async def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """Create a new project"""
    try:
        # In a real implementation, this would save to database
        project_data = {
            "id": f"proj_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "start_date": project.start_date,
            "end_date": project.end_date,
            "budget": project.budget,
            "progress": 0.0,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "team": [],
            "tasks": [],
            "milestones": []
        }
        
        # Log project creation
        print(f"Created project: {project_data['id']} - {project.name}")
        
        return ProjectResponse(**project_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")

@router.get("/", response_model=List[ProjectResponse])
async def get_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Get all projects with optional filtering"""
    try:
        # In a real implementation, this would query the database
        projects = []
        
        # Mock data for demonstration
        mock_projects = [
            {
                "id": "proj_001",
                "name": "Website Redesign",
                "description": "Complete redesign of company website",
                "status": "active",
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 6, 30),
                "budget": 50000.0,
                "progress": 65.0,
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime.now(),
                "team": [],
                "tasks": [],
                "milestones": []
            },
            {
                "id": "proj_002",
                "name": "Mobile App Development",
                "description": "Develop new mobile application",
                "status": "planning",
                "start_date": date(2024, 3, 1),
                "end_date": date(2024, 12, 31),
                "budget": 120000.0,
                "progress": 15.0,
                "created_at": datetime(2024, 2, 15),
                "updated_at": datetime.now(),
                "team": [],
                "tasks": [],
                "milestones": []
            }
        ]
        
        # Filter by status if provided
        if status:
            mock_projects = [p for p in mock_projects if p["status"] == status]
        
        # Apply pagination
        paginated_projects = mock_projects[skip:skip + limit]
        
        return [ProjectResponse(**p) for p in paginated_projects]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projects: {str(e)}")

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: Session = Depends(get_db)):
    """Get a specific project by ID"""
    try:
        # In a real implementation, this would query the database
        if project_id == "proj_001":
            project_data = {
                "id": "proj_001",
                "name": "Website Redesign",
                "description": "Complete redesign of company website",
                "status": "active",
                "start_date": date(2024, 1, 1),
                "end_date": date(2024, 6, 30),
                "budget": 50000.0,
                "progress": 65.0,
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime.now(),
                "team": [
                    {
                        "id": "member_001",
                        "name": "John Doe",
                        "email": "john@example.com",
                        "role": "Frontend Developer",
                        "avatar": "",
                        "workload": 80.0,
                        "skills": ["React", "TypeScript", "CSS"]
                    }
                ],
                "tasks": [
                    {
                        "id": "task_001",
                        "title": "Design Homepage",
                        "description": "Create homepage design mockups",
                        "status": "completed",
                        "priority": "high",
                        "assignee": "John Doe",
                        "estimated_hours": 40.0,
                        "actual_hours": 35.0,
                        "due_date": date(2024, 2, 15),
                        "dependencies": [],
                        "tags": ["design", "ui/ux"],
                        "created_at": datetime(2024, 1, 5),
                        "updated_at": datetime(2024, 2, 14)
                    }
                ],
                "milestones": [
                    {
                        "id": "milestone_001",
                        "title": "Design Phase Complete",
                        "description": "All design mockups approved",
                        "due_date": date(2024, 3, 1),
                        "status": "completed",
                        "progress": 100.0
                    }
                ]
            }
            return ProjectResponse(**project_data)
        else:
            raise HTTPException(status_code=404, detail="Project not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch project: {str(e)}")

@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, project_update: ProjectUpdate, db: Session = Depends(get_db)):
    """Update a project"""
    try:
        # Get existing project
        existing_project = await get_project(project_id, db)
        
        # Update fields
        update_data = project_update.dict(exclude_unset=True)
        
        # In a real implementation, this would update the database
        updated_project = existing_project.dict()
        updated_project.update(update_data)
        updated_project["updated_at"] = datetime.now()
        
        print(f"Updated project: {project_id}")
        
        return ProjectResponse(**updated_project)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")

@router.delete("/{project_id}")
async def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Delete a project"""
    try:
        # In a real implementation, this would delete from database
        print(f"Deleted project: {project_id}")
        
        return {"message": f"Project {project_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")

# Task endpoints
@router.post("/{project_id}/tasks", response_model=TaskResponse)
async def create_task(project_id: str, task: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task for a project"""
    try:
        task_data = {
            "id": f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": task.title,
            "description": task.description,
            "status": task.status,
            "priority": task.priority,
            "assignee": task.assignee,
            "estimated_hours": task.estimated_hours,
            "actual_hours": 0.0,
            "due_date": task.due_date,
            "dependencies": task.dependencies,
            "tags": task.tags,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        print(f"Created task: {task_data['id']} for project: {project_id}")
        
        return TaskResponse(**task_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")

@router.get("/{project_id}/tasks", response_model=List[TaskResponse])
async def get_tasks(project_id: str, db: Session = Depends(get_db)):
    """Get all tasks for a project"""
    try:
        # Mock data for demonstration
        tasks = [
            {
                "id": "task_001",
                "title": "Design Homepage",
                "description": "Create homepage design mockups",
                "status": "completed",
                "priority": "high",
                "assignee": "John Doe",
                "estimated_hours": 40.0,
                "actual_hours": 35.0,
                "due_date": date(2024, 2, 15),
                "dependencies": [],
                "tags": ["design", "ui/ux"],
                "created_at": datetime(2024, 1, 5),
                "updated_at": datetime(2024, 2, 14)
            },
            {
                "id": "task_002",
                "title": "Implement Navigation",
                "description": "Build responsive navigation component",
                "status": "in_progress",
                "priority": "medium",
                "assignee": "Jane Smith",
                "estimated_hours": 25.0,
                "actual_hours": 15.0,
                "due_date": date(2024, 3, 1),
                "dependencies": ["task_001"],
                "tags": ["development", "frontend"],
                "created_at": datetime(2024, 2, 1),
                "updated_at": datetime.now()
            }
        ]
        
        return [TaskResponse(**task) for task in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch tasks: {str(e)}")

@router.put("/{project_id}/tasks/{task_id}", response_model=TaskResponse)
async def update_task(project_id: str, task_id: str, task_update: TaskUpdate, db: Session = Depends(get_db)):
    """Update a task"""
    try:
        # Get existing task
        tasks = await get_tasks(project_id, db)
        existing_task = next((t for t in tasks if t.id == task_id), None)
        
        if not existing_task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Update fields
        update_data = task_update.dict(exclude_unset=True)
        updated_task = existing_task.dict()
        updated_task.update(update_data)
        updated_task["updated_at"] = datetime.now()
        
        print(f"Updated task: {task_id}")
        
        return TaskResponse(**updated_task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")

@router.delete("/{project_id}/tasks/{task_id}")
async def delete_task(project_id: str, task_id: str, db: Session = Depends(get_db)):
    """Delete a task"""
    try:
        print(f"Deleted task: {task_id} from project: {project_id}")
        
        return {"message": f"Task {task_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")

# Team member endpoints
@router.post("/{project_id}/team", response_model=TeamMemberResponse)
async def add_team_member(project_id: str, member: TeamMemberCreate, db: Session = Depends(get_db)):
    """Add a team member to a project"""
    try:
        member_data = {
            "id": f"member_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": member.name,
            "email": member.email,
            "role": member.role,
            "avatar": member.avatar,
            "workload": member.workload,
            "skills": member.skills
        }
        
        print(f"Added team member: {member_data['id']} to project: {project_id}")
        
        return TeamMemberResponse(**member_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to add team member: {str(e)}")

# Milestone endpoints
@router.post("/{project_id}/milestones", response_model=MilestoneResponse)
async def create_milestone(project_id: str, milestone: MilestoneCreate, db: Session = Depends(get_db)):
    """Create a new milestone for a project"""
    try:
        milestone_data = {
            "id": f"milestone_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": milestone.title,
            "description": milestone.description,
            "due_date": milestone.due_date,
            "status": milestone.status,
            "progress": milestone.progress
        }
        
        print(f"Created milestone: {milestone_data['id']} for project: {project_id}")
        
        return MilestoneResponse(**milestone_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create milestone: {str(e)}")

# Resource allocation endpoints
@router.post("/resources", response_model=ResourceResponse)
async def create_resource(resource: ResourceCreate, db: Session = Depends(get_db)):
    """Create a new resource"""
    try:
        resource_data = {
            "id": f"resource_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": resource.name,
            "type": resource.type,
            "allocation": resource.allocation,
            "availability": resource.availability,
            "cost": resource.cost
        }
        
        print(f"Created resource: {resource_data['id']}")
        
        return ResourceResponse(**resource_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create resource: {str(e)}")

@router.put("/resources/{resource_id}/allocate")
async def allocate_resource(resource_id: str, allocation: float, db: Session = Depends(get_db)):
    """Allocate a resource"""
    try:
        print(f"Allocated resource: {resource_id} with {allocation}% allocation")
        
        return {"message": f"Resource {resource_id} allocated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to allocate resource: {str(e)}")

# Time tracking endpoints
@router.post("/time-entries", response_model=TimeEntryResponse)
async def log_time(time_entry: TimeEntryCreate, db: Session = Depends(get_db)):
    """Log time entry"""
    try:
        entry_data = {
            "id": f"time_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "task_id": time_entry.task_id,
            "user_id": time_entry.user_id,
            "hours": time_entry.hours,
            "description": time_entry.description,
            "date": time_entry.date,
            "billable": time_entry.billable,
            "created_at": datetime.now()
        }
        
        print(f"Logged time entry: {entry_data['id']}")
        
        return TimeEntryResponse(**entry_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log time: {str(e)}")

# Analytics and reporting endpoints
@router.get("/{project_id}/analytics")
async def get_project_analytics(project_id: str, db: Session = Depends(get_db)):
    """Get project analytics and metrics"""
    try:
        analytics = {
            "project_id": project_id,
            "total_tasks": 25,
            "completed_tasks": 15,
            "in_progress_tasks": 8,
            "blocked_tasks": 2,
            "completion_rate": 60.0,
            "overdue_tasks": 3,
            "total_estimated_hours": 400.0,
            "total_actual_hours": 350.0,
            "efficiency": 87.5,
            "team_productivity": 85.0,
            "budget_utilization": 45.0,
            "milestone_completion": 75.0,
            "risk_score": 25.0
        }
        
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")

@router.post("/reports/generate")
async def generate_report(
    report_type: str,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Generate various types of reports"""
    try:
        report_data = {
            "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "type": report_type,
            "project_id": project_id,
            "generated_at": datetime.now(),
            "data": {}
        }
        
        # Generate different report types
        if report_type == "project_summary":
            report_data["data"] = {
                "overview": "Project summary statistics",
                "tasks": {"total": 25, "completed": 15, "in_progress": 8},
                "team": {"members": 5, "avg_workload": 75.0},
                "budget": {"allocated": 50000, "spent": 22500},
                "timeline": {"start": "2024-01-01", "end": "2024-06-30"}
            }
        elif report_type == "time_analysis":
            report_data["data"] = {
                "total_hours": 350.0,
                "billable_hours": 280.0,
                "efficiency": 87.5,
                "productivity_trend": "increasing"
            }
        elif report_type == "resource_utilization":
            report_data["data"] = {
                "human_resources": {"utilization": 80.0, "efficiency": 85.0},
                "equipment": {"utilization": 65.0, "availability": 35.0},
                "budget": {"utilization": 45.0, "remaining": 27500}
            }
        elif report_type == "progress_report":
            report_data["data"] = {
                "overall_progress": 65.0,
                "milestones_completed": 3,
                "milestones_total": 4,
                "tasks_completed": 15,
                "tasks_total": 25,
                "estimated_completion": "2024-06-15"
            }
        
        print(f"Generated report: {report_data['report_id']} of type: {report_type}")
        
        return report_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
