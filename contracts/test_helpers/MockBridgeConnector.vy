# @version 0.2.12
from vyper.interfaces import ERC20


event Test__Forwarded:
    asset_name: String[100]
    terra_address: bytes32
    amount: uint256
    extra_data: Bytes[1024]


SINKHOLE: constant(address) = 0xDeaDbeefdEAdbeefdEadbEEFdeadbeEFdEaDbeeF
UST_TOKEN: constant(address) = 0xa47c8bf37f92aBed4A126BDA807A7b7498661acD

beth_token: address
bridge: address


@external
def __init__(beth_token: address, bridge: address):
    self.beth_token = beth_token
    self.bridge = bridge


@external
def forward_beth(terra_address: bytes32, amount: uint256, extra_data: Bytes[1024]):
    ERC20(self.beth_token).transfer(SINKHOLE, amount)
    log Test__Forwarded("bETH", terra_address, amount, extra_data)


@external
def forward_ust(terra_address: bytes32, amount: uint256, extra_data: Bytes[1024]):
    ERC20(UST_TOKEN).transfer(SINKHOLE, amount)
    log Test__Forwarded("UST", terra_address, amount, extra_data)


@external
@view
def adjust_amount(_amount: uint256, _decimals: uint256) -> uint256:
    mult: uint256 = 10 ** (_decimals - 9)
    return (_amount / mult) * mult
