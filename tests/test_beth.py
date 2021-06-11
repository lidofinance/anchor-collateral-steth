import pytest
from brownie import ZERO_ADDRESS, reverts
from time import time


@pytest.fixture(scope='module')
def beth_minter(beth_token, admin, accounts):
    minter = accounts.add()
    beth_token.set_minter(minter, {'from': admin})
    return minter


def test_init(deployer, admin, bEth):
    contract = bEth.deploy('bETH', admin, admin, {'from': deployer})

    assert contract.symbol() == 'bETH'
    assert contract.minter() == admin
    assert contract.admin() == admin


def test_configure(beth_token, stranger, admin, helpers):
    with reverts():
        beth_token.change_admin(stranger, {"from": stranger})

    with reverts():
        beth_token.set_minter(stranger, {"from": stranger})
    
    tx = beth_token.change_admin(stranger, {"from": admin})
    helpers.assert_single_event_named('AdminChanged', tx, source=beth_token, evt_keys_dict = {
        "new_admin": stranger
    })

    tx = beth_token.set_minter(stranger, {"from": stranger})
    helpers.assert_single_event_named('MinterChanged', tx, source=beth_token, evt_keys_dict = {
        "new_minter": stranger
    })


def test_mint_burn(beth_token, stranger, helpers, beth_minter):
    amount = 10**18
    with reverts():
        beth_token.mint(stranger, amount, {"from": stranger})

    with reverts():
        beth_token.burn(stranger, amount, {"from": stranger})

    assert beth_token.balanceOf(stranger) == 0

    total_supply_before = beth_token.totalSupply()
    tx = beth_token.mint(stranger, amount, {"from": beth_minter})
    assert beth_token.balanceOf(stranger) == amount
    assert beth_token.totalSupply() == total_supply_before + amount
    helpers.assert_single_event_named('Transfer', tx, source=beth_token, evt_keys_dict = {
        "sender": ZERO_ADDRESS,
        "receiver": stranger,
        "value": amount
    })

    total_supply_before = beth_token.totalSupply()
    tx = beth_token.burn(stranger, amount, {"from": beth_minter})
    assert beth_token.balanceOf(stranger) == 0
    assert beth_token.totalSupply() == total_supply_before - amount
    helpers.assert_single_event_named('Transfer', tx, source=beth_token, evt_keys_dict = {
        "sender": stranger,
        "receiver": ZERO_ADDRESS,
        "value": amount
    })


def test_holder_cannot_burn_their_tokens(beth_token, stranger, beth_minter):
    beth_token.mint(stranger, 10**18, {"from": beth_minter})
    assert beth_token.balanceOf(stranger) == 10**18
    with reverts():
        beth_token.burn(stranger, 10**17, {"from": stranger})


def test_transfer(beth_token, vault_user, beth_minter, stranger, helpers):
    amount = 10**18

    tx = beth_token.mint(vault_user, amount, {"from": beth_minter})
    
    with reverts():
        beth_token.transfer(ZERO_ADDRESS, amount, {"from": vault_user})
    
    with reverts():
        beth_token.transfer(beth_token, amount, {"from": vault_user})

    vault_user_balance_before = beth_token.balanceOf(vault_user)
    stranger_balance_before = beth_token.balanceOf(stranger)
    tx = beth_token.transfer(stranger, amount, {"from": vault_user})
    assert beth_token.balanceOf(vault_user) == vault_user_balance_before - amount
    assert beth_token.balanceOf(stranger) == stranger_balance_before + amount
    helpers.assert_single_event_named('Transfer', tx, source=beth_token, evt_keys_dict = {
        "sender": vault_user,
        "receiver": stranger,
        "value": amount
    })


def test_transfer_from(beth_token, vault_user, beth_minter, stranger, helpers):
    amount = 10**18

    beth_token.mint(vault_user, 10 * amount, {"from": beth_minter})

    with reverts():
        beth_token.transferFrom(vault_user, stranger, amount, {"from": stranger})

    stranger_beth_balance_before = beth_token.balanceOf(stranger)
    vault_user_beth_balance_before = beth_token.balanceOf(vault_user)
    tx = beth_token.transferFrom(vault_user, stranger, amount, {"from": vault_user})
    assert beth_token.balanceOf(stranger) == stranger_beth_balance_before + amount
    assert beth_token.balanceOf(vault_user) == vault_user_beth_balance_before - amount
    helpers.assert_single_event_named('Transfer', tx, source=beth_token, evt_keys_dict = {
        "sender": vault_user,
        "receiver": stranger,
        "value": amount
    })
    helpers.assert_no_events_named('Approval', tx)
    

    tx = beth_token.approve(stranger, 2**256-1, {"from": vault_user})
    stranger_beth_balance_before = beth_token.balanceOf(stranger)
    vault_user_beth_balance_before = beth_token.balanceOf(vault_user)
    tx = beth_token.transferFrom(vault_user, stranger, amount, {"from": stranger})
    assert beth_token.balanceOf(stranger) == stranger_beth_balance_before + amount
    assert beth_token.balanceOf(vault_user) == vault_user_beth_balance_before - amount
    helpers.assert_single_event_named('Transfer', tx, source=beth_token, evt_keys_dict = {
        "sender": vault_user,
        "receiver": stranger,
        "value": amount
    })
    helpers.assert_no_events_named('Approval', tx)


    tx = beth_token.approve(stranger, amount, {"from": vault_user})
    helpers.assert_single_event_named('Approval', tx, source=beth_token, evt_keys_dict = {
        "owner": vault_user,
        "spender": stranger,
        "value": amount
    })

    with reverts():
        beth_token.transferFrom(vault_user, stranger, 2 * amount, {"from": stranger})

    stranger_beth_balance_before = beth_token.balanceOf(stranger)
    vault_user_beth_balance_before = beth_token.balanceOf(vault_user)
    tx = beth_token.transferFrom(vault_user, stranger, amount, {"from": stranger})
    assert beth_token.balanceOf(stranger) == stranger_beth_balance_before + amount
    assert beth_token.balanceOf(vault_user) == vault_user_beth_balance_before - amount
    helpers.assert_single_event_named('Transfer', tx, source=beth_token, evt_keys_dict = {
        "sender": vault_user,
        "receiver": stranger,
        "value": amount
    })
