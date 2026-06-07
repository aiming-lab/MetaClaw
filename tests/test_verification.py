from metaclaw.config import MetaClawConfig, VerificationConfig
from metaclaw.verification.base import VerificationVerdict
from metaclaw.verification.factory import build_verifier, build_verifier_safe
from metaclaw.verification.local_verifier import LocalVerifier
from metaclaw.verification.null_verifier import NullVerifier


def test_null_verifier_pass():
    r = NullVerifier().verify(task_id='t', spec={}, output={})
    assert r.verdict == VerificationVerdict.PASS


def test_local_verifier_cases():
    v = LocalVerifier()
    fail = v.verify(task_id='t', spec={}, output={'skill_name':'a','skill_content':'','evaluation_criteria':[1],'evaluation_result':{}}, context={})
    assert fail.verdict == VerificationVerdict.FAIL
    dup = v.verify(task_id='t', spec={}, output={'skill_name':'a','skill_content':'x','evaluation_criteria':[1],'evaluation_result':{'criteria_satisfied':['a']}}, context={'existing_skill_contents':['x']})
    assert dup.verdict == VerificationVerdict.FAIL
    ind = v.verify(task_id='t', spec={}, output={'skill_name':'a','skill_content':'x','evaluation_criteria':[1],'evaluation_result':{}}, context={})
    assert ind.verdict == VerificationVerdict.INDETERMINATE
    ok = v.verify(task_id='t', spec={}, output={'skill_name':'a','skill_content':'x','evaluation_criteria':[1],'evaluation_result':{'criteria_satisfied':['a']}}, context={})
    assert ok.verdict == VerificationVerdict.PASS


def test_factory_selection_and_fallback():
    cfg = MetaClawConfig(mode='verified_skills', verification=VerificationConfig(enabled=True, verifier='local'))
    assert build_verifier(cfg).__class__.__name__ == 'LocalVerifier'
    cfg.verification.verifier = 'unknown'
    fv = build_verifier_safe(cfg)
    assert isinstance(fv, NullVerifier)
