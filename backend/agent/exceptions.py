
class AgentConfigError(Exception):
    """Raised when the AI agent configuration is invalid."""
    pass


class AgentServiceError(Exception):
    """Raised when the AI service fails."""
    pass


class AgentTimeoutError(AgentServiceError):
    """Raised when an AI request times out."""
    pass
