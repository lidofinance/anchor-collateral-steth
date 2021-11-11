import pytest
import time
from brownie import chain, reverts, ZERO_ADDRESS
from brownie.network.event import _decode_logs

from test_vault import vault, ANCHOR_REWARDS_DISTRIBUTOR


MAX_STETH_ETH_PRICE_DIFF_PERCENT = 1.11
MAX_ETH_USDC_PRICE_DIFF_PERCENT = 1.22
MAX_USDC_UST_PRICE_DIFF_PERCENT = 0.55
MAX_STETH_UST_PRICE_DIFF_PERCENT = 2.33

CURVE_STETH_POOL = "0xDC24316b9AE028F1497c275EB9192a3Ea0f67022"
CURVE_UST_POOL = "0x890f4e345B1dAED0367A877a1612f86A1f86985f"
CURVE_USDC_POOL = "0xB0a0716841F2Fc03fbA72A891B8Bb13584F52F2d"
CURVE_ETH_INDEX = 0
CURVE_STETH_INDEX = 1
CURVE_USDC_INDEX = 2
CURVE_UST_INDEX = 0

UNISWAP_ROUTER_V3 = "0xE592427A0AEce92De3Edee1F18E0157C05861564"
UNISWAP_USDC_POOL_3_FEE = 3000
WETH_TOKEN = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
WETH_DECIMALS = 18
USDC_TOKEN = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
USDC_DECIMALS = 6


@pytest.fixture(scope="module")
def whale(lido, accounts, ust_token, usdc_token):
    acct = accounts[5]
    lido.submit(ZERO_ADDRESS, {"from": acct, "value": acct.balance() // 2})

    ust_amount = 1_000_000_000 * 10 ** 18
    ust_owner = accounts.at(ust_token.owner(), force=True)
    ust_token.mint(acct, ust_amount, {"from": ust_owner})
    assert ust_token.balanceOf(acct) == ust_amount

    usdc_amount = 1_000_000_000 * 10 ** 6
    usdc_masterMinter = accounts.at(usdc_token.masterMinter(), force=True)
    usdc_token.configureMinter(usdc_masterMinter, usdc_amount, {"from": usdc_masterMinter})
    print(usdc_token.minterAllowance(usdc_masterMinter))
    usdc_token.mint(acct, usdc_amount, {"from": usdc_masterMinter})
    assert usdc_token.balanceOf(acct) == usdc_amount

    return acct


@pytest.fixture(scope="module")
def mock_vault(accounts, deployer):
    acct = accounts.add()
    deployer.transfer(acct, 10 ** 18)
    return acct


@pytest.fixture(scope="module")
def liquidator(RewardsLiquidator, deployer, admin, mock_vault):
    return RewardsLiquidator.deploy(
        mock_vault,
        admin,
        int(MAX_STETH_ETH_PRICE_DIFF_PERCENT * 10 ** 18 / 100),
        int(MAX_ETH_USDC_PRICE_DIFF_PERCENT * 10 ** 18 / 100),
        int(MAX_USDC_UST_PRICE_DIFF_PERCENT * 10 ** 18 / 100),
        int(MAX_STETH_UST_PRICE_DIFF_PERCENT * 10 ** 18 / 100),
        {"from": deployer},
    )


@pytest.fixture(scope="module")
def ust_recipient(accounts, ust_token):
    acct = accounts.add()
    assert ust_token.balanceOf(acct) == 0
    return acct


def test_init(RewardsLiquidator, deployer, admin, mock_vault, helpers):
    max_steth_eth_diff = int(MAX_STETH_ETH_PRICE_DIFF_PERCENT * 10 ** 18 / 100)
    max_eth_usdc_diff = int(MAX_ETH_USDC_PRICE_DIFF_PERCENT * 10 ** 18 / 100)
    max_usdc_ust_diff = int(MAX_USDC_UST_PRICE_DIFF_PERCENT * 10 ** 18 / 100)
    max_steth_ust_diff = int(MAX_STETH_UST_PRICE_DIFF_PERCENT * 10 ** 18 / 100)

    with reverts():
        RewardsLiquidator.deploy(mock_vault, admin, 10 ** 18 + 1, max_eth_usdc_diff, 10 ** 18 + 1, 10 ** 18 + 1, {"from": deployer})

    with reverts():
        RewardsLiquidator.deploy(mock_vault, admin, max_steth_eth_diff, 10 ** 18 + 1, 10 ** 18 + 1, 10 ** 18 + 1, {"from": deployer})

    with reverts():
        RewardsLiquidator.deploy(mock_vault, admin, 10 ** 18 + 1, 10 ** 18 + 1, max_usdc_ust_diff, 10 ** 18 + 1, {"from": deployer})

    with reverts():
        RewardsLiquidator.deploy(mock_vault, admin, 10 ** 18 + 1, 10 ** 18 + 1, 10 ** 18 + 1, max_steth_ust_diff, {"from": deployer})

    liquidator = RewardsLiquidator.deploy(
        mock_vault, admin, max_steth_eth_diff, max_eth_usdc_diff, max_usdc_ust_diff, max_steth_ust_diff, {"from": deployer}
    )
    assert liquidator.max_steth_eth_price_difference_percent() == max_steth_eth_diff
    assert liquidator.max_eth_usdc_price_difference_percent() == max_eth_usdc_diff
    assert liquidator.max_usdc_ust_price_difference_percent() == max_usdc_ust_diff
    assert liquidator.max_steth_ust_price_difference_percent() == max_steth_ust_diff
    assert liquidator.admin() == admin
    assert liquidator.vault() == mock_vault

    tx_events = _decode_logs(liquidator.tx.logs)

    assert "PoolsChanged" in tx_events
    assert "PriceDifferenceChanged" in tx_events
    assert "AdminChanged" in tx_events
 
    assert tx_events["PoolsChanged"]["curve_steth_pool"] == CURVE_STETH_POOL
    assert tx_events["PoolsChanged"]["curve_ust_pool"] == CURVE_UST_POOL
    assert tx_events["PoolsChanged"]["uniswap_router_v3"] == UNISWAP_ROUTER_V3
    assert tx_events["PoolsChanged"]["uniswap_usdc_pool_fee"] == UNISWAP_USDC_POOL_3_FEE
    assert tx_events["PoolsChanged"]["curve_eth_index"] == CURVE_ETH_INDEX
    assert tx_events["PoolsChanged"]["curve_steth_index"] == CURVE_STETH_INDEX
    assert tx_events["PoolsChanged"]["curve_usdc_index"] == CURVE_USDC_INDEX
    assert tx_events["PoolsChanged"]["curve_ust_index"] == CURVE_UST_INDEX

    assert tx_events["PriceDifferenceChanged"]["max_steth_eth_price_difference_percent"] == max_steth_eth_diff
    assert tx_events["PriceDifferenceChanged"]["max_eth_usdc_price_difference_percent"] == max_eth_usdc_diff
    assert tx_events["PriceDifferenceChanged"]["max_usdc_ust_price_difference_percent"] == max_usdc_ust_diff
    assert tx_events["PriceDifferenceChanged"]["max_steth_ust_price_difference_percent"] == max_steth_ust_diff
    assert tx_events["AdminChanged"]["new_admin"] == admin


def test_only_allows_liquidation_by_vault(
    liquidator,
    steth_token,
    vault_user,
    mock_vault,
    stranger,
    ust_recipient,
):
    steth_amount = 2 * 10 ** 18
    steth_token.transfer(liquidator, steth_amount, {"from": vault_user})

    with reverts("unauthorized"):
        liquidator.liquidate(ust_recipient, {"from": stranger})

    liquidator.liquidate(ust_recipient, {"from": mock_vault})


def test_sells_steth_balance_to_ust(
    liquidator,
    steth_token,
    ust_token,
    vault_user,
    mock_vault,
    ust_recipient,
    helpers,
):
    steth_amount = 10 ** 18
    steth_token.transfer(liquidator, steth_amount, {"from": vault_user})

    tx = liquidator.liquidate(ust_recipient, {"from": mock_vault})

    assert liquidator.balance() == 0
    assert steth_token.balanceOf(liquidator) < 100

    evt = helpers.assert_single_event_named("SoldStethToUST", tx, source=liquidator)

    assert abs(evt["steth_amount"] - steth_amount) < 100
    assert evt["ust_amount"] > 0

    assert ust_token.balanceOf(ust_recipient) == evt["ust_amount"]


def test_configure(liquidator, admin, stranger, helpers):
    with reverts():
        liquidator.configure(10 ** 18, 10 ** 18, 10 ** 18, 10 ** 18, {"from": stranger})

    with reverts():
        liquidator.configure(10 ** 18 + 1, 10 ** 18, 10 ** 18, 10 ** 18, {"from": admin})

    with reverts():
        liquidator.configure(10 ** 18, 10 ** 18 + 1, 10 ** 18, 10 ** 18, {"from": admin})

    with reverts():
        liquidator.configure(10 ** 18, 10 ** 18, 10 ** 18 + 1, 10 ** 18, {"from": admin})

    with reverts():
        liquidator.configure(10 ** 18, 10 ** 18, 10 ** 18, 10 ** 18 + 1, {"from": admin})

    new_max_eth_usdc_diff = 0.5 * 10 ** 18
    new_max_steth_eth_diff = 0.6 * 10 ** 18

    new_max_steth_eth_diff = 0.5 * 10 ** 18
    new_max_eth_usdc_diff = 0.5 * 10 ** 18
    new_max_usdc_ust_diff = 0.5 * 10 ** 18
    new_max_steth_ust_diff = 0.6 * 10 ** 18

    assert liquidator.max_steth_eth_price_difference_percent() != new_max_steth_eth_diff
    assert liquidator.max_eth_usdc_price_difference_percent() != new_max_eth_usdc_diff
    assert liquidator.max_usdc_ust_price_difference_percent() != new_max_usdc_ust_diff
    assert liquidator.max_steth_ust_price_difference_percent() != new_max_steth_ust_diff

    tx = liquidator.configure(new_max_steth_eth_diff, new_max_eth_usdc_diff, new_max_usdc_ust_diff, new_max_steth_ust_diff, {"from": admin})

    assert liquidator.max_steth_eth_price_difference_percent() == new_max_steth_eth_diff
    assert liquidator.max_eth_usdc_price_difference_percent() == new_max_eth_usdc_diff
    assert liquidator.max_usdc_ust_price_difference_percent() == new_max_usdc_ust_diff
    assert liquidator.max_steth_ust_price_difference_percent() == new_max_steth_ust_diff

    helpers.assert_single_event_named(
        "PriceDifferenceChanged",
        tx,
        source=liquidator,
        evt_keys_dict={
            "max_steth_eth_price_difference_percent": new_max_steth_eth_diff,
            "max_eth_usdc_price_difference_percent": new_max_eth_usdc_diff,
            "max_usdc_ust_price_difference_percent": new_max_usdc_ust_diff,
            "max_steth_ust_price_difference_percent": new_max_steth_ust_diff,
        },
    )

    with reverts():
        liquidator.change_admin(stranger, {"from": stranger})

    tx = liquidator.change_admin(stranger, {"from": admin})
    assert liquidator.admin() == stranger

    helpers.assert_single_event_named("AdminChanged", tx, source=liquidator, evt_keys_dict={"new_admin": stranger})


def test_fails_on_excess_steth_eth_price_change(interface, whale, steth_token, vault_user, mock_vault, ust_recipient, liquidator):
    steth_pool = interface.CurveSTETH(CURVE_STETH_POOL)

    old_steth_price = steth_pool.get_dy(CURVE_STETH_INDEX, CURVE_ETH_INDEX, 10 ** 18)

    liquidity_amount = 3_000_000 * 10 ** 18
    steth_token.approve(steth_pool, liquidity_amount, {"from": whale})
    steth_pool.add_liquidity([0, liquidity_amount], 0, {"from": whale})

    new_steth_price = steth_pool.get_dy(CURVE_STETH_INDEX, CURVE_ETH_INDEX, 10 ** 18)
    assert old_steth_price * ((100 - MAX_STETH_ETH_PRICE_DIFF_PERCENT) / 100) >= new_steth_price

    steth_amount = 10 ** 18
    steth_token.transfer(liquidator, steth_amount, {"from": vault_user})

    with reverts():
        liquidator.liquidate(ust_recipient, {"from": mock_vault})


def test_fails_on_excess_usdc_ust_price_change(
    interface, whale, ust_token, usdc_token, steth_token, vault_user, mock_vault, ust_recipient, liquidator
):
    ust_pool = interface.CurveUST(CURVE_UST_POOL)

    old_ust_price = ust_pool.get_dy_underlying(CURVE_USDC_INDEX, CURVE_UST_INDEX, 10 ** 6)
    print("old_ust_price", old_ust_price)

    liquidity_amount = 15_000_000 * 10 ** 6
    usdc_pool = interface.CurveUSDC(CURVE_USDC_POOL)
    usdc_token.approve(usdc_pool, liquidity_amount, {"from": whale})
    usdc_pool.add_liquidity([0, 0, liquidity_amount, 0], 0, {"from": whale})

    new_ust_price = ust_pool.get_dy_underlying(CURVE_USDC_INDEX, CURVE_UST_INDEX, 10 ** 6)
    print("new_ust_price", new_ust_price)
    assert old_ust_price * ((100 - MAX_USDC_UST_PRICE_DIFF_PERCENT) / 100) >= new_ust_price

    steth_amount = 10 ** 18
    steth_token.transfer(liquidator, steth_amount, {"from": vault_user})

    with reverts():
        liquidator.liquidate(ust_recipient, {"from": mock_vault})


def test_fails_on_excess_eth_usdc_price_change(interface, whale, steth_token, vault_user, ust_recipient, liquidator, mock_vault):
    router = interface.UniswapV3Router(UNISWAP_ROUTER_V3)
    factory = interface.UniswapV3Factory(router.factory())
    pool = interface.UniswapV3Pool(factory.getPool(USDC_TOKEN, WETH_TOKEN, UNISWAP_USDC_POOL_3_FEE))
    sqrtPriceX96 = pool.slot0()[0]
    old_eth_price = (10 ** WETH_DECIMALS) / (10 ** USDC_DECIMALS) * (2 ** 192 / sqrtPriceX96 ** 2)

    deadline = chain.time() + 3600
    liquidity_amount = 3_000 * 10 ** 18
    router.exactInputSingle(
        (
            WETH_TOKEN,
            USDC_TOKEN,
            UNISWAP_USDC_POOL_3_FEE,
            whale,  # recipient
            deadline,  # deadline
            liquidity_amount,  # amount_in,
            0,  # amount_out_min,
            0,  # sqrtPriceLimitX96
        ),
        {"from": whale, "amount": liquidity_amount},
    )
    sqrtPriceX96 = pool.slot0()[0]
    new_eth_price = (10 ** WETH_DECIMALS) / (10 ** USDC_DECIMALS) * (2 ** 192 / sqrtPriceX96 ** 2)
    assert old_eth_price * (100 - MAX_ETH_USDC_PRICE_DIFF_PERCENT) / 100 >= new_eth_price

    steth_amount = 10 ** 18
    steth_token.transfer(liquidator, steth_amount, {"from": vault_user})

    with reverts():
        liquidator.liquidate(ust_recipient, {"from": mock_vault})


TERRA_ADDRESS = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd"


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
    helpers,
):
    liquidator = RewardsLiquidator.deploy(
        vault,
        admin,
        int(MAX_STETH_ETH_PRICE_DIFF_PERCENT * 10 ** 18 / 100),
        int(MAX_ETH_USDC_PRICE_DIFF_PERCENT * 10 ** 18 / 100),
        int(MAX_USDC_UST_PRICE_DIFF_PERCENT * 10 ** 18 / 100),
        int(MAX_STETH_UST_PRICE_DIFF_PERCENT * 10 ** 18 / 100),
        {"from": deployer},
    )

    vault.set_rewards_liquidator(liquidator, {"from": admin})

    amount = 1 * 10 ** 18
    adjusted_amount = steth_adjusted_ammount(amount)

    steth_token.approve(vault, amount, {"from": vault_user})
    vault.submit(amount, TERRA_ADDRESS, b"", {"from": vault_user})
    assert mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS) == adjusted_amount

    lido_oracle_report(steth_rebase_mult=1.01)

    tx = vault.collect_rewards({"from": liquidations_admin})

    vault_evt = helpers.assert_single_event_named("RewardsCollected", tx, source=vault)

    assert vault_evt["steth_amount"] > 0
    assert vault_evt["ust_amount"] > 0

    liquidator_evt = helpers.assert_single_event_named("SoldStethToUST", tx, source=liquidator)

    assert abs(liquidator_evt["steth_amount"] - vault_evt["steth_amount"]) < 10
    assert liquidator_evt["ust_amount"] == vault_evt["ust_amount"]
