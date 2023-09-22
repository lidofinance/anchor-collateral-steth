import pytest
from brownie import ZERO_ADDRESS, Contract, reverts

@pytest.fixture(scope='function')
def vault(
    AnchorVault,
    AnchorVaultProxy,
    deployer,
    admin
):
    impl = AnchorVault.deploy({'from': deployer})
    proxy = AnchorVaultProxy.deploy(impl, admin, {'from': deployer})
    vault = Contract.from_abi('AnchorVault', proxy.address, AnchorVault.abi)

    return vault

@pytest.fixture(scope='function')
def proxy(vault, AnchorVaultProxy):
    return Contract.from_abi('AnchorVaultProxy', vault.address, AnchorVaultProxy.abi)


@pytest.fixture(scope='function')
def new_impl(deployer, Test__NewImplementation):
    return Test__NewImplementation.deploy({'from': deployer})


def test_initial_admin_is_correct(proxy, admin):
    assert proxy.proxy_getAdmin() == admin
    assert not proxy.proxy_getIsOssified()


def test_non_admin_cannot_change_implementation(proxy, new_impl, deployer, stranger):
    with reverts('proxy: unauthorized'):
        proxy.proxy_upgradeTo(new_impl, b'', {'from': deployer})

    with reverts('proxy: unauthorized'):
        proxy.proxy_upgradeTo(new_impl, b'', {'from': stranger})


def test_non_admin_cannot_change_admin(proxy, new_impl, deployer, stranger):
    with reverts('proxy: unauthorized'):
        proxy.proxy_changeAdmin(stranger, {'from': deployer})

    with reverts('proxy: unauthorized'):
        proxy.proxy_changeAdmin(deployer, {'from': stranger})


def test_admin_can_change_implementation(
    proxy,
    new_impl,
    admin,
    Test__NewImplementation,
    stranger,
    helpers,
):
    tx = proxy.proxy_upgradeTo(new_impl, b'', {'from': admin})

    assert proxy.implementation() == new_impl
    helpers.assert_single_event_named('Upgraded', tx, {'implementation': new_impl})

    upgraded_vault = Contract.from_abi(
        'Test__NewImplementation',
        proxy.address,
        Test__NewImplementation.abi
    )

    assert upgraded_vault.wasUpgraded()

    tx = stranger.transfer(upgraded_vault, '1 ether', gas_limit=400_000)
    helpers.assert_single_event_named('EtherReceived', tx, {'amount': '1 ether'})


def test_admin_can_call_implementation_methods(
    proxy,
    new_impl,
    Test__NewImplementation,
    admin,
    helpers,
):
    proxy.proxy_upgradeTo(new_impl, b'', {'from': admin})

    upgraded_vault = Contract.from_abi(
        'Test__NewImplementation',
        proxy.address,
        Test__NewImplementation.abi
    )

    tx = upgraded_vault.doSmth({'from': admin})

    helpers.assert_single_event_named('SmthHappened', tx)


def test_admin_can_change_admin(proxy, stranger, admin, helpers):
    tx = proxy.proxy_changeAdmin(stranger, {'from': admin})

    assert proxy.proxy_getAdmin() == stranger

    helpers.assert_single_event_named('AdminChanged', tx, {
        'previousAdmin': admin,
        'newAdmin': stranger
    })


def test_admin_can_ossify_the_proxy(proxy, new_impl, helpers, admin, deployer):
    tx = proxy.proxy_changeAdmin(ZERO_ADDRESS, {'from': admin})

    assert proxy.proxy_getIsOssified()
    assert proxy.proxy_getAdmin() == ZERO_ADDRESS

    helpers.assert_single_event_named('AdminChanged', tx, {
        'previousAdmin': admin,
        'newAdmin': ZERO_ADDRESS
    })

    with reverts('proxy: ossified'):
        proxy.proxy_upgradeTo(new_impl, b'', {'from': admin})

    with reverts('proxy: ossified'):
        proxy.proxy_changeAdmin(deployer, {'from': admin})
