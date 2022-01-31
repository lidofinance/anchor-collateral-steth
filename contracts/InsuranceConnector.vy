# @version 0.3.1
# @author skozin <info@lido.fi>
# @author Eugene Mamin <TheDZhon@gmail.com>
# @licence MIT


interface SelfOwnedStETHBurner:
    def getCoverSharesBurnt() -> uint256: view


SELF_OWNDED_STETH_BURNER: immutable(address)


@external
def __init__(
    _self_owned_steth_burner: address
):
    assert _self_owned_steth_burner != ZERO_ADDRESS, "ZERO_BURNER_ADDRESS"

    SELF_OWNDED_STETH_BURNER = _self_owned_steth_burner

@external
@view
def total_shares_burnt() -> uint256:
    return SelfOwnedStETHBurner(SELF_OWNDED_STETH_BURNER).getCoverSharesBurnt()
