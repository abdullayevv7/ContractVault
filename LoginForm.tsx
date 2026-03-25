"""
Custom exception handling for ContractVault API.
"""
import logging

from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import APIException

logger = logging.getLogger(__name__)


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides consistent error response format.
    """
    response = exception_handler(exc, context)

    if response is not None:
        error_payload = {
            "success": False,
            "error": {
                "code": response.status_code,
                "message": _get_error_message(response),
                "details": response.data if isinstance(response.data, dict) else {"detail": response.data},
            },
        }
        response.data = error_payload
    else:
        logger.exception("Unhandled exception in view %s", context.get("view", "unknown"))
        response = Response(
            {
                "success": False,
                "error": {
                    "code": 500,
                    "message": "An internal server error occurred.",
                    "details": {},
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _get_error_message(response):
    """Extract a human-readable error message from the response."""
    if isinstance(response.data, dict):
        if "detail" in response.data:
            return str(response.data["detail"])
        first_key = next(iter(response.data), None)
        if first_key:
            value = response.data[first_key]
            if isinstance(value, list):
                return str(value[0])
            return str(value)
    if isinstance(response.data, list) and response.data:
        return str(response.data[0])
    return "An error occurred."


class ContractVaultException(APIException):
    """Base exception for ContractVault business logic errors."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "A business logic error occurred."
    default_code = "business_error"


class ContractStateError(ContractVaultException):
    """Raised when a contract operation is invalid for the current state."""

    default_detail = "This operation is not allowed for the current contract state."
    default_code = "invalid_contract_state"


class ApprovalFlowError(ContractVaultException):
    """Raised when an approval workflow operation fails."""

    default_detail = "The approval workflow operation could not be completed."
    default_code = "approval_flow_error"


class SignatureError(ContractVaultException):
    """Raised when a signature operation fails."""

    default_detail = "The signature operation could not be completed."
    default_code = "signature_error"


class TemplateRenderError(ContractVaultException):
    """Raised when template rendering fails."""

    default_detail = "Failed to render contract from template."
    default_code = "template_render_error"


class PermissionDeniedError(ContractVaultException):
    """Raised when a user lacks the required permissions."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = "You do not have permission to perform this action."
    default_code = "permission_denied"
