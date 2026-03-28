"""
GDPR Compliance API Endpoints
"""

from flask import Flask, request, jsonify
import json
from datetime import datetime
from typing import Dict, Any

try:
    from db_config import get_connection
    from persistence import (
        store_user_consent, 
        get_user_consent, 
        export_user_data, 
        delete_user_data,
        create_user_consent_table
    )
except Exception:
    get_connection = lambda: None
    def store_user_consent(*args, **kwargs): return False  # type: ignore
    def get_user_consent(*args, **kwargs): return []  # type: ignore
    def export_user_data(*args, **kwargs): return {}  # type: ignore
    def delete_user_data(*args, **kwargs): return {"prediction_history": 0, "user_consent": 0}  # type: ignore
    def create_user_consent_table(): return False  # type: ignore


def register_gdpr_endpoints(app: Flask):
    """Register GDPR compliance endpoints"""
    
    @app.route('/gdpr/consent', methods=['POST'])
    def handle_consent():
        """Store or update user consent"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            user_id = data.get('user_id')
            consent_type = data.get('consent_type')
            granted = data.get('granted')
            ip_address = data.get('ip_address')
            user_agent = data.get('user_agent')
            
            if not user_id or not consent_type or granted is None:
                return jsonify({
                    'error': 'Missing required fields: user_id, consent_type, granted'
                }), 400
            
            if not isinstance(granted, bool):
                return jsonify({'error': 'granted must be a boolean'}), 400
            
            success = store_user_consent(
                user_id=user_id,
                consent_type=consent_type,
                granted=granted,
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            if success:
                return jsonify({
                    'success': True,
                    'message': f'Consent for {consent_type} {"granted" if granted else "revoked"} successfully'
                })
            else:
                return jsonify({'error': 'Failed to store consent'}), 500
                
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
    @app.route('/gdpr/consent', methods=['GET'])
    def get_consent():
        """Get user consent records"""
        try:
            user_id = request.args.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Missing required parameter: user_id'}), 400
            
            consents = get_user_consent(user_id)
            
            return jsonify({
                'user_id': user_id,
                'consents': consents,
                'count': len(consents)
            })
            
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
    @app.route('/gdpr/export', methods=['GET'])
    def export_data():
        """Export user data for GDPR compliance"""
        try:
            user_id = request.args.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Missing required parameter: user_id'}), 400
            
            user_data = export_user_data(user_id)
            
            if not user_data:
                return jsonify({'error': 'No data found for user'}), 404
            
            # Add metadata to export
            user_data['export_metadata'] = {
                'export_reason': 'GDPR data portability request',
                'export_format': 'JSON',
                'compliance_framework': 'GDPR',
                'data_controller': 'FlavorSnap',
                'contact_email': 'privacy@flavorsnap.com'
            }
            
            return jsonify(user_data)
            
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
    @app.route('/gdpr/delete', methods=['DELETE'])
    def delete_data():
        """Delete user data for GDPR compliance"""
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({'error': 'Invalid JSON data'}), 400
            
            user_id = data.get('user_id')
            
            if not user_id:
                return jsonify({'error': 'Missing required field: user_id'}), 400
            
            # Log the deletion request for audit purposes
            deletion_log = {
                'user_id': user_id,
                'deletion_requested_at': datetime.utcnow().isoformat(),
                'ip_address': request.remote_addr,
                'user_agent': request.headers.get('User-Agent'),
                'request_source': 'GDPR deletion request'
            }
            
            # Perform deletion
            deletion_counts = delete_user_data(user_id)
            
            # Create audit log entry
            try:
                conn = get_connection()
                if conn:
                    with conn:
                        with conn.cursor() as cur:
                            cur.execute("""
                                CREATE TABLE IF NOT EXISTS gdpr_deletion_log (
                                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                                    user_id TEXT NOT NULL,
                                    deletion_requested_at TIMESTAMPTZ NOT NULL,
                                    ip_address TEXT,
                                    user_agent TEXT,
                                    request_source TEXT,
                                    deletion_counts JSONB,
                                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                                );
                            """)
                            cur.execute("""
                                INSERT INTO gdpr_deletion_log 
                                (user_id, deletion_requested_at, ip_address, user_agent, request_source, deletion_counts)
                                VALUES (%s, %s, %s, %s, %s, %s::jsonb);
                            """, (
                                user_id,
                                deletion_log['deletion_requested_at'],
                                deletion_log['ip_address'],
                                deletion_log['user_agent'],
                                deletion_log['request_source'],
                                json.dumps(deletion_counts)
                            ))
            except Exception as log_error:
                # Log error but don't fail the deletion
                print(f"Failed to create deletion audit log: {log_error}")
            
            return jsonify({
                'success': True,
                'message': 'User data deleted successfully',
                'deletion_counts': deletion_counts,
                'deletion_id': f"del_{user_id}_{int(datetime.utcnow().timestamp())}"
            })
            
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
    @app.route('/gdpr/privacy-policy', methods=['GET'])
    def get_privacy_policy():
        """Get current privacy policy"""
        try:
            privacy_policy = {
                'version': '1.0',
                'last_updated': '2024-03-28',
                'data_controller': 'FlavorSnap',
                'contact_email': 'privacy@flavorsnap.com',
                'contact_address': '123 Privacy Street, Security City, SC 12345',
                'data_purposes': [
                    'Food image classification and analysis',
                    'Service improvement and analytics',
                    'Technical support and troubleshooting'
                ],
                'data_retention': {
                    'prediction_history': '365 days',
                    'consent_records': 'indefinite until revoked',
                    'analytics_data': '730 days'
                },
                'user_rights': [
                    'Right to access personal data',
                    'Right to rectify inaccurate data',
                    'Right to erasure (right to be forgotten)',
                    'Right to data portability',
                    'Right to withdraw consent',
                    'Right to lodge a complaint'
                ],
                'legal_basis': [
                    {
                        'purpose': 'Service provision',
                        'basis': 'Legitimate interest',
                        'description': 'Processing food images for classification'
                    },
                    {
                        'purpose': 'Analytics',
                        'basis': 'Consent',
                        'description': 'Usage analytics for service improvement'
                    }
                ]
            }
            
            return jsonify(privacy_policy)
            
        except Exception as e:
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500
    
    @app.route('/gdpr/health', methods=['GET'])
    def gdpr_health_check():
        """Health check for GDPR endpoints"""
        try:
            # Test database connection and table creation
            conn = get_connection()
            tables_created = False
            
            if conn:
                try:
                    with conn:
                        with conn.cursor() as cur:
                            # Test consent table creation
                            create_user_consent_table()
                            tables_created = True
                except Exception:
                    tables_created = False
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
            
            return jsonify({
                'status': 'healthy',
                'database_connection': conn is not None,
                'tables_ready': tables_created,
                'endpoints_available': [
                    'POST /gdpr/consent',
                    'GET /gdpr/consent',
                    'GET /gdpr/export',
                    'DELETE /gdpr/delete',
                    'GET /gdpr/privacy-policy',
                    'GET /gdpr/health'
                ],
                'timestamp': datetime.utcnow().isoformat()
            })
            
        except Exception as e:
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500


# Helper function to register all GDPR endpoints
def setup_gdpr_compliance(app: Flask):
    """Setup GDPR compliance endpoints"""
    register_gdpr_endpoints(app)
    print("✅ GDPR compliance endpoints registered")
