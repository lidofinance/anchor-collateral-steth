import pytest
from brownie import Contract, ZERO_ADDRESS

TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'
BETH_TOKEN = '0x707F9118e33A9B8998beA41dd0d46f38bb963FC8'

@pytest.fixture(scope='module')
def bridge_connector(
    mock_wormhole_token_bridge, 
    deployer, 
    BridgeConnectorWormhole
):
    return BridgeConnectorWormhole.deploy(
        mock_wormhole_token_bridge,
        {'from': deployer}
    )

def test_anchor_vault_submit(
    vault, 
    vault_user, 
    steth_token, 
    helpers,
    mock_wormhole_token_bridge
):
    amount = 1 * 10**18

    steth_token.approve(vault, amount, {'from': vault_user})

    tx = vault.submit(amount, TERRA_ADDRESS, b'', {'from': vault_user})

    helpers.assert_single_event_named('WormholeTransfer', tx, source=mock_wormhole_token_bridge, evt_keys_dict={
        'token': BETH_TOKEN, 
        'amount': amount, 
        'recipientChain': 3, 
        'recipient': TERRA_ADDRESS, 
        'arbiterFee': 0, 
        'nonce': 0,
    })


def test_forward_beth(
    helpers,
    bridge_connector,
    mock_wormhole_token_bridge
):
    amount = 1 * 10**18
    tx = bridge_connector.forward_beth(TERRA_ADDRESS, amount, b'')
    helpers.assert_single_event_named('WormholeTransfer', tx, source=mock_wormhole_token_bridge, evt_keys_dict={
        'token': BETH_TOKEN, 
        'amount': amount, 
        'recipientChain': 3, 
        'recipient': TERRA_ADDRESS, 
        'arbiterFee': 0, 
        'nonce': 0,
    })


def test_forward_ust(
    ust_token,
    helpers,
    bridge_connector,
    mock_wormhole_token_bridge
):
    amount = 1 * 10**18
    tx = bridge_connector.forward_ust(TERRA_ADDRESS, amount, b'')
    helpers.assert_single_event_named('WormholeTransfer', tx, source=mock_wormhole_token_bridge, evt_keys_dict={
        'token': ust_token.address, 
        'amount': amount, 
        'recipientChain': 3, 
        'recipient': TERRA_ADDRESS, 
        'arbiterFee': 0, 
        'nonce': 0,
    })

@pytest.mark.parametrize(
    'amount,decimals,expected',
    [
        (11111111111111111111, 18, 11111111110000000000),
        (11111111111111111111, 10, 11111111111111111100),
        (11111111111111111111, 9, 11111111111111111110),
        (11111111111111111111, 8, 11111111111111111111),
        (11111111111111111111, 5, 11111111111111111111),
    ]
)
def test_adjust_amount(
    amount,
    decimals,
    expected,
    bridge_connector
):
    assert bridge_connector.adjust_amount(amount, decimals) == expected
