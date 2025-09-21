from django.urls import path
from .views import TestDownloadCertificateView, TestGetCertificateDataView
from .api.views import DownloadCertificatePDFView, GetCertificateDataView
app_name = 'surveys'

urlpatterns = [
    path('certificate/<str:session_id>/download/', DownloadCertificatePDFView.as_view(), name='download-certificate'),
    path('certificate/<str:session_id>/data/', GetCertificateDataView.as_view(), name='certificate-data'),
    path('test/certificate/<str:session_id>/download', TestDownloadCertificateView.as_view(), name='test-download-certificate'), 
    path('test/certificate/<str:session_id>/data/', TestGetCertificateDataView.as_view(), name='test-certificate-data'),
]