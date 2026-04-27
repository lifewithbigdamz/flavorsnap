import { NextApiRequest, NextApiResponse } from 'next';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { user_id, consent_type, granted, ip_address, user_agent } = req.body;

    if (!user_id || !consent_type || typeof granted !== 'boolean') {
      return res.status(400).json({ 
        error: 'Missing required fields: user_id, consent_type, granted (boolean)' 
      });
    }

    // In a real implementation, this would call the backend API
    // For now, we'll simulate the response
    
    // Simulate API call to backend
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/gdpr/consent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        user_id,
        consent_type,
        granted,
        ip_address: ip_address || req.socket.remoteAddress,
        user_agent: user_agent || req.headers['user-agent']
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to store consent');
    }

    const result = await response.json();
    
    res.status(200).json({ 
      success: true,
      message: `Consent for ${consent_type} ${granted ? 'granted' : 'revoked'} successfully`,
      ...result
    });

  } catch (error) {
    console.error('Consent API error:', error);
    res.status(500).json({ 
      error: 'Internal server error',
      message: 'Failed to update consent'
    });
  }
}
