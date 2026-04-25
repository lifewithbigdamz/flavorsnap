from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date
import json
import asyncio
from enum import Enum

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])

class NotificationType(str, Enum):
    TASK_ASSIGNED = "task_assigned"
    TASK_COMPLETED = "task_completed"
    TASK_OVERDUE = "task_overdue"
    PROJECT_UPDATE = "project_update"
    MILESTONE_REACHED = "milestone_reached"
    COMMENT_ADDED = "comment_added"
    FILE_SHARED = "file_shared"
    DEADLINE_REMINDER = "deadline_reminder"
    SYSTEM_ALERT = "system_alert"

class MessageType(str, Enum):
    TEXT = "text"
    FILE = "file"
    IMAGE = "image"
    LINK = "link"
    TASK_UPDATE = "task_update"
    PROJECT_UPDATE = "project_update"

# Pydantic models
class CommentBase(BaseModel):
    content: str
    author_id: str
    author_name: str
    task_id: Optional[str] = None
    project_id: Optional[str] = None

class CommentCreate(CommentBase):
    pass

class CommentResponse(CommentBase):
    id: str
    created_at: datetime
    updated_at: datetime
    replies: List['CommentResponse'] = []

class NotificationBase(BaseModel):
    title: str
    message: str
    type: NotificationType
    recipient_id: str
    data: Optional[Dict[str, Any]] = {}

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: str
    created_at: datetime
    read: bool = False

class MessageBase(BaseModel):
    content: str
    type: MessageType = MessageType.TEXT
    author_id: str
    channel_id: str

class MessageCreate(MessageBase):
    pass

class MessageResponse(MessageBase):
    id: str
    created_at: datetime
    author_name: str
    reactions: Dict[str, List[str]] = {}

class ChannelBase(BaseModel):
    name: str
    description: str
    type: str  # project, team, direct
    project_id: Optional[str] = None
    members: List[str] = []

class ChannelCreate(ChannelBase):
    pass

class ChannelResponse(ChannelBase):
    id: str
    created_at: datetime
    last_message: Optional[MessageResponse] = None
    unread_count: Dict[str, int] = {}

class ActivityBase(BaseModel):
    action: str
    entity_type: str
    entity_id: str
    user_id: str
    user_name: str
    details: Optional[Dict[str, Any]] = {}

class ActivityCreate(ActivityBase):
    pass

class ActivityResponse(ActivityBase):
    id: str
    created_at: datetime

class FileShareBase(BaseModel):
    name: str
    url: str
    size: int
    type: str
    uploaded_by: str
    uploaded_by_name: str
    project_id: Optional[str] = None
    task_id: Optional[str] = None

class FileShareCreate(FileShareBase):
    pass

class FileShareResponse(FileShareBase):
    id: str
    uploaded_at: datetime
    downloads: int = 0

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        self.user_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        if user_id in self.user_connections and self.user_connections[user_id] == websocket:
            del self.user_connections[user_id]

    async def send_personal_message(self, message: str, user_id: str):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    # Connection might be closed
                    pass

    async def broadcast_to_project(self, message: str, project_id: str, project_members: List[str]):
        for member_id in project_members:
            await self.send_personal_message(message, member_id)

    async def broadcast_to_channel(self, message: str, channel_id: str, channel_members: List[str]):
        for member_id in channel_members:
            await self.send_personal_message(message, member_id)

manager = ConnectionManager()

# Database dependency
def get_db():
    # This would be replaced with actual database session
    pass

# Notification endpoints
@router.post("/notifications", response_model=NotificationResponse)
async def create_notification(notification: NotificationCreate, db: Session = Depends(get_db)):
    """Create a new notification"""
    try:
        notification_data = {
            "id": f"notif_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "recipient_id": notification.recipient_id,
            "data": notification.data,
            "created_at": datetime.now(),
            "read": False
        }
        
        # Send real-time notification via WebSocket
        await manager.send_personal_message(
            json.dumps({
                "type": "notification",
                "data": notification_data
            }),
            notification.recipient_id
        )
        
        print(f"Created notification: {notification_data['id']} for user: {notification.recipient_id}")
        
        return NotificationResponse(**notification_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create notification: {str(e)}")

@router.get("/notifications/{user_id}", response_model=List[NotificationResponse])
async def get_notifications(
    user_id: str,
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get notifications for a user"""
    try:
        # Mock data for demonstration
        notifications = [
            {
                "id": "notif_001",
                "title": "Task Assigned",
                "message": "You have been assigned to 'Design Homepage'",
                "type": NotificationType.TASK_ASSIGNED,
                "recipient_id": user_id,
                "data": {"task_id": "task_001", "project_id": "proj_001"},
                "created_at": datetime.now(),
                "read": False
            },
            {
                "id": "notif_002",
                "title": "Project Update",
                "message": "Website Redesign project progress updated to 65%",
                "type": NotificationType.PROJECT_UPDATE,
                "recipient_id": user_id,
                "data": {"project_id": "proj_001", "progress": 65},
                "created_at": datetime.now(),
                "read": True
            }
        ]
        
        if unread_only:
            notifications = [n for n in notifications if not n["read"]]
        
        return [NotificationResponse(**n) for n in notifications[:limit]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch notifications: {str(e)}")

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, db: Session = Depends(get_db)):
    """Mark a notification as read"""
    try:
        print(f"Marked notification as read: {notification_id}")
        return {"message": "Notification marked as read"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")

# Comment endpoints
@router.post("/comments", response_model=CommentResponse)
async def create_comment(comment: CommentCreate, db: Session = Depends(get_db)):
    """Create a new comment"""
    try:
        comment_data = {
            "id": f"comment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "content": comment.content,
            "author_id": comment.author_id,
            "author_name": comment.author_name,
            "task_id": comment.task_id,
            "project_id": comment.project_id,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "replies": []
        }
        
        # Notify relevant users
        if comment.task_id:
            # Notify task assignee and project team
            await manager.send_personal_message(
                json.dumps({
                    "type": "comment_added",
                    "data": comment_data
                }),
                comment.author_id  # In real implementation, would notify task assignee
            )
        
        print(f"Created comment: {comment_data['id']}")
        
        return CommentResponse(**comment_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create comment: {str(e)}")

@router.get("/tasks/{task_id}/comments", response_model=List[CommentResponse])
async def get_task_comments(task_id: str, db: Session = Depends(get_db)):
    """Get comments for a task"""
    try:
        comments = [
            {
                "id": "comment_001",
                "content": "Great progress on this task!",
                "author_id": "user_001",
                "author_name": "John Doe",
                "task_id": task_id,
                "project_id": "proj_001",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "replies": []
            }
        ]
        
        return [CommentResponse(**c) for c in comments]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch comments: {str(e)}")

@router.get("/projects/{project_id}/comments", response_model=List[CommentResponse])
async def get_project_comments(project_id: str, db: Session = Depends(get_db)):
    """Get comments for a project"""
    try:
        comments = [
            {
                "id": "comment_002",
                "content": "Project is moving along nicely",
                "author_id": "user_002",
                "author_name": "Jane Smith",
                "task_id": None,
                "project_id": project_id,
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "replies": []
            }
        ]
        
        return [CommentResponse(**c) for c in comments]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch comments: {str(e)}")

# Chat/Channel endpoints
@router.post("/channels", response_model=ChannelResponse)
async def create_channel(channel: ChannelCreate, db: Session = Depends(get_db)):
    """Create a new chat channel"""
    try:
        channel_data = {
            "id": f"channel_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": channel.name,
            "description": channel.description,
            "type": channel.type,
            "project_id": channel.project_id,
            "members": channel.members,
            "created_at": datetime.now(),
            "last_message": None,
            "unread_count": {member: 0 for member in channel.members}
        }
        
        print(f"Created channel: {channel_data['id']}")
        
        return ChannelResponse(**channel_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create channel: {str(e)}")

@router.get("/channels/{user_id}", response_model=List[ChannelResponse])
async def get_user_channels(user_id: str, db: Session = Depends(get_db)):
    """Get channels for a user"""
    try:
        channels = [
            {
                "id": "channel_001",
                "name": "Website Redesign Team",
                "description": "General discussion for website redesign project",
                "type": "project",
                "project_id": "proj_001",
                "members": [user_id, "user_002", "user_003"],
                "created_at": datetime.now(),
                "last_message": {
                    "id": "msg_001",
                    "content": "Great work everyone!",
                    "type": MessageType.TEXT,
                    "author_id": "user_002",
                    "channel_id": "channel_001",
                    "created_at": datetime.now(),
                    "author_name": "Jane Smith",
                    "reactions": {"👍": [user_id]}
                },
                "unread_count": {user_id: 2}
            }
        ]
        
        return [ChannelResponse(**c) for c in channels]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch channels: {str(e)}")

@router.post("/channels/{channel_id}/messages", response_model=MessageResponse)
async def send_message(channel_id: str, message: MessageCreate, db: Session = Depends(get_db)):
    """Send a message to a channel"""
    try:
        message_data = {
            "id": f"msg_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "content": message.content,
            "type": message.type,
            "author_id": message.author_id,
            "channel_id": channel_id,
            "created_at": datetime.now(),
            "author_name": message.author_id,  # In real implementation, would fetch from user DB
            "reactions": {}
        }
        
        # Broadcast message to channel members
        # In real implementation, would fetch channel members from DB
        channel_members = [message.author_id, "user_002", "user_003"]
        await manager.broadcast_to_channel(
            json.dumps({
                "type": "new_message",
                "data": message_data
            }),
            channel_id,
            channel_members
        )
        
        print(f"Sent message: {message_data['id']} to channel: {channel_id}")
        
        return MessageResponse(**message_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")

@router.get("/channels/{channel_id}/messages", response_model=List[MessageResponse])
async def get_channel_messages(
    channel_id: str,
    limit: int = 50,
    before: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get messages for a channel"""
    try:
        messages = [
            {
                "id": "msg_001",
                "content": "Let's discuss the homepage design",
                "type": MessageType.TEXT,
                "author_id": "user_001",
                "channel_id": channel_id,
                "created_at": datetime.now(),
                "author_name": "John Doe",
                "reactions": {"👍": ["user_002"], "❤️": ["user_003"]}
            },
            {
                "id": "msg_002",
                "content": "I've uploaded the mockups",
                "type": MessageType.FILE,
                "author_id": "user_002",
                "channel_id": channel_id,
                "created_at": datetime.now(),
                "author_name": "Jane Smith",
                "reactions": {}
            }
        ]
        
        return [MessageResponse(**m) for m in messages[:limit]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch messages: {str(e)}")

# Activity feed endpoints
@router.post("/activities", response_model=ActivityResponse)
async def log_activity(activity: ActivityCreate, db: Session = Depends(get_db)):
    """Log a team activity"""
    try:
        activity_data = {
            "id": f"activity_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "action": activity.action,
            "entity_type": activity.entity_type,
            "entity_id": activity.entity_id,
            "user_id": activity.user_id,
            "user_name": activity.user_name,
            "details": activity.details,
            "created_at": datetime.now()
        }
        
        # Broadcast activity to project team
        if activity.entity_type == "project":
            # In real implementation, would fetch project members
            project_members = [activity.user_id, "user_002", "user_003"]
            await manager.broadcast_to_project(
                json.dumps({
                    "type": "activity",
                    "data": activity_data
                }),
                activity.entity_id,
                project_members
            )
        
        print(f"Logged activity: {activity_data['id']}")
        
        return ActivityResponse(**activity_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to log activity: {str(e)}")

@router.get("/projects/{project_id}/activities", response_model=List[ActivityResponse])
async def get_project_activities(
    project_id: str,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get activities for a project"""
    try:
        activities = [
            {
                "id": "activity_001",
                "action": "completed",
                "entity_type": "task",
                "entity_id": "task_001",
                "user_id": "user_001",
                "user_name": "John Doe",
                "details": {"task_title": "Design Homepage"},
                "created_at": datetime.now()
            },
            {
                "id": "activity_002",
                "action": "commented",
                "entity_type": "task",
                "entity_id": "task_002",
                "user_id": "user_002",
                "user_name": "Jane Smith",
                "details": {"task_title": "Implement Navigation"},
                "created_at": datetime.now()
            }
        ]
        
        return [ActivityResponse(**a) for a in activities[:limit]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch activities: {str(e)}")

# File sharing endpoints
@router.post("/files", response_model=FileShareResponse)
async def share_file(file_share: FileShareCreate, db: Session = Depends(get_db)):
    """Share a file with the team"""
    try:
        file_data = {
            "id": f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "name": file_share.name,
            "url": file_share.url,
            "size": file_share.size,
            "type": file_share.type,
            "uploaded_by": file_share.uploaded_by,
            "uploaded_by_name": file_share.uploaded_by_name,
            "project_id": file_share.project_id,
            "task_id": file_share.task_id,
            "uploaded_at": datetime.now(),
            "downloads": 0
        }
        
        # Notify team members
        if file_share.project_id:
            # In real implementation, would fetch project members
            project_members = [file_share.uploaded_by, "user_002", "user_003"]
            await manager.broadcast_to_project(
                json.dumps({
                    "type": "file_shared",
                    "data": file_data
                }),
                file_share.project_id,
                project_members
            )
        
        print(f"Shared file: {file_data['id']}")
        
        return FileShareResponse(**file_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to share file: {str(e)}")

@router.get("/projects/{project_id}/files", response_model=List[FileShareResponse])
async def get_project_files(project_id: str, db: Session = Depends(get_db)):
    """Get files shared for a project"""
    try:
        files = [
            {
                "id": "file_001",
                "name": "homepage-mockup.png",
                "url": "https://example.com/files/homepage-mockup.png",
                "size": 2048576,
                "type": "image/png",
                "uploaded_by": "user_001",
                "uploaded_by_name": "John Doe",
                "project_id": project_id,
                "task_id": "task_001",
                "uploaded_at": datetime.now(),
                "downloads": 5
            }
        ]
        
        return [FileShareResponse(**f) for f in files]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch files: {str(e)}")

@router.post("/files/{file_id}/download")
async def download_file(file_id: str, db: Session = Depends(get_db)):
    """Record a file download"""
    try:
        print(f"File downloaded: {file_id}")
        return {"message": "Download recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record download: {str(e)}")

# WebSocket endpoint for real-time collaboration
@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle different message types
            if message["type"] == "typing":
                # Broadcast typing indicator to channel
                await manager.broadcast_to_channel(
                    json.dumps({
                        "type": "typing",
                        "user_id": user_id,
                        "channel_id": message["channel_id"]
                    }),
                    message["channel_id"],
                    [user_id]  # In real implementation, would fetch channel members
                )
            elif message["type"] == "presence":
                # Update user presence status
                await manager.send_personal_message(
                    json.dumps({
                        "type": "presence_update",
                        "user_id": user_id,
                        "status": message["status"]
                    }),
                    user_id
                )
            
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
        # Broadcast user offline status
        await manager.broadcast_to_project(
            json.dumps({
                "type": "presence_update",
                "user_id": user_id,
                "status": "offline"
            }),
            "global",  # Broadcast to all projects user is part of
            [user_id]
        )

# Team presence endpoints
@router.get("/presence/{project_id}")
async def get_team_presence(project_id: str, db: Session = Depends(get_db)):
    """Get online status of team members"""
    try:
        # Mock presence data
        presence = {
            "project_id": project_id,
            "online_members": [
                {
                    "user_id": "user_001",
                    "name": "John Doe",
                    "status": "online",
                    "last_seen": datetime.now().isoformat()
                },
                {
                    "user_id": "user_002",
                    "name": "Jane Smith",
                    "status": "away",
                    "last_seen": (datetime.now().timestamp() - 900) * 1000  # 15 minutes ago
                }
            ],
            "offline_members": [
                {
                    "user_id": "user_003",
                    "name": "Bob Johnson",
                    "status": "offline",
                    "last_seen": (datetime.now().timestamp() - 3600) * 1000  # 1 hour ago
                }
            ]
        }
        
        return presence
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch presence data: {str(e)}")

# Integration endpoints
@router.post("/integrations/slack/webhook")
async def slack_webhook(webhook_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Handle Slack webhook for integration"""
    try:
        # Process Slack message and convert to internal format
        if webhook_data.get("type") == "message":
            message_data = {
                "content": webhook_data.get("text", ""),
                "author_name": webhook_data.get("user", "Slack User"),
                "channel_id": "slack_integration",
                "type": MessageType.TEXT
            }
            
            # Broadcast to relevant project/channel
            await manager.broadcast_to_project(
                json.dumps({
                    "type": "slack_message",
                    "data": message_data
                }),
                "proj_001",  # Would determine from webhook context
                ["user_001", "user_002"]
            )
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Slack webhook: {str(e)}")

@router.post("/integrations/teams/webhook")
async def teams_webhook(webhook_data: Dict[str, Any], db: Session = Depends(get_db)):
    """Handle Microsoft Teams webhook for integration"""
    try:
        # Process Teams message and convert to internal format
        if webhook_data.get("type") == "message":
            message_data = {
                "content": webhook_data.get("text", ""),
                "author_name": webhook_data.get("from", {}).get("user", {}).get("displayName", "Teams User"),
                "channel_id": "teams_integration",
                "type": MessageType.TEXT
            }
            
            # Broadcast to relevant project/channel
            await manager.broadcast_to_project(
                json.dumps({
                    "type": "teams_message",
                    "data": message_data
                }),
                "proj_001",  # Would determine from webhook context
                ["user_001", "user_002"]
            )
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process Teams webhook: {str(e)}")
