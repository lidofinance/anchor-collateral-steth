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


def deploy_wormhole_migration_components(executor, tx_params):
    log.h('Deploying Wormhole migration components...')

    bridge_connector = BridgeConnectorWormhole.deploy(c.wormhole_token_bridge_addr, tx_params)
    log.ok('BridgeConnectorWormhole', bridge_connector.address)

    print()
    rewards_liquidator = RewardsLiquidator.deploy(
        c.vault_proxy_addr,
        c.dev_multisig_addr,
        int(c.rew_liq_max_steth_eth_price_difference_percent * 10**18 / 100),
        int(c.rew_liq_max_eth_usdc_price_difference_percent * 10**18 / 100),
        int(c.rew_liq_max_usdc_ust_price_difference_percent * 10**18 / 100),
        int(c.rew_liq_max_steth_ust_price_difference_percent * 10**18 / 100),
        tx_params
    )
    log.ok('RewardsLiquidator', rewards_liquidator.address)

    print()
    migrator = AnchorVaultMigrator.deploy(
        rewards_liquidator,
        bridge_connector,
        tx_params
    )
    log.ok('AnchorVaultMigrator', migrator.address)

    vault = Contract.from_abi('AnchorVault', c.vault_proxy_addr, AnchorVault.abi)

    assert_equals('  executor', migrator.executor(), executor.address)
    assert_equals('  state', migrator.state(), 0)
    assert_equals('  pre_migration_admin', migrator.pre_migration_admin(), vault.admin())

    return (bridge_connector, rewards_liquidator, migrator)

