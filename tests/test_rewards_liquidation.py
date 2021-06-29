import pytest
from brownie import reverts, chain, ZERO_ADDRESS


ANCHOR_REWARDS_DISTRIBUTOR = '0x1234123412341234123412341234123412341234123412341234123412341234'

MAX_STETH_PRICE_DIFF_PERCENT = 10
MAX_ETH_PRICE_DIFF_PERCENT = 5


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
