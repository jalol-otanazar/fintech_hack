"""services/brain/security.py — AES-256 PII encryption + anonymization helper."""
from __future__ import annotations
import base64, hashlib, hmac, os, re

try:
    from cryptography.fernet import Fernet
    _CRYPTO_AVAILABLE = True
except ImportError:
    _CRYPTO_AVAILABLE = False

# ── Key derivation ────────────────────────────────────────────────────────────

def _derive_fernet_key(secret: str) -> bytes:
    """SHA-256 of secret → 32 bytes → Fernet-safe base64."""
    return base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())


# ── PII patterns to strip from transcripts ───────────────────────────────────

_PII_PATTERNS = [
    # Uzbek PINFL (14 digits)
    (re.compile(r'\b\d{14}\b'), "[PINFL]"),
    # Phone numbers  +998 XX XXX-XX-XX or 8XXXXXXXXXX
    (re.compile(r'(?:\+998|8)[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'), "[PHONE]"),
    # Card numbers (16 digits with optional spaces/dashes)
    (re.compile(r'\b(?:\d{4}[\s\-]?){3}\d{4}\b'), "[CARD]"),
    # Uzbek passport series (2 letters + 7 digits)
    (re.compile(r'\b[A-Z]{2}\d{7}\b'), "[PASSPORT]"),
]


class PiiEncryptor:
    """
    AES-256 (Fernet) encryption for PII fields stored at rest.
    Falls back to identity cipher if cryptography library not installed
    (dev/test mode — logs a warning).
    """

    def __init__(self, secret: str | None = None):
        secret = secret or os.environ.get("ENCRYPTION_KEY", "bankcopilot-dev-key-change-in-prod")
        if _CRYPTO_AVAILABLE:
            self._fernet = Fernet(_derive_fernet_key(secret))
        else:
            self._fernet = None
            import warnings
            warnings.warn(
                "cryptography not installed — PII encryption disabled (dev mode only)",
                RuntimeWarning, stacklevel=2,
            )

    def encrypt(self, plaintext: str) -> str:
        if self._fernet is None:
            return plaintext  # dev fallback
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        if self._fernet is None:
            return token
        return self._fernet.decrypt(token.encode()).decode()

    def anonymize_customer_id(self, raw_id: str) -> str:
        """Stable HMAC-based pseudonym: same input → same output, not reversible."""
        salt = os.environ.get("ANON_SALT", "bankcopilot-anon-salt").encode()
        h = hmac.new(salt, raw_id.encode(), hashlib.sha256)
        return f"Anon-{h.hexdigest()[:8]}"

    @staticmethod
    def strip_pii_from_transcript(text: str) -> str:
        """Replace PII patterns in transcript text before sending to Claude API."""
        for pattern, placeholder in _PII_PATTERNS:
            text = pattern.sub(placeholder, text)
        return text


# ── Module-level singleton (import and use directly) ─────────────────────────
_encryptor: PiiEncryptor | None = None

def get_encryptor() -> PiiEncryptor:
    global _encryptor
    if _encryptor is None:
        _encryptor = PiiEncryptor()
    return _encryptor
