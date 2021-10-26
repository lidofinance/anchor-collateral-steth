# @version 0.2.12
# @author skozin <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20

TERRA_CHAIN_ID: constant(uint256) = 3
ARBITER_FEE: constant(uint256) = 0

wormhole_token_bridge: public(address)
beth_token: public(address)
ust_token: public(address)

next_nonce: uint256

@external
def __init__(wormhole_token_bridge: address, beth_token: address, ust_token: address):
    self.wormhole_token_bridge = wormhole_token_bridge
    self.beth_token = beth_token
    self.ust_token = ust_token


@internal
def _get_nonce() -> uint256:
    # @TODO: maybe we can get nonce from _extra_data
    nonce: uint256 = self.next_nonce

    self.next_nonce = nonce + 1

    return nonce


@internal
def _transfer_asset(bridge: address, asset: address, amount: uint256, recipient: bytes32, arbiter_fee: uint256, nonce: uint256):
    ERC20(asset).approve(bridge, amount)

    # Method signature: https://etherscan.io/address/0x6c4c12987303b2c94b2c76c612fc5f4d2f0360f7#code#F2#L93
    # Vyper does not support uint16 and uint32. Using raw_call() for compatibility.
    raw_call(
        bridge,
        concat(
            method_id('transferTokens(address,uint256,uint16,bytes32,uint256,uint32)'),
            convert(asset, bytes32),
            convert(amount, bytes32),
            convert(TERRA_CHAIN_ID, bytes32),
            recipient,
            convert(arbiter_fee, bytes32),
            convert(nonce, bytes32)
        )
    )


@external
def forward_beth(_terra_address: bytes32, _amount: uint256, _extra_data: Bytes[1024]):
    self._transfer_asset(self.wormhole_token_bridge, self.beth_token, _amount, _terra_address, ARBITER_FEE, self._get_nonce())


@external
def forward_ust(_terra_address: bytes32, _amount: uint256, _extra_data: Bytes[1024]):
    self._transfer_asset(self.wormhole_token_bridge, self.ust_token, _amount, _terra_address, ARBITER_FEE, self._get_nonce())


@external
@view
def adjust_amount(_amount: uint256, _decimals: uint256) -> uint256:
    # Wormhole only supports the precision of 8 decimals
    # See https://etherscan.io/address/0x6c4c12987303b2c94b2c76c612fc5f4d2f0360f7#code#F2#L113
    if _decimals > 8:
        mult: uint256 = 10 ** (_decimals - 8)

        return (_amount / mult) * mult

    return _amount
