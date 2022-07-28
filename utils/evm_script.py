import eth_abi
from web3 import Web3
from eth_typing.evm import HexAddress

EMPTY_CALLSCRIPT = '0x00000001'

def create_executor_id(id):
    return '0x' + str(id).zfill(8)

def strip_byte_prefix(hexstr):
    return hexstr[2:] if hexstr[0:2] == '0x' else hexstr

def encode_call_script(actions, spec_id = 1):
    result = create_executor_id(spec_id)
    for to, calldata in actions:
        addr_bytes = Web3.toBytes(hexstr=HexAddress(to)).hex()
        calldata_bytes = strip_byte_prefix(calldata)
        length = eth_abi.encode_single('int256', len(calldata_bytes) // 2).hex()
        result += addr_bytes + length[56:] + calldata_bytes
    return result
