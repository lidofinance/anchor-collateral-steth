# @version 0.2.11
# @author skozin <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20


interface BridgeConnector:
    def forward_beth(terra_address: bytes32, amount: uint256, extra_data: Bytes[1024]): nonpayable
    def forward_ust(terra_address: bytes32, amount: uint256, extra_data: Bytes[1024]): nonpayable
    def adjust_amount(amount: uint256, decimals: uint256) -> uint256: view


interface RewardsLiquidator:
    def liquidate(ust_recipient: address) -> uint256: nonpayable


interface Mintable:
    def mint(owner: address, amount: uint256): nonpayable
    def burn(owner: address, amount: uint256): nonpayable


# FIXME: use the actual address
BETH_TOKEN: constant(address) = ZERO_ADDRESS
BETH_DECIMALS: constant(uint256) = 18
STETH_TOKEN: constant(address) = 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84
ANCHOR_REWARDS_DISTRIBUTOR: constant(bytes32) = 0x0000000000000000000000000000000000000000000000000000000000000000

# no rewards liquidations for 24h since previous liquidation
NO_LIQUIDATION_INTERVAL: constant(uint256) = 60 * 60 * 24
# only admin can do liquidate rewards for the first 2h after that
RESTRICTED_LIQUIDATION_INTERVAL: constant(uint256) = NO_LIQUIDATION_INTERVAL + 60 * 60 * 2

admin: public(address)
bridge_connector: public(address)
rewards_liquidator: public(address)
liquidations_admin: public(address)
last_liquidation_time: public(uint256)


@external
def __init__(_admin: address):
    self.admin = _admin


@external
def change_admin(new_admin: address):
    assert msg.sender == self.admin
    self.admin = new_admin


@external
def configure(
    _bridge_connector: address,
    _rewards_liquidator: address,
    _liquidations_admin: address,
):
    assert msg.sender == self.admin
    self.bridge_connector = _bridge_connector
    self.rewards_liquidator = _rewards_liquidator
    self.liquidations_admin = _liquidations_admin


@external
def submit(_amount: uint256, _terra_address: bytes32, _extra_data: Bytes[1024]):
    connector: address = self.bridge_connector
    adjusted_amount: uint256 = BridgeConnector(connector).adjust_amount(_amount, BETH_DECIMALS)
    assert adjusted_amount <= _amount
    ERC20(STETH_TOKEN).transferFrom(msg.sender, self, adjusted_amount)
    Mintable(BETH_TOKEN).mint(connector, adjusted_amount)
    BridgeConnector(connector).forward_beth(_terra_address, adjusted_amount, _extra_data)


@internal
@view
def _get_rewards_amount() -> uint256:
    steth_balance: uint256 = ERC20(STETH_TOKEN).balanceOf(self)
    beth_supply: uint256 = ERC20(BETH_TOKEN).totalSupply()
    if steth_balance > beth_supply:
        return steth_balance - beth_supply
    else:
        return 0


@internal
@view
def _get_withdraw_rate() -> uint256:
    steth_balance: uint256 = ERC20(STETH_TOKEN).balanceOf(self)
    beth_supply: uint256 = ERC20(BETH_TOKEN).totalSupply()
    if steth_balance > beth_supply:
        return 10**18
    else:
        return (steth_balance * 10**18) / beth_supply


@external
def withdraw(_amount: uint256, _recipient: address = msg.sender):
    Mintable(BETH_TOKEN).burn(msg.sender, _amount)
    steth_rate: uint256 = self._get_withdraw_rate()
    steth_amount: uint256 = (_amount * steth_rate) / 10**18
    ERC20(STETH_TOKEN).transfer(_recipient, steth_amount)


@external
def collect_rewards() -> uint256:
    time_since_last_liquidation: uint256 = block.timestamp - self.last_liquidation_time

    if msg.sender == self.liquidations_admin:
        assert time_since_last_liquidation > NO_LIQUIDATION_INTERVAL
    else:
        assert time_since_last_liquidation > RESTRICTED_LIQUIDATION_INTERVAL

    self.last_liquidation_time = block.timestamp

    steth_amount: uint256 = self._get_rewards_amount()
    if steth_amount == 0:
        return 0

    connector: address = self.bridge_connector
    liquidator: address = self.rewards_liquidator
    ERC20(STETH_TOKEN).transfer(liquidator, steth_amount)
    ust_amount: uint256 = RewardsLiquidator(liquidator).liquidate(connector)
    BridgeConnector(connector).forward_ust(ANCHOR_REWARDS_DISTRIBUTOR, ust_amount, b"")

    return ust_amount
