import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Avatar, AvatarImage, AvatarFallback } from '@/components/ui/avatar';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  MessageSquare, 
  Users, 
  TrendingUp, 
  Heart, 
  Share2, 
  Bookmark, 
  Flag, 
  Search,
  Filter,
  Plus,
  Edit,
  Trash2,
  Pin,
  Lock,
  Eye,
  ThumbsUp,
  MessageCircle,
  Award,
  Star,
  Bell,
  Settings
} from 'lucide-react';

interface User {
  id: string;
  username: string;
  displayName: string;
  avatar: string;
  email: string;
  bio: string;
  reputation: number;
  badges: Badge[];
  joinDate: string;
  lastActive: string;
  isOnline: boolean;
  role: 'admin' | 'moderator' | 'member' | 'guest';
  preferences: UserPreferences;
}

interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  earnedAt: string;
}

interface UserPreferences {
  emailNotifications: boolean;
  pushNotifications: boolean;
  theme: 'light' | 'dark' | 'auto';
  language: string;
  privacy: 'public' | 'friends' | 'private';
}

interface Forum {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  color: string;
  threads: number;
  posts: number;
  lastActivity: string;
  moderators: string[];
  isPrivate: boolean;
  tags: string[];
}

interface Thread {
  id: string;
  title: string;
  content: string;
  author: User;
  forum: string;
  category: string;
  tags: string[];
  views: number;
  replies: number;
  likes: number;
  isPinned: boolean;
  isLocked: boolean;
  isSolved: boolean;
  createdAt: string;
  updatedAt: string;
  lastReply: {
    author: string;
    timestamp: string;
  };
  poll?: Poll;
}

interface Post {
  id: string;
  content: string;
  author: User;
  thread: string;
  parent?: string;
  likes: number;
  dislikes: number;
  isAnswer: boolean;
  isEdited: boolean;
  createdAt: string;
  updatedAt: string;
  attachments: Attachment[];
  reactions: Reaction[];
}

interface Poll {
  id: string;
  question: string;
  options: PollOption[];
  isMultipleChoice: boolean;
  endsAt: string;
  totalVotes: number;
  userVoted: boolean;
}

interface PollOption {
  id: string;
  text: string;
  votes: number;
  percentage: number;
}

interface Attachment {
  id: string;
  name: string;
  url: string;
  type: string;
  size: number;
  thumbnail?: string;
}

interface Reaction {
  emoji: string;
  count: number;
  users: string[];
}

interface Notification {
  id: string;
  type: 'reply' | 'mention' | 'like' | 'follow' | 'badge' | 'moderation';
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
  data: any;
}

export default function CommunityForum() {
  const [activeTab, setActiveTab] = useState('forums');
  const [selectedForum, setSelectedForum] = useState<Forum | null>(null);
  const [selectedThread, setSelectedThread] = useState<Thread | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [forums, setForums] = useState<Forum[]>([]);
  const [threads, setThreads] = useState<Thread[]>([]);
  const [posts, setPosts] = useState<Post[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [sortBy, setSortBy] = useState('latest');
  const [showNewThreadModal, setShowNewThreadModal] = useState(false);
  const [showNewPostModal, setShowNewPostModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      // Load current user
      const userResponse = await fetch('/api/community/user/profile');
      if (userResponse.ok) {
        const userData = await userResponse.json();
        setCurrentUser(userData);
      }

      // Load forums
      const forumsResponse = await fetch('/api/community/forums');
      if (forumsResponse.ok) {
        const forumsData = await forumsResponse.json();
        setForums(forumsData);
      }

      // Load notifications
      const notifsResponse = await fetch('/api/community/notifications');
      if (notifsResponse.ok) {
        const notifsData = await notifsResponse.json();
        setNotifications(notifsData);
      }
    } catch (error) {
      console.error('Error loading initial data:', error);
    }
  };

  const createThread = async (threadData: Partial<Thread>) => {
    if (!currentUser || !selectedForum) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/community/threads', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...threadData,
          author: currentUser.id,
          forum: selectedForum.id
        })
      });

      if (response.ok) {
        const newThread = await response.json();
        setThreads([newThread, ...threads]);
        setShowNewThreadModal(false);
        setSelectedThread(newThread);
      }
    } catch (error) {
      console.error('Error creating thread:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const createPost = async (postData: Partial<Post>) => {
    if (!currentUser || !selectedThread) return;

    setIsLoading(true);
    try {
      const response = await fetch('/api/community/posts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...postData,
          author: currentUser.id,
          thread: selectedThread.id
        })
      });

      if (response.ok) {
        const newPost = await response.json();
        setPosts([newPost, ...posts]);
        setShowNewPostModal(false);
        
        // Update thread reply count
        const updatedThread = { ...selectedThread, replies: selectedThread.replies + 1 };
        setSelectedThread(updatedThread);
        setThreads(threads.map(t => t.id === selectedThread.id ? updatedThread : t));
      }
    } catch (error) {
      console.error('Error creating post:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const likePost = async (postId: string) => {
    try {
      const response = await fetch(`/api/community/posts/${postId}/like`, {
        method: 'POST'
      });

      if (response.ok) {
        setPosts(posts.map(p => 
          p.id === postId ? { ...p, likes: p.likes + 1 } : p
        ));
      }
    } catch (error) {
      console.error('Error liking post:', error);
    }
  };

  const followUser = async (userId: string) => {
    try {
      const response = await fetch(`/api/community/users/${userId}/follow`, {
        method: 'POST'
      });

      if (response.ok) {
        // Update user following status
        console.log(`Started following user: ${userId}`);
      }
    } catch (error) {
      console.error('Error following user:', error);
    }
  };

  const reportContent = async (contentType: string, contentId: string, reason: string) => {
    try {
      const response = await fetch('/api/community/moderation/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contentType,
          contentId,
          reason,
          reporter: currentUser?.id
        })
      });

      if (response.ok) {
        console.log(`Reported ${contentType}: ${contentId}`);
      }
    } catch (error) {
      console.error('Error reporting content:', error);
    }
  };

  const markNotificationRead = async (notificationId: string) => {
    try {
      await fetch(`/api/community/notifications/${notificationId}/read`, {
        method: 'PUT'
      });

      setNotifications(notifications.map(n => 
        n.id === notificationId ? { ...n, read: true } : n
      ));
    } catch (error) {
      console.error('Error marking notification as read:', error);
    }
  };

  const getFilteredThreads = () => {
    let filtered = [...threads];

    // Filter by selected forum
    if (selectedForum) {
      filtered = filtered.filter(t => t.forum === selectedForum.id);
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(t => t.category === selectedCategory);
    }

    // Filter by search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(t => 
        t.title.toLowerCase().includes(query) ||
        t.content.toLowerCase().includes(query) ||
        t.tags.some(tag => tag.toLowerCase().includes(query))
      );
    }

    // Sort threads
    switch (sortBy) {
      case 'latest':
        filtered.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
        break;
      case 'popular':
        filtered.sort((a, b) => (b.likes + b.replies) - (a.likes + a.replies));
        break;
      case 'views':
        filtered.sort((a, b) => b.views - a.views);
        break;
      case 'solved':
        filtered = filtered.filter(t => t.isSolved);
        break;
    }

    return filtered;
  };

  const getForumStats = (forum: Forum) => {
    const forumThreads = threads.filter(t => t.forum === forum.id);
    const totalPosts = forumThreads.reduce((sum, t) => sum + t.replies + 1, 0);
    const recentActivity = forumThreads.reduce((latest, t) => {
      const threadTime = new Date(t.updatedAt).getTime();
      return threadTime > latest ? threadTime : latest;
    }, 0);

    return {
      threads: forumThreads.length,
      posts: totalPosts,
      lastActivity: recentActivity > 0 ? new Date(recentActivity).toISOString() : null
    };
  };

  const getRoleColor = (role: string) => {
    switch (role) {
      case 'admin': return 'bg-red-500';
      case 'moderator': return 'bg-blue-500';
      case 'member': return 'bg-green-500';
      default: return 'bg-gray-500';
    }
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'reply': return <MessageCircle className="w-4 h-4" />;
      case 'mention': return <MessageSquare className="w-4 h-4" />;
      case 'like': return <Heart className="w-4 h-4" />;
      case 'follow': return <Users className="w-4 h-4" />;
      case 'badge': return <Award className="w-4 h-4" />;
      case 'moderation': return <Flag className="w-4 h-4" />;
      default: return <Bell className="w-4 h-4" />;
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Community Forum</h1>
        <div className="flex gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
            <Input
              placeholder="Search forums..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 w-64"
            />
          </div>
          <Button variant="outline">
            <Settings className="w-4 h-4 mr-2" />
            Settings
          </Button>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="forums">Forums</TabsTrigger>
          <TabsTrigger value="threads">Threads</TabsTrigger>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="notifications">
            Notifications
            {notifications.filter(n => !n.read).length > 0 && (
              <Badge className="ml-2 bg-red-500">
                {notifications.filter(n => !n.read).length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
        </TabsList>

        <TabsContent value="forums" className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex gap-2">
              <Select value={selectedCategory} onValueChange={setSelectedCategory}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Category" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Categories</SelectItem>
                  <SelectItem value="general">General</SelectItem>
                  <SelectItem value="support">Support</SelectItem>
                  <SelectItem value="feature-requests">Feature Requests</SelectItem>
                  <SelectItem value="announcements">Announcements</SelectItem>
                  <SelectItem value="off-topic">Off Topic</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Sort by" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="latest">Latest</SelectItem>
                  <SelectItem value="popular">Popular</SelectItem>
                  <SelectItem value="views">Most Viewed</SelectItem>
                  <SelectItem value="solved">Solved</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {selectedForum && (
              <Button onClick={() => setShowNewThreadModal(true)}>
                <Plus className="w-4 h-4 mr-2" />
                New Thread
              </Button>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Forums List */}
            <div className="lg:col-span-1">
              <Card>
                <CardHeader>
                  <CardTitle>Forums</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  {forums.map(forum => {
                    const stats = getForumStats(forum);
                    return (
                      <div
                        key={forum.id}
                        className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                          selectedForum?.id === forum.id 
                            ? 'border-blue-500 bg-blue-50' 
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                        onClick={() => setSelectedForum(forum)}
                      >
                        <div className="flex items-center gap-3 mb-2">
                          <div className={`w-10 h-10 rounded-lg flex items-center justify-center text-white ${forum.color}`}>
                            {forum.icon}
                          </div>
                          <div className="flex-1">
                            <h3 className="font-medium">{forum.name}</h3>
                            <p className="text-sm text-gray-600">{forum.description}</p>
                          </div>
                        </div>
                        <div className="flex justify-between text-xs text-gray-500">
                          <span>{stats.threads} threads</span>
                          <span>{stats.posts} posts</span>
                        </div>
                      </div>
                    );
                  })}
                </CardContent>
              </Card>
            </div>

            {/* Threads List */}
            <div className="lg:col-span-2">
              <Card>
                <CardHeader>
                  <CardTitle>
                    {selectedForum ? `${selectedForum.name} Threads` : 'All Threads'}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {getFilteredThreads().map(thread => (
                      <div
                        key={thread.id}
                        className="p-4 border rounded-lg hover:border-gray-300 cursor-pointer transition-colors"
                        onClick={() => setSelectedThread(thread)}
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-1">
                              {thread.isPinned && <Pin className="w-4 h-4 text-yellow-500" />}
                              {thread.isLocked && <Lock className="w-4 h-4 text-red-500" />}
                              {thread.isSolved && <CheckCircle className="w-4 h-4 text-green-500" />}
                              <h3 className="font-medium hover:text-blue-600">{thread.title}</h3>
                            </div>
                            <p className="text-sm text-gray-600 line-clamp-2">{thread.content}</p>
                          </div>
                          <div className="text-right">
                            <div className="flex items-center gap-1 text-sm text-gray-500">
                              <Eye className="w-4 h-4" />
                              {thread.views}
                            </div>
                          </div>
                        </div>
                        
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <div className="flex items-center gap-2">
                              <Avatar className="w-6 h-6">
                                <AvatarImage src={thread.author.avatar} />
                                <AvatarFallback>{thread.author.displayName.charAt(0)}</AvatarFallback>
                              </Avatar>
                              <span className="text-sm text-gray-600">{thread.author.displayName}</span>
                            </div>
                            <div className="flex items-center gap-1 text-sm text-gray-500">
                              <MessageCircle className="w-4 h-4" />
                              {thread.replies}
                            </div>
                            <div className="flex items-center gap-1 text-sm text-gray-500">
                              <ThumbsUp className="w-4 h-4" />
                              {thread.likes}
                            </div>
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(thread.updatedAt).toLocaleDateString()}
                          </div>
                        </div>

                        {thread.tags.length > 0 && (
                          <div className="flex gap-1 mt-2">
                            {thread.tags.map(tag => (
                              <Badge key={tag} variant="outline" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="threads" className="space-y-4">
          {selectedThread ? (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Thread Posts */}
              <div className="lg:col-span-3">
                <Card>
                  <CardHeader>
                    <CardTitle>{selectedThread.title}</CardTitle>
                    <div className="flex items-center gap-2">
                      {selectedThread.isPinned && <Pin className="w-4 h-4 text-yellow-500" />}
                      {selectedThread.isLocked && <Lock className="w-4 h-4 text-red-500" />}
                      {selectedThread.isSolved && <CheckCircle className="w-4 h-4 text-green-500" />}
                    </div>
                  </CardHeader>
                  <CardContent>
                    {/* Original Post */}
                    <div className="p-4 border rounded-lg mb-4">
                      <div className="flex items-start gap-3 mb-3">
                        <Avatar>
                          <AvatarImage src={selectedThread.author.avatar} />
                          <AvatarFallback>{selectedThread.author.displayName.charAt(0)}</AvatarFallback>
                        </Avatar>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-medium">{selectedThread.author.displayName}</span>
                            <Badge className={getRoleColor(selectedThread.author.role)}>
                              {selectedThread.author.role}
                            </Badge>
                            <span className="text-sm text-gray-500">
                              {new Date(selectedThread.createdAt).toLocaleDateString()}
                            </span>
                          </div>
                          <p className="text-gray-800">{selectedThread.content}</p>
                        </div>
                      </div>
                      
                      <div className="flex items-center gap-4 mt-4">
                        <Button variant="ghost" size="sm" onClick={() => likePost(selectedThread.id)}>
                          <ThumbsUp className="w-4 h-4 mr-1" />
                          {selectedThread.likes}
                        </Button>
                        <Button variant="ghost" size="sm">
                          <MessageCircle className="w-4 h-4 mr-1" />
                          Reply
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Bookmark className="w-4 h-4" />
                        </Button>
                        <Button variant="ghost" size="sm">
                          <Flag className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>

                    {/* Reply Posts */}
                    <div className="space-y-3">
                      {posts.filter(p => p.thread === selectedThread.id).map(post => (
                        <div key={post.id} className="p-4 border rounded-lg">
                          <div className="flex items-start gap-3 mb-3">
                            <Avatar>
                              <AvatarImage src={post.author.avatar} />
                              <AvatarFallback>{post.author.displayName.charAt(0)}</AvatarFallback>
                            </Avatar>
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <span className="font-medium">{post.author.displayName}</span>
                                <Badge className={getRoleColor(post.author.role)}>
                                  {post.author.role}
                                </Badge>
                                <span className="text-sm text-gray-500">
                                  {new Date(post.createdAt).toLocaleDateString()}
                                </span>
                                {post.isEdited && <span className="text-xs text-gray-500">(edited)</span>}
                                {post.isAnswer && <Badge className="bg-green-500">Answer</Badge>}
                              </div>
                              <p className="text-gray-800">{post.content}</p>
                            </div>
                          </div>
                          
                          <div className="flex items-center gap-4 mt-4">
                            <Button variant="ghost" size="sm" onClick={() => likePost(post.id)}>
                              <ThumbsUp className="w-4 h-4 mr-1" />
                              {post.likes}
                            </Button>
                            <Button variant="ghost" size="sm">
                              <MessageCircle className="w-4 h-4 mr-1" />
                              Reply
                            </Button>
                            <Button variant="ghost" size="sm">
                              <Flag className="w-4 h-4" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>

                    {/* Reply Form */}
                    <div className="mt-6">
                      <Button onClick={() => setShowNewPostModal(true)} className="w-full">
                        <Plus className="w-4 h-4 mr-2" />
                        Add Reply
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Thread Sidebar */}
              <div className="lg:col-span-1">
                <Card>
                  <CardHeader>
                    <CardTitle>Thread Info</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div>
                      <h4 className="font-medium mb-2">Statistics</h4>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span>Views:</span>
                          <span>{selectedThread.views}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Replies:</span>
                          <span>{selectedThread.replies}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Likes:</span>
                          <span>{selectedThread.likes}</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">Tags</h4>
                      <div className="flex flex-wrap gap-1">
                        {selectedThread.tags.map(tag => (
                          <Badge key={tag} variant="outline" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">Share</h4>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm">
                          <Share2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="p-8 text-center">
                <p className="text-gray-500">Select a thread to view posts</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="profile" className="space-y-4">
          {currentUser ? (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Profile Info */}
              <div className="lg:col-span-1">
                <Card>
                  <CardHeader>
                    <CardTitle>Profile</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="text-center">
                      <Avatar className="w-20 h-20 mx-auto mb-3">
                        <AvatarImage src={currentUser.avatar} />
                        <AvatarFallback>{currentUser.displayName.charAt(0)}</AvatarFallback>
                      </Avatar>
                      <h3 className="font-medium">{currentUser.displayName}</h3>
                      <p className="text-sm text-gray-600">@{currentUser.username}</p>
                      <Badge className={getRoleColor(currentUser.role)}>
                        {currentUser.role}
                      </Badge>
                    </div>
                    
                    <div>
                      <h4 className="font-medium mb-2">Bio</h4>
                      <p className="text-sm text-gray-600">{currentUser.bio}</p>
                    </div>
                    
                    <div>
                      <h4 className="font-medium mb-2">Statistics</h4>
                      <div className="space-y-1 text-sm">
                        <div className="flex justify-between">
                          <span>Reputation:</span>
                          <span>{currentUser.reputation}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Joined:</span>
                          <span>{new Date(currentUser.joinDate).toLocaleDateString()}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Last Active:</span>
                          <span>{new Date(currentUser.lastActive).toLocaleDateString()}</span>
                        </div>
                      </div>
                    </div>

                    <div>
                      <h4 className="font-medium mb-2">Badges</h4>
                      <div className="flex flex-wrap gap-2">
                        {currentUser.badges.map(badge => (
                          <div key={badge.id} className="flex items-center gap-1">
                            <span className={`text-lg ${badge.color}`}>{badge.icon}</span>
                            <span className="text-xs">{badge.name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Recent Activity */}
              <div className="lg:col-span-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Recent Activity</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      {threads.filter(t => t.author.id === currentUser.id).slice(0, 5).map(thread => (
                        <div key={thread.id} className="p-3 border rounded-lg">
                          <h4 className="font-medium hover:text-blue-600 cursor-pointer">{thread.title}</h4>
                          <p className="text-sm text-gray-600">{thread.content.substring(0, 100)}...</p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                            <span>{new Date(thread.createdAt).toLocaleDateString()}</span>
                            <span>{thread.replies} replies</span>
                            <span>{thread.views} views</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="p-8 text-center">
                <p className="text-gray-500">Please log in to view your profile</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="notifications" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {notifications.map(notification => (
                  <div
                    key={notification.id}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      notification.read ? 'bg-white' : 'bg-blue-50'
                    }`}
                    onClick={() => markNotificationRead(notification.id)}
                  >
                    <div className="flex items-start gap-3">
                      <div className="mt-1">
                        {getNotificationIcon(notification.type)}
                      </div>
                      <div className="flex-1">
                        <h4 className="font-medium">{notification.title}</h4>
                        <p className="text-sm text-gray-600">{notification.message}</p>
                        <span className="text-xs text-gray-500">
                          {new Date(notification.createdAt).toLocaleDateString()}
                        </span>
                      </div>
                      {!notification.read && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Community Analytics</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="text-2xl font-bold">{forums.length}</div>
                  <div className="text-sm text-gray-500">Total Forums</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">{threads.length}</div>
                  <div className="text-sm text-gray-500">Total Threads</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold">{posts.length}</div>
                  <div className="text-sm text-gray-500">Total Posts</div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
