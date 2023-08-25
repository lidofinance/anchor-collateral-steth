import math
from typing import TypedDict, TypeVar, Any

T = TypeVar("T")
SHARE_RATE_PRECISION = 10**27

def ETH(amount):
    return math.floor(amount * 10**18)

class TokenRebased(TypedDict):
    """TokenRebased event definition"""

    reportTimestamp: int
    timeElapsed: int
    preTotalShares: int
    preTotalEther: int
    postTotalShares: int
    postTotalEther: int
    sharesMintedAsFees: int

def _get_events(tx, event: type[T]) -> list[T]:
    """Get event of type T from transaction"""

    assert event.__name__ in tx.events, f"Event {event.__name__} was not found in the transaction"
    return tx.events[event.__name__]

def _first_event(tx, event: type[T]) -> T:
    """Get first event of type T from transaction"""

    events = _get_events(tx, event)
    assert len(events) == 1, f"Event {event.__name__} was found more than once in the transaction"
    return events[0]

def _shares_rate_from_event(tx) -> tuple[int, int]:
    """Get shares rate from TokenRebased event"""

    token_rebased_event = _first_event(tx, TokenRebased)
    return (
        token_rebased_event["preTotalEther"] * SHARE_RATE_PRECISION // token_rebased_event["preTotalShares"],
        token_rebased_event["postTotalEther"] * SHARE_RATE_PRECISION // token_rebased_event["postTotalShares"],
    )