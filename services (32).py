"""
Compliance checking services.
Evaluates contracts against compliance rules and generates reports.
"""
import importlib
import logging
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import ComplianceRule, ComplianceCheck, ComplianceReport

logger = logging.getLogger(__name__)

# ---- Built-in compliance check functions --------------------------------

def check_contract_has_parties(contract, params):
    """Check that a contract has at least the minimum number of parties."""
    min_parties = params.get("min_parties", 2)
    count = contract.parties.count()
    if count >= min_parties:
        return "pass", f"Contract has {count} parties (minimum {min_parties})."
    return "fail", f"Contract has only {count} parties (minimum {min_parties} required)."


def check_contract_has_expiration(contract, params):
    """Check that a contract has an expiration date set."""
    if contract.expiration_date:
        return "pass", f"Expiration date is set to {contract.expiration_date}."
    return "fail", "Contract does not have an expiration date."


def check_contract_value_limit(contract, params):
    """Check that the contract value is within the allowed limit."""
    max_value = Decimal(str(params.get("max_value", 1_000_000)))
    if contract.total_value is None:
        return "warning", "Contract has no value set; cannot validate limit."
    if contract.total_value <= max_value:
        return "pass", f"Contract value ${contract.total_value:,.2f} is within limit ${max_value:,.2f}."
    return "fail", f"Contract value ${contract.total_value:,.2f} exceeds limit ${max_value:,.2f}."


def check_contract_has_clauses(contract, params):
    """Check that a contract has at least one clause."""
    count = contract.clauses.filter(is_active=True).count()
    if count > 0:
        return "pass", f"Contract has {count} active clauses."
    return "fail", "Contract has no active clauses."


def check_contract_duration_limit(contract, params):
    """Check that the contract duration does not exceed a maximum."""
    max_days = params.get("max_days", 365 * 5)
    if not contract.effective_date or not contract.expiration_date:
        return "warning", "Missing dates; cannot validate duration."
    duration = (contract.expiration_date - contract.effective_date).days
    if duration <= max_days:
        return "pass", f"Duration {duration} days is within the {max_days}-day limit."
    return "fail", f"Duration {duration} days exceeds the {max_days}-day limit."


# ---- Registry of built-in checks ----------------------------------------

BUILTIN_CHECKS = {
    "compliance.checks.has_parties": check_contract_has_parties,
    "compliance.checks.has_expiration": check_contract_has_expiration,
    "compliance.checks.value_limit": check_contract_value_limit,
    "compliance.checks.has_clauses": check_contract_has_clauses,
    "compliance.checks.duration_limit": check_contract_duration_limit,
}


def _resolve_check_function(dotted_path):
    """Resolve a check function from a dotted path, trying built-ins first."""
    if dotted_path in BUILTIN_CHECKS:
        return BUILTIN_CHECKS[dotted_path]

    try:
        module_path, func_name = dotted_path.rsplit(".", 1)
        module = importlib.import_module(module_path)
        return getattr(module, func_name)
    except (ImportError, AttributeError, ValueError):
        logger.error("Cannot resolve compliance check function: %s", dotted_path)
        return None


def run_compliance_check(contract, rule, user=None):
    """
    Run a single compliance rule against a contract.

    Args:
        contract: Contract instance
        rule: ComplianceRule instance
        user: User who triggered the check (optional)

    Returns:
        ComplianceCheck instance
    """
    check_func = _resolve_check_function(rule.check_function)

    if check_func is None:
        return ComplianceCheck.objects.create(
            contract=contract,
            rule=rule,
            result=ComplianceCheck.Result.ERROR,
            message=f"Check function '{rule.check_function}' could not be resolved.",
            checked_by=user,
        )

    try:
        result, message = check_func(contract, rule.parameters)
    except Exception as exc:
        logger.exception(
            "Error running compliance check %s on contract %s",
            rule.name, contract.contract_number,
        )
        result = "error"
        message = f"Check raised an exception: {exc}"

    return ComplianceCheck.objects.create(
        contract=contract,
        rule=rule,
        result=result,
        message=message,
        details={"parameters": rule.parameters},
        checked_by=user,
    )


def run_all_checks_for_contract(contract, user=None):
    """
    Run all applicable compliance rules against a contract.

    Args:
        contract: Contract instance
        user: User who triggered the checks

    Returns:
        list[ComplianceCheck]
    """
    today = timezone.now().date()

    rules = ComplianceRule.objects.filter(
        organization=contract.organization,
        is_active=True,
    ).filter(
        models_Q_effective_date_lte=today,  # placeholder, actual filter below
    )
    # Correct ORM filtering
    rules = ComplianceRule.objects.filter(
        organization=contract.organization,
        is_active=True,
    )
    # Filter by effective/expiration dates
    applicable = []
    for rule in rules:
        if rule.effective_date and rule.effective_date > today:
            continue
        if rule.expiration_date and rule.expiration_date < today:
            continue
        if rule.contract_type and rule.contract_type != contract.contract_type:
            continue
        applicable.append(rule)

    checks = []
    for rule in applicable:
        check = run_compliance_check(contract, rule, user)
        checks.append(check)

    logger.info(
        "Ran %d compliance checks on contract %s",
        len(checks),
        contract.contract_number,
    )
    return checks


@transaction.atomic
def generate_compliance_report(organization, period_start, period_end, user=None):
    """
    Generate a compliance report for all contracts in the organization.

    Args:
        organization: Organization instance
        period_start: start date of the reporting period
        period_end: end date of the reporting period
        user: User generating the report

    Returns:
        ComplianceReport instance
    """
    from apps.contracts.models import Contract

    contracts = Contract.objects.filter(
        organization=organization,
        created_at__date__lte=period_end,
    ).exclude(status="archived")

    total_checks = 0
    passed = 0
    failed = 0
    warnings = 0
    by_category = {}

    for contract in contracts:
        checks = run_all_checks_for_contract(contract, user)
        for check in checks:
            total_checks += 1
            if check.result == "pass":
                passed += 1
            elif check.result == "fail":
                failed += 1
            elif check.result == "warning":
                warnings += 1

            cat = check.rule.category
            if cat not in by_category:
                by_category[cat] = {"pass": 0, "fail": 0, "warning": 0}
            if check.result in by_category[cat]:
                by_category[cat][check.result] += 1

    score = Decimal("0.00")
    if total_checks > 0:
        score = Decimal(str(round(passed / total_checks * 100, 2)))

    report = ComplianceReport.objects.create(
        organization=organization,
        title=f"Compliance Report {period_start} to {period_end}",
        period_start=period_start,
        period_end=period_end,
        total_contracts_checked=contracts.count(),
        total_checks_run=total_checks,
        passed=passed,
        failed=failed,
        warnings=warnings,
        compliance_score=score,
        summary=by_category,
        generated_by=user,
    )

    logger.info(
        "Generated compliance report %s: %d contracts, %d checks, score %.1f%%",
        report.id,
        contracts.count(),
        total_checks,
        score,
    )
    return report
