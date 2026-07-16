"""Custom exception hierarchy for the platform foundation."""


class HealthcareLanguageAIError(Exception):
    """Base class for package-specific errors."""


class ConfigurationError(HealthcareLanguageAIError):
    """Raised when application configuration cannot be loaded or validated."""


class DomainValidationError(HealthcareLanguageAIError):
    """Raised when domain contracts are violated."""


class DataGovernanceError(HealthcareLanguageAIError):
    """Raised when synthetic-data governance rules are violated."""


class PipelineError(HealthcareLanguageAIError):
    """Raised by future pipeline orchestration code."""


class ExternalIntegrationError(HealthcareLanguageAIError):
    """Raised by future external integration adapters."""
