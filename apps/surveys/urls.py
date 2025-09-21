from django.urls import path
from .api.views import (
    DownloadCertificatePDFView, 
    GetCertificateDataView,
    DownloadUserCertificatePDFView,
    GetUserCertificateDataView
)
app_name = 'surveys'

urlpatterns = [
    # Certificate endpoints by session ID
    path('certificate/<str:session_id>/download/', DownloadCertificatePDFView.as_view(), name='download-certificate'),
    path('certificate/<str:session_id>/data/', GetCertificateDataView.as_view(), name='certificate-data'),
    
    # Certificate endpoints by user UUID
    path('user/<str:user_uuid>/certificate/download/', DownloadUserCertificatePDFView.as_view(), name='download-user-certificate'),
    path('user/<str:user_uuid>/certificate/data/', GetUserCertificateDataView.as_view(), name='user-certificate-data'),
]