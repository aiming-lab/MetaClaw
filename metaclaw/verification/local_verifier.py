from .base import VerificationResult, VerificationVerdict, VerifierInterface

class LocalVerifier(VerifierInterface):
    def verify(self, *, task_id, spec, output, context=None):
        context = context or {}
        skill_name = (output.get("skill_name") or "").strip()
        content = (output.get("skill_content") or "").strip()
        if not skill_name or not content:
            return VerificationResult(VerificationVerdict.FAIL, verifier_id="local", reason_code="MALFORMED_SKILL")
        if not output.get("evaluation_criteria") or output.get("evaluation_result") is None:
            return VerificationResult(VerificationVerdict.FAIL, verifier_id="local", reason_code="MISSING_EVAL")
        existing_contents = context.get("existing_skill_contents") or []
        if content in existing_contents:
            return VerificationResult(VerificationVerdict.FAIL, verifier_id="local", reason_code="DUPLICATE_SKILL_CONTENT")
        satisfied = (output.get("evaluation_result") or {}).get("criteria_satisfied") or []
        if not satisfied:
            return VerificationResult(VerificationVerdict.INDETERMINATE, verifier_id="local", reason_code="INSUFFICIENT_IMPROVEMENT_EVIDENCE")
        return VerificationResult(VerificationVerdict.PASS, verifier_id="local", confidence=0.72, reason_code="LOCAL_CHECKS_PASSED")
