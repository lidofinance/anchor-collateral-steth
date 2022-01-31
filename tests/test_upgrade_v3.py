import pytest
from brownie import accounts, interface, Contract, AnchorVault, reverts, chain, ZERO_ADDRESS

"""
These tests should be ran on a mainnet block produced
before the v3 upgrade, e.g. on the block 14158645.
"""

MAINNET_VAULT = '0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf'


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
        vault.initialize(new_beth_token, steth_token, stranger, {'from': stranger})

    with reverts():
        vault.initialize(new_beth_token, steth_token, vault_admin, {'from': vault_admin})


def upgrade_vault_to_v3(vault_proxy, impl_deployer):
    proxy_admin = accounts.at(vault_proxy.proxy_getAdmin(), force=True)

    new_impl = AnchorVault.deploy({'from': impl_deployer})
    new_impl.petrify_impl({'from': impl_deployer})

    setup_calldata = new_impl.finalize_upgrade_v3.encode_input()
    return vault_proxy.proxy_upgradeTo(new_impl, setup_calldata, {'from': proxy_admin})


def test_upgrade_changes_version_to_3(vault_proxy, stranger, helpers):
    tx = upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger)
    vault = as_vault_v3(vault_proxy)

    assert vault.version() == 3

    helpers.assert_single_event_named('VersionIncremented', tx, source=vault, evt_keys_dict={
        'new_version': 3
    })


def test_finalize_upgrade_v3_cannot_be_called_twice(vault_proxy, stranger, vault_admin):
    tx = upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger)
    vault = as_vault_v3(vault_proxy)

    with reverts('unexpected contract version'):
        vault.finalize_upgrade_v3({'from': vault_admin})


def test_finalize_upgrade_v3_cannot_be_called_on_v4_vault(vault_proxy, stranger, vault_admin):
    tx = upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger)
    vault = as_vault_v3(vault_proxy)

    vault.bump_version({'from': vault_admin})
    assert vault.version() == 4

    with reverts('unexpected contract version'):
        vault.finalize_upgrade_v3({'from': vault_admin})
