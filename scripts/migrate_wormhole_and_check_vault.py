from brownie import interface, accounts, network, Contract, ZERO_ADDRESS

from brownie import (
    AnchorVault,
    BridgeConnectorWormhole,
    RewardsLiquidator,
    AnchorVaultMigrator
)

import utils.log as log
import utils.config as c

from utils.log import assert_equals
from utils.mainnet_fork import chain_snapshot

from scripts.deploy_wormhole_migration import deploy_wormhole_migration_components
from scripts.check_vault import check_vault


def warn_live():
    print('Running on a live network, cannot run further checks.')
    print('Run on a mainnet fork to do this.')


def main():
    migrator = None
    bridge_connector = None
    rewards_liquidator = None
    migration_executor_addr = None

    if c.wh_migrator_addr is None:
        log.nb('Wormhole migration components are not yet deployed')
        if c.get_is_live():
            warn_live()
            return
        executor = accounts[0]
        (bridge_connector,
            rewards_liquidator,
            migrator) = deploy_wormhole_migration_components(executor, {'from': executor})
        migration_executor_addr = executor.address
    else:
        log.ok('Wormhole migration components are already deployed')
        migrator = AnchorVaultMigrator.at(c.wh_migrator_addr)
        bridge_connector = BridgeConnectorWormhole.at(c.bridge_connector_addr)
        rewards_liquidator = RewardsLiquidator.at(c.rewards_liquidator_addr)
        migration_executor_addr = c.wh_migration_executor_addr

    vault = Contract.from_abi('AnchorVault', c.vault_proxy_addr, AnchorVault.abi)

    log.ok('AnchorVaultMigrator', migrator.address)
    assert_equals('  executor', migrator.executor(), migration_executor_addr)
    assert_equals('  state', migrator.state(), 0)
    assert_equals('  pre_migration_admin', migrator.pre_migration_admin(), vault.admin())

    if c.get_is_live():
        warn_live()
        return

    with chain_snapshot():
        executor = accounts.at(migration_executor_addr, force=True)

        migrate_wormhole(
            migrator,
            executor,
            bridge_connector,
            rewards_liquidator
        )

        check_vault(
            vault_proxy_addr=c.vault_proxy_addr,
            vault_impl_addr=c.vault_impl_addr,
            beth_token_addr=c.beth_token_addr,
            bridge_connector_addr=bridge_connector.address,
            rewards_liquidator_addr=rewards_liquidator.address,
            insurance_connector_addr=c.insurance_connector_addr,
            terra_rewards_distributor_addr=c.terra_rewards_distributor_addr,
            vault_admin=c.dev_multisig_addr,
            vault_liquidations_admin=c.vault_liquidations_admin_addr,
            rew_liq_max_steth_eth_price_difference_percent=c.rew_liq_max_steth_eth_price_difference_percent,
            rew_liq_max_eth_usdc_price_difference_percent=c.rew_liq_max_eth_usdc_price_difference_percent,
            rew_liq_max_usdc_ust_price_difference_percent=c.rew_liq_max_usdc_ust_price_difference_percent,
            rew_liq_max_steth_ust_price_difference_percent=c.rew_liq_max_steth_ust_price_difference_percent
        )


def migrate_wormhole(migrator, executor, bridge_connector, rewards_liquidator):
    log.h('Changing vault admin...')

    vault = Contract.from_abi('AnchorVault', c.vault_proxy_addr, AnchorVault.abi)
    admin = accounts.at(vault.admin(), force=True)

    vault.change_admin(migrator, {'from': admin})
    assert_equals('AnchorVault.admin', vault.admin(), migrator.address)

    log.h('Statring migration...')

    pre_migration_bridge_connector = vault.bridge_connector()

    migrator.start_migration({'from': executor})

    assert_equals('AnchorVaultMigrator.state', migrator.state(), 1)
    assert_equals(
        'AnchorVaultMigrator.pre_migration_bridge_connector',
        migrator.pre_migration_bridge_connector(),
        pre_migration_bridge_connector
    )
    assert_equals('vault.bridge_connector', vault.bridge_connector(), ZERO_ADDRESS)

    log.h('Finishing migration...')

    migrator.finish_migration({'from': executor})

    assert_equals('AnchorVaultMigrator.state', migrator.state(), 2)
    assert_equals('AnchorVault.bridge_connector', vault.bridge_connector(), bridge_connector.address)
    assert_equals('AnchorVault.rewards_liquidator', vault.rewards_liquidator(), rewards_liquidator.address)
    assert_equals('AnchorVault.admin', vault.admin(), admin.address)
