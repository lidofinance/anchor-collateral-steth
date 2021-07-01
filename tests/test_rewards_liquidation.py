import pytest
from brownie import chain, reverts, ZERO_ADDRESS
from brownie.network.event import _decode_logs

from test_vault import vault, ANCHOR_REWARDS_DISTRIBUTOR


MAX_STETH_PRICE_DIFF_PERCENT = 10
MAX_ETH_PRICE_DIFF_PERCENT = 5

CURVE_STETH_POOL = '0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'
CURVE_ETH_INDEX = 0
CURVE_STETH_INDEX = 1
SUSHISWAP_ROUTER_V2 = '0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'
WETH_TOKEN = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'


@pytest.fixture(scope='module')
def whale(lido, accounts):
    acct = accounts[5]
    lido.submit(ZERO_ADDRESS, {'from': acct, 'value': acct.balance() // 2})
    return acct


@pytest.fixture(scope='module')
def mock_vault(accounts, deployer):
    acct = accounts.add()
    deployer.transfer(acct, 10**18)
    return acct


@pytest.fixture(scope='module')
def liquidator(RewardsLiquidator, deployer, admin, mock_vault):
    return RewardsLiquidator.deploy(
        mock_vault,
        admin,
        int(MAX_STETH_PRICE_DIFF_PERCENT * 10**18 / 100),
        int(MAX_ETH_PRICE_DIFF_PERCENT * 10**18 / 100),
        {'from': deployer}
    )


@pytest.fixture(scope='module')
def ust_recipient(accounts, ust_token):
    acct = accounts.add()
    assert ust_token.balanceOf(acct) == 0
    return acct


def test_init(RewardsLiquidator, deployer, admin, mock_vault, helpers):
    max_steth_diff = int(MAX_STETH_PRICE_DIFF_PERCENT * 10**18 / 100)
    max_eth_diff = int(MAX_ETH_PRICE_DIFF_PERCENT * 10**18 / 100)

    with reverts():
        RewardsLiquidator.deploy(
            mock_vault,
            admin,
            10**18+1,
            max_eth_diff,
            {'from': deployer}
        )

    with reverts():
        RewardsLiquidator.deploy(
            mock_vault,
            admin,
            max_steth_diff,
            10**18+1,
            {'from': deployer}
        )

    liquidator = RewardsLiquidator.deploy(
        mock_vault,
        admin,
        max_steth_diff,
        max_eth_diff,
        {'from': deployer}
    )

    assert liquidator.max_steth_price_difference_percent() == max_steth_diff
    assert liquidator.max_eth_price_difference_percent() == max_eth_diff
    assert liquidator.admin() == admin
    assert liquidator.vault() == mock_vault

    tx_events = _decode_logs(liquidator.tx.logs)

    assert 'PriceDifferenceChanged' in tx_events
    assert 'AdminChanged' in tx_events

    assert tx_events['PriceDifferenceChanged']['max_steth_price_difference_percent'] == max_steth_diff
    assert tx_events['PriceDifferenceChanged']['max_eth_price_difference_percent'] == max_eth_diff
    assert tx_events['AdminChanged']['new_admin'] == admin


def test_only_allows_liquidation_by_vault(
    liquidator,
    steth_token,
    vault_user,
    mock_vault,
    stranger,
    ust_recipient,
):
    steth_amount = 10**18
    steth_token.transfer(liquidator, steth_amount, {'from': vault_user})

    with reverts('unauthorized'):
        liquidator.liquidate(ust_recipient, {'from': stranger})

    liquidator.liquidate(ust_recipient, {'from': mock_vault})


def test_sells_steth_balance_to_ust(
    liquidator,
    steth_token,
    ust_token,
    vault_user,
    mock_vault,
    ust_recipient,
    helpers,
):
    steth_amount = 10**18
    steth_token.transfer(liquidator, steth_amount, {'from': vault_user})

    tx = liquidator.liquidate(ust_recipient, {'from': mock_vault})

    assert liquidator.balance() == 0
    assert steth_token.balanceOf(liquidator) < 100

    evt = helpers.assert_single_event_named('SoldStethToUST', tx, source=liquidator)

    assert abs(evt['steth_amount'] - steth_amount) < 100
    assert evt['ust_amount'] > 0

    assert ust_token.balanceOf(ust_recipient) == evt['ust_amount']


def test_configure(liquidator, admin, stranger, helpers):
    with reverts():
        liquidator.configure(10**18, 10**18, {'from': stranger})

    with reverts():
        liquidator.configure(10**18 + 1, 10**18, {'from': admin})

    with reverts():
        liquidator.configure(10**18, 10**18 + 1, {'from': admin})
    
    new_max_eth_diff = 0.5 * 10**18
    new_max_steth_diff = 0.6 * 10**18

    assert liquidator.max_steth_price_difference_percent() != new_max_steth_diff
    assert liquidator.max_eth_price_difference_percent() != new_max_eth_diff
    tx = liquidator.configure(new_max_steth_diff, new_max_eth_diff, {'from': admin})

    assert liquidator.max_steth_price_difference_percent() == new_max_steth_diff
    assert liquidator.max_eth_price_difference_percent() == new_max_eth_diff
   
    helpers.assert_single_event_named('PriceDifferenceChanged', tx, source=liquidator, evt_keys_dict={
        'max_steth_price_difference_percent': new_max_steth_diff,
        'max_eth_price_difference_percent': new_max_eth_diff
    })

    with reverts():
        liquidator.change_admin(stranger, {'from': stranger})

    tx = liquidator.change_admin(stranger, {'from': admin})
    assert liquidator.admin() == stranger
    
    helpers.assert_single_event_named('AdminChanged', tx, source=liquidator, evt_keys_dict={
        'new_admin': stranger
    })


def test_fails_on_excess_steth_price_change(
    interface,
    whale,
    steth_token,
    vault_user,
    mock_vault,
    ust_recipient,
    liquidator
):
    steth_pool = interface.Curve(CURVE_STETH_POOL)

    old_steth_price = steth_pool.get_dy(CURVE_STETH_INDEX,CURVE_ETH_INDEX,10**18)

    liquidity_amount = 3 * 10**24
    steth_token.approve(steth_pool, liquidity_amount, {'from': whale})
    steth_pool.add_liquidity([0, liquidity_amount], 0, {'from': whale})

    new_steth_price = steth_pool.get_dy(CURVE_STETH_INDEX,CURVE_ETH_INDEX,10**18)
    assert old_steth_price * ((100 - MAX_STETH_PRICE_DIFF_PERCENT) / 100) >= new_steth_price

    steth_amount = 10**18
    steth_token.transfer(liquidator, steth_amount, {'from': vault_user})

    with reverts():
        liquidator.liquidate(ust_recipient, {'from': mock_vault})


def test_fails_on_excess_eth_price_change(
    interface,
    whale,
    steth_token,
    vault_user,
    ust_recipient,
    liquidator,
    ust_token,
    mock_vault
):
    pool = interface.Sushi(SUSHISWAP_ROUTER_V2)

    (_, old_eth_price) = pool.getAmountsOut(10**18, [WETH_TOKEN, ust_token])
    deadline = chain.time() + 3600
    pool.swapExactETHForTokens(
        779298770, 
        [WETH_TOKEN, ust_token], 
        whale,
        deadline,
        {'from': whale, 'amount': 2.9*10**24}
    )
    (_, new_price) = pool.getAmountsOut(10**18, [WETH_TOKEN, ust_token]) 
    assert new_price < old_eth_price * (100 - MAX_ETH_PRICE_DIFF_PERCENT) / 100

    steth_amount = 10**18
    steth_token.transfer(liquidator, steth_amount, {'from': vault_user})

    with reverts():
        liquidator.liquidate(ust_recipient, {'from': mock_vault})


TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'


def test_integrates_with_real_vault(
    RewardsLiquidator,
    mock_bridge_connector,
    steth_token,
    deployer,
    admin,
    vault,
    vault_user,
    liquidations_admin,
    lido_oracle_report,
    steth_adjusted_ammount,
    helpers
):
    liquidator = RewardsLiquidator.deploy(
        vault,
        admin,
        int(MAX_STETH_PRICE_DIFF_PERCENT * 10**18 / 100),
        int(MAX_ETH_PRICE_DIFF_PERCENT * 10**18 / 100),
        {'from': deployer}
    )

    vault.set_rewards_liquidator(liquidator, {'from': admin})

    amount = 1 * 10**18
    adjusted_amount = steth_adjusted_ammount(amount)

    steth_token.approve(vault, amount, {'from': vault_user})
    vault.submit(amount, TERRA_ADDRESS, b'', {'from': vault_user})
    assert mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS) == adjusted_amount

    lido_oracle_report(steth_rebase_mult=1.01)

    tx = vault.collect_rewards({'from': liquidations_admin})

    vault_evt = helpers.assert_single_event_named('RewardsCollected', tx, source=vault)

    assert vault_evt['steth_amount'] > 0
    assert vault_evt['ust_amount'] > 0

    liquidator_evt = helpers.assert_single_event_named('SoldStethToUST', tx, source=liquidator)

    assert abs(liquidator_evt['steth_amount'] - vault_evt['steth_amount']) < 10
    assert liquidator_evt['ust_amount'] == vault_evt['ust_amount']
