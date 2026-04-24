from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, date
import json
import uuid

router = APIRouter(prefix="/api/community", tags=["community"])

# Pydantic models
class UserBase(BaseModel):
    username: str
    display_name: str
    email: str
    bio: str = ""
    avatar: str = ""
    role: str = "member"

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    avatar: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

class UserResponse(UserBase):
    id: str
    reputation: int = 0
    badges: List[Dict[str, Any]] = []
    join_date: datetime
    last_active: datetime
    is_online: bool = False
    preferences: Dict[str, Any] = {}

class ForumBase(BaseModel):
    name: str
    description: str
    category: str
    icon: str = "📁"
    color: str = "bg-blue-500"
    is_private: bool = False
    tags: List[str] = []

class ForumCreate(ForumBase):
    moderators: List[str] = []

class ForumUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_private: Optional[bool] = None
    moderators: Optional[List[str]] = None

class ForumResponse(ForumBase):
    id: str
    threads: int = 0
    posts: int = 0
    last_activity: Optional[datetime] = None
    moderators: List[str] = []
    created_at: datetime

class ThreadBase(BaseModel):
    title: str
    content: str
    forum_id: str
    tags: List[str] = []
    is_pinned: bool = False
    is_locked: bool = False

class ThreadCreate(ThreadBase):
    pass

class ThreadUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    is_pinned: Optional[bool] = None
    is_locked: Optional[bool] = None
    is_solved: Optional[bool] = None

class ThreadResponse(ThreadBase):
    id: str
    author_id: str
    author: UserResponse
    forum: str
    category: str
    views: int = 0
    replies: int = 0
    likes: int = 0
    is_solved: bool = False
    created_at: datetime
    updated_at: datetime
    last_reply: Dict[str, Any] = {}

class PostBase(BaseModel):
    content: str
    thread_id: str
    parent_id: Optional[str] = None

class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    content: Optional[str] = None
    is_answer: Optional[bool] = None

class PostResponse(PostBase):
    id: str
    author_id: str
    author: UserResponse
    thread: str
    likes: int = 0
    dislikes: int = 0
    is_answer: bool = False
    is_edited: bool = False
    created_at: datetime
    updated_at: datetime
    attachments: List[Dict[str, Any]] = []
    reactions: Dict[str, List[str]] = {}

class BadgeBase(BaseModel):
    name: str
    description: str
    icon: str = "🏆"
    color: str = "text-yellow-500"

class BadgeCreate(BadgeBase):
    user_id: str

class BadgeResponse(BadgeBase):
    id: str
    earned_at: datetime

class NotificationBase(BaseModel):
    type: str
    title: str
    message: str
    recipient_id: str
    data: Optional[Dict[str, Any]] = {}

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: str
    created_at: datetime
    read: bool = False

# Database dependency
def get_db():
    # This would be replaced with actual database session
    pass

# User endpoints
@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    try:
        user_data = {
            "id": f"user_{uuid.uuid4().hex[:8]}",
            "username": user.username,
            "display_name": user.display_name,
            "email": user.email,
            "bio": user.bio,
            "avatar": user.avatar,
            "role": user.role,
            "reputation": 0,
            "badges": [],
            "join_date": datetime.now(),
            "last_active": datetime.now(),
            "is_online": False,
            "preferences": {
                "email_notifications": True,
                "push_notifications": True,
                "theme": "light",
                "language": "en",
                "privacy": "public"
            }
        }
        
        print(f"Created user: {user_data['id']} - {user.username}")
        
        return UserResponse(**user_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user: {str(e)}")

@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """Get user profile"""
    try:
        # Mock data for demonstration
        user_data = {
            "id": user_id,
            "username": "johndoe",
            "display_name": "John Doe",
            "email": "john@example.com",
            "bio": "Passionate developer and community member",
            "avatar": "https://example.com/avatar.jpg",
            "role": "member",
            "reputation": 1250,
            "badges": [
                {
                    "id": "badge_001",
                    "name": "First Post",
                    "description": "Created your first post",
                    "icon": "🎉",
                    "color": "text-blue-500",
                    "earned_at": datetime.now()
                }
            ],
            "join_date": datetime(2024, 1, 15),
            "last_active": datetime.now(),
            "is_online": True,
            "preferences": {
                "email_notifications": True,
                "push_notifications": True,
                "theme": "light",
                "language": "en",
                "privacy": "public"
            }
        }
        
        return UserResponse(**user_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch user: {str(e)}")

@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update user profile"""
    try:
        # Get existing user
        existing_user = await get_user(user_id, db)
        
        # Update fields
        update_data = user_update.dict(exclude_unset=True)
        updated_user = existing_user.dict()
        updated_user.update(update_data)
        updated_user["last_active"] = datetime.now()
        
        print(f"Updated user: {user_id}")
        
        return UserResponse(**updated_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

@router.post("/users/{user_id}/follow")
async def follow_user(user_id: str, current_user_id: str, db: Session = Depends(get_db)):
    """Follow a user"""
    try:
        print(f"User {current_user_id} followed user {user_id}")
        return {"message": f"Successfully followed user {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to follow user: {str(e)}")

@router.delete("/users/{user_id}/follow")
async def unfollow_user(user_id: str, current_user_id: str, db: Session = Depends(get_db)):
    """Unfollow a user"""
    try:
        print(f"User {current_user_id} unfollowed user {user_id}")
        return {"message": f"Successfully unfollowed user {user_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unfollow user: {str(e)}")

# Forum endpoints
@router.get("/forums", response_model=List[ForumResponse])
async def get_forums(
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all forums"""
    try:
        forums = [
            {
                "id": "forum_001",
                "name": "General Discussion",
                "description": "General community discussions",
                "category": "general",
                "icon": "💬",
                "color": "bg-blue-500",
                "is_private": False,
                "tags": ["general", "discussion"],
                "threads": 150,
                "posts": 1250,
                "last_activity": datetime.now(),
                "moderators": ["mod_001", "mod_002"],
                "created_at": datetime(2024, 1, 1)
            },
            {
                "id": "forum_002",
                "name": "Technical Support",
                "description": "Get help with technical issues",
                "category": "support",
                "icon": "🛠️",
                "color": "bg-green-500",
                "is_private": False,
                "tags": ["support", "technical"],
                "threads": 89,
                "posts": 567,
                "last_activity": datetime.now(),
                "moderators": ["mod_001"],
                "created_at": datetime(2024, 1, 1)
            }
        ]
        
        # Filter by category if provided
        if category:
            forums = [f for f in forums if f["category"] == category]
        
        # Apply pagination
        paginated_forums = forums[skip:skip + limit]
        
        return [ForumResponse(**f) for f in paginated_forums]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch forums: {str(e)}")

@router.post("/forums", response_model=ForumResponse)
async def create_forum(forum: ForumCreate, db: Session = Depends(get_db)):
    """Create a new forum"""
    try:
        forum_data = {
            "id": f"forum_{uuid.uuid4().hex[:8]}",
            "name": forum.name,
            "description": forum.description,
            "category": forum.category,
            "icon": forum.icon,
            "color": forum.color,
            "is_private": forum.is_private,
            "tags": forum.tags,
            "threads": 0,
            "posts": 0,
            "last_activity": None,
            "moderators": forum.moderators,
            "created_at": datetime.now()
        }
        
        print(f"Created forum: {forum_data['id']} - {forum.name}")
        
        return ForumResponse(**forum_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create forum: {str(e)}")

@router.get("/forums/{forum_id}", response_model=ForumResponse)
async def get_forum(forum_id: str, db: Session = Depends(get_db)):
    """Get a specific forum"""
    try:
        forums = await get_forums(db=db)
        forum = next((f for f in forums if f.id == forum_id), None)
        
        if not forum:
            raise HTTPException(status_code=404, detail="Forum not found")
        
        return forum
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch forum: {str(e)}")

# Thread endpoints
@router.get("/threads", response_model=List[ThreadResponse])
async def get_threads(
    forum_id: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sort_by: str = Query("latest", regex="^(latest|popular|views|solved)$"),
    db: Session = Depends(get_db)
):
    """Get threads"""
    try:
        threads = [
            {
                "id": "thread_001",
                "title": "Welcome to the community!",
                "content": "Introduce yourself and say hello to other members.",
                "forum_id": "forum_001",
                "forum": "General Discussion",
                "category": "general",
                "tags": ["welcome", "introduction"],
                "is_pinned": True,
                "is_locked": False,
                "author_id": "user_001",
                "author": {
                    "id": "user_001",
                    "username": "admin",
                    "display_name": "Community Admin",
                    "email": "admin@example.com",
                    "bio": "Community administrator",
                    "avatar": "",
                    "role": "admin",
                    "reputation": 5000,
                    "badges": [],
                    "join_date": datetime(2024, 1, 1),
                    "last_active": datetime.now(),
                    "is_online": True,
                    "preferences": {}
                },
                "views": 1250,
                "replies": 89,
                "likes": 45,
                "is_solved": False,
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime.now(),
                "last_reply": {
                    "author": "user_002",
                    "timestamp": datetime.now().isoformat()
                }
            },
            {
                "id": "thread_002",
                "title": "How to get started with development?",
                "content": "Looking for tips on getting started with web development.",
                "forum_id": "forum_002",
                "forum": "Technical Support",
                "category": "support",
                "tags": ["development", "beginner"],
                "is_pinned": False,
                "is_locked": False,
                "author_id": "user_002",
                "author": {
                    "id": "user_002",
                    "username": "newbie",
                    "display_name": "New Developer",
                    "email": "newbie@example.com",
                    "bio": "Learning to code",
                    "avatar": "",
                    "role": "member",
                    "reputation": 50,
                    "badges": [],
                    "join_date": datetime(2024, 2, 1),
                    "last_active": datetime.now(),
                    "is_online": False,
                    "preferences": {}
                },
                "views": 342,
                "replies": 23,
                "likes": 12,
                "is_solved": True,
                "created_at": datetime(2024, 2, 15),
                "updated_at": datetime.now(),
                "last_reply": {
                    "author": "user_003",
                    "timestamp": datetime.now().isoformat()
                }
            }
        ]
        
        # Filter by forum_id if provided
        if forum_id:
            threads = [t for t in threads if t.forum_id == forum_id]
        
        # Filter by category if provided
        if category:
            threads = [t for t in threads if t.category == category]
        
        # Sort threads
        if sort_by == "latest":
            threads.sort(key=lambda x: x.updated_at, reverse=True)
        elif sort_by == "popular":
            threads.sort(key=lambda x: x.likes + x.replies, reverse=True)
        elif sort_by == "views":
            threads.sort(key=lambda x: x.views, reverse=True)
        elif sort_by == "solved":
            threads = [t for t in threads if t.is_solved]
        
        # Apply pagination
        paginated_threads = threads[skip:skip + limit]
        
        return [ThreadResponse(**t) for t in paginated_threads]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch threads: {str(e)}")

@router.post("/threads", response_model=ThreadResponse)
async def create_thread(thread: ThreadCreate, author_id: str, db: Session = Depends(get_db)):
    """Create a new thread"""
    try:
        thread_data = {
            "id": f"thread_{uuid.uuid4().hex[:8]}",
            "title": thread.title,
            "content": thread.content,
            "forum_id": thread.forum_id,
            "forum": "General Discussion",  # Would fetch from forum
            "category": "general",  # Would fetch from forum
            "tags": thread.tags,
            "is_pinned": thread.is_pinned,
            "is_locked": thread.is_locked,
            "author_id": author_id,
            "author": await get_user(author_id, db),
            "views": 0,
            "replies": 0,
            "likes": 0,
            "is_solved": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "last_reply": {}
        }
        
        print(f"Created thread: {thread_data['id']} - {thread.title}")
        
        return ThreadResponse(**thread_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create thread: {str(e)}")

@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(thread_id: str, db: Session = Depends(get_db)):
    """Get a specific thread"""
    try:
        threads = await get_threads(db=db)
        thread = next((t for t in threads if t.id == thread_id), None)
        
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # Increment view count
        thread.views += 1
        
        return thread
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch thread: {str(e)}")

@router.put("/threads/{thread_id}", response_model=ThreadResponse)
async def update_thread(thread_id: str, thread_update: ThreadUpdate, db: Session = Depends(get_db)):
    """Update a thread"""
    try:
        # Get existing thread
        existing_thread = await get_thread(thread_id, db)
        
        # Update fields
        update_data = thread_update.dict(exclude_unset=True)
        updated_thread = existing_thread.dict()
        updated_thread.update(update_data)
        updated_thread["updated_at"] = datetime.now()
        
        print(f"Updated thread: {thread_id}")
        
        return ThreadResponse(**updated_thread)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update thread: {str(e)}")

# Post endpoints
@router.get("/threads/{thread_id}/posts", response_model=List[PostResponse])
async def get_thread_posts(
    thread_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get posts for a thread"""
    try:
        posts = [
            {
                "id": "post_001",
                "content": "Welcome everyone! Feel free to introduce yourselves here.",
                "thread_id": thread_id,
                "author_id": "user_001",
                "author": {
                    "id": "user_001",
                    "username": "admin",
                    "display_name": "Community Admin",
                    "email": "admin@example.com",
                    "bio": "Community administrator",
                    "avatar": "",
                    "role": "admin",
                    "reputation": 5000,
                    "badges": [],
                    "join_date": datetime(2024, 1, 1),
                    "last_active": datetime.now(),
                    "is_online": True,
                    "preferences": {}
                },
                "thread": thread_id,
                "likes": 15,
                "dislikes": 0,
                "is_answer": False,
                "is_edited": False,
                "created_at": datetime(2024, 1, 1),
                "updated_at": datetime(2024, 1, 1),
                "attachments": [],
                "reactions": {"👍": ["user_002", "user_003"], "❤️": ["user_004"]}
            },
            {
                "id": "post_002",
                "content": "Hi everyone! I'm excited to be part of this community.",
                "thread_id": thread_id,
                "author_id": "user_002",
                "author": {
                    "id": "user_002",
                    "username": "newbie",
                    "display_name": "New Developer",
                    "email": "newbie@example.com",
                    "bio": "Learning to code",
                    "avatar": "",
                    "role": "member",
                    "reputation": 50,
                    "badges": [],
                    "join_date": datetime(2024, 2, 1),
                    "last_active": datetime.now(),
                    "is_online": False,
                    "preferences": {}
                },
                "thread": thread_id,
                "likes": 8,
                "dislikes": 0,
                "is_answer": False,
                "is_edited": False,
                "created_at": datetime(2024, 2, 1),
                "updated_at": datetime(2024, 2, 1),
                "attachments": [],
                "reactions": {"👋": ["user_001"]}
            }
        ]
        
        # Apply pagination
        paginated_posts = posts[skip:skip + limit]
        
        return [PostResponse(**p) for p in paginated_posts]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch posts: {str(e)}")

@router.post("/threads/{thread_id}/posts", response_model=PostResponse)
async def create_post(thread_id: str, post: PostCreate, author_id: str, db: Session = Depends(get_db)):
    """Create a new post"""
    try:
        post_data = {
            "id": f"post_{uuid.uuid4().hex[:8]}",
            "content": post.content,
            "thread_id": thread_id,
            "author_id": author_id,
            "author": await get_user(author_id, db),
            "thread": thread_id,
            "likes": 0,
            "dislikes": 0,
            "is_answer": False,
            "is_edited": False,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "attachments": [],
            "reactions": {}
        }
        
        print(f"Created post: {post_data['id']} in thread: {thread_id}")
        
        return PostResponse(**post_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create post: {str(e)}")

@router.put("/posts/{post_id}/like")
async def like_post(post_id: str, user_id: str, db: Session = Depends(get_db)):
    """Like a post"""
    try:
        print(f"User {user_id} liked post {post_id}")
        return {"message": "Post liked successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to like post: {str(e)}")

@router.put("/posts/{post_id}/answer")
async def mark_post_as_answer(post_id: str, user_id: str, db: Session = Depends(get_db)):
    """Mark a post as the answer to its thread"""
    try:
        print(f"Post {post_id} marked as answer by user {user_id}")
        return {"message": "Post marked as answer"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark post as answer: {str(e)}")

# Badge endpoints
@router.post("/badges", response_model=BadgeResponse)
async def create_badge(badge: BadgeCreate, db: Session = Depends(get_db)):
    """Award a badge to a user"""
    try:
        badge_data = {
            "id": f"badge_{uuid.uuid4().hex[:8]}",
            "name": badge.name,
            "description": badge.description,
            "icon": badge.icon,
            "color": badge.color,
            "earned_at": datetime.now()
        }
        
        print(f"Awarded badge {badge_data['id']} to user {badge.user_id}")
        
        return BadgeResponse(**badge_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to award badge: {str(e)}")

@router.get("/users/{user_id}/badges", response_model=List[BadgeResponse])
async def get_user_badges(user_id: str, db: Session = Depends(get_db)):
    """Get badges for a user"""
    try:
        badges = [
            {
                "id": "badge_001",
                "name": "First Post",
                "description": "Created your first post",
                "icon": "🎉",
                "color": "text-blue-500",
                "earned_at": datetime(2024, 2, 1)
            },
            {
                "id": "badge_002",
                "name": "Helpful",
                "description": "Received 10 likes on posts",
                "icon": "👍",
                "color": "text-green-500",
                "earned_at": datetime(2024, 2, 15)
            }
        ]
        
        return [BadgeResponse(**b) for b in badges]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch badges: {str(e)}")

# Notification endpoints
@router.get("/notifications", response_model=List[NotificationResponse])
async def get_notifications(
    user_id: str,
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get notifications for a user"""
    try:
        notifications = [
            {
                "id": "notif_001",
                "type": "reply",
                "title": "New Reply",
                "message": "Someone replied to your thread",
                "recipient_id": user_id,
                "data": {"thread_id": "thread_001"},
                "created_at": datetime.now(),
                "read": False
            },
            {
                "id": "notif_002",
                "type": "like",
                "title": "Post Liked",
                "message": "Your post received a like",
                "recipient_id": user_id,
                "data": {"post_id": "post_001"},
                "created_at": datetime.now(),
                "read": True
            }
        ]
        
        if unread_only:
            notifications = [n for n in notifications if not n.read]
        
        return [NotificationResponse(**n) for n in notifications[:limit]]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch notifications: {str(e)}")

@router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, db: Session = Depends(get_db)):
    """Mark a notification as read"""
    try:
        print(f"Marked notification {notification_id} as read")
        return {"message": "Notification marked as read"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to mark notification as read: {str(e)}")

# Analytics endpoints
@router.get("/analytics")
async def get_community_analytics(db: Session = Depends(get_db)):
    """Get community analytics"""
    try:
        analytics = {
            "total_users": 1250,
            "active_users": 342,
            "total_forums": 8,
            "total_threads": 1567,
            "total_posts": 12450,
            "posts_today": 45,
            "new_users_today": 12,
            "top_forums": [
                {"name": "General Discussion", "posts": 5678},
                {"name": "Technical Support", "posts": 3421},
                {"name": "Feature Requests", "posts": 2156}
            ],
            "user_growth": [
                {"date": "2024-01-01", "users": 1000},
                {"date": "2024-01-02", "users": 1012},
                {"date": "2024-01-03", "users": 1025}
            ],
            "engagement_metrics": {
                "avg_posts_per_user": 9.96,
                "avg_likes_per_post": 3.4,
                "thread_resolution_rate": 0.67
            }
        }
        
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch analytics: {str(e)}")

# Search endpoints
@router.get("/search")
async def search_community(
    q: str = Query(..., min_length=1),
    type: str = Query("all", regex="^(all|threads|posts|users|forums)$"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search community content"""
    try:
        results = {
            "threads": [],
            "posts": [],
            "users": [],
            "forums": []
        }
        
        if type in ["all", "threads"]:
            # Search threads
            threads = await get_threads(db=db)
            results["threads"] = [
                {
                    "id": t.id,
                    "title": t.title,
                    "content": t.content[:200] + "...",
                    "author": t.author.display_name,
                    "forum": t.forum,
                    "replies": t.replies,
                    "likes": t.likes,
                    "created_at": t.created_at
                }
                for t in threads 
                if q.lower() in t.title.lower() or q.lower() in t.content.lower()
            ][:limit]
        
        if type in ["all", "users"]:
            # Search users
            users = [
                {
                    "id": "user_001",
                    "username": "johndoe",
                    "display_name": "John Doe",
                    "bio": "Passionate developer",
                    "reputation": 1250,
                    "role": "member"
                }
            ]
            results["users"] = [
                u for u in users 
                if q.lower() in u["username"].lower() or q.lower() in u["display_name"].lower()
            ][:limit]
        
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to search: {str(e)}")
