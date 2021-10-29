# @version 0.2.12
# @author skozin <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20

BETH_TOKEN: constant(address) = 0x707F9118e33A9B8998beA41dd0d46f38bb963FC8
UST_WRAPPER_TOKEN: constant(address) = 0xa47c8bf37f92aBed4A126BDA807A7b7498661acD

TERRA_CHAIN_ID: constant(uint256) = 3

MAX_UINT32: constant(uint256) = 4294967295

wormhole_token_bridge: public(address)

@external
def __init__(wormhole_token_bridge: address):
    self.wormhole_token_bridge = wormhole_token_bridge


@internal
def _transfer_asset(_bridge: address, _asset: address, _amount: uint256, _recipient: bytes32, _extra_data: Bytes[1024]):
    nonce: uint256 = 0
    arbiter_fee: uint256 = 0

    # TODO: Discuss if making first 64 bytes as required will break anything
    if len(_extra_data) >= 32:
        nonce = extract32(_extra_data, 0, output_type=uint256)

        assert nonce <= 4294967295, "nonce exceeds size of uint32 (4 bytes)"

    if len(_extra_data) >= 64:
        arbiter_fee = extract32(_extra_data, 32, output_type=uint256)

    ERC20(_asset).approve(_bridge, _amount)

    # Method signature: https://etherscan.io/address/0x6c4c12987303b2c94b2c76c612fc5f4d2f0360f7#code#F2#L93
    # Vyper does not support uint16 and uint32. Using raw_call() for compatibility.
    raw_call(
        _bridge,
        concat(
            method_id('transferTokens(address,uint256,uint16,bytes32,uint256,uint32)'),
            convert(_asset, bytes32),
            convert(_amount, bytes32),
            convert(TERRA_CHAIN_ID, bytes32),
            _recipient,
            convert(arbiter_fee, bytes32),
            convert(nonce, bytes32)
        )
    )


@external
def forward_beth(_terra_address: bytes32, _amount: uint256, _extra_data: Bytes[1024]):
    self._transfer_asset(self.wormhole_token_bridge, BETH_TOKEN, _amount, _terra_address, _extra_data)


@external
def forward_ust(_terra_address: bytes32, _amount: uint256, _extra_data: Bytes[1024]):
    self._transfer_asset(self.wormhole_token_bridge, UST_WRAPPER_TOKEN, _amount, _terra_address, _extra_data)


@external
@view
def adjust_amount(_amount: uint256, _decimals: uint256) -> uint256:
    # Wormhole only supports the precision of 8 decimals
    # See https://etherscan.io/address/0x6c4c12987303b2c94b2c76c612fc5f4d2f0360f7#code#F2#L113
    if _decimals > 8:
        mult: uint256 = 10 ** (_decimals - 8)

        return (_amount / mult) * mult

    return _amount
