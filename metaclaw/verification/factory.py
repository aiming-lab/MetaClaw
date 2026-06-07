import logging
from .local_verifier import LocalVerifier
from .null_verifier import NullVerifier
from .remote_http_verifier import RemoteHTTPVerifier
from .settlement_witness import SettlementWitnessVerifier


def build_verifier(config):
    vc = config.verification
    if not vc.enabled:
        return NullVerifier()
    if vc.verifier == "local":
        return LocalVerifier()
    if vc.verifier == "remote_http":
        return RemoteHTTPVerifier(vc)
    if vc.verifier == "settlement_witness":
        return SettlementWitnessVerifier(vc)
    if vc.verifier == "null":
        return NullVerifier()
    raise ValueError(f"Unknown verifier: {vc.verifier}")


def build_verifier_safe(config, logger=None):
    logger = logger or logging.getLogger(__name__)
    try:
        return build_verifier(config)
    except Exception as exc:
        logger.warning("Verifier configuration failed; falling back to NullVerifier: %s", exc)
        return NullVerifier(reason_code="VERIFIER_CONFIG_ERROR")
