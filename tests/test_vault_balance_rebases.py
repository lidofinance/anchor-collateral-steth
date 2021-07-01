import pytest
from brownie import reverts, chain, ZERO_ADDRESS

from test_vault import vault, ANCHOR_REWARDS_DISTRIBUTOR


TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'
ANOTHER_TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabca'


def test_rate_changes(vault, lido_oracle_report, vault_user, liquidations_admin, steth_token, helpers):
    assert vault.get_rate() == 10**18

    steth_token.approve(vault, 10**18, {'from': vault_user})
    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff = 1000
    )

    lido_oracle_report(steth_rebase_mult=1.1)

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff = 1000
    )

    vault.collect_rewards({'from': liquidations_admin})

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff = 1000
    )

    lido_oracle_report(steth_rebase_mult=0.9)

    assert helpers.equal_with_precision(
        vault.get_rate(),
        int((1 / 0.9) * 10**18),
        max_diff = 1000
    )

    lido_oracle_report(steth_rebase_mult=1.01)

    assert helpers.equal_with_precision(
        vault.get_rate(),
        int((1 / 0.909) * 10**18),
        max_diff = 1000
    )

    chain.mine(timedelta = 3600*24 + 1)
    vault.collect_rewards({'from': liquidations_admin})

    assert helpers.equal_with_precision(
        vault.get_rate(),
        int((1 / 0.909) * 10**18),
        max_diff = 1000
    )

    lido_oracle_report(steth_rebase_mult=2.0)

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff = 1000
    )

    chain.mine(timedelta = 3600*24 + 1)
    vault.collect_rewards({'from': liquidations_admin})

    assert helpers.equal_with_precision(
        vault.get_rate(),
        int((1 / 0.909) * 10**18),
        max_diff = 1000
    )


@pytest.mark.parametrize('steth_io_amount', [x * 10**18 for x in [1,2,3,5,6,7,9]])
def test_beth_io_possible_after_steth_io(
    lido,
    vault,
    vault_user,
    stranger,
    steth_token,
    withdraw_from_terra,
    steth_io_amount
):
    steth_token.approve(vault, 2 * 10**18, {'from': vault_user})

    assert vault.can_deposit_or_withdraw()
    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    lido.submit(ZERO_ADDRESS, {'from': stranger, 'value': steth_io_amount})

    assert vault.can_deposit_or_withdraw()
    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    withdraw_from_terra(TERRA_ADDRESS, to_address=vault_user, amount=10**18)
    vault.withdraw(10**18, {'from': vault_user})


def test_beth_io_possible_after_non_rebasing_lido_oracle_report(
    vault,
    vault_user,
    lido_oracle_report,
    steth_token,
    withdraw_from_terra
):
    steth_token.approve(vault, 2 * 10**18, {'from': vault_user})

    assert vault.can_deposit_or_withdraw()
    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    lido_oracle_report(steth_rebase_mult=1.0)

    assert vault.can_deposit_or_withdraw()
    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    withdraw_from_terra(TERRA_ADDRESS, to_address=vault_user, amount=10**18)
    vault.withdraw(10**18, {'from': vault_user})


def test_beth_io_prohibited_between_positive_rebase_by_oracle_report_and_rewards_sell(
    lido,
    vault,
    vault_user,
    liquidations_admin,
    steth_token,
    lido_oracle_report,
    withdraw_from_terra
):
    steth_token.approve(vault, 100 * 10**18, {'from': vault_user})
    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    lido_oracle_report(steth_rebase_mult = 1 + 0.04/365)

    assert not vault.can_deposit_or_withdraw()

    with reverts('dev: share price changed'):
        vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    withdraw_from_terra(TERRA_ADDRESS, to_address=vault_user, amount=10**18)

    with reverts('dev: share price changed'):
        vault.withdraw(10**18, {'from': vault_user})

    vault.collect_rewards({'from': liquidations_admin})
    assert vault.can_deposit_or_withdraw()

    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})
    vault.withdraw(10**18, {'from': vault_user})


def test_beth_io_prohibited_between_negative_rebase_by_oracle_report_and_rewards_sell(
    lido,
    vault,
    vault_user,
    liquidations_admin,
    steth_token,
    lido_oracle_report,
    withdraw_from_terra
):
    steth_token.approve(vault, 100 * 10**18, {'from': vault_user})
    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    lido_oracle_report(steth_rebase_mult = 1 - 0.00000004/365)

    assert not vault.can_deposit_or_withdraw()

    with reverts('dev: share price changed'):
        vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    withdraw_from_terra(TERRA_ADDRESS, to_address=vault_user, amount=10**18)

    with reverts('dev: share price changed'):
        vault.withdraw(10**18, {'from': vault_user})

    vault.collect_rewards({'from': liquidations_admin})
    assert vault.can_deposit_or_withdraw()

    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})
    vault.withdraw(10**18, {'from': vault_user})


def test_beth_io_prohibited_between_rebase_by_burning_steth_and_rewards_sell(
    lido,
    vault,
    vault_user,
    another_vault_user,
    stranger,
    liquidations_admin,
    steth_token,
    burn_steth,
    withdraw_from_terra
):
    steth_token.approve(vault, 100 * 10**18, {'from': vault_user})
    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    burn_steth(another_vault_user, 10**18)

    assert not vault.can_deposit_or_withdraw()

    with reverts('dev: share price changed'):
        vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})

    withdraw_from_terra(TERRA_ADDRESS, to_address=vault_user, amount=10**18)

    with reverts('dev: share price changed'):
        vault.withdraw(10**18, {'from': vault_user})

    vault.collect_rewards({'from': liquidations_admin})
    assert vault.can_deposit_or_withdraw()

    vault.submit(10**18, TERRA_ADDRESS, b'', {'from': vault_user})
    vault.withdraw(10**18, {'from': vault_user})


def test_steth_positive_rebase(
    vault,
    vault_user,
    stranger,
    liquidations_admin,
    steth_token,
    mock_bridge_connector,
    withdraw_from_terra,
    lido_oracle_report,
    steth_adjusted_ammount,
    helpers
):
    amount = 1 * 10**18
    adjusted_amount = steth_adjusted_ammount(amount)

    steth_token.approve(vault, amount, {'from': vault_user})
    vault.submit(amount, TERRA_ADDRESS, '0xab', {'from': vault_user})
    assert mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS) == amount

    vault_steth_balance_before = steth_token.balanceOf(vault)
    assert helpers.equal_with_precision(vault_steth_balance_before, amount, 10)

    lido_oracle_report(steth_rebase_mult=1.01)

    vault_steth_balance_after = steth_token.balanceOf(vault)
    assert vault_steth_balance_after > vault_steth_balance_before

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff = 100
    )

    vault.collect_rewards({'from': liquidations_admin})

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff = 100
    )

    withdraw_from_terra(TERRA_ADDRESS, to_address=stranger, amount=amount)
    vault.withdraw(amount, {'from': stranger})

    assert helpers.equal_with_precision(steth_token.balanceOf(stranger), adjusted_amount, 100)


def test_steth_negative_rebase(
    vault,
    vault_user,
    stranger,
    liquidations_admin,
    steth_token,
    mock_bridge_connector,
    withdraw_from_terra,
    lido_oracle_report,
    steth_adjusted_ammount,
    helpers
):
    amount = 1 * 10**18
    adjusted_amount = steth_adjusted_ammount(amount)

    steth_token.approve(vault, amount, {'from': vault_user})
    vault.submit(amount, TERRA_ADDRESS, '0xab', {'from': vault_user})
    assert mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS) == amount

    vault_steth_balance_before = steth_token.balanceOf(vault)
    assert helpers.equal_with_precision(vault_steth_balance_before, amount, 10)

    lido_oracle_report(steth_rebase_mult=0.99)

    vault_steth_balance_after = steth_token.balanceOf(vault)
    assert vault_steth_balance_after < vault_steth_balance_before

    expected_withdraw_rate = int((1 / 0.99) * 10**18)

    assert helpers.equal_with_precision(vault.get_rate(), expected_withdraw_rate, 100)

    withdraw_from_terra(TERRA_ADDRESS, to_address=stranger, amount=amount)

    tx = vault.collect_rewards({'from': liquidations_admin})

    helpers.assert_single_event_named('RewardsCollected', tx, source=vault, evt_keys_dict={
        'steth_amount': 0,
        'ust_amount': 0
    })

    assert helpers.equal_with_precision(vault.get_rate(), expected_withdraw_rate, 100)

    vault.withdraw(amount, {'from': stranger})

    assert helpers.equal_with_precision(
        steth_token.balanceOf(stranger),
        steth_adjusted_ammount(adjusted_amount * 0.99),
        100
    )


def test_steth_rewards_after_penalties(
    vault,
    vault_user,
    another_vault_user,
    stranger,
    another_stranger,
    liquidations_admin,
    steth_token,
    beth_token,
    withdraw_from_terra,
    lido_oracle_report,
    mock_bridge_connector,
    helpers,
    steth_adjusted_ammount
):
    amount = 1 * 10**18
    adjusted_amount = steth_adjusted_ammount(amount)
    negative_rebase_multiplier = 0.99
    positive_rebase_multiplier = 1 / negative_rebase_multiplier

    steth_token.approve(vault, amount, {'from': vault_user})
    vault.submit(amount, TERRA_ADDRESS, b'', {'from': vault_user})
   
    lido_oracle_report(steth_rebase_mult=negative_rebase_multiplier)

    assert helpers.equal_with_precision(
        vault.get_rate(),
        (1 / negative_rebase_multiplier) * 10**18,
        100
    )

    tx = vault.collect_rewards({'from': liquidations_admin})

    helpers.assert_single_event_named('RewardsCollected', tx, source=vault, evt_keys_dict={
        'steth_amount': 0,
        'ust_amount': 0
    })

    steth_token.approve(vault, amount, {'from': another_vault_user})
    vault.submit(amount, ANOTHER_TERRA_ADDRESS, b'', {'from': another_vault_user})
    
    lido_oracle_report(steth_rebase_mult=positive_rebase_multiplier)
    chain.mine(timedelta = 3600*24 + 1)
    vault.collect_rewards({'from': liquidations_admin})

    withdraw_from_terra(
        TERRA_ADDRESS, 
        to_address=stranger, 
        amount=mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)
    )
    vault.withdraw(beth_token.balanceOf(stranger), {'from': stranger})

    assert helpers.equal_with_precision(
        steth_token.balanceOf(stranger),
        steth_adjusted_ammount(adjusted_amount * negative_rebase_multiplier),
        10**10
    )

    withdraw_from_terra(
        ANOTHER_TERRA_ADDRESS, 
        to_address=another_stranger,
        amount=mock_bridge_connector.terra_beth_balance_of(ANOTHER_TERRA_ADDRESS)
    )
    vault.withdraw(beth_token.balanceOf(another_stranger), {'from': another_stranger})

    assert helpers.equal_with_precision(
        steth_token.balanceOf(another_stranger),
        adjusted_amount,
        10**10
    )


def test_collect_rewards_events(
    vault,
    vault_user,
    lido_oracle_report,
    liquidations_admin,
    deposit_to_terra,
    withdraw_from_terra,
    mock_bridge_connector,
    beth_token,
    helpers
):
    amount = 1 * 10**18
    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)
    
    lido_oracle_report(steth_rebase_mult=1)
    tx = vault.collect_rewards({'from': liquidations_admin})

    helpers.assert_single_event_named('RewardsCollected', tx, source=vault, evt_keys_dict={
        'steth_amount': 0,
        'ust_amount': 0
    })

    chain.mine(timedelta = 3600*26 + 1)

    lido_oracle_report(steth_rebase_mult=1.1)
    tx = vault.collect_rewards({'from': liquidations_admin})

    rewardsCollectedEvent = tx.events['RewardsCollected'][0]
    assert helpers.equal_with_precision(rewardsCollectedEvent['steth_amount'], 0.1 * 10**18, 200)
    assert rewardsCollectedEvent['ust_amount'] == 42 * 10**18

    helpers.assert_single_event_named('Test__Forwarded', tx, source=mock_bridge_connector, evt_keys_dict={
        'asset_name': 'UST',
        'terra_address': ANCHOR_REWARDS_DISTRIBUTOR,
        'amount': 42 * 10**18,
        'extra_data': '0x00'
    })


def test_collect_rewards_restrictions(
    vault,
    vault_user,
    deposit_to_terra,
    liquidations_admin,
    stranger,
    lido_oracle_report
):
    deposit_to_terra(TERRA_ADDRESS, vault_user, amount=10**18)

    lido_oracle_report(steth_rebase_mult=1)
    vault.collect_rewards({'from': liquidations_admin})

    chain.sleep(24 * 3600 - 1) #sleep less then 24 hours

    with reverts():
        vault.collect_rewards({"from": stranger})
    with reverts():
        vault.collect_rewards({'from': liquidations_admin})

    chain.sleep(2 * 3600) #sleep less then 24 + 2 hours

    with reverts():
        vault.collect_rewards({"from": stranger})


def test_shares_balance_decrease_liquidation(
    vault, 
    vault_user,
    liquidations_admin,
    deposit_to_terra,
    steth_token,
    beth_token,
    helpers,
    withdraw_from_terra,
    lido_oracle_report
):
    deposit_to_terra(TERRA_ADDRESS, vault_user, amount=10**18)

    lido_oracle_report(steth_rebase_mult=1)
    vault.collect_rewards({'from': liquidations_admin})

    withdraw_from_terra(TERRA_ADDRESS, to_address=vault_user, amount=0.5 * 10**18)
    vault.withdraw(0.5 * 10**18, {'from': vault_user})
    
    chain.mine(timedelta=3600*28)

    vault_steth_balance_before = steth_token.balanceOf(vault)
    vault_beth_balance_before = beth_token.balanceOf(vault)

    lido_oracle_report(steth_rebase_mult=1.1)
    vault.collect_rewards({'from': liquidations_admin})

    assert beth_token.balanceOf(vault) == vault_beth_balance_before

    assert helpers.equal_with_precision(
        steth_token.balanceOf(vault),
        vault_steth_balance_before,
        100
    )
