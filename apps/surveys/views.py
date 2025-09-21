from .api.views import DownloadCertificatePDFView, GetCertificateDataView
from django.views import View
from django.http import HttpResponse
import requests

class TestDownloadCertificateView(View):
    """Test view for downloading PDF certificate without authentication."""
    
    def get(self, request, session_id, *args, **kwargs):
        """Generate and download PDF certificate for survey session."""
        from apps.surveys.models import SurveySession
        
        try:
            # Get session with related data
            session = SurveySession.objects.select_related(
                'user', 'survey'
            ).get(id=session_id)
        except SurveySession.DoesNotExist:
            return HttpResponse(
                '{"error": "Session not found"}', 
                content_type="application/json", 
                status=404
            )
        
        # Check if session is completed
        if session.status != 'completed':
            return HttpResponse(
                '{"error": "Certificate can only be generated for completed sessions"}', 
                content_type="application/json", 
                status=400
            )
        
        # Construct certificate URL
        base_url = 'https://savollar.leetcode.uz'
        if not base_url.endswith('/'):
            base_url += '/'
        
        certificate_url = f"{base_url}certificate/{session_id}"
        
        # Prepare data for Gotenberg
        gotenberg_url = "http://gotenberg:3000/forms/chromium/convert/url"
        
        # Options for PDF generation - using multipart/form-data
        # Need at least one file to trigger multipart/form-data content type
        files = {"dummy": ("", "", "text/plain")}
        data = {
            "url": certificate_url,
            "marginTop": "0",
            "marginBottom": "0", 
            "marginLeft": "0",
            "marginRight": "0",
            "format": "A4",
            "landscape": "true",
            "waitTimeout": "10s",
            "waitForSelector": "body",
        }
        
        try:
            # Send request to Gotenberg with multipart/form-data
            response = requests.post(
                gotenberg_url, 
                data=data,
                files=files,
                timeout=60
            )
            response.raise_for_status()
            
            # Get PDF content from Gotenberg response
            pdf_content = response.content
            
            # Return PDF file for download
            http_response = HttpResponse(pdf_content, content_type="application/pdf")
            http_response["Content-Disposition"] = f'attachment; filename="certificate_{session.user.name}_{session.survey.title}.pdf"'
            return http_response
            
        except Exception as e:
            return HttpResponse(
                f'{{"error": "Error generating PDF: {str(e)}"}}', 
                content_type="application/json", 
                status=500
            )


class TestGetCertificateDataView(View):
    """Test view for getting certificate data without authentication."""
    
    def get(self, request, session_id, *args, **kwargs):
        """Get certificate data for survey session."""
        from apps.surveys.models import SurveySession
        from apps.surveys.api.serializers import CertificateDataSerializer
        import json
        
        try:
            # Get session with related data
            session = SurveySession.objects.select_related(
                'user', 'survey'
            ).get(id=session_id)
        except SurveySession.DoesNotExist:
            return HttpResponse(
                '{"error": "Session not found"}', 
                content_type="application/json", 
                status=404
            )
        
        # Check if session is completed
        if session.status != 'completed':
            return HttpResponse(
                '{"error": "Certificate data is only available for completed sessions"}', 
                content_type="application/json", 
                status=400
            )
        
        # Serialize certificate data
        serializer = CertificateDataSerializer(session)
        return HttpResponse(
            json.dumps(serializer.data, ensure_ascii=False, indent=2),
            content_type="application/json; charset=utf-8"
        )
