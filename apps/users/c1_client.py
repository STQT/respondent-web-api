"""1C API client for fetching employee data."""
import requests
import base64
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class C1Client:
    """Client for interacting with 1C system."""
    
    def __init__(self):
        self.base_url = settings.C1_BASE_URL
        self.basic_token = settings.C1_BASIC_TOKEN
        
    def get_headers(self):
        """Get HTTP headers for 1C API requests."""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        if self.basic_token:
            # Basic authentication
            auth_string = f"Basic {self.basic_token}"
            headers['Authorization'] = auth_string
        else:
            # If token is provided as username:password, encode it
            # For now, just use the token as-is
            pass
            
        return headers
    
    def get_employee_by_pinfl(self, pinfl):
        """
        Get employee data by PINFL from 1C system.
        
        Args:
            pinfl: Employee PINFL (Personal Identification Number)
            
        Returns:
            dict: Employee data from 1C API or None if error
            
        Raises:
            Exception: If API request fails
        """
        url = f"{self.base_url}/employee"
        params = {'pinfl': pinfl}
        headers = self.get_headers()
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if request was successful
            if data.get('status') == 'OK':
                return data
            else:
                return None
                
        except requests.exceptions.RequestException as e:
            # Log error but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error fetching employee data from 1C: {str(e)}")
            return None
        
    def transform_employee_data(self, c1_data):
        """
        Transform 1C employee data to internal format.
        
        Args:
            c1_data: Raw data from 1C API
            
        Returns:
            dict: Transformed employee data
        """
        if not c1_data:
            return None
            
        return {
            'full_name': c1_data.get('full_name', ''),
            'tin': c1_data.get('tin', ''),
            'pinfl': c1_data.get('pinfl', ''),
            'birth_date': c1_data.get('birth_date', ''),
            'hired_at': c1_data.get('hired_at', ''),
            'work_status': c1_data.get('work_status', ''),
            'photo': c1_data.get('photo', ''),
            'org_name': c1_data.get('org_name', ''),
            'org_code': c1_data.get('org_code', ''),
            'branch': c1_data.get('branch', ''),
            'branch_id': c1_data.get('branch_id', ''),
            'department': c1_data.get('department', ''),
            'department_id': c1_data.get('department_id', ''),
            'position': c1_data.get('position', ''),
            'position_id': c1_data.get('position_id', ''),
            'position_class': c1_data.get('position_class', 0),
            'fte': c1_data.get('fte', ''),
            'passport_series': c1_data.get('passport_series', ''),
            'passport_issue_date': c1_data.get('passport_issue_date', ''),
            'passport_issued_by': c1_data.get('passport_issued_by', ''),
            'home_address': c1_data.get('home_address', ''),
            'phone': c1_data.get('phone', ''),
        }

