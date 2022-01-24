# @version 0.3.1
# @author skozin <info@lido.fi>
# @author Eugene Mamin <TheDZhon@gmail.com>
# @licence MIT


interface SelfOwnedStETHBurner:
    def getCoverSharesBurnt() -> uint256: view


self_owned_steth_burner: public(address)


@external
def __init__(
    self_owned_steth_burner: address
):
    assert self_owned_steth_burner != ZERO_ADDRESS, "ZERO_BURNER_ADDRESS"

    self.self_owned_steth_burner = self_owned_steth_burner

@external
@view
def total_shares_burnt() -> uint256:
    return SelfOwnedStETHBurner(self.self_owned_steth_burner).getCoverSharesBurnt()
