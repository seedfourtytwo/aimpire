"""The rules loader's single error type."""


class RulesError(ValueError):
    """A rules file is missing, unreadable or invalid."""
