import pytest
from brownie import chain, reverts
from helpers import equal_with_epsilon


TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'


@pytest.fixture(scope='module')
def mock_bridge(accounts):
    return accounts.add()


@pytest.fixture(scope='function')
def mock_bridge_connector(beth_token, deployer, admin, mock_bridge, MockBridgeConnector):
    return MockBridgeConnector.deploy(beth_token, mock_bridge, {'from': deployer})


@pytest.fixture(scope='function')
def mock_rewards_liquidator(MockRewardsLiquidator, deployer):
    return MockRewardsLiquidator.deploy({'from': deployer})
    
@pytest.fixture(scope='function')
def withdraw_from_terra(mock_bridge, beth_token):
  def withdraw(to_address, amount):
    beth_token.transfer(to_address, amount, {'from': mock_bridge})
  return withdraw


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
    assert vault.liquidation_base_balance() == 0


def test_deposit(vault, vault_user, steth_token, beth_token, mock_bridge_connector, helpers):
    amount = 1 * 10**18
    steth_balance_before = steth_token.balanceOf(vault_user)

    steth_token.approve(vault, amount, {'from': vault_user})
    tx = vault.submit(amount, TERRA_ADDRESS, '0xab', {'from': vault_user})

    helpers.assert_single_event_named('Deposited', tx, source=vault, evt_keys_dict={
        'sender': vault_user,
        'amount': amount,
        'terra_address': TERRA_ADDRESS
    })

    helpers.assert_single_event_named('Test__Forwarded', tx, source=mock_bridge_connector, evt_keys_dict={
        'asset_name': 'bETH',
        'terra_address': TERRA_ADDRESS,
        'amount': amount,
        'extra_data': '0xab'
    })

    assert beth_token.balanceOf(vault_user) == 0

    steth_balance_decrease = steth_balance_before - steth_token.balanceOf(vault_user)
    assert helpers.equal_with_precision(steth_balance_decrease, amount, max_diff=1)


def test_withdraw(vault, vault_user, steth_token, beth_token, withdraw_from_terra, helpers):
    amount = 1 * 10**18

    steth_balance_before = steth_token.balanceOf(vault_user)

    steth_token.approve(vault, amount, {'from': vault_user})
    vault.submit(amount, TERRA_ADDRESS, '0xab', {'from': vault_user})

    withdraw_from_terra(vault_user, amount)

    assert beth_token.balanceOf(vault_user) == amount
    tx = vault.withdraw(amount, {'from': vault_user})

    assert equal_with_epsilon(steth_token.balanceOf(vault_user), steth_balance_before)

    helpers.assert_single_event_named('Withdrawn', tx, source=vault, evt_keys_dict={
        'recipient': vault_user,
        'amount': amount
    })


def test_withdraw_fails_on_balance(vault, vault_user, steth_token, beth_token, mock_bridge_connector, helpers, admin):
    amount = 1 * 10**18

    steth_balance_before = steth_token.balanceOf(vault_user)

    steth_token.approve(vault, amount, {'from': vault_user})
    vault.submit(amount, TERRA_ADDRESS, '0xab', {'from': vault_user})

    withdraw_from_terra(vault_user, amount)

    with reverts():
        vault.withdraw(amount + 1, {'from': vault_user})