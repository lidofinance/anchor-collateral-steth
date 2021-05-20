import pytest
from brownie import chain

from test_vault import vault


TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'


def test_steth_positive_rebase(
    vault,
    vault_user,
    stranger,
    steth_token,
    deposit_to_terra,
    withdraw_from_terra,
    rebase_steth_by,
    helpers
):
    amount = 1 * 10**18

    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)

    vault_steth_balance_before = steth_token.balanceOf(vault)
    assert helpers.equal_with_precision(vault_steth_balance_before, amount, 10)

    rebase_steth_by(mult=1.01)

    vault_steth_balance_after = steth_token.balanceOf(vault)
    assert vault_steth_balance_after > vault_steth_balance_before

    assert vault.get_rate() == 10**18

    withdraw_from_terra(TERRA_ADDRESS, to_address=stranger, amount=amount)
    vault.withdraw(amount, {'from': stranger})

    assert helpers.equal_with_precision(steth_token.balanceOf(stranger), amount, 10)


def test_steth_negative_rebase(
    vault,
    vault_user,
    stranger,
    steth_token,
    deposit_to_terra,
    withdraw_from_terra,
    rebase_steth_by,
    helpers
):
    amount = 1 * 10**18

    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)

    vault_steth_balance_before = steth_token.balanceOf(vault)
    assert helpers.equal_with_precision(vault_steth_balance_before, amount, 10)

    rebase_steth_by(mult=0.99)

    vault_steth_balance_after = steth_token.balanceOf(vault)
    assert vault_steth_balance_after < vault_steth_balance_before

    expected_withdraw_rate = int((1 / 0.99) * 10**18)

    assert helpers.equal_with_precision(vault.get_rate(), expected_withdraw_rate, 100)

    withdraw_from_terra(TERRA_ADDRESS, to_address=stranger, amount=amount)
    vault.withdraw(amount, {'from': stranger})

    assert helpers.equal_with_precision(steth_token.balanceOf(stranger), int(amount * 0.99), 10)

