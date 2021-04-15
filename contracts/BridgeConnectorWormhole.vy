# @version 0.2.11
# @author skozin <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20


# FIXME: use the actual values
WORMHOLE: constant(address) = ZERO_ADDRESS
BETH_TOKEN: constant(address) = ZERO_ADDRESS
UST_WRAPPER_TOKEN: constant(address) = ZERO_ADDRESS
TERRA_CHAIN_ID: constant(uint256) = 3


next_nonce: uint256


@internal
def _lockAssets(_asset: address, _amount: uint256, _recipient: bytes32):
    nonce: uint256 = self.next_nonce
    self.next_nonce = nonce + 1

    ERC20(_asset).approve(WORMHOLE, _amount)

    raw_call(
        WORMHOLE,
        concat(
            method_id('lockAssets(address,uint256,bytes32,uint8,uint32,bool)'),
            convert(_asset, bytes32),
            convert(_amount, bytes32),
            _recipient,
            convert(TERRA_CHAIN_ID, bytes32),
            convert(nonce, bytes32),
            convert(False, bytes32)
        )
    )


@external
def forward_beth(_terra_address: bytes32, _amount: uint256, _extra_data: Bytes[1024]):
    self._lockAssets(BETH_TOKEN, _amount, _terra_address)


@external
def forward_ust(_terra_address: bytes32, _amount: uint256, _extra_data: Bytes[1024]):
    self._lockAssets(UST_WRAPPER_TOKEN, _amount, _terra_address)


@external
def adjust_amount(_amount: uint256, _decimals: uint256) -> uint256:
    # Wormhole only supports the precision of 9 decimals
    mult: uint256 = 10 ** (_decimals - 9)
    return (_amount / mult) * mult
