import pytest

from brownie import ZERO_ADDRESS, reverts, Contract

ZERO_BYTES32 = '0x0000000000000000000000000000000000000000000000000000000000000000'

TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'

# no rewards liquidations for 24h since previous liquidation
NO_LIQUIDATION_INTERVAL = 60 * 60 * 24

# only admin can liquidate rewards for the first 2h after that
RESTRICTED_LIQUIDATION_INTERVAL = NO_LIQUIDATION_INTERVAL + 60 * 60 * 2

VAULT_VERSION = 4

def deploy_and_initialize_vault(
    beth_token,
    steth_token,
    deployer,
    stranger,
    admin,
    lido_dao_agent,
    AnchorVault,
    AnchorVaultProxy,
    helpers
):
    impl = AnchorVault.deploy({'from': deployer})
    impl.petrify_impl({'from': stranger})

    assert impl.admin() == ZERO_ADDRESS
    assert impl.beth_token() == ZERO_ADDRESS
    assert impl.steth_token() == ZERO_ADDRESS

    with reverts('dev: already initialized'):
        impl.initialize(beth_token, steth_token, stranger, {'from': stranger})

    with reverts('dev: already initialized'):
        impl.initialize(beth_token, steth_token, deployer, {'from': deployer})

    proxy = AnchorVaultProxy.deploy(impl, admin, {'from': deployer})
    vault = Contract.from_abi('AnchorVault', proxy.address, AnchorVault.abi)

    tx = vault.initialize(beth_token, steth_token, lido_dao_agent, {'from': stranger})

    helpers.assert_single_event_named('AdminChanged', tx, source=vault, evt_keys_dict={
        'new_admin': lido_dao_agent
    })

    helpers.assert_single_event_named('EmergencyAdminChanged', tx, source=vault, evt_keys_dict={
        'new_emergency_admin': ZERO_ADDRESS
    })

    helpers.assert_single_event_named('VersionIncremented', tx, source=vault, evt_keys_dict={
        'new_version': VAULT_VERSION
    })

    beth_token.set_minter(vault, {'from': admin})

    return vault


def resume_vault(vault, lido_dao_agent):
    assert not vault.operations_allowed()
    vault.resume({'from': lido_dao_agent})
    assert vault.operations_allowed()
    return vault

@pytest.fixture(scope='module')
def vault(
    beth_token,
    steth_token,
    deployer,
    stranger,
    admin,
    lido_dao_agent,
    AnchorVault,
    AnchorVaultProxy,
    helpers
):
    vault = deploy_and_initialize_vault(**locals())
    resume_vault(vault, lido_dao_agent)
    return vault

def test_init_cannot_be_called_twice(beth_token, steth_token, deployer, admin, stranger, AnchorVault):
    vault = AnchorVault.deploy({'from': deployer})

    vault.initialize(beth_token, steth_token, admin, {'from': stranger})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, admin, {'from': stranger})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, admin, {'from': deployer})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, admin, {'from': admin})

def test_init_fails_on_zero_token_address(beth_token, steth_token, deployer, admin, AnchorVault):
    vault = AnchorVault.deploy({'from': deployer})

    with reverts('dev: invalid bETH address'):
        vault.initialize(ZERO_ADDRESS, steth_token, admin, {'from': deployer})

    with reverts('dev: invalid stETH address'):
        vault.initialize(beth_token, ZERO_ADDRESS, admin, {'from': deployer})

def test_init_fails_on_non_zero_beth_total_supply(
    beth_token,
    steth_token,
    admin,
    deployer,
    AnchorVault
):
    beth_token.set_minter(admin, {'from': admin})
    beth_token.mint(admin, 10**18, {'from': admin})

    vault = AnchorVault.deploy({'from': deployer})

    with reverts('dev: non-zero bETH total supply'):
        vault.initialize(beth_token, steth_token, admin, {'from': deployer})


def test_initialized_vault_cannot_be_petrified(
    beth_token,
    steth_token,
    deployer,
    admin,
    stranger,
    AnchorVault
):
    vault = AnchorVault.deploy({'from': deployer})
    vault.initialize(beth_token, steth_token, admin, {'from': stranger})

    with reverts('dev: already initialized'):
        vault.petrify_impl({'from': stranger})

    with reverts('dev: already initialized'):
        vault.petrify_impl({'from': deployer})

    with reverts('dev: already initialized'):
        vault.petrify_impl({'from': admin})

def test_petrified_vault_cannot_be_initialized(
    beth_token,
    steth_token,
    deployer,
    stranger,
    AnchorVault
):
    vault = AnchorVault.deploy({'from': deployer})
    vault.petrify_impl({'from': stranger})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, stranger, {'from': stranger})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, deployer, {'from': deployer})

def test_initial_config_correct(
    vault,
    beth_token,
    lido_dao_agent
):
    assert vault.admin() == lido_dao_agent
    assert vault.emergency_admin() == ZERO_ADDRESS
    assert vault.version() == VAULT_VERSION
    assert vault.beth_token() == beth_token
    assert vault.bridge_connector() == ZERO_ADDRESS
    assert vault.rewards_liquidator() == ZERO_ADDRESS
    assert vault.insurance_connector() == ZERO_ADDRESS
    assert vault.anchor_rewards_distributor() == ZERO_BYTES32
    assert vault.liquidations_admin() == ZERO_ADDRESS
    assert vault.no_liquidation_interval() == 0
    assert vault.restricted_liquidation_interval() == 0

def test_finalize_upgrade_v4_cannot_be_called_on_v4_vault(vault, lido_dao_agent):
    with reverts('unexpected contract version'):
        vault.finalize_upgrade_v4({'from': lido_dao_agent})

@pytest.mark.parametrize('amount', [1 * 10**18, 1 * 10**18 + 10])
def test_deposit_closed(
    vault,
    vault_user,
    amount
):
    with reverts("Minting is discontinued"):
        vault.submit(amount, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user})

def test_change_admin(vault, stranger, admin, helpers, lido_dao_agent):
    with reverts():
        vault.change_admin(stranger, {"from": stranger})

    with reverts():
        tx = vault.change_admin(stranger, {"from": admin})

    tx = vault.change_admin(stranger, {"from": lido_dao_agent})

    helpers.assert_single_event_named('AdminChanged', tx, source=vault, evt_keys_dict={
        'new_admin': stranger
    })
