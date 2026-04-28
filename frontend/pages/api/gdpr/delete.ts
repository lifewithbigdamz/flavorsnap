import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'DELETE') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { user_id } = req.body;

    if (!user_id) {
      return res.status(400).json({ 
        error: 'Missing required field: user_id' 
      });
    }

    // In a real implementation, this would call the backend API
    // For now, we'll simulate the response
    
    // Simulate API call to backend
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/gdpr/delete`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to delete user data');
    }

    const result = await response.json();
    
    res.status(200).json({ 
      success: true,
      message: 'User data deleted successfully',
      deletion_counts: result
    });

  } catch (error) {
    console.error('Delete API error:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: 'Failed to delete user data'
    });
  }
}
