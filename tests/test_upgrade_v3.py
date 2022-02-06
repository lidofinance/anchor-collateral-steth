import pytest
from brownie import accounts, interface, Contract, AnchorVault, reverts, chain, ZERO_ADDRESS

from utils.config import beth_token_addr, wormhole_token_bridge_addr

"""
These tests should be ran on a mainnet block produced
before the v3 upgrade, e.g. on the block 14158645.
"""

MAINNET_VAULT = '0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf'
REFUND_BETH_AMOUNT = 4449999990000000000 + 439111118580000000000
REFUND_MESSAGE = 'refund for 2022-01-26 incident, txid 0x7abe086dd5619a577f50f87660a03ea0a1934c4022cd432ddf00734771019951 and 0xc875f85f525d9bc47314eeb8dc13c288f0814cf06865fc70531241e21f5da09d'
LIDO_DAO_FINANCE_MULTISIG = '0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'


def as_vault_v2(addr):
    return Contract.from_abi('AnchorVault_v2', addr, interface.AnchorVault_v2.abi)


def as_vault_v3(addr):
    return Contract.from_abi('AnchorVault', addr, AnchorVault.abi)


@pytest.fixture(scope='module')
def vault_admin(accounts):
    vault = as_vault_v2(MAINNET_VAULT)
    return accounts.at(vault.admin(), force=True)


@pytest.fixture(scope='module')
def vault_proxy(AnchorVaultProxy):
    proxy = AnchorVaultProxy.at(MAINNET_VAULT)
    vault = as_vault_v2(proxy)
    assert vault.version() == 2
    assert vault.admin() == proxy.proxy_getAdmin()
    return proxy


@pytest.fixture(scope='module')
def beth_token(bEth):
    return bEth.at(beth_token_addr)


def test_initialize_cannot_be_called_after_upgrading_impl(
    vault_proxy,
    steth_token,
    vault_admin,
    stranger,
    bEth
):
    proxy_admin = accounts.at(vault_proxy.proxy_getAdmin(), force=True)

    new_impl = AnchorVault.deploy({'from': stranger})
    new_impl.petrify_impl({'from': stranger})

    vault_proxy.proxy_upgradeTo(new_impl, b'', {'from': proxy_admin})
    vault = as_vault_v3(vault_proxy)

    new_beth_token = bEth.deploy('bETH', ZERO_ADDRESS, stranger, {'from': stranger})

    with reverts():
        vault.initialize(new_beth_token, steth_token, stranger, stranger, {'from': stranger})

    with reverts():
        vault.initialize(new_beth_token, steth_token, vault_admin, vault_admin, {'from': vault_admin})


def upgrade_vault_to_v3(vault_proxy, impl_deployer, emergency_admin):
    proxy_admin = accounts.at(vault_proxy.proxy_getAdmin(), force=True)

    new_impl = AnchorVault.deploy({'from': impl_deployer})
    new_impl.petrify_impl({'from': impl_deployer})

    setup_calldata = new_impl.finalize_upgrade_v3.encode_input(emergency_admin)
    return vault_proxy.proxy_upgradeTo(new_impl, setup_calldata, {'from': proxy_admin})


def test_upgrade_changes_version_to_3(vault_proxy, stranger, emergency_admin, helpers):
    tx = upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    vault = as_vault_v3(vault_proxy)

    assert vault.version() == 3

    helpers.assert_single_event_named('VersionIncremented', tx, source=vault, evt_keys_dict={
        'new_version': 3
    })


def test_finalize_upgrade_v3_cannot_be_called_twice(vault_proxy, stranger, vault_admin, emergency_admin):
    tx = upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    vault = as_vault_v3(vault_proxy)

    with reverts('unexpected contract version'):
        vault.finalize_upgrade_v3(emergency_admin, {'from': vault_admin})


def test_finalize_upgrade_v3_cannot_be_called_on_v4_vault(
    vault_proxy,
    stranger,
    vault_admin,
    emergency_admin
):
    tx = upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    vault = as_vault_v3(vault_proxy)

    vault.bump_version({'from': vault_admin})
    assert vault.version() == 4

    with reverts('unexpected contract version'):
        vault.finalize_upgrade_v3(emergency_admin, {'from': vault_admin})


def test_upgrade_performs_the_refund(vault_proxy, steth_token, stranger, emergency_admin, helpers):
    vault = as_vault_v3(vault_proxy)

    vault_steth_balance_before = steth_token.balanceOf(vault_proxy)
    dao_steth_balance_before = steth_token.balanceOf(LIDO_DAO_FINANCE_MULTISIG)
    beth_rate_before = vault.get_rate()
    expected_refund_steth_amount = (REFUND_BETH_AMOUNT * 10**18) // beth_rate_before

    tx = upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)

    assert helpers.equal_with_precision(vault.get_rate(), beth_rate_before, 1)
    assert vault.total_beth_refunded() == REFUND_BETH_AMOUNT

    refund_evt = helpers.assert_single_event_named('Refunded', tx, source=vault)
    assert refund_evt['recipient'] == LIDO_DAO_FINANCE_MULTISIG
    assert refund_evt['beth_amount'] == REFUND_BETH_AMOUNT
    assert refund_evt['comment'] == REFUND_MESSAGE
    assert helpers.equal_with_precision(refund_evt['steth_amount'], expected_refund_steth_amount, 1000)

    vault_steth_balance_change = steth_token.balanceOf(vault_proxy) - vault_steth_balance_before
    assert helpers.equal_with_precision(vault_steth_balance_change, -expected_refund_steth_amount, 1000)

    dao_steth_balance_change = steth_token.balanceOf(LIDO_DAO_FINANCE_MULTISIG) - dao_steth_balance_before
    assert helpers.equal_with_precision(dao_steth_balance_change, -vault_steth_balance_change, 2)


def test_cannot_finalize_upgrade_twice(vault_proxy, stranger, vault_admin, emergency_admin):
    upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    vault = as_vault_v3(vault_proxy)

    with reverts():
        vault.finalize_upgrade_v3(emergency_admin, {'from': vault_admin})

    with reverts():
        vault.finalize_upgrade_v3(emergency_admin, {'from': stranger})


def test_admin_can_burn_the_refunded_beth(
    vault_proxy,
    beth_token,
    stranger,
    vault_admin,
    emergency_admin,
    helpers
):
    upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    vault = as_vault_v3(vault_proxy)

    beth_total_supply_before = beth_token.totalSupply()
    beth_rate_before = vault.get_rate()

    # simulate the unlock of the refunded bETH
    token_bridge = accounts.at(wormhole_token_bridge_addr, force=True)
    beth_token.transfer(vault, REFUND_BETH_AMOUNT, {'from': token_bridge})

    tx = vault.burn_refunded_beth(REFUND_BETH_AMOUNT, {'from': vault_admin})

    assert beth_token.totalSupply() == beth_total_supply_before - REFUND_BETH_AMOUNT
    assert vault.get_rate() == beth_rate_before

    helpers.assert_single_event_named('RefundedBethBurned', tx, source=vault, evt_keys_dict={
        'beth_amount': REFUND_BETH_AMOUNT
    })


def test_admin_can_burn_the_refunded_beth_in_two_chunks(
    vault_proxy,
    beth_token,
    stranger,
    vault_admin,
    emergency_admin,
    helpers
):
    upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    vault = as_vault_v3(vault_proxy)

    beth_total_supply_before = beth_token.totalSupply()
    beth_rate_before = vault.get_rate()

    beth_amount_unlock_1 = REFUND_BETH_AMOUNT // 3
    beth_amount_unlock_2 = REFUND_BETH_AMOUNT - beth_amount_unlock_1

    # simulate the unlock of the refunded bETH
    token_bridge = accounts.at(wormhole_token_bridge_addr, force=True)

    beth_token.transfer(vault, beth_amount_unlock_1, {'from': token_bridge})
    tx_1 = vault.burn_refunded_beth(beth_amount_unlock_1, {'from': vault_admin})

    assert beth_token.totalSupply() == beth_total_supply_before - beth_amount_unlock_1
    assert vault.get_rate() == beth_rate_before

    helpers.assert_single_event_named('RefundedBethBurned', tx_1, source=vault, evt_keys_dict={
        'beth_amount': beth_amount_unlock_1
    })

    beth_token.transfer(vault, beth_amount_unlock_2, {'from': token_bridge})
    tx_2 = vault.burn_refunded_beth(beth_amount_unlock_2, {'from': vault_admin})

    assert beth_token.totalSupply() == beth_total_supply_before - REFUND_BETH_AMOUNT
    assert vault.get_rate() == beth_rate_before

    helpers.assert_single_event_named('RefundedBethBurned', tx_2, source=vault, evt_keys_dict={
        'beth_amount': beth_amount_unlock_2
    })


def test_cannot_burn_more_than_the_refunded_amount(
    vault_proxy,
    beth_token,
    stranger,
    vault_admin,
    emergency_admin
):
    upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    vault = as_vault_v3(vault_proxy)

    # simulate the unlock of the refunded bETH
    token_bridge = accounts.at(wormhole_token_bridge_addr, force=True)
    beth_token.transfer(vault, REFUND_BETH_AMOUNT, {'from': token_bridge})

    with reverts():
        vault.burn_refunded_beth(REFUND_BETH_AMOUNT + 1, {'from': vault_admin})

    beth_chunk_1 = REFUND_BETH_AMOUNT // 3

    vault.burn_refunded_beth(beth_chunk_1, {'from': vault_admin})

    with reverts():
        vault.burn_refunded_beth(REFUND_BETH_AMOUNT - beth_chunk_1 + 1, {'from': vault_admin})


def test_non_admin_cannot_burn_the_refunded_beth(vault_proxy, beth_token, stranger, emergency_admin):
    upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    vault = as_vault_v3(vault_proxy)

    # simulate the unlock of the refunded bETH
    token_bridge = accounts.at(wormhole_token_bridge_addr, force=True)
    beth_token.transfer(vault, REFUND_BETH_AMOUNT, {'from': token_bridge})

    liquidations_admin = accounts.at(vault.liquidations_admin(), force=True)

    with reverts():
        vault.burn_refunded_beth(REFUND_BETH_AMOUNT, {'from': stranger})

    with reverts():
        vault.burn_refunded_beth(REFUND_BETH_AMOUNT, {'from': liquidations_admin})

    with reverts():
        vault.burn_refunded_beth(REFUND_BETH_AMOUNT, {'from': emergency_admin})
