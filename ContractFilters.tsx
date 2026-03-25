"""
Tests for the approvals app: services and API endpoints.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.accounts.models import User, Organization, Role
from apps.approvals.models import ApprovalWorkflow, ApprovalStep, ApprovalRequest
from apps.approvals.services import (
    get_workflow_for_contract,
    create_approval_request,
    process_approval_decision,
)
from apps.contracts.models import Contract, ContractType
from utils.exceptions import ApprovalFlowError


class ApprovalServiceTests(TestCase):
    """Unit tests for approval business logic."""

    def setUp(self):
        self.org = Organization.objects.create(
            name="Approval Org", slug="approval-org",
        )
        self.admin_role = Role.objects.create(
            organization=self.org,
            name="Admin",
            role_type="admin",
            can_approve_contracts=True,
        )
        self.approver = User.objects.create_user(
            email="approver@test.com",
            password="securepassword1",
            first_name="Approver",
            last_name="User",
            organization=self.org,
            role=self.admin_role,
        )
        self.submitter = User.objects.create_user(
            email="submitter@test.com",
            password="securepassword1",
            first_name="Submitter",
            last_name="User",
            organization=self.org,
        )
        self.contract_type = ContractType.objects.create(
            organization=self.org,
            name="SOW",
            prefix="SOW",
        )
        self.workflow = ApprovalWorkflow.objects.create(
            organization=self.org,
            name="Standard Workflow",
            is_active=True,
            is_default=True,
        )
        self.step1 = ApprovalStep.objects.create(
            workflow=self.workflow,
            name="Manager Review",
            order=1,
            approver=self.approver,
        )
        self.step2 = ApprovalStep.objects.create(
            workflow=self.workflow,
            name="Legal Review",
            order=2,
            approver_role=self.admin_role,
        )
        self.contract = Contract.objects.create(
            organization=self.org,
            title="SOW for Testing",
            contract_type=self.contract_type,
            status=Contract.Status.PENDING_APPROVAL,
            total_value=Decimal("25000.00"),
            created_by=self.submitter,
        )

    def test_get_workflow_returns_default(self):
        workflow = get_workflow_for_contract(self.contract)
        self.assertEqual(workflow, self.workflow)

    def test_create_approval_request(self):
        request = create_approval_request(self.contract, self.submitter)
        self.assertEqual(request.status, ApprovalRequest.Status.IN_PROGRESS)
        self.assertEqual(request.current_step, self.step1)
        self.assertEqual(request.workflow, self.workflow)

    def test_approve_advances_to_next_step(self):
        request = create_approval_request(self.contract, self.submitter)
        updated = process_approval_decision(
            request, self.approver, "approve", "Looks good",
        )
        self.assertEqual(updated.current_step, self.step2)
        self.assertEqual(updated.status, ApprovalRequest.Status.IN_PROGRESS)

    def test_approve_all_steps_completes_request(self):
        request = create_approval_request(self.contract, self.submitter)
        process_approval_decision(request, self.approver, "approve")
        updated = process_approval_decision(
            request, self.approver, "approve", "All good",
        )
        self.assertEqual(updated.status, ApprovalRequest.Status.APPROVED)
        self.assertIsNotNone(updated.completed_at)

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.APPROVED)

    def test_reject_completes_request(self):
        request = create_approval_request(self.contract, self.submitter)
        updated = process_approval_decision(
            request, self.approver, "reject", "Not ready",
        )
        self.assertEqual(updated.status, ApprovalRequest.Status.REJECTED)

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.REJECTED)

    def test_decision_history_tracks_decisions(self):
        request = create_approval_request(self.contract, self.submitter)
        process_approval_decision(
            request, self.approver, "approve", "Step 1 OK",
        )
        request.refresh_from_db()
        self.assertEqual(len(request.decision_history), 1)
        self.assertEqual(request.decision_history[0]["decision"], "approve")

    def test_no_workflow_raises_error(self):
        self.workflow.is_active = False
        self.workflow.is_default = False
        self.workflow.save()

        with self.assertRaises(ApprovalFlowError):
            create_approval_request(self.contract, self.submitter)


class ApprovalAPITests(APITestCase):
    """Integration tests for approval API endpoints."""

    def setUp(self):
        self.org = Organization.objects.create(
            name="API Approval Org", slug="api-approval-org",
        )
        self.role = Role.objects.create(
            organization=self.org,
            name="Admin",
            role_type="admin",
            can_approve_contracts=True,
        )
        self.user = User.objects.create_user(
            email="approver@api.com",
            password="securepassword1",
            organization=self.org,
            role=self.role,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.workflow = ApprovalWorkflow.objects.create(
            organization=self.org,
            name="API Workflow",
            is_active=True,
            is_default=True,
            created_by=self.user,
        )

    def test_list_workflows(self):
        response = self.client.get("/api/approvals/workflows/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_workflow(self):
        data = {
            "name": "New Workflow",
            "description": "For testing",
            "is_active": True,
        }
        response = self.client.post(
            "/api/approvals/workflows/",
            data, format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_list_approval_requests(self):
        response = self.client.get("/api/approvals/requests/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
