"""
URL configuration for contracts app.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ContractViewSet,
    ContractTypeViewSet,
    ContractPartyViewSet,
    ContractClauseViewSet,
)

router = DefaultRouter()
router.register(r"types", ContractTypeViewSet, basename="contract-type")
router.register(r"", ContractViewSet, basename="contract")

urlpatterns = [
    path(
        "<uuid:contract_id>/parties/",
        ContractPartyViewSet.as_view({"get": "list", "post": "create"}),
        name="contract-parties",
    ),
    path(
        "<uuid:contract_id>/parties/<uuid:id>/",
        ContractPartyViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="contract-party-detail",
    ),
    path(
        "<uuid:contract_id>/clauses/",
        ContractClauseViewSet.as_view({"get": "list", "post": "create"}),
        name="contract-clauses",
    ),
    path(
        "<uuid:contract_id>/clauses/<uuid:id>/",
        ContractClauseViewSet.as_view(
            {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
        ),
        name="contract-clause-detail",
    ),
    path("", include(router.urls)),
]
