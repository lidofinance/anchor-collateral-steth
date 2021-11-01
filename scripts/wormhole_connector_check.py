from brownie import interface, accounts, Contract, ZERO_ADDRESS
from brownie import (
    bEth,
    AnchorVault,
    AnchorVaultProxy,
    BridgeConnectorShuttle,
)

from scripts.deploy_wormhole_connector import (
    deploy_wormhole_bridge_connector,
    switch_bridge_connector_in_vault,
)

import utils.log as log

from utils.config import (
    get_is_live,
    token_bridge_wormhole_address,
    vault_proxy_address
)

from utils.mainnet_fork import chain_snapshot

TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'

def assert_equals(desc, actual, expected):
    assert actual == expected
    log.ok(desc, actual)


def main():
    dev_multisig = '0x3cd9F71F80AB08ea5a7Dca348B5e94BC595f26A0'
    
    vault_proxy = AnchorVaultProxy.at(vault_proxy_address)
    vault = Contract.from_abi('AnchorVault', vault_proxy.address, AnchorVault.abi)
    beth_token = bEth.at('0x707F9118e33A9B8998beA41dd0d46f38bb963FC8')
    ust_token = interface.ERC20('0xa47c8bf37f92aBed4A126BDA807A7b7498661acD')
    steth_token = interface.Lido('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')
    bridge_connector_shuttle = BridgeConnectorShuttle.at('0x513251faB2542532753972B8FE9A7b60621affaD')
    token_bridge_wormhole = interface.Bridge(token_bridge_wormhole_address)

    # Needed to properly decode LogMessagePublished events of Wormhole bridge
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

    if get_is_live():
        print('Running on a live network, cannot run further checks.')
        print('Run on a mainnet fork to do this.')
        return

    print('Deploying BridgeConnectorWormhole...')

    bridge_connector_wormhole = deploy_wormhole_bridge_connector(token_bridge_wormhole.address, {'from': dev_multisig})

    log.ok('Wormhole bridge connector', bridge_connector_wormhole.address)
    assert_equals('  wormhole_token_bridge', bridge_connector_wormhole.wormhole_token_bridge(), token_bridge_wormhole.address)

    print()

    print('Changing bridge connector on vault...')

    switch_bridge_connector_in_vault(vault, bridge_connector_wormhole, {'from': dev_multisig})

    log.ok('AnchorVault', vault.address)
    assert_equals('  bridge_connector', vault.bridge_connector(), bridge_connector_wormhole.address)

    with chain_snapshot():
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
        assert str(tx.events['LogMessagePublished']['payload']).endswith('000000000000000000000000707f9118e33a9b8998bea41dd0d46f38bb963fc80002abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd00030000000000000000000000000000000000000000000000000000000000000000')

        log.ok('bridge bETH balance', bridge_balance / 10**18)

        print()

        print('Selling rewards...')

        burner = accounts.add()
        voting_app = accounts.at('0x2e59A20f205bB85a89C53f1936454680651E618e', force=True)
        acl = interface.ACL('0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb')
        acl.grantPermission(burner, steth_token, steth_token.BURN_ROLE(), {'from': voting_app})

        steth_token.burnShares(holder_1, steth_token.getSharesByPooledEth(1 * 5**18), {'from': burner})

        tx = vault.collect_rewards({'from': liquidations_admin})
        tx.info()

        assert 'LogMessagePublished' in tx.events
        assert str(tx.events['LogMessagePublished']['payload']).endswith('000000000000000000000000a47c8bf37f92abed4a126bda807a7b7498661acd00022c4ab12675bccba793170e21285f8793611135df00000000000000000000000000030000000000000000000000000000000000000000000000000000000000000000')
