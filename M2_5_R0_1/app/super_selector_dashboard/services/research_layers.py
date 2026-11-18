"""Five-layer research progression and explicit evidence status."""
from dataclasses import dataclass


LAYER_NAMES = (
    "situational pressure and team task",
    "player responsibility and opportunity",
    "historical expectation and baseline",
    "observed performance and pressure response",
    "evidence reliability and uncertainty",
)


@dataclass(frozen=True)
class LayerState:
    layer: str
    state: str
    explanation: str


def layer_states(*, synthetic: bool = False) -> tuple[LayerState, ...]:
    if synthetic:
        return tuple(LayerState(name, "ILLUSTRATIVE FIXTURE ONLY", "No real IPL interpretation or estimate.") for name in LAYER_NAMES)
    return tuple(LayerState(name, "NOT READY", "Required source evidence, operational rule and authorization are absent.") for name in LAYER_NAMES)
