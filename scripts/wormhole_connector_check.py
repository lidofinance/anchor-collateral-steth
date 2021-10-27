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

TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'

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
    token_bridge_wormhole = interface.Bridge('0x3ee18B2214AFF97000D974cf647E7C347E8fa585')
    wormhole = interface.Wormhole('0x98f3c9e6E3fAce36bAAd05FE09d375Ef1464288B')

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

    with chain_snapshot():
        dev_multisig_acct = accounts.at(dev_multisig, force=True)
        liquidations_admin = accounts.at('0x1A9967A7b0c3dd39962296E53F5cf56471385dF2', force=True)

        print()

        print('Submitting stETH...')
        beth_supply = beth_token.totalSupply()

        holder_1 = accounts[0]

        steth_token.submit(ZERO_ADDRESS, {'from': holder_1, 'value': 3 * 10**18})
        assert steth_token.balanceOf(holder_1) > 0
        assert beth_token.balanceOf(token_bridge_wormhole) == 0
        steth_token.approve(vault, 2 * 10**18, {'from': holder_1})

        tx = vault.submit(2 * 10**18, TERRA_ADDRESS, b'', {'from': holder_1})
        tx.info()

        bridge_balance = beth_token.balanceOf(token_bridge_wormhole)

        assert bridge_balance == 2 * 10**18
        assert beth_token.balanceOf(holder_1) == 0
        assert beth_token.totalSupply() == beth_supply + 2 * 10**18

        assert 'LogMessagePublished' in tx.events
        assert tx.events['LogMessagePublished']['payload'] == '0x01000000000000000000000000000000000000000000000000000000000bebc200000000000000000000000000707f9118e33a9b8998bea41dd0d46f38bb963fc80002abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd00030000000000000000000000000000000000000000000000000000000000000000'

        log.ok('bridge bETH balance', bridge_balance / 10**18)

        print()
        
        print('Selling rewards...')

        tx = vault.collect_rewards({'from': liquidations_admin})
        tx.info()
        # @TODO: get to collect_rewards() stage when it calls forward_ust()