import pytest
from brownie.network.state import Chain

from test_vault import vault


TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'
ANOTHER_TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabca'

# rebase steth and collect rewards will be called at the same time in one oracle callback transaction
@pytest.fixture(scope="function")
def rebase_steth_and_collect_rewards(rebase_steth_by, vault, liquidations_admin):
    def rebase_and_collect(mult):
        rebase_steth_by(mult)
        vault.collect_rewards({"from": liquidations_admin})
    return rebase_and_collect


def test_steth_positive_rebase(
    vault,
    vault_user,
    stranger,
    steth_token,
    mock_bridge_connector,
    withdraw_from_terra,
    rebase_steth_by,
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

    rebase_steth_by(mult=1.01)

    vault_steth_balance_after = steth_token.balanceOf(vault)
    assert vault_steth_balance_after > vault_steth_balance_before

    assert vault.get_rate() == 10**18

    withdraw_from_terra(TERRA_ADDRESS, to_address=stranger, amount=amount)
    vault.withdraw(amount, {'from': stranger})

    assert helpers.equal_with_precision(steth_token.balanceOf(stranger), adjusted_amount, 100)


def test_steth_negative_rebase(
    vault,
    vault_user,
    stranger,
    steth_token,
    mock_bridge_connector,
    withdraw_from_terra,
    rebase_steth_by,
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

    rebase_steth_by(mult=0.99)

    vault_steth_balance_after = steth_token.balanceOf(vault)
    assert vault_steth_balance_after < vault_steth_balance_before

    expected_withdraw_rate = int((1 / 0.99) * 10**18)

    assert helpers.equal_with_precision(vault.get_rate(), expected_withdraw_rate, 100)

    withdraw_from_terra(TERRA_ADDRESS, to_address=stranger, amount=amount)
    vault.withdraw(amount, {'from': stranger})

    assert helpers.equal_with_precision(steth_token.balanceOf(stranger), int(adjusted_amount * 0.99), 100)


def test_steth_rewards_after_slashing(
    vault,
    vault_user,
    another_vault_user,
    stranger,
    steth_token,
    beth_token,
    withdraw_from_terra,
    deposit_to_terra,
    rebase_steth_by,
    mock_bridge_connector,
    helpers,
    steth_adjusted_ammount
):
    amount = 1 * 10**18
    adjusted_amount = steth_adjusted_ammount(amount)
    positive_rebase_multiplier = 1.01010101010101010101
    negative_rebase_multiplier = 0.99

    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)
   
    rebase_steth_by(mult=negative_rebase_multiplier)

    deposit_to_terra(ANOTHER_TERRA_ADDRESS, another_vault_user, amount)
    
    rebase_steth_by(mult=positive_rebase_multiplier)

    withdraw_from_terra(
        TERRA_ADDRESS, 
        to_address=stranger, 
        amount=mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)
    )
    vault.withdraw(beth_token.balanceOf(stranger), {'from': stranger})
    
    assert helpers.equal_with_precision(steth_token.balanceOf(stranger), adjusted_amount, 20)
    steth_token.transfer(vault_user, steth_token.balanceOf(stranger), {"from": stranger})

    withdraw_from_terra(
        ANOTHER_TERRA_ADDRESS, 
        to_address=stranger, 
        amount=mock_bridge_connector.terra_beth_balance_of(ANOTHER_TERRA_ADDRESS)
    )
    vault.withdraw(beth_token.balanceOf(stranger), {'from': stranger})

    assert helpers.equal_with_precision(
        steth_token.balanceOf(stranger), 
        steth_adjusted_ammount(adjusted_amount * positive_rebase_multiplier), 
        20
    )


def test_steth_negative_rebase_and_rewards_collect(
    vault,
    vault_user,
    stranger,
    steth_adjusted_ammount,
    rebase_steth_and_collect_rewards,
    deposit_to_terra,
    withdraw_from_terra,
    mock_bridge_connector,
    beth_token,
    steth_token,
    helpers
):
    amount = 1 * 10**18
    rebase_multiplier = 0.99
    adjusted_amount = steth_adjusted_ammount(amount)
    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)
    
    rebase_steth_and_collect_rewards(rebase_multiplier)

    withdraw_from_terra(
        TERRA_ADDRESS, 
        to_address=stranger, 
        amount=mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)
    )
    vault.withdraw(beth_token.balanceOf(stranger), {'from': stranger})

    assert helpers.equal_with_precision(
        steth_token.balanceOf(stranger), 
        adjusted_amount * rebase_multiplier, 
        20
    )
 

def test_steth_positive_rebase_and_rewards_collect(
    vault,
    vault_user,
    stranger,
    steth_adjusted_ammount,
    rebase_steth_and_collect_rewards,
    deposit_to_terra,
    withdraw_from_terra,
    mock_bridge_connector,
    beth_token,
    steth_token,
    helpers
):
    amount = 1 * 10**18
    rebase_multiplier = 1.01
    adjusted_amount = steth_adjusted_ammount(amount)
    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)
    
    rebase_steth_and_collect_rewards(rebase_multiplier)

    withdraw_from_terra(
        TERRA_ADDRESS, 
        to_address=stranger, 
        amount=mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)
    )
    vault.withdraw(beth_token.balanceOf(stranger), {'from': stranger})

    assert helpers.equal_with_precision(
        steth_token.balanceOf(stranger), 
        adjusted_amount, 
        20
    )
 

def test_steth_rewards_after_slashing_with_reward_collecting(
    vault,
    vault_user,
    another_vault_user,
    stranger,
    steth_token,
    beth_token,
    withdraw_from_terra,
    deposit_to_terra,
    rebase_steth_and_collect_rewards,
    mock_bridge_connector,
    helpers,
    steth_adjusted_ammount
):
    amount = 1 * 10**18
    adjusted_amount = steth_adjusted_ammount(amount)
    positive_rebase_multiplier = 2
    negative_rebase_multiplier = 0.5

    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)

    rebase_steth_and_collect_rewards(mult=negative_rebase_multiplier)

    deposit_to_terra(ANOTHER_TERRA_ADDRESS, another_vault_user, amount)

    chain = Chain()
    chain.sleep(3600*24)
    chain.mine()

    rebase_steth_and_collect_rewards(mult=positive_rebase_multiplier)

    withdraw_from_terra(
        TERRA_ADDRESS, 
        to_address=stranger, 
        amount=mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)
    )
    vault.withdraw(beth_token.balanceOf(stranger), {'from': stranger})
    
    assert helpers.equal_with_precision(
        steth_token.balanceOf(stranger), 
        adjusted_amount * negative_rebase_multiplier, 
        100
    )
    steth_token.transfer(vault_user, steth_token.balanceOf(stranger), {"from": stranger})

    withdraw_from_terra(
        ANOTHER_TERRA_ADDRESS, 
        to_address=stranger, 
        amount=mock_bridge_connector.terra_beth_balance_of(ANOTHER_TERRA_ADDRESS)
    )
    vault.withdraw(beth_token.balanceOf(stranger), {'from': stranger})

    assert helpers.equal_with_precision(
        steth_token.balanceOf(stranger), 
        adjusted_amount, 
        100
    )
