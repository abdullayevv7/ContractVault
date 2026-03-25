"""
URL configuration for templates_mgr app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ContractTemplateViewSet, TemplateFieldViewSet, TemplateClauseViewSet

router = DefaultRouter()
router.register(r"", ContractTemplateViewSet, basename="template")

urlpatterns = [
    path(
        "<uuid:template_id>/fields/",
        TemplateFieldViewSet.as_view({"get": "list", "post": "create"}),
        name="template-fields",
    ),
    path(
        "<uuid:template_id>/fields/<uuid:id>/",
        TemplateFieldViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="template-field-detail",
    ),
    path(
        "<uuid:template_id>/clauses/",
        TemplateClauseViewSet.as_view({"get": "list", "post": "create"}),
        name="template-clauses",
    ),
    path(
        "<uuid:template_id>/clauses/<uuid:id>/",
        TemplateClauseViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="template-clause-detail",
    ),
    path("", include(router.urls)),
]
