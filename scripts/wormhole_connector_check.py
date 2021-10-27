from brownie import interface, accounts, network, Contract, ZERO_ADDRESS
from brownie import (
    bEth,
    AnchorVault,
    AnchorVaultProxy,
    BridgeConnectorShuttle,
    BridgeConnectorWormhole,
)

import utils.log as log
from utils.mainnet_fork import chain_snapshot


def assert_equals(desc, actual, expected):
    assert actual == expected
    log.ok(desc, actual)


def main():
    dev_multisig = '0x3cd9F71F80AB08ea5a7Dca348B5e94BC595f26A0'

    vault_proxy = AnchorVaultProxy.at('0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf')
    vault_impl = AnchorVault.at('0x0627054d17eAe63ec23C6d8b07d8Db7A66ffd45a')
    vault = Contract.from_abi('AnchorVault', vault_proxy.address, AnchorVault.abi)
    beth_token = bEth.at('0x707F9118e33A9B8998beA41dd0d46f38bb963FC8')
    ust_token = interface.ERC20('0xa47c8bf37f92aBed4A126BDA807A7b7498661acD')
    steth_token = interface.Lido('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')
    bridge_connector_shuttle = BridgeConnectorShuttle.at('0x513251faB2542532753972B8FE9A7b60621affaD')
    token_bridge_wormhole = interface.Bridge('0x736D2A394f7810C17b3c6fEd017d5BC7D60c077d')

    log.ok('dev multisig', dev_multisig)

    print()

    log.ok('stETH', steth_token.address)
    log.ok('bETH', beth_token.address)
    log.ok('UST', ust_token.address)

    print()

    log.ok('AnchorVault', vault.address)
    assert_equals('  admin', vault.admin(), dev_multisig)
    assert_equals('  beth_token', vault.beth_token(), beth_token.address)
    assert_equals('  steth_token', vault.steth_token(), steth_token.address)
    assert_equals('  bridge_connector', vault.bridge_connector(), bridge_connector_shuttle.address)

    print()

    print('Deploying BridgeConnectorWormhole...')

    bridge_connector_wormhole = BridgeConnectorWormhole.deploy(token_bridge_wormhole, {'from': dev_multisig})

    log.ok('Wormhole bridge connector', bridge_connector_wormhole.address)
    assert_equals('  wormhole_token_bridge', bridge_connector_wormhole.wormhole_token_bridge(), token_bridge_wormhole.address)

    print()

    print('Changing bridge connector on vault...')

    tx = vault.set_bridge_connector(bridge_connector_wormhole.address, {'from': dev_multisig})
    tx.info()

    log.ok('AnchorVault', vault.address)
    assert_equals('  bridge_connector', vault.bridge_connector(), bridge_connector_wormhole.address)
    # TODO: By some reason same is not applied to vault_impl. It such behavior correct?
