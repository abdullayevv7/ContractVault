"""
Root URL configuration for ContractVault.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("api/admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/contracts/", include("apps.contracts.urls")),
    path("api/templates/", include("apps.templates_mgr.urls")),
    path("api/approvals/", include("apps.approvals.urls")),
    path("api/signatures/", include("apps.signatures.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/amendments/", include("apps.amendments.urls")),
    path("api/compliance/", include("apps.compliance.urls")),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

admin.site.site_header = "ContractVault Administration"
admin.site.site_title = "ContractVault Admin"
admin.site.index_title = "Contract Lifecycle Management"
