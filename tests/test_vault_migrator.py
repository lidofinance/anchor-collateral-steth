import pytest
from brownie import Contract, ZERO_ADDRESS, chain, reverts, ETH_ADDRESS

import utils.config as c


NEW_BRIDGE_CONNECTOR = '0xDeaDbeefdEAdbeefdEadbEEFdeadbeEFdEaDbeeF'
NEW_REWARDS_LIQUIDATOR = '0x8badf00d8badf00d8badf00d8badf00d8badf00d'
NEW_ANCHOR_REWARDS_DISTRIBUTOR = '0x0000000000000000000000002c4ab12675bccba793170e21285f8793611135df'

STATE_MIGRATION_NOT_STARTED = 0
STATE_MIGRATION_STARTED = 1
STATE_MIGRATION_FINISHED = 2
STATE_MIGRATION_CANCELLED = 3


@pytest.fixture(scope='module')
def mainnet_vault(AnchorVault):
    return Contract.from_abi('AnchorVault', c.vault_proxy_addr, AnchorVault.abi)


@pytest.fixture(scope='module')
def pre_migration_bridge_connector(mainnet_vault):
    return mainnet_vault.bridge_connector()


@pytest.fixture(scope='module')
def pre_migration_rewards_liquidator(mainnet_vault):
    return mainnet_vault.rewards_liquidator()


@pytest.fixture(scope='module')
def pre_migration_anchor_rewards_distributor(mainnet_vault):
    return mainnet_vault.anchor_rewards_distributor()


@pytest.fixture(scope='module')
def pre_migration_admin(mainnet_vault, accounts):
    return accounts.at(mainnet_vault.admin(), force=True)


@pytest.fixture(scope='module')
def migrator_deployer(accounts):
    return accounts[10]


@pytest.fixture(scope='module', params=[True, False], ids=['exec1(deployer)', 'exec1(admin)'])
def executor_1(migrator_deployer, pre_migration_admin, request):
    return migrator_deployer if request.param else pre_migration_admin


@pytest.fixture(scope='module', params=[True, False], ids=['exec2(deployer)', 'exec2(admin)'])
def executor_2(migrator_deployer, pre_migration_admin, request):
    return migrator_deployer if request.param else pre_migration_admin


@pytest.fixture(scope='module')
def stranger(accounts):
    return accounts[12]


@pytest.fixture(scope='function')
def migrator(
    migrator_deployer,
    mainnet_vault,
    pre_migration_admin,
    pre_migration_bridge_connector,
    pre_migration_rewards_liquidator,
    pre_migration_anchor_rewards_distributor,
    AnchorVaultMigrator
):
    assert mainnet_vault.admin() == pre_migration_admin
    assert mainnet_vault.bridge_connector() == pre_migration_bridge_connector
    assert mainnet_vault.rewards_liquidator() == pre_migration_rewards_liquidator
    assert mainnet_vault.anchor_rewards_distributor() == pre_migration_anchor_rewards_distributor

    migrator = AnchorVaultMigrator.deploy(
        NEW_REWARDS_LIQUIDATOR,
        NEW_BRIDGE_CONNECTOR,
        {'from': migrator_deployer}
    )

    mainnet_vault.change_admin(migrator, {'from': pre_migration_admin})
    assert mainnet_vault.admin() == migrator

    return migrator


def test_initial_state(
    migrator,
    migrator_deployer,
    mainnet_vault,
    pre_migration_admin,
    pre_migration_bridge_connector,
    pre_migration_rewards_liquidator,
    pre_migration_anchor_rewards_distributor
):
    assert migrator.state() == STATE_MIGRATION_NOT_STARTED
    assert migrator.executor() == migrator_deployer
    assert migrator.pre_migration_admin() == pre_migration_admin
    assert migrator.pre_migration_bridge_connector() == ZERO_ADDRESS

    assert mainnet_vault.bridge_connector() == pre_migration_bridge_connector
    assert mainnet_vault.rewards_liquidator() == pre_migration_rewards_liquidator
    assert mainnet_vault.anchor_rewards_distributor() == pre_migration_anchor_rewards_distributor


def test_cannot_start_migration_by_unrelated_address(migrator, stranger):
    with reverts('unauthorized'):
        migrator.start_migration({'from': stranger})


def test_starting_migration_sets_bridge_connector_to_zero(
    migrator,
    executor_1,
    mainnet_vault,
    pre_migration_rewards_liquidator,
    pre_migration_anchor_rewards_distributor,
    helpers
):
    tx = migrator.start_migration({'from': executor_1})
    helpers.assert_single_event_named('MigrationStarted', tx, source=migrator)

    assert mainnet_vault.bridge_connector() == ZERO_ADDRESS
    assert mainnet_vault.rewards_liquidator() == pre_migration_rewards_liquidator
    assert mainnet_vault.anchor_rewards_distributor() == pre_migration_anchor_rewards_distributor
    assert mainnet_vault.admin() == migrator


def test_cannot_start_migration_twice(migrator, executor_1):
    migrator.start_migration({'from': executor_1})
    with reverts('invalid state'):
        migrator.start_migration({'from': executor_1})


def test_cancelling_migration_before_start_resets_admin(
    migrator,
    executor_1,
    mainnet_vault,
    pre_migration_admin,
    pre_migration_bridge_connector,
    pre_migration_rewards_liquidator,
    pre_migration_anchor_rewards_distributor,
    helpers
):
    tx = migrator.cancel_migration({'from': executor_1})
    helpers.assert_single_event_named('MigrationCancelled', tx, source=migrator)

    assert mainnet_vault.admin() == pre_migration_admin
    assert mainnet_vault.bridge_connector() == pre_migration_bridge_connector
    assert mainnet_vault.rewards_liquidator() == pre_migration_rewards_liquidator
    assert mainnet_vault.anchor_rewards_distributor() == pre_migration_anchor_rewards_distributor


def test_cannot_cancel_migration_twice(migrator, executor_1, executor_2):
    migrator.cancel_migration({'from': executor_1})
    with reverts('invalid state'):
        migrator.cancel_migration({'from': executor_2})


def test_cannot_cancel_migration_by_unrelated_address(migrator, stranger):
    with reverts('unauthorized'):
        migrator.cancel_migration({'from': stranger})


def test_cancelling_migration_after_start_resets_vault_state(
    migrator,
    executor_1,
    executor_2,
    mainnet_vault,
    pre_migration_admin,
    pre_migration_bridge_connector,
    pre_migration_rewards_liquidator,
    pre_migration_anchor_rewards_distributor
):
    migrator.start_migration({'from': executor_1})
    migrator.cancel_migration({'from': executor_2})

    assert mainnet_vault.admin() == pre_migration_admin
    assert mainnet_vault.bridge_connector() == pre_migration_bridge_connector
    assert mainnet_vault.rewards_liquidator() == pre_migration_rewards_liquidator
    assert mainnet_vault.anchor_rewards_distributor() == pre_migration_anchor_rewards_distributor


def test_cannot_cancel_migration_by_unrelated_address_after_start(migrator, executor_1, stranger):
    migrator.start_migration({'from': executor_1})
    with reverts('unauthorized'):
        migrator.cancel_migration({'from': stranger})


def test_cannot_start_migration_after_cancellation(migrator, executor_1, executor_2):
    migrator.cancel_migration({'from': executor_1})
    with reverts('invalid state'):
        migrator.start_migration({'from': executor_2})


def test_cannot_start_migration_after_start_and_cancellation(migrator, executor_1, executor_2):
    migrator.start_migration({'from': executor_1})
    migrator.cancel_migration({'from': executor_1})
    with reverts('invalid state'):
        migrator.start_migration({'from': executor_2})


def test_cannot_finish_migration_before_start(migrator, executor_1):
    with reverts('invalid state'):
        migrator.finish_migration({'from': executor_1})


def test_cannot_finish_migration_by_unrelated_address(migrator, executor_1, stranger):
    migrator.start_migration({'from': executor_1})
    with reverts('unauthorized'):
        migrator.finish_migration({'from': stranger})


def test_finishing_migration_sets_final_vault_state(
    migrator,
    executor_1,
    executor_2,
    mainnet_vault,
    pre_migration_admin,
    helpers
):
    migrator.start_migration({'from': executor_1})

    tx = migrator.finish_migration({'from': executor_2})
    helpers.assert_single_event_named('MigrationFinished', tx, source=migrator)

    assert mainnet_vault.admin() == pre_migration_admin
    assert mainnet_vault.bridge_connector() == NEW_BRIDGE_CONNECTOR
    assert mainnet_vault.rewards_liquidator() == NEW_REWARDS_LIQUIDATOR
    assert mainnet_vault.anchor_rewards_distributor() == NEW_ANCHOR_REWARDS_DISTRIBUTOR


def test_cannot_start_migration_after_finish(migrator, executor_1, executor_2):
    migrator.start_migration({'from': executor_1})
    migrator.finish_migration({'from': executor_1})
    with reverts('invalid state'):
        migrator.start_migration({'from': executor_2})


def test_cannot_start_migration_after_finish(migrator, executor_1, executor_2):
    migrator.start_migration({'from': executor_1})
    migrator.finish_migration({'from': executor_1})
    with reverts('invalid state'):
        migrator.start_migration({'from': executor_2})


def test_cannot_cancel_migration_after_finish(migrator, executor_1, executor_2):
    migrator.start_migration({'from': executor_1})
    migrator.finish_migration({'from': executor_1})
    with reverts('invalid state'):
        migrator.cancel_migration({'from': executor_2})


def test_cannot_destroy_migrator_in_a_non_final_state(migrator, executor_1, executor_2):
    with reverts('invalid state'):
        migrator.destroy({'from': executor_1})

    migrator.start_migration({'from': executor_1})

    with reverts('invalid state'):
        migrator.destroy({'from': executor_2})


def test_can_destroy_migrator_after_finish(migrator, executor_1, executor_2):
    migrator.start_migration({'from': executor_1})
    migrator.finish_migration({'from': executor_1})
    migrator.destroy({'from': executor_2})


def test_can_destroy_migrator_after_cancellation(migrator, executor_1, executor_2):
    migrator.start_migration({'from': executor_1})
    migrator.cancel_migration({'from': executor_1})
    migrator.destroy({'from': executor_2})
