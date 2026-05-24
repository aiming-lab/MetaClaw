from __future__ import annotations
import requests
from .base import VerificationResult, VerificationVerdict, VerifierInterface

class RemoteHTTPVerifier(VerifierInterface):
    def __init__(self, config):
        self.endpoint = config.endpoint
        self.timeout = config.timeout_seconds
    def verify(self, *, task_id, spec, output, context=None):
        try:
            r = requests.post(self.endpoint, json={"task_id": task_id, "spec": spec, "output": output, "context": context or {}}, timeout=self.timeout)
            data = r.json()
            return VerificationResult(VerificationVerdict(data.get("verdict", "INDETERMINATE")), confidence=float(data.get("confidence", 0.0)), verifier_id=data.get("verifier_id", "remote_http"), reason_code=data.get("reason_code"), message=data.get("message"), receipt_id=data.get("receipt_id"), verifier_kid=data.get("verifier_kid"), receipt=data.get("receipt"), evidence=data.get("evidence") or {})
        except Exception:
            return VerificationResult(VerificationVerdict.INDETERMINATE, verifier_id="remote_http", reason_code="VERIFIER_UNAVAILABLE", message="Remote verifier unavailable or timed out.")
