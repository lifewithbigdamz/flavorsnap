import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { user_id } = req.query;

    if (!user_id || typeof user_id !== 'string') {
      return res.status(400).json({ 
        error: 'Missing required parameter: user_id' 
      });
    }

    // In a real implementation, this would call the backend API
    // For now, we'll simulate the response
    
    // Simulate API call to backend
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/gdpr/export?user_id=${encodeURIComponent(user_id)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error('Failed to export user data');
    }

    const userData = await response.json();
    
    // Set headers for file download
    res.setHeader('Content-Type', 'application/json');
    res.setHeader('Content-Disposition', `attachment; filename="user_data_export_${new Date().toISOString().split('T')[0]}.json"`);
    
    res.status(200).json(userData);

  } catch (error) {
    console.error('Export API error:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: 'Failed to export user data'
    });
  }
}
