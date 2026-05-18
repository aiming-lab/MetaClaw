from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional

class VerificationVerdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INDETERMINATE = "INDETERMINATE"

@dataclass
class VerificationResult:
    verdict: VerificationVerdict
    confidence: float = 0.0
    verifier_id: str = "unknown"
    reason_code: Optional[str] = None
    message: Optional[str] = None
    receipt_id: Optional[str] = None
    verifier_kid: Optional[str] = None
    receipt: Optional[Dict[str, Any]] = None
    evidence: Dict[str, Any] = field(default_factory=dict)

class VerifierInterface(ABC):
    @abstractmethod
    def verify(self, *, task_id: str, spec: Dict[str, Any], output: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> VerificationResult:
        raise NotImplementedError
