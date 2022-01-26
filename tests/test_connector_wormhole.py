import pytest
from brownie import ZERO_ADDRESS, reverts, Wei, AnchorVault

TERRA_CHAIN_ID = 3
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

def test_bridge_connector_wormhole_requires_non_zero_address(
    deployer,
    BridgeConnectorWormhole
):
    with reverts("bridge is zero address"):
        BridgeConnectorWormhole.deploy(ZERO_ADDRESS, {'from': deployer})

def test_anchor_vault_submit(
    vault, 
    vault_user, 
    steth_token, 
    helpers,
    mock_wormhole_token_bridge
):
    amount = 1 * 10**18

    steth_token.approve(vault, amount, {'from': vault_user})

    tx = vault.submit(amount, TERRA_ADDRESS, '', vault.version(), {'from': vault_user})

    helpers.assert_single_event_named('WormholeTransfer', tx, source=mock_wormhole_token_bridge, evt_keys_dict={
        'token': BETH_TOKEN,
        'amount': amount,
        'recipientChain': TERRA_CHAIN_ID,
        'recipient': TERRA_ADDRESS,
        'arbiterFee': 0,
        'nonce': 0,
        'value': 0,
    })


@pytest.mark.parametrize(
    'amount,extra_data,eth_msg_value,expected_amount,expected_arbiter_fee,expected_nonce',
    [
        (
            1 * 10**18,
            '0x00000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
            Wei("1 ether"),
            1 * 10**18,
            115792089237316195423570985008687907853269984665640564039457584007913129639935,
            4294967295
        ),
        (
            500,
            '0x0000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
            Wei("5 gwei"),
            500,
            115792089237316195423570985008687907853269984665640564039457584007913129639935,
            0
        ),
        (
            100,
            '0x00000000000000000000000000000000000000000000000000000000ffffffff',
            Wei("100"),
            100,
            0,
            4294967295
        ),
        (
            0,
            '0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',
            Wei("0"),
            0,
            0,
            0
        ),
        (0, '', Wei("0"), 0, 0, 0),
    ]
)
def test_forward_beth_positive(
    vault_user,
    helpers,
    bridge_connector,
    mock_wormhole_token_bridge,
    amount,
    extra_data,
    eth_msg_value,
    expected_amount,
    expected_arbiter_fee,
    expected_nonce
):
    tx = bridge_connector.forward_beth(TERRA_ADDRESS, amount, extra_data, { 'from': vault_user, 'value': eth_msg_value })

    helpers.assert_single_event_named('WormholeTransfer', tx, source=mock_wormhole_token_bridge, evt_keys_dict={
        'token': BETH_TOKEN,
        'amount': expected_amount,
        'recipientChain': TERRA_CHAIN_ID,
        'recipient': TERRA_ADDRESS,
        'arbiterFee': expected_arbiter_fee,
        'nonce': expected_nonce,
        'value': eth_msg_value,
    })


@pytest.mark.parametrize(
    'amount,extra_data',
    [
        (
            1 * 10**18,
            '0x000000000000000000000000000000000000000000000000000000ffffffffff',
        ),
        (
            1 * 10**18,
            '0x0000000000000000000000000000000000000000000000000000001000000000',
        ),
    ]
)
def test_forward_beth_negative(
    bridge_connector,
    amount,
    extra_data,
):
    with reverts('nonce exceeds size of uint32 (4 bytes)'):
        bridge_connector.forward_beth(TERRA_ADDRESS, amount, extra_data)


@pytest.mark.parametrize(
    'amount,extra_data,eth_msg_value,expected_amount,expected_arbiter_fee,expected_nonce',
    [
        (
            1 * 10**18,
            '0x00000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
            Wei("1 ether"),
            1 * 10**18,
            115792089237316195423570985008687907853269984665640564039457584007913129639935,
            4294967295
        ),
        (
            500,
            '0x0000000000000000000000000000000000000000000000000000000000000000ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff',
            Wei("5 gwei"),
            500,
            115792089237316195423570985008687907853269984665640564039457584007913129639935,
            0
        ),
        (
            100,
            '0x00000000000000000000000000000000000000000000000000000000ffffffff',
            Wei("100"),
            100,
            0,
            4294967295
        ),
        (
            0,
            '0x00000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000',
            Wei("0"),
            0,
            0,
            0
        ),
        (0, '', Wei("0"), 0, 0, 0),
    ]
)
def test_forward_ust_positive(
    vault_user,
    ust_token,
    helpers,
    bridge_connector,
    mock_wormhole_token_bridge,
    amount,
    extra_data,
    eth_msg_value,
    expected_amount,
    expected_arbiter_fee,
    expected_nonce
):
    tx = bridge_connector.forward_ust(TERRA_ADDRESS, amount, extra_data, { 'from': vault_user, 'value': eth_msg_value })

    helpers.assert_single_event_named('WormholeTransfer', tx, source=mock_wormhole_token_bridge, evt_keys_dict={
        'token': ust_token.address,
        'amount': expected_amount,
        'recipientChain': 3,
        'recipient': TERRA_ADDRESS,
        'arbiterFee': expected_arbiter_fee,
        'nonce': expected_nonce,
        'value': eth_msg_value,
    })


@pytest.mark.parametrize(
    'amount,extra_data',
    [
        (
            1 * 10**18,
            '0x000000000000000000000000000000000000000000000000000000ffffffffff',
        ),
        (
            1 * 10**18,
            '0x0000000000000000000000000000000000000000000000000000001000000000',
        ),
    ]
)
def test_forward_ust_negative(
    bridge_connector,
    amount,
    extra_data,
):
    with reverts('nonce exceeds size of uint32 (4 bytes)'):
        bridge_connector.forward_ust(TERRA_ADDRESS, amount, extra_data)


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
    bridge_connector,
    amount,
    decimals,
    expected,
):
    assert bridge_connector.adjust_amount(amount, decimals) == expected
