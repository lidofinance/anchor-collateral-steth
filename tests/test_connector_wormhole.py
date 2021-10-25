import pytest
from brownie import Contract, ZERO_ADDRESS

TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'

@pytest.fixture(scope='module')
def bridge_connector(
    beth_token,  
    ust_token,
    mock_wormhole_token_bridge, 
    deployer, 
    BridgeConnectorWormhole
):
    return BridgeConnectorWormhole.deploy(
        mock_wormhole_token_bridge, 
        beth_token,
        ust_token,
        {'from': deployer}
    )

def test_anchor_vault_submit(
    vault, 
    vault_user, 
    beth_token,
    steth_token, 
    helpers,
    mock_wormhole_token_bridge
):
    amount = 1 * 10**18

    steth_token.approve(vault, amount, {'from': vault_user})

    tx = vault.submit(amount, TERRA_ADDRESS, b'', {'from': vault_user})

    helpers.assert_single_event_named('WormholeTransfer', tx, source=mock_wormhole_token_bridge, evt_keys_dict={
        'token': beth_token.address, 
        'amount': amount, 
        'recipientChain': 3, 
        'recipient': TERRA_ADDRESS, 
        'arbiterFee': 0, 
        'nonce': 0,
    })


def test_forward_beth(
    vault, 
    vault_user, 
    beth_token, 
    helpers,
    bridge_connector,
    mock_wormhole_token_bridge
):
    amount = 1 * 10**18
    tx = bridge_connector.forward_beth(TERRA_ADDRESS, amount, b'')
    helpers.assert_single_event_named('WormholeTransfer', tx, source=mock_wormhole_token_bridge, evt_keys_dict={
        'token': beth_token.address, 
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


def test_adjust_amount(
    helpers,
    bridge_connector,
    mock_wormhole_token_bridge
):
    decimals = 18
    amount = 1 * 10**decimals
    adjusted_amount = bridge_connector.adjust_amount(amount, decimals)
    assert adjusted_amount == amount