import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';

interface ConsentRecord {
  consent_type: string;
  granted: boolean;
  timestamp: string;
  ip_address?: string;
  user_agent?: string;
}

interface UserDataExport {
  user_id: string;
  export_timestamp: string;
  prediction_history: any[];
  consent_records: ConsentRecord[];
}

export default function PrivacyPolicy() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error' | 'info'>('info');
  const [userConsents, setUserConsents] = useState<ConsentRecord[]>([]);
  const [showConsentManagement, setShowConsentManagement] = useState(false);

  useEffect(() => {
    // Load user consents when component mounts
    loadUserConsents();
  }, []);

  const showMessage = (msg: string, type: 'success' | 'error' | 'info') => {
    setMessage(msg);
    setMessageType(type);
    setTimeout(() => setMessage(''), 5000);
  };

  const loadUserConsents = async () => {
    try {
      const response = await fetch('/api/gdpr/consent?user_id=current_user');
      if (response.ok) {
        const data = await response.json();
        setUserConsents(data.consents || []);
      }
    } catch (error) {
      console.error('Failed to load user consents:', error);
    }
  };

  const updateConsent = async (consentType: string, granted: boolean) => {
    setLoading(true);
    try {
      const response = await fetch('/api/gdpr/consent', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: 'current_user',
          consent_type: consentType,
          granted: granted,
          ip_address: 'client_ip', // This would be set by server
          user_agent: navigator.userAgent
        }),
      });

      if (response.ok) {
        showMessage(`Consent for ${consentType} ${granted ? 'granted' : 'revoked'} successfully`, 'success');
        loadUserConsents();
      } else {
        showMessage('Failed to update consent', 'error');
      }
    } catch (error) {
      showMessage('Error updating consent', 'error');
    } finally {
      setLoading(false);
    }
  };

  const exportUserData = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/gdpr/export?user_id=current_user');
      if (response.ok) {
        const data: UserDataExport = await response.json();
        
        // Create and download JSON file
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `user_data_export_${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showMessage('Your data has been exported successfully', 'success');
      } else {
        showMessage('Failed to export data', 'error');
      }
    } catch (error) {
      showMessage('Error exporting data', 'error');
    } finally {
      setLoading(false);
    }
  };

  const deleteUserData = async () => {
    const confirmed = window.confirm(
      'Are you sure you want to delete all your data? This action cannot be undone and will permanently remove all your prediction history and consent records.'
    );

    if (!confirmed) return;

    setLoading(true);
    try {
      const response = await fetch('/api/gdpr/delete', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: 'current_user'
        }),
      });

      if (response.ok) {
        const result = await response.json();
        showMessage(`Successfully deleted: ${JSON.stringify(result)}`, 'success');
        setUserConsents([]);
      } else {
        showMessage('Failed to delete data', 'error');
      }
    } catch (error) {
      showMessage('Error deleting data', 'error');
    } finally {
      setLoading(false);
    }
  };

  const getConsentStatus = (consentType: string) => {
    const consent = userConsents.find(c => c.consent_type === consentType);
    return consent ? consent.granted : false;
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-white shadow-lg rounded-lg p-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-8">Privacy Policy & GDPR Rights</h1>

          {/* Message Display */}
          {message && (
            <div className={`mb-6 p-4 rounded-md ${
              messageType === 'success' ? 'bg-green-50 text-green-800 border border-green-200' :
              messageType === 'error' ? 'bg-red-50 text-red-800 border border-red-200' :
              'bg-blue-50 text-blue-800 border border-blue-200'
            }`}>
              {message}
            </div>
          )}

          {/* GDPR Rights Section */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Your GDPR Rights</h2>
            <div className="space-y-4 text-gray-600">
              <p>
                Under the General Data Protection Regulation (GDPR), you have the following rights regarding your personal data:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong>Right to Access:</strong> You can request a copy of your personal data</li>
                <li><strong>Right to Rectification:</strong> You can request correction of inaccurate data</li>
                <li><strong>Right to Erasure:</strong> You can request deletion of your personal data</li>
                <li><strong>Right to Portability:</strong> You can request your data in a machine-readable format</li>
                <li><strong>Right to Withdraw Consent:</strong> You can withdraw your consent at any time</li>
              </ul>
            </div>
          </div>

          {/* Data We Collect */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Data We Collect</h2>
            <div className="space-y-4 text-gray-600">
              <p>We collect the following types of data:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li><strong>Prediction History:</strong> Images you've analyzed, prediction results, and timestamps</li>
                <li><strong>Technical Data:</strong> IP address, user agent, and processing times</li>
                <li><strong>Consent Records:</strong> Your privacy preferences and consent history</li>
              </ul>
            </div>
          </div>

          {/* Consent Management */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Consent Management</h2>
            <button
              onClick={() => setShowConsentManagement(!showConsentManagement)}
              className="mb-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
            >
              {showConsentManagement ? 'Hide' : 'Show'} Consent Settings
            </button>

            {showConsentManagement && (
              <div className="border border-gray-200 rounded-lg p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">Analytics Tracking</h3>
                    <p className="text-sm text-gray-600">Allow us to collect anonymous usage analytics</p>
                  </div>
                  <button
                    onClick={() => updateConsent('analytics', !getConsentStatus('analytics'))}
                    disabled={loading}
                    className={`px-4 py-2 rounded-md transition-colors ${
                      getConsentStatus('analytics')
                        ? 'bg-green-600 text-white hover:bg-green-700'
                        : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
                    }`}
                  >
                    {getConsentStatus('analytics') ? 'Granted' : 'Revoked'}
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">Marketing Communications</h3>
                    <p className="text-sm text-gray-600">Allow us to send you marketing emails</p>
                  </div>
                  <button
                    onClick={() => updateConsent('marketing', !getConsentStatus('marketing'))}
                    disabled={loading}
                    className={`px-4 py-2 rounded-md transition-colors ${
                      getConsentStatus('marketing')
                        ? 'bg-green-600 text-white hover:bg-green-700'
                        : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
                    }`}
                  >
                    {getConsentStatus('marketing') ? 'Granted' : 'Revoked'}
                  </button>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-medium text-gray-900">Data Processing</h3>
                    <p className="text-sm text-gray-600">Allow processing of your images for food classification</p>
                  </div>
                  <button
                    onClick={() => updateConsent('data_processing', !getConsentStatus('data_processing'))}
                    disabled={loading}
                    className={`px-4 py-2 rounded-md transition-colors ${
                      getConsentStatus('data_processing')
                        ? 'bg-green-600 text-white hover:bg-green-700'
                        : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
                    }`}
                  >
                    {getConsentStatus('data_processing') ? 'Granted' : 'Revoked'}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* GDPR Actions */}
          <div className="mb-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Exercise Your Rights</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <button
                onClick={exportUserData}
                disabled={loading}
                className="px-6 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
              >
                {loading ? 'Processing...' : 'Export My Data'}
              </button>
              
              <button
                onClick={deleteUserData}
                disabled={loading}
                className="px-6 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:bg-gray-400 transition-colors"
              >
                {loading ? 'Processing...' : 'Delete My Data'}
              </button>
            </div>
            <p className="mt-4 text-sm text-gray-500">
              Data export will be downloaded as a JSON file. Data deletion is permanent and cannot be undone.
            </p>
          </div>

          {/* Contact Information */}
          <div className="border-t border-gray-200 pt-8">
            <h2 className="text-2xl font-semibold text-gray-800 mb-4">Contact Us</h2>
            <div className="text-gray-600">
              <p>If you have any questions about this Privacy Policy or your GDPR rights, please contact us:</p>
              <div className="mt-4 space-y-2">
                <p><strong>Email:</strong> privacy@flavorsnap.com</p>
                <p><strong>Address:</strong> 123 Privacy Street, Security City, SC 12345</p>
                <p><strong>Phone:</strong> +1 (555) 123-4567</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
