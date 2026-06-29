"""Custom exception types for the Prefect secret rotation tool."""


class RotationError(Exception):
    """Base class for all rotation-related errors."""


class DecryptionError(RotationError):
    """Raised when decryption fails, e.g. wrong key or tampered ciphertext."""


class EncryptionError(RotationError):
    """Raised when encryption fails unexpectedly."""


class ExportParseError(RotationError):
    """Raised when an export file cannot be parsed or has an unexpected schema."""


class BlockParseError(RotationError):
    """Raised when a Prefect block YAML file cannot be parsed."""


class KeySizeError(RotationError):
    """Raised when a key has an unsupported size."""


class RotationLockError(RotationError):
    """Raised when a rotation lock cannot be acquired."""


class IntegrityError(RotationError):
    """Raised when an export integrity seal does not verify."""


class MissingSecretsError(RotationError):
    """Raised when an export file contains no secret fields."""
