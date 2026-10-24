import pybreaker
from .adapters import ADAPTERS
from .base import SourceUnavailable

class _Listener(pybreaker.CircuitBreakerListener):
    def state_change(self, cb, old, new):
        print(f"[circuit] {cb.name}: {old.name} -> {new.name}")

BREAKERS = {n: pybreaker.CircuitBreaker(fail_max=3, reset_timeout=60, name=n, listeners=[_Listener()],
                                        exclude=[]) for n in ADAPTERS}

def call(source: str, fn, *a):
    """Run fn under the source's breaker. Open circuit -> SourceUnavailable immediately."""
    try:
        return BREAKERS[source].call(fn, *a)
    except pybreaker.CircuitBreakerError:
        raise SourceUnavailable(f"circuit open for {source}")
