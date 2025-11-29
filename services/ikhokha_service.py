"""
iKhokha Payment Gateway Integration Service

This module provides integration with iKhokha payment gateway for processing
conference registration payments.

iKhokha API Documentation: https://developer.ikhokha.com/
"""

import hashlib
import hmac
import json
import requests
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from urllib.parse import urlencode
import logging
from config import Config

logger = logging.getLogger(__name__)


class IKhokhaPaymentService:
    """
    Service class for handling iKhokha payment gateway integration
    """
    
    def __init__(self, app_id: str = None, secret_key: str = None, base_url: str = None):
        """
        Initialize iKhokha payment service
        
        Args:
            app_id: iKhokha application ID
            secret_key: iKhokha secret key
            base_url: iKhokha API base URL
        """
        self.app_id = app_id or Config.IKHOKHA_APP_ID
        self.secret_key = secret_key or Config.IKHOKHA_SECRET_KEY
        self.base_url = base_url or Config.IKHOKHA_BASE_URL
        
        if not self.app_id or not self.secret_key:
            raise ValueError("iKhokha credentials are required")
    
    def _generate_signature(self, data: Dict[str, Any]) -> str:
        """
        Generate HMAC signature for iKhokha API requests
        
        Args:
            data: Request data dictionary
            
        Returns:
            Generated signature string
        """
        # Sort parameters alphabetically and create query string
        sorted_params = sorted(data.items())
        query_string = urlencode(sorted_params)
        
        # Generate HMAC SHA256 signature
        signature = hmac.new(
            self.secret_key.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def create_payment_request(self, registration_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a payment request with iKhokha
        
        Args:
            registration_data: Registration information including amount, user details, etc.
            
        Returns:
            Dictionary containing payment URL and transaction reference
        """
        try:
            # Generate unique transaction reference
            transaction_ref = f"REG_{registration_data.get('user_id', 'ANON')}_{int(datetime.now().timestamp())}"
            
            # Prepare payment request data
            payment_data = {
                'app_id': self.app_id,
                'amount': int(registration_data['total_amount'] * 100),  # Convert to cents
                'currency': 'ZAR',  # South African Rand
                'reference': transaction_ref,
                'description': f"Conference Registration - {registration_data.get('conference_name', 'GIIP Conference')}",
                'customer_name': registration_data.get('full_name', ''),
                'customer_email': registration_data.get('email', ''),
                'customer_phone': registration_data.get('phone', ''),
                'return_url': Config.IKHOKHA_RETURN_URL,
                'cancel_url': Config.IKHOKHA_CANCEL_URL,
                'webhook_url': f"{Config.IKHOKHA_RETURN_URL.split('/payment/callback')[0]}/payment/webhook",
                'timestamp': int(datetime.now().timestamp())
            }
            
            # Generate signature
            payment_data['signature'] = self._generate_signature(payment_data)
            
            # Make API request to iKhokha
            response = requests.post(
                f"{self.base_url}/payments/create",
                json=payment_data,
                headers={
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {self.app_id}'
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            if result.get('success'):
                return {
                    'success': True,
                    'payment_url': result.get('payment_url'),
                    'transaction_reference': transaction_ref,
                    'payment_id': result.get('payment_id'),
                    'expires_at': result.get('expires_at')
                }
            else:
                logger.error(f"iKhokha payment creation failed: {result.get('message', 'Unknown error')}")
                return {
                    'success': False,
                    'error': result.get('message', 'Payment creation failed')
                }
                
        except requests.RequestException as e:
            logger.error(f"iKhokha API request failed: {str(e)}")
            return {
                'success': False,
                'error': 'Payment service temporarily unavailable. Please try again later.'
            }
        except Exception as e:
            logger.error(f"Unexpected error creating payment: {str(e)}")
            return {
                'success': False,
                'error': 'An unexpected error occurred. Please try again.'
            }
    
    def verify_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Verify payment status with iKhokha
        
        Args:
            payment_id: iKhokha payment ID
            
        Returns:
            Payment status information
        """
        try:
            # Prepare request data
            verify_data = {
                'app_id': self.app_id,
                'payment_id': payment_id,
                'timestamp': int(datetime.now().timestamp())
            }
            
            # Generate signature
            verify_data['signature'] = self._generate_signature(verify_data)
            
            # Make API request
            response = requests.get(
                f"{self.base_url}/payments/{payment_id}/status",
                params=verify_data,
                headers={
                    'Authorization': f'Bearer {self.app_id}'
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            return {
                'success': True,
                'status': result.get('status'),
                'amount': result.get('amount'),
                'reference': result.get('reference'),
                'payment_date': result.get('payment_date'),
                'transaction_id': result.get('transaction_id')
            }
            
        except requests.RequestException as e:
            logger.error(f"iKhokha status check failed: {str(e)}")
            return {
                'success': False,
                'error': 'Unable to verify payment status'
            }
    
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """
        Verify webhook signature from iKhokha
        
        Args:
            payload: Webhook payload
            signature: Provided signature
            
        Returns:
            True if signature is valid
        """
        try:
            expected_signature = hmac.new(
                Config.IKHOKHA_WEBHOOK_SECRET.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, signature)
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return False
    
    def process_webhook_data(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process webhook data from iKhokha
        
        Args:
            webhook_data: Webhook payload data
            
        Returns:
            Processed payment information
        """
        try:
            return {
                'success': True,
                'payment_id': webhook_data.get('payment_id'),
                'status': webhook_data.get('status'),
                'amount': webhook_data.get('amount'),
                'reference': webhook_data.get('reference'),
                'transaction_id': webhook_data.get('transaction_id'),
                'payment_date': webhook_data.get('payment_date'),
                'payment_method': webhook_data.get('payment_method')
            }
            
        except Exception as e:
            logger.error(f"Webhook processing failed: {str(e)}")
            return {
                'success': False,
                'error': 'Invalid webhook data'
            }


# Global instance
payment_service = IKhokhaPaymentService()


def create_payment_session(registration_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a payment session for registration
    
    Args:
        registration_data: Registration information
        
    Returns:
        Payment session details
    """
    return payment_service.create_payment_request(registration_data)


def verify_payment(payment_id: str) -> Dict[str, Any]:
    """
    Verify payment status
    
    Args:
        payment_id: Payment ID to verify
        
    Returns:
        Payment verification result
    """
    return payment_service.verify_payment_status(payment_id)


def process_payment_webhook(payload: str, signature: str) -> Dict[str, Any]:
    """
    Process payment webhook
    
    Args:
        payload: Webhook payload
        signature: Webhook signature
        
    Returns:
        Processing result
    """
    if not payment_service.verify_webhook_signature(payload, signature):
        return {
            'success': False,
            'error': 'Invalid webhook signature'
        }
    
    try:
        webhook_data = json.loads(payload)
        return payment_service.process_webhook_data(webhook_data)
    except json.JSONDecodeError:
        return {
            'success': False,
            'error': 'Invalid webhook payload'
        }