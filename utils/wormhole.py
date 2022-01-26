CHAIN_ID_ETHERUM = 2
CHAIN_ID_TERRA = 3


def normalize_amount(amount, token_decimals):
    return amount if token_decimals <= 8 else int(amount / (10 ** (token_decimals - 8)))


def assemble_transfer_payload(token_address, normalized_amount, to_address, token_chain_id, to_chain_id, fee):
    payload = '0x01' # payloadId
    payload += f'{normalized_amount:064x}'
    payload += strip_0x(encode_addr(token_address))
    payload += f'{token_chain_id:04x}'
    payload += strip_0x(encode_addr(to_address))
    payload += f'{to_chain_id:04x}'
    payload += f'{fee:064x}'
    return payload.lower()


def encode_addr(addr):
    # left-pad to 32 bytes with zeroes
    return f'0x{strip_0x(addr):0>64}'


def strip_0x(line):
    return line[2:] if line.startswith('0x') else line
