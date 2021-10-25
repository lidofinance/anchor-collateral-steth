import pytest
from brownie import Contract, ZERO_ADDRESS

ANCHOR_REWARDS_DISTRIBUTOR = '0x1234123412341234123412341234123412341234123412341234123412341234'
TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'

NO_LIQUIDATION_INTERVAL = 60 * 60 * 24
RESTRICTED_LIQUIDATION_INTERVAL = NO_LIQUIDATION_INTERVAL + 60 * 60 * 2

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

@pytest.fixture(scope='module')
def vault(
    beth_token,
    steth_token,
    bridge_connector,
    mock_rewards_liquidator,
    mock_insurance_connector,
    deployer,
    admin,
    liquidations_admin,
    AnchorVault,
    AnchorVaultProxy
):
    impl = AnchorVault.deploy({'from': deployer})
    impl.initialize(beth_token, steth_token, ZERO_ADDRESS, {'from': deployer})

    proxy = AnchorVaultProxy.deploy(impl, admin, {'from': deployer})

    vault = Contract.from_abi('AnchorVault', proxy.address, AnchorVault.abi)

    vault.initialize(beth_token, steth_token, admin, {'from': deployer})

    vault.configure(
        bridge_connector,
        mock_rewards_liquidator,
        mock_insurance_connector,
        liquidations_admin,
        NO_LIQUIDATION_INTERVAL,
        RESTRICTED_LIQUIDATION_INTERVAL,
        ANCHOR_REWARDS_DISTRIBUTOR,
        {'from': admin}
    )

    beth_token.set_minter(vault, {'from': admin})

    return vault


def test_forward_beth(
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
