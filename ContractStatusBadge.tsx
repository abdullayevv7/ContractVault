"""
Tests for the contracts app: models, services, and API endpoints.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient

from apps.accounts.models import User, Organization, Role
from apps.contracts.models import (
    Contract, ContractType, ContractVersion, ContractParty, ContractClause,
)
from apps.contracts.services import (
    transition_contract_status,
    create_contract_version,
    duplicate_contract,
    check_and_update_expired_contracts,
    get_expiring_contracts,
)
from utils.exceptions import ContractStateError


class ContractModelTests(TestCase):
    """Unit tests for the Contract model."""

    def setUp(self):
        self.org = Organization.objects.create(
            name="Acme Corp",
            slug="acme-corp",
        )
        self.user = User.objects.create_user(
            email="alice@acme.com",
            password="securepassword1",
            first_name="Alice",
            last_name="Johnson",
            organization=self.org,
        )
        self.contract_type = ContractType.objects.create(
            organization=self.org,
            name="NDA",
            prefix="NDA",
            requires_approval=True,
        )

    def test_contract_number_auto_generated(self):
        contract = Contract.objects.create(
            organization=self.org,
            title="Test NDA",
            contract_type=self.contract_type,
            created_by=self.user,
        )
        self.assertTrue(contract.contract_number.startswith("NDA-"))

    def test_contract_default_status_is_draft(self):
        contract = Contract.objects.create(
            organization=self.org,
            title="Draft Contract",
            created_by=self.user,
        )
        self.assertEqual(contract.status, Contract.Status.DRAFT)

    def test_is_expired_property(self):
        contract = Contract.objects.create(
            organization=self.org,
            title="Expired Contract",
            expiration_date=date.today() - timedelta(days=1),
            created_by=self.user,
        )
        self.assertTrue(contract.is_expired)

    def test_days_until_expiration(self):
        future = date.today() + timedelta(days=30)
        contract = Contract.objects.create(
            organization=self.org,
            title="Future Contract",
            expiration_date=future,
            created_by=self.user,
        )
        self.assertEqual(contract.days_until_expiration, 30)

    def test_days_until_expiration_none_when_no_date(self):
        contract = Contract.objects.create(
            organization=self.org,
            title="No Date Contract",
            created_by=self.user,
        )
        self.assertIsNone(contract.days_until_expiration)

    def test_sequential_contract_numbers(self):
        c1 = Contract.objects.create(
            organization=self.org,
            title="First",
            contract_type=self.contract_type,
            created_by=self.user,
        )
        c2 = Contract.objects.create(
            organization=self.org,
            title="Second",
            contract_type=self.contract_type,
            created_by=self.user,
        )
        num1 = int(c1.contract_number.split("-")[-1])
        num2 = int(c2.contract_number.split("-")[-1])
        self.assertEqual(num2, num1 + 1)


class ContractServiceTests(TestCase):
    """Unit tests for contract business logic services."""

    def setUp(self):
        self.org = Organization.objects.create(
            name="Test Org",
            slug="test-org",
        )
        self.user = User.objects.create_user(
            email="bob@test.com",
            password="securepassword1",
            first_name="Bob",
            last_name="Smith",
            organization=self.org,
        )
        self.contract = Contract.objects.create(
            organization=self.org,
            title="Service Test Contract",
            status=Contract.Status.DRAFT,
            total_value=Decimal("50000.00"),
            created_by=self.user,
        )

    def test_valid_transition(self):
        result = transition_contract_status(
            self.contract, "pending_approval", self.user,
        )
        self.assertEqual(result.status, "pending_approval")

    def test_invalid_transition_raises_error(self):
        with self.assertRaises(ContractStateError):
            transition_contract_status(
                self.contract, "active", self.user,
            )

    def test_transition_to_active_sets_effective_date(self):
        self.contract.status = "approved"
        self.contract.save()
        transition_contract_status(self.contract, "active", self.user)
        self.assertIsNotNone(self.contract.effective_date)

    def test_transition_to_terminated_sets_termination_date(self):
        self.contract.status = "active"
        self.contract.save()
        transition_contract_status(self.contract, "terminated", self.user)
        self.assertIsNotNone(self.contract.termination_date)

    def test_create_version_increments_version_number(self):
        original_version = self.contract.version
        create_contract_version(self.contract, self.user, "Test snapshot")
        self.contract.refresh_from_db()
        self.assertEqual(self.contract.version, original_version + 1)

    def test_create_version_captures_snapshot(self):
        version = create_contract_version(
            self.contract, self.user, "Initial snapshot",
        )
        self.assertEqual(version.title, self.contract.title)
        self.assertIn("title", version.content_snapshot)
        self.assertEqual(
            version.content_snapshot["total_value"],
            str(self.contract.total_value),
        )

    def test_duplicate_contract(self):
        ContractParty.objects.create(
            contract=self.contract,
            name="Jane Doe",
            email="jane@example.com",
            role="counterparty",
        )
        ContractClause.objects.create(
            contract=self.contract,
            title="Confidentiality",
            content="All information is confidential.",
        )

        new_contract = duplicate_contract(self.contract, self.user)

        self.assertNotEqual(new_contract.id, self.contract.id)
        self.assertTrue(new_contract.title.startswith("Copy of"))
        self.assertEqual(new_contract.status, Contract.Status.DRAFT)
        self.assertEqual(new_contract.parties.count(), 1)
        self.assertEqual(new_contract.clauses.count(), 1)

    def test_check_and_update_expired_contracts(self):
        self.contract.status = Contract.Status.ACTIVE
        self.contract.expiration_date = date.today() - timedelta(days=1)
        self.contract.save()

        count = check_and_update_expired_contracts()
        self.assertEqual(count, 1)

        self.contract.refresh_from_db()
        self.assertEqual(self.contract.status, Contract.Status.EXPIRED)

    def test_get_expiring_contracts(self):
        self.contract.status = Contract.Status.ACTIVE
        self.contract.expiration_date = date.today() + timedelta(days=10)
        self.contract.save()

        contracts = get_expiring_contracts(30)
        self.assertIn(self.contract, contracts)

        contracts = get_expiring_contracts(5)
        self.assertNotIn(self.contract, contracts)


class ContractAPITests(APITestCase):
    """Integration tests for contract API endpoints."""

    def setUp(self):
        self.org = Organization.objects.create(
            name="API Test Org",
            slug="api-test-org",
        )
        self.role = Role.objects.create(
            organization=self.org,
            name="Admin",
            role_type="admin",
            can_create_contracts=True,
            can_edit_contracts=True,
            can_delete_contracts=True,
        )
        self.user = User.objects.create_user(
            email="admin@apitest.com",
            password="securepassword1",
            first_name="Admin",
            last_name="User",
            organization=self.org,
            role=self.role,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.contract_type = ContractType.objects.create(
            organization=self.org,
            name="MSA",
            prefix="MSA",
        )

    def test_list_contracts(self):
        Contract.objects.create(
            organization=self.org,
            title="Contract A",
            created_by=self.user,
        )
        response = self.client.get("/api/contracts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(response.data["count"], 1)

    def test_create_contract(self):
        data = {
            "title": "New Service Agreement",
            "description": "Agreement for consulting services.",
            "contract_type": str(self.contract_type.id),
            "priority": "high",
            "total_value": "100000.00",
            "currency": "USD",
        }
        response = self.client.post("/api/contracts/", data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], data["title"])

    def test_retrieve_contract(self):
        contract = Contract.objects.create(
            organization=self.org,
            title="Retrieve Test",
            created_by=self.user,
        )
        response = self.client.get(f"/api/contracts/{contract.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Retrieve Test")

    def test_update_contract(self):
        contract = Contract.objects.create(
            organization=self.org,
            title="Before Update",
            created_by=self.user,
        )
        response = self.client.patch(
            f"/api/contracts/{contract.id}/",
            {"title": "After Update"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        contract.refresh_from_db()
        self.assertEqual(contract.title, "After Update")

    def test_transition_action(self):
        contract = Contract.objects.create(
            organization=self.org,
            title="Transition Test",
            status=Contract.Status.DRAFT,
            created_by=self.user,
        )
        response = self.client.post(
            f"/api/contracts/{contract.id}/transition/",
            {"status": "pending_approval"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "pending_approval")

    def test_invalid_transition_returns_400(self):
        contract = Contract.objects.create(
            organization=self.org,
            title="Bad Transition",
            status=Contract.Status.DRAFT,
            created_by=self.user,
        )
        response = self.client.post(
            f"/api/contracts/{contract.id}/transition/",
            {"status": "active"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_version_action(self):
        contract = Contract.objects.create(
            organization=self.org,
            title="Versioned Contract",
            created_by=self.user,
        )
        response = self.client.post(
            f"/api/contracts/{contract.id}/create_version/",
            {"change_summary": "First version"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version_number"], 1)
