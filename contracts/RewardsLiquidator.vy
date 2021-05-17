# @version 0.2.12
# @author skozin <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20


# FIXME: use the actual address
UST_WRAPPER_TOKEN: constant(address) = ZERO_ADDRESS
STETH_TOKEN: constant(address) = 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84

# max 3% slippage
MAX_SLIPPAGE_MULT: constant(uint256) = 97 * 10**16


@external
def liquidate(_ust_recipient: address) -> uint256:
    steth_amount: uint256 = ERC20(STETH_TOKEN).balanceOf(self)
    assert steth_amount > 0
    # TODO: sell on 1inch
    return 0
