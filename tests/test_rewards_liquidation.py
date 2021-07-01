import pytest
from brownie import reverts, ZERO_ADDRESS, Contract
from brownie.network.state import Chain


ANCHOR_REWARDS_DISTRIBUTOR = '0x1234123412341234123412341234123412341234123412341234123412341234'

MAX_STETH_PRICE_DIFF_PERCENT = 10
MAX_ETH_PRICE_DIFF_PERCENT = 5

CURVE_STETH_POOL = '0xDC24316b9AE028F1497c275EB9192a3Ea0f67022'
CURVE_ETH_INDEX = 0
CURVE_STETH_INDEX = 1
SUSHISWAP_ROUTER_V2 = 'd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'
WETH_TOKEN = '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'

@pytest.fixture(scope='module')
def someone_with_money(lido, accounts):
    whale = accounts.at('0x00000000219ab540356cBB839Cbe05303d7705Fa', force=True)
    lido.submit(ZERO_ADDRESS, {"from": whale, "value": "3000000 ether"})
    return whale


@pytest.fixture(scope='module')
def liquidator(RewardsLiquidator, deployer, admin):
    return RewardsLiquidator.deploy(
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


def test_init(RewardsLiquidator, deployer, admin):
    max_steth_diff = int(MAX_STETH_PRICE_DIFF_PERCENT * 10**18 / 100)
    max_eth_diff = int(MAX_ETH_PRICE_DIFF_PERCENT * 10**18 / 100)

    with reverts():
        RewardsLiquidator.deploy(
            admin, 
            10**18+1,
            max_eth_diff,
            {'from': deployer}
        )

    with reverts():
        RewardsLiquidator.deploy(
            admin, 
            max_steth_diff,
            10**18+1,
            {'from': deployer}
        )

    liquidator = RewardsLiquidator.deploy(
        admin, 
        max_steth_diff,
        max_eth_diff,
        {'from': deployer}
    )

    assert liquidator.max_steth_price_difference_percent() == max_steth_diff
    assert liquidator.max_eth_price_difference_percent() == max_eth_diff
    assert liquidator.admin() == admin

def test_sells_steth_balance_to_ust(
    liquidator,
    steth_token,
    ust_token,
    vault_user,
    ust_recipient,
    helpers,
):
    steth_amount = 10**18
    steth_token.transfer(liquidator, steth_amount, {'from': vault_user})

    tx = liquidator.liquidate(ust_recipient)

    assert liquidator.balance() == 0
    assert steth_token.balanceOf(liquidator) < 100

    evt = helpers.assert_single_event_named('SoldStethToUST', tx, source=liquidator)

    assert abs(evt['steth_amount'] - steth_amount) < 100
    assert evt['ust_amount'] > 0

    assert ust_token.balanceOf(ust_recipient) == evt['ust_amount']


def test_configure(liquidator, admin, stranger):
    with reverts():
        liquidator.configure(10**18, 10**18, {"from": stranger})

    with reverts():
        liquidator.configure(10**18 + 1, 10**18, {"from": admin})

    with reverts():
        liquidator.configure(10**18, 10**18 + 1, {"from": admin})
    
    new_max_eth_diff = 0.5 * 10**18
    new_max_steth_diff = 0.6 * 10**18

    assert liquidator.max_steth_price_difference_percent() != new_max_steth_diff
    assert liquidator.max_eth_price_difference_percent() != new_max_eth_diff
    liquidator.configure(new_max_steth_diff, new_max_eth_diff, {"from": admin})

    assert liquidator.max_steth_price_difference_percent() == new_max_steth_diff
    assert liquidator.max_eth_price_difference_percent() == new_max_eth_diff

    with reverts():
        liquidator.change_admin(stranger, {"from": stranger})

    liquidator.change_admin(stranger, {"from": admin})
    assert liquidator.admin() == stranger


def test_steth_pool_price_change(
    interface,
    someone_with_money,
    steth_token,
    vault_user,
    ust_recipient,
    liquidator
):
    steth_pool = interface.Curve(CURVE_STETH_POOL)

    old_steth_price = steth_pool.get_dy(CURVE_STETH_INDEX,CURVE_ETH_INDEX,10**18)

    liquidity_amount = 3 * 10**24
    steth_token.approve(steth_pool, liquidity_amount, {"from": someone_with_money})
    steth_pool.add_liquidity([0,liquidity_amount], 0, {"from": someone_with_money})

    new_steth_price = steth_pool.get_dy(CURVE_STETH_INDEX,CURVE_ETH_INDEX,10**18)
    assert old_steth_price*((100-MAX_STETH_PRICE_DIFF_PERCENT)/100) >= new_steth_price

    steth_amount = 10**18
    steth_token.transfer(liquidator, steth_amount, {'from': vault_user})

    with reverts():
        liquidator.liquidate(ust_recipient)


def test_eth_pool_price_change(
    interface,
    someone_with_money,
    steth_token,
    vault_user,
    ust_recipient,
    liquidator,
    ust_token
):
    chain = Chain()
    pool = interface.Sushi(SUSHISWAP_ROUTER_V2)

    (_, old_eth_price) = pool.getAmountsOut(10**18, [WETH_TOKEN, ust_token])
    deadline = chain.time() + 3600
    pool.swapExactETHForTokens(
        779298770, 
        [WETH_TOKEN, ust_token], 
        someone_with_money, 
        deadline,
        {"from": someone_with_money, "amount": 2.9*10**24}
    )
    (_, new_price) = pool.getAmountsOut(10**18, [WETH_TOKEN, ust_token]) 
    assert new_price < old_eth_price * (100-MAX_ETH_PRICE_DIFF_PERCENT)/100

    steth_amount = 10**18
    steth_token.transfer(liquidator, steth_amount, {'from': vault_user})

    with reverts():
        liquidator.liquidate(ust_recipient)