from brownie import interface, accounts, Contract, ZERO_ADDRESS
from brownie import (
    bEth,
    AnchorVault,
    AnchorVaultProxy,
    BridgeConnectorShuttle,
    BridgeConnectorWormhole,
)

from scripts.deploy_wormhole_connector import (
    deploy_wormhole_bridge_connector,
    switch_bridge_connector_in_vault,
)

import utils.log as log

from utils.config import (
    get_is_live,
    get_env, 
    vault_proxy_address,
    vault_ropsten_address,
    beth_token_address,
    beth_token_ropsten_address,
    ust_wormhole_token_address,
    ust_wormhole_token_ropsten_address,
    steth_token_address,
    steth_token_ropsten_address,
    bridge_connector_shuttle_address,
    bridge_connector_shuttle_ropsten_address,
    token_bridge_wormhole_ropsten_address,
    token_bridge_wormhole_address,
    wormhole_address,
    wormhole_ropsten_address,
    mock_liquidator_shuttle_ropsten,
    mock_liquidator_wormhole_ropsten,
)

from utils.mainnet_fork import chain_snapshot

TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'

def assert_equals(desc, actual, expected):
    assert actual == expected
    log.ok(desc, actual)

def run_ropsten():
    dev_multisig = '0x02139137fdd974181a49268d7b0ae888634e5469'

    vault = AnchorVault.at(vault_ropsten_address)
    beth_token = bEth.at(beth_token_ropsten_address)
    ust_token = interface.ERC20(ust_wormhole_token_ropsten_address)
    steth_token = interface.LidoRopsten(steth_token_ropsten_address)
    bridge_connector_shuttle = BridgeConnectorShuttle.at(bridge_connector_shuttle_ropsten_address)
    token_bridge_wormhole = interface.Bridge(token_bridge_wormhole_ropsten_address)

    # Needed to properly decode LogMessagePublished events of Wormhole bridge
    wormhole = interface.Wormhole(wormhole_ropsten_address)

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

    if vault.bridge_connector() == bridge_connector_shuttle.address:
        log.ok('  bridge_connector', vault.bridge_connector())
    else:
        print()
        print('AnchorVault.bridge_connector is set to other location than known shuttle connector. Exiting...')
        return

    print()

    if get_is_live():
        print('Running on a live network, cannot run further checks.')
        print('Run on a ropsten fork to do this.')
        return

    print('Deploying BridgeConnectorWormhole...')

    bridge_connector_wormhole = deploy_wormhole_bridge_connector(
        token_bridge_wormhole.address, 
        beth_token.address,
        ust_token.address,
        {'from': dev_multisig}
    )

    log.ok('Wormhole bridge connector', bridge_connector_wormhole.address)
    assert_equals('  wormhole_token_bridge', bridge_connector_wormhole.wormhole_token_bridge(), token_bridge_wormhole.address)

    print()

    print('Changing bridge connector on vault...')

    switch_bridge_connector_in_vault(vault, bridge_connector_wormhole, {'from': dev_multisig})

    log.ok('AnchorVault', vault.address)
    assert_equals('  bridge_connector', vault.bridge_connector(), bridge_connector_wormhole.address)

    print('Changing rewards liquidator on vault...')

    assert_equals('  rewards_liquidator', vault.rewards_liquidator(), mock_liquidator_shuttle_ropsten)

    vault.set_rewards_liquidator(mock_liquidator_wormhole_ropsten, {'from': dev_multisig})

    log.ok('AnchorVault', vault.address)
    assert_equals('  rewards_liquidator', vault.rewards_liquidator(), mock_liquidator_wormhole_ropsten)

    with chain_snapshot():
        print()

        print('Submitting stETH...')
        beth_supply = beth_token.totalSupply()

        holder_1 = accounts[0]

        steth_token.submit(ZERO_ADDRESS, {'from': holder_1, 'value': 3 * 10**18})

        assert steth_token.balanceOf(holder_1) > 0

        bridge_beth_balance_before = beth_token.balanceOf(token_bridge_wormhole)

        value_to_submit = 2 * 10**18

        steth_token.approve(vault, value_to_submit, {'from': holder_1})

        tx = vault.submit(value_to_submit, TERRA_ADDRESS, b'', {'from': holder_1})
        tx.info()

        bridge_beth_balance_after = beth_token.balanceOf(token_bridge_wormhole)

        assert (bridge_beth_balance_after - bridge_beth_balance_before) == value_to_submit
        assert beth_token.balanceOf(holder_1) == 0
        assert beth_token.totalSupply() == beth_supply + 2 * 10**18

        assert 'LogMessagePublished' in tx.events
        
        reference_payload = "0x01" # payloadId
        reference_payload += "000000000000000000000000000000000000000000000000000000000bebc200" # amount
        reference_payload += "000000000000000000000000" + beth_token_ropsten_address[2:].lower() # tokenAddress
        reference_payload += "2711" # tokenChain 
        reference_payload += "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd" # to
        reference_payload += "0003" # toChain
        reference_payload += "0000000000000000000000000000000000000000000000000000000000000000" # fee

        assert str(tx.events['LogMessagePublished']['payload']) == reference_payload

        log.ok('bridge bETH balance', bridge_beth_balance_after / 10**18)

        print()

        print('Selling rewards...')

        steth_token.simulateBeaconRewards({'from': dev_multisig})

        tx = vault.collect_rewards({'from': dev_multisig})
        tx.info()

        assert 'LogMessagePublished' in tx.events

        # See https://github.com/certusone/wormhole/blob/aff369ff4dcd7ec287bfe6b0778ee410f8bd9587/ethereum/contracts/bridge/Bridge.sol#L97-L103
        # reference_payload = "0x01" # payloadId
        # reference_payload += "00000000000000000000000000000000000000000000000000000002dd8dedd2" # amount
        reference_payload = "0100000000000000000000000000000000000000000000000000000075757364" # tokenAddress (UST native)
        reference_payload += "0003" # tokenChain (Terra)
        reference_payload += "976309db2db556f107c28fe4d7eab7c7e676c194000000000000000000000000" # to
        reference_payload += "0003" # toChain (Terra)
        reference_payload += "0000000000000000000000000000000000000000000000000000000000000000" # fee

        assert str(tx.events['LogMessagePublished']['payload']).endswith(reference_payload)

def run_mainnet():
    dev_multisig = '0x3cd9F71F80AB08ea5a7Dca348B5e94BC595f26A0'

    vault_proxy = AnchorVaultProxy.at(vault_proxy_address)
    vault = Contract.from_abi('AnchorVault', vault_proxy.address, AnchorVault.abi)
    beth_token = bEth.at(beth_token_address)
    ust_token = interface.ERC20(ust_wormhole_token_address)
    steth_token = interface.Lido(steth_token_address)
    bridge_connector_shuttle = BridgeConnectorShuttle.at(bridge_connector_shuttle_address)
    token_bridge_wormhole = interface.Bridge(token_bridge_wormhole_address)

    # Needed to properly decode LogMessagePublished events of Wormhole bridge
    wormhole = interface.Wormhole(wormhole_address)

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

    if vault.bridge_connector() == bridge_connector_shuttle.address:
        log.ok('  bridge_connector', vault.bridge_connector())
    else:
        print()
        print('AnchorVault.bridge_connector is set to other location than known shuttle connector. Exiting...')
        return

    print()

    if get_is_live():
        print('Running on a live network, cannot run further checks.')
        print('Run on a mainnet fork to do this.')
        return

    print('Deploying BridgeConnectorWormhole...')

    bridge_connector_wormhole = deploy_wormhole_bridge_connector(
        token_bridge_wormhole.address, 
        beth_token.address,
        ust_token.address,
        {'from': dev_multisig}
    )

    log.ok('Wormhole bridge connector', bridge_connector_wormhole.address)
    assert_equals('  wormhole_token_bridge', bridge_connector_wormhole.wormhole_token_bridge(), token_bridge_wormhole.address)

    print()

    print('Changing bridge connector on vault...')

    switch_bridge_connector_in_vault(vault, bridge_connector_wormhole, {'from': dev_multisig})

    log.ok('AnchorVault', vault.address)
    assert_equals('  bridge_connector', vault.bridge_connector(), bridge_connector_wormhole.address)

    with chain_snapshot():
        print()

        print('Submitting stETH...')
        beth_supply = beth_token.totalSupply()

        holder_1 = accounts[0]

        steth_token.submit(ZERO_ADDRESS, {'from': holder_1, 'value': 3 * 10**18})

        assert steth_token.balanceOf(holder_1) > 0

        bridge_beth_balance_before = beth_token.balanceOf(token_bridge_wormhole)

        value_to_submit = 2 * 10**18

        steth_token.approve(vault, value_to_submit, {'from': holder_1})

        tx = vault.submit(value_to_submit, TERRA_ADDRESS, b'', {'from': holder_1})
        tx.info()

        bridge_beth_balance_after = beth_token.balanceOf(token_bridge_wormhole)

        assert (bridge_beth_balance_after - bridge_beth_balance_before) == value_to_submit
        assert beth_token.balanceOf(holder_1) == 0
        assert beth_token.totalSupply() == beth_supply + 2 * 10**18

        assert 'LogMessagePublished' in tx.events
        
        reference_payload = "0x01" # payloadId
        reference_payload += "000000000000000000000000000000000000000000000000000000000bebc200" # amount
        reference_payload += "000000000000000000000000" + beth_token_address[2:].lower() # tokenAddress
        reference_payload += "0002" # tokenChain
        reference_payload += "abcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd" # to
        reference_payload += "0003" # toChain
        reference_payload += "0000000000000000000000000000000000000000000000000000000000000000" # fee

        assert str(tx.events['LogMessagePublished']['payload']) == reference_payload

        log.ok('bridge bETH balance', bridge_beth_balance_after / 10**18)

        print()

        liquidations_admin = accounts.at('0x1A9967A7b0c3dd39962296E53F5cf56471385dF2', force=True)
        print('Selling rewards...')

        burner = accounts.add()
        voting_app = accounts.at('0x2e59A20f205bB85a89C53f1936454680651E618e', force=True)
        acl = interface.ACL('0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb')
        acl.grantPermission(burner, steth_token, steth_token.BURN_ROLE(), {'from': voting_app})

        steth_token.burnShares(holder_1, steth_token.getSharesByPooledEth(1 * 5**18), {'from': burner})
        tx = vault.collect_rewards({'from': liquidations_admin})
        tx.info()

        assert 'LogMessagePublished' in tx.events
        # reference_payload = "0x01" # payloadId
        # reference_payload += "0000000000000000000000000000000000000000000000000000000000016b06" # amount 
        reference_payload = "0100000000000000000000000000000000000000000000000000000075757364" # tokenAddress (UST native)
        reference_payload += "0003" # tokenChain (Terra)
        reference_payload += "2c4ab12675bccba793170e21285f8793611135df000000000000000000000000" # to
        reference_payload += "0003" # toChain (Terra)
        reference_payload += "0000000000000000000000000000000000000000000000000000000000000000" # fee
        
        assert str(tx.events['LogMessagePublished']['payload']).endswith(reference_payload)

def main():
    net = get_env("NET", False, None, "mainnet")
    
    if net == "ropsten":
        run_ropsten()
    else:
        run_mainnet()
