export interface User {
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

export interface Badge {
  id: string;
  name: string;
  description: string;
  icon: string;
  color: string;
  earnedAt: string;
}

export interface UserPreferences {
  emailNotifications: boolean;
  pushNotifications: boolean;
  theme: 'light' | 'dark' | 'auto';
  language: string;
  privacy: 'public' | 'friends' | 'private';
}

export interface Forum {
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

export interface Thread {
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

export interface Post {
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

export interface Poll {
  id: string;
  question: string;
  options: PollOption[];
  isMultipleChoice: boolean;
  endsAt: string;
  totalVotes: number;
  userVoted: boolean;
}

export interface PollOption {
  id: string;
  text: string;
  votes: number;
  percentage: number;
}

export interface Attachment {
  id: string;
  name: string;
  url: string;
  type: string;
  size: number;
  thumbnail?: string;
}

export interface Reaction {
  emoji: string;
  count: number;
  users: string[];
}

export interface Notification {
  id: string;
  type: 'reply' | 'mention' | 'like' | 'follow' | 'badge' | 'moderation';
  title: string;
  message: string;
  read: boolean;
  createdAt: string;
  data: any;
}
