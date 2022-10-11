import pytest
from brownie import reverts, chain, ZERO_ADDRESS

from test_vault import vault, ANCHOR_REWARDS_DISTRIBUTOR


TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'
ANOTHER_TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabca'


@pytest.fixture(scope='module')
def apply_insurance(lido, steth_burner, deployer, mock_self_owned_steth_burner):
    def apply(steth_rebase_mult):
        # steth_in_share = total_eth / total_shares
        # mult * total_eth / total_shares = total_eth / (total_shares - shares_burnt)
        # shares_burnt = total_shares * (1 - 1 / mult)
        total_shares = lido.getTotalShares()
        shares_to_burn = int(total_shares * (1 - 1 / steth_rebase_mult))
        steth_to_burn = lido.getPooledEthByShares(shares_to_burn)
        print(f'steth_to_burn: {steth_to_burn}')
        lido.submit(ZERO_ADDRESS, {'from': deployer, 'value': steth_to_burn + 100})
        lido.burnShares(deployer, shares_to_burn, {'from': steth_burner})
        mock_self_owned_steth_burner.increment_total_shares_burnt(shares_to_burn)
    return apply


def test_insurance_applied_before_rewards_collection_avoids_changing_rate(
    vault,
    vault_user,
    another_vault_user,
    liquidations_admin,
    steth_token,
    steth_adjusted_ammount,
    lido_oracle_report,
    apply_insurance,
    helpers,
):
    amount = steth_adjusted_ammount(10**18)

    steth_token.approve(vault, amount, {'from': vault_user})
    vault.submit(amount, TERRA_ADDRESS, b'', vault.version(), {'from': vault_user})

    vault_steth_balance_before = steth_token.balanceOf(vault)

    lido_oracle_report(steth_rebase_mult = 0.99)
    apply_insurance(steth_rebase_mult = 1/0.99)

    assert vault.get_rate() >= 10**18

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff_percent = 0.1
    )

    tx = vault.collect_rewards({'from': liquidations_admin})

    helpers.assert_single_event_named('RewardsCollected', tx, source=vault, evt_keys_dict={
        'steth_amount': 0,
        'ust_amount': 0
    })

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff_percent = 0.1
    )



def test_insurance_is_not_counted_as_rewards(
    vault,
    vault_user,
    another_vault_user,
    liquidations_admin,
    steth_token,
    steth_adjusted_ammount,
    lido_oracle_report,
    apply_insurance,
    helpers,
):
    amount = steth_adjusted_ammount(10**18)

    steth_token.approve(vault, amount, {'from': vault_user})
    vault.submit(amount, TERRA_ADDRESS, b'', vault.version(), {'from': vault_user})

    vault_steth_balance_before = steth_token.balanceOf(vault)

    lido_oracle_report(steth_rebase_mult=0.99)
    vault.collect_rewards({'from': liquidations_admin})

    assert helpers.equal_with_precision(
        vault.get_rate(),
        int((1 / 0.99) * 10**18),
        100
    )

    chain.mine(timedelta = 24*3600 + 1)
    apply_insurance(steth_rebase_mult = 1/0.99)

    assert vault.get_rate() >= 10**18

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff_percent = 0.1
    )

    tx = vault.collect_rewards({'from': liquidations_admin})

    helpers.assert_single_event_named('RewardsCollected', tx, source=vault, evt_keys_dict={
        'steth_amount': 0,
        'ust_amount': 0
    })

    assert helpers.equal_with_precision(
        vault.get_rate(),
        10**18,
        max_diff_percent = 0.1
    )
