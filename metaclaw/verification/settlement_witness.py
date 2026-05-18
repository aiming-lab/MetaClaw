from .remote_http_verifier import RemoteHTTPVerifier

class SettlementWitnessVerifier(RemoteHTTPVerifier):
    def verify(self, *, task_id, spec, output, context=None):
        return super().verify(task_id=task_id, spec=spec, output=output, context=context)
