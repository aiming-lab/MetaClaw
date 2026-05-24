from .base import VerificationResult, VerificationVerdict, VerifierInterface

class NullVerifier(VerifierInterface):
    def __init__(self, reason_code: str | None = None):
        self.reason_code = reason_code

    def verify(self, *, task_id, spec, output, context=None):
        return VerificationResult(verdict=VerificationVerdict.PASS, verifier_id="null", reason_code=self.reason_code)
