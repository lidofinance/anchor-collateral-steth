import pytest
from brownie import chain

from test_vault import vault


TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'
ANOTHER_TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabca'


def test_steth_positive_rebase(
    vault,
    vault_user,
    stranger,
    steth_token,
    mock_bridge_connector,
    withdraw_from_terra,
    rebase_steth_by,
    helpers
):
    amount = 1 * 10**18

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

    assert helpers.equal_with_precision(steth_token.balanceOf(stranger), amount, 10)


def test_steth_negative_rebase(
    vault,
    vault_user,
    stranger,
    steth_token,
    mock_bridge_connector,
    withdraw_from_terra,
    rebase_steth_by,
    helpers
):
    amount = 1 * 10**18

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

    assert helpers.equal_with_precision(steth_token.balanceOf(stranger), int(amount * 0.99), 10)


def test_steth_rewards_after_slashing(
    vault,
    vault_user,
    another_vault_user,
    stranger,
    steth_token,
    beth_token,
    withdraw_from_terra,
    rebase_steth_by,
    mock_bridge,
    mock_bridge_connector,
    helpers
):
    amount = 1 * 10**18
    positive_rebase_multiplier = 1.010101010101010101
    negative_rebase_multiplier = 0.99

    print(f'vault_user before {vault_user}\n amount:        {amount}\n steth_balance: {steth_token.balanceOf(vault_user)}\n beth balance:  {beth_token.balanceOf(vault_user)}\n terra_balance: {mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)}\n steth_vault:   {steth_token.balanceOf(vault)}\n beth connector:{beth_token.balanceOf(mock_bridge)}')
    steth_token.approve(vault, amount, {'from': vault_user})
    tx = vault.submit(amount, TERRA_ADDRESS, '0xab', {'from': vault_user})
    print(f'\n\nvault_user after {vault_user}\n amount:        {amount}\n steth_balance: {steth_token.balanceOf(vault_user)}\n beth balance:  {beth_token.balanceOf(vault_user)}\n terra_balance: {mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)}\n steth_vault:   {steth_token.balanceOf(vault)}\n beth connector:{beth_token.balanceOf(mock_bridge)}')
    
    rebase_steth_by(mult=negative_rebase_multiplier)

    print(f'\n\nvault_user before {another_vault_user}\n amount:        {amount}\n steth_balance: {steth_token.balanceOf(another_vault_user)}\n beth balance:  {beth_token.balanceOf(another_vault_user)}\n terra_balance: {mock_bridge_connector.terra_beth_balance_of(ANOTHER_TERRA_ADDRESS)}\n steth_vault:   {steth_token.balanceOf(vault)}\n beth connector:{beth_token.balanceOf(mock_bridge)}')
    steth_token.approve(vault, amount, {'from': another_vault_user})
    tx = vault.submit(amount, ANOTHER_TERRA_ADDRESS, '0xab', {'from': another_vault_user})
    print(f'\n\nvault_user after {another_vault_user}\n amount:        {amount}\n steth_balance: {steth_token.balanceOf(another_vault_user)}\n beth balance:  {beth_token.balanceOf(another_vault_user)}\n terra_balance: {mock_bridge_connector.terra_beth_balance_of(ANOTHER_TERRA_ADDRESS)}\n steth_vault:   {steth_token.balanceOf(vault)}\n beth connector:{beth_token.balanceOf(mock_bridge)}')
    
    rebase_steth_by(mult=positive_rebase_multiplier)

    print('Withdraw')

    print('strander steth balance: ', steth_token.balanceOf(stranger))
    print(f'\n\nvault_user before {vault_user}\n amount:        {amount}\n steth_balance: {steth_token.balanceOf(vault_user)}\n beth balance:  {beth_token.balanceOf(vault_user)}\n terra_balance: {mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)}\n steth_vault:   {steth_token.balanceOf(vault)}\n beth connector:{beth_token.balanceOf(mock_bridge)}')
    withdraw_from_terra(TERRA_ADDRESS, to_address=stranger, amount=mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS))
    vault.withdraw(beth_token.balanceOf(stranger), {'from': stranger})
    print(f'\n\nvault_user after {vault_user}\n amount:        {amount}\n steth_balance: {steth_token.balanceOf(vault_user)}\n beth balance:  {beth_token.balanceOf(vault_user)}\n terra_balance: {mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)}\n steth_vault:   {steth_token.balanceOf(vault)}\n beth connector:{beth_token.balanceOf(mock_bridge)}')
    
    print('strander steth balance: ', steth_token.balanceOf(stranger))

    # assert helpers.equal_with_precision(steth_token.balanceOf(stranger), amount, 10)

    print(f'\n\nvault_user before {another_vault_user}\n amount:        {amount}\n steth_balance: {steth_token.balanceOf(another_vault_user)}\n beth balance:  {beth_token.balanceOf(another_vault_user)}\n terra_balance: {mock_bridge_connector.terra_beth_balance_of(ANOTHER_TERRA_ADDRESS)}\n steth_vault:   {steth_token.balanceOf(vault)}\n beth connector:{beth_token.balanceOf(mock_bridge)}')
    withdraw_from_terra(ANOTHER_TERRA_ADDRESS, to_address=stranger, amount=mock_bridge_connector.terra_beth_balance_of(ANOTHER_TERRA_ADDRESS))
    vault.withdraw(beth_token.balanceOf(stranger), {'from': stranger})
    print(f'\n\nvault_user after {another_vault_user}\n amount:        {amount}\n steth_balance: {steth_token.balanceOf(another_vault_user)}\n beth balance:  {beth_token.balanceOf(another_vault_user)}\n terra_balance: {mock_bridge_connector.terra_beth_balance_of(ANOTHER_TERRA_ADDRESS)}\n steth_vault:   {steth_token.balanceOf(vault)}\n beth connector:{beth_token.balanceOf(mock_bridge)}')

    print('strander steth balance: ', steth_token.balanceOf(stranger))
    assert helpers.equal_with_precision(steth_token.balanceOf(stranger), int(amount*(1+positive_rebase_multiplier)), 500)

