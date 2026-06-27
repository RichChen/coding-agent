from parts.alpha import VALUE as ALPHA
from parts.beta import VALUE as BETA
from parts.gamma import VALUE as GAMMA
from parts.delta import VALUE as DELTA


def total():
    # Bug: gamma exports VALUE but this reads GAMMA_VAL which does not exist.
    return ALPHA + BETA + GAMMA_VAL + DELTA
