"""Custom exceptions for the Solidity mutation testing framework."""


class MutationToolError(Exception):
    """Base exception for all mutation tool errors."""
    pass


class ProjectNotFoundError(MutationToolError):
    """Raised when the specified Solidity project cannot be found or accessed."""
    pass


class InvalidProjectError(MutationToolError):
    """Raised when the project structure is invalid or missing required files."""
    pass


class ToolchainNotFoundError(MutationToolError):
    """Raised when a required external tool (e.g., Forge/Foundry) is missing."""
    pass


class BaselineVerificationError(MutationToolError):
    """Raised when the original project fails to compile or its baseline tests fail."""
    pass


class CompilationError(MutationToolError):
    """Raised when a compilation command fails unexpectedly."""
    pass


class TestExecutionError(MutationToolError):
    """Raised when a test execution process fails unexpectedly."""
    pass


class InvalidMutantError(MutationToolError):
    """Raised when a mutant definition or transformation is malformed."""
    pass


class OperatorNotFoundError(MutationToolError):
    """Raised when a requested mutation operator identifier is not registered."""
    pass
