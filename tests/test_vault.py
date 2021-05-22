import pytest
from brownie import ZERO_ADDRESS, chain, reverts, ETH_ADDRESS


TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'
BETH_DECIMALS = 18


@pytest.fixture(scope='function')
def vault(
    beth_token,
    mock_bridge_connector,
    mock_rewards_liquidator,
    deployer,
    admin,
    liquidations_admin,
    AnchorVault
):
    vault = AnchorVault.deploy(beth_token, admin, {'from': deployer})
    vault.configure(
        mock_bridge_connector,
        mock_rewards_liquidator,
        liquidations_admin,
        {'from': admin}
    )
    beth_token.set_minter(vault, {'from': admin})
    return vault


def test_initial_config_correct(
    vault,
    admin,
    beth_token,
    lido,
    mock_bridge_connector,
    mock_rewards_liquidator,
    liquidations_admin
):
    assert vault.admin() == admin
    assert vault.beth_token() == beth_token
    assert vault.bridge_connector() == mock_bridge_connector
    assert vault.rewards_liquidator() == mock_rewards_liquidator
    assert vault.liquidations_admin() == liquidations_admin
    assert vault.last_liquidation_time() == 0
    assert vault.last_liquidation_steth_balance() == 0
    assert vault.last_liquidation_shares_balance() == 0
    assert vault.last_liquidation_shares_steth_rate() == lido.getPooledEthByShares(10**18)

@pytest.mark.parametrize('amount', [1 * 10**18, 1 * 10**18 + 10])
def test_deposit(
    vault,
    vault_user,
    steth_token,
    beth_token,
    mock_bridge_connector,
    helpers,
    steth_adjusted_ammount,
    amount
):
    steth_balance_before = steth_token.balanceOf(vault_user)
    terra_balance_before = mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)

    steth_token.approve(vault, amount, {'from': vault_user})
    tx = vault.submit(amount, TERRA_ADDRESS, '0xab', {'from': vault_user})

    adjusted_amount = steth_adjusted_ammount(amount)

    helpers.assert_single_event_named('Deposited', tx, source=vault, evt_keys_dict={
        'sender': vault_user,
        'amount': adjusted_amount,
        'terra_address': TERRA_ADDRESS
    })

    helpers.assert_single_event_named('Test__Forwarded', tx, source=mock_bridge_connector, evt_keys_dict={
        'asset_name': 'bETH',
        'terra_address': TERRA_ADDRESS,
        'amount': adjusted_amount,
        'extra_data': '0xab'
    })

    assert beth_token.balanceOf(vault_user) == 0

    assert mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS) == terra_balance_before + adjusted_amount

    steth_balance_decrease = steth_balance_before - steth_token.balanceOf(vault_user)
    assert helpers.equal_with_precision(steth_balance_decrease, adjusted_amount, max_diff=1)


def test_withdraw(
    vault, 
    vault_user, 
    steth_token, 
    beth_token, 
    helpers, 
    withdraw_from_terra, 
    mock_bridge_connector, 
    deposit_to_terra
):
    amount = 1 * 10**18

    steth_balance_before = steth_token.balanceOf(vault_user)

    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)

    terra_balance_before = mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)

    withdraw_from_terra(TERRA_ADDRESS, vault_user, amount)

    assert beth_token.balanceOf(vault_user) == amount
    assert mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS) == terra_balance_before - amount

    tx = vault.withdraw(amount, {'from': vault_user})

    assert helpers.equal_with_precision(steth_token.balanceOf(vault_user), steth_balance_before, 10)

    helpers.assert_single_event_named('Withdrawn', tx, source=vault, evt_keys_dict={
        'recipient': vault_user,
        'amount': amount
    })


def test_withdraw_fails_on_balance(vault, vault_user, steth_token, withdraw_from_terra, deposit_to_terra):
    amount = 1 * 10**18

    steth_balance_before = steth_token.balanceOf(vault_user)

    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)

    withdraw_from_terra(TERRA_ADDRESS, vault_user, amount)

    with reverts():
        vault.withdraw(amount + 1, {'from': vault_user})


def test_change_admin(vault, stranger, admin, helpers):
    with reverts():
        vault.change_admin(stranger, {"from": stranger})

    tx = vault.change_admin(stranger, {"from": admin})

    helpers.assert_single_event_named('AdminChanged', tx, source=vault, evt_keys_dict={
        'new_admin': stranger
    })


def test_configuration(vault, stranger, admin, helpers):
    with reverts():
        vault.configure(ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, {"from": stranger})

    tx = vault.configure(ZERO_ADDRESS, ZERO_ADDRESS, ZERO_ADDRESS, {"from": admin})

    helpers.assert_single_event_named('BridgeConnectorUpdated', tx, source=vault, evt_keys_dict={
        'bridge_connector': ZERO_ADDRESS
    })
    helpers.assert_single_event_named('RewardsLiquidatorUpdated', tx, source=vault, evt_keys_dict={
        'rewards_liquidator': ZERO_ADDRESS
    })
    helpers.assert_single_event_named('LiquidationsAdminUpdated', tx, source=vault, evt_keys_dict={
        'liquidations_admin': ZERO_ADDRESS
    })


def test_set_bridge_connector(vault, stranger, admin, helpers):
    with reverts():
        vault.set_bridge_connector(ETH_ADDRESS, {"from": stranger})

    tx = vault.set_bridge_connector(ETH_ADDRESS, {"from": admin})
    helpers.assert_single_event_named('BridgeConnectorUpdated', tx, source=vault, evt_keys_dict={
        'bridge_connector': ETH_ADDRESS
    })


def test_set_rewards_liquidator(vault, stranger, admin, helpers):
    with reverts():
        vault.set_rewards_liquidator(ETH_ADDRESS, {"from": stranger})

    tx = vault.set_rewards_liquidator(ETH_ADDRESS, {"from": admin})
    helpers.assert_single_event_named('RewardsLiquidatorUpdated', tx, source=vault, evt_keys_dict={
        'rewards_liquidator': ETH_ADDRESS
    })


def test_set_liquidations_admin(vault, stranger, admin, helpers):
    with reverts():
        vault.set_liquidations_admin(ETH_ADDRESS, {"from": stranger})

    tx = vault.set_liquidations_admin(ETH_ADDRESS, {"from": admin})
    helpers.assert_single_event_named('LiquidationsAdminUpdated', tx, source=vault, evt_keys_dict={
        'liquidations_admin': ETH_ADDRESS
    })

