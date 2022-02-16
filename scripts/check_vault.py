from brownie import interface, accounts, network, Contract, ZERO_ADDRESS
from brownie import (
    bEth,
    AnchorVault,
    AnchorVaultProxy,
    BridgeConnectorWormhole,
    RewardsLiquidator,
    InsuranceConnector
)

import utils.log as log
import utils.config as c
import utils.wormhole as wh

from utils.log import assert_equals
from utils.mainnet_fork import chain_snapshot


def main():
    check_vault(
        vault_proxy_addr=c.vault_proxy_addr,
        vault_impl_addr=c.vault_impl_addr,
        beth_token_addr=c.beth_token_addr,
        bridge_connector_addr=c.bridge_connector_addr,
        rewards_liquidator_addr=c.rewards_liquidator_addr,
        insurance_connector_addr=c.insurance_connector_addr,
        terra_rewards_distributor_addr=c.terra_rewards_distributor_addr,
        vault_admin=c.lido_dao_agent_addr,
        rewards_liquidator_admin=c.dev_multisig_addr,
        vault_liquidations_admin=c.vault_liquidations_admin_addr,
        rew_liq_max_steth_eth_price_difference_percent=c.rew_liq_max_steth_eth_price_difference_percent,
        rew_liq_max_eth_usdc_price_difference_percent=c.rew_liq_max_eth_usdc_price_difference_percent,
        rew_liq_max_usdc_ust_price_difference_percent=c.rew_liq_max_usdc_ust_price_difference_percent,
        rew_liq_max_steth_ust_price_difference_percent=c.rew_liq_max_steth_ust_price_difference_percent
    )


def check_vault(
    vault_proxy_addr,
    vault_impl_addr,
    beth_token_addr,
    bridge_connector_addr,
    rewards_liquidator_addr,
    insurance_connector_addr,
    terra_rewards_distributor_addr,
    vault_admin,
    rewards_liquidator_admin,
    vault_liquidations_admin,
    rew_liq_max_steth_eth_price_difference_percent,
    rew_liq_max_eth_usdc_price_difference_percent,
    rew_liq_max_usdc_ust_price_difference_percent,
    rew_liq_max_steth_ust_price_difference_percent
):
    # Needed to properly decode LogMessagePublished events of Wormhole bridge
    wormhole = interface.Wormhole(c.wormhole_addr)

    vault_proxy = AnchorVaultProxy.at(vault_proxy_addr)
    vault_impl = AnchorVault.at(vault_impl_addr)
    vault = Contract.from_abi('AnchorVault', vault_proxy.address, AnchorVault.abi)
    beth_token = bEth.at(beth_token_addr)
    ust_token = interface.WormholeWrappedToken(c.ust_token_addr)
    steth_token = interface.Lido(c.steth_token_addr)

    bridge_connector = BridgeConnectorWormhole.at(bridge_connector_addr)
    rewards_liquidator = RewardsLiquidator.at(rewards_liquidator_addr)
    insurance_connector = InsuranceConnector.at(insurance_connector_addr)

    terra_rewards_distributor_wh_encoded_addr = wh.encode_addr(terra_rewards_distributor_addr)

    log.ok('vault admin', vault_admin)

    print()

    log.ok('stETH', steth_token.address)
    log.ok('UST', ust_token.address)

    print()

    log.ok('bETH', beth_token.address)
    assert_equals('  admin', beth_token.admin(), vault_admin)
    assert_equals('  minter', beth_token.minter(), vault_proxy)
    # assert_equals('  totalSupply', beth_token.totalSupply(), 0)
    assert_equals('  name', beth_token.name(), 'bETH')
    assert_equals('  symbol', beth_token.symbol(), 'bETH')
    assert_equals('  decimals', beth_token.decimals(), 18)

    print()

    log.ok('AnchorVault impl', vault_impl.address)

    assert_equals('  admin', vault_impl.admin(), ZERO_ADDRESS)
    assert_equals('  bridge_connector', vault_impl.bridge_connector(), ZERO_ADDRESS)
    assert_equals('  rewards_liquidator', vault_impl.rewards_liquidator(), ZERO_ADDRESS)
    assert_equals('  insurance_connector', vault_impl.insurance_connector(), ZERO_ADDRESS)

    print()

    no_liquidation_interval = 0
    restricted_liquidation_interval = 26 * 60 * 60

    log.ok('AnchorVaultProxy', vault_proxy.address)
    assert_equals('  proxy_getAdmin', vault_proxy.proxy_getAdmin(), vault_admin)
    assert_equals('  proxy_getIsOssified', vault_proxy.proxy_getIsOssified(), False)
    assert_equals('  implementation', vault_proxy.implementation(), vault_impl)
    assert_equals('  admin', vault.admin(), vault_admin)
    assert_equals('  beth_token', vault.beth_token(), beth_token.address)
    assert_equals('  steth_token', vault.steth_token(), steth_token.address)
    assert_equals('  bridge_connector', vault.bridge_connector(), bridge_connector.address)
    assert_equals('  rewards_liquidator', vault.rewards_liquidator(), rewards_liquidator.address)
    assert_equals('  insurance_connector', vault.insurance_connector(), insurance_connector.address)
    assert_equals('  vault_liquidations_admin', vault.liquidations_admin(), vault_liquidations_admin)
    assert_equals('  no_liquidation_interval', vault.no_liquidation_interval(), no_liquidation_interval)
    assert_equals('  restricted_liquidation_interval', vault.restricted_liquidation_interval(), restricted_liquidation_interval)
    assert_equals('  anchor_rewards_distributor', vault.anchor_rewards_distributor(), terra_rewards_distributor_wh_encoded_addr)
    assert_equals('  get_rate', vault.get_rate(), 10**18)

    print()

    log.ok('BridgeConnectorWormhole', bridge_connector.address)
    assert_equals('  wormhole_token_bridge', bridge_connector.wormhole_token_bridge(), c.wormhole_token_bridge_addr)

    print()

    log.ok('RewardsLiquidator', rewards_liquidator.address)
    assert_equals('  admin', rewards_liquidator.admin(), rewards_liquidator_admin)
    assert_equals('  vault', rewards_liquidator.vault(), vault_proxy.address)
    assert_equals('  max_steth_eth_price_difference_percent',
        rewards_liquidator.max_steth_eth_price_difference_percent(),
        int(rew_liq_max_steth_eth_price_difference_percent * 10**18 / 100)
    )
    assert_equals('  max_eth_usdc_price_difference_percent',
        rewards_liquidator.max_eth_usdc_price_difference_percent(),
        int(rew_liq_max_eth_usdc_price_difference_percent * 10**18 / 100)
    )
    assert_equals('  max_usdc_ust_price_difference_percent',
        rewards_liquidator.max_usdc_ust_price_difference_percent(),
        int(rew_liq_max_usdc_ust_price_difference_percent * 10**18 / 100)
    )
    assert_equals('  max_steth_ust_price_difference_percent',
        rewards_liquidator.max_steth_ust_price_difference_percent(),
        int(rew_liq_max_steth_ust_price_difference_percent * 10**18 / 100)
    )

    print()

    log.ok('InsuranceConnector', insurance_connector.address)

    print()

    log.ok('liquidations admin', vault_liquidations_admin)
    log.ok('no liquidation interval', f'{no_liquidation_interval} sec ({no_liquidation_interval / 3600} hrs)')
    log.ok('restricted liquidation interval', f'{restricted_liquidation_interval} sec ({restricted_liquidation_interval / 3600} hrs)')
    log.ok('terra rewards distributor', terra_rewards_distributor_wh_encoded_addr)

    print()

    if c.get_is_live():
        print('Running on a live network, cannot run further checks.')
        print('Run on a mainnet fork to do this.')
        return

    log.h('Performing AnchorVault fork checks')

    with chain_snapshot():
        if not vault.can_deposit_or_withdraw():
            log.h('Selling rewards...')
            tx = vault.collect_rewards({'from': accounts.at(vault_liquidations_admin, force=True)})
            # tx.info()
            assert_equals('AnchorVault.can_deposit_or_withdraw', vault.can_deposit_or_withdraw(), True)

        beth_supply_before = beth_token.totalSupply()
        bridge_balance_before = beth_token.balanceOf(c.wormhole_token_bridge_addr)

        log.ok('bETH total supply', beth_supply_before)
        log.ok('bridge bETH balance', bridge_balance_before)

        log.h('Obtaining stETH...')

        holder_1 = accounts[0]
        holder_2 = accounts[1]

        steth_token.submit(ZERO_ADDRESS, {'from': holder_1, 'value': 3 * 10**18})
        assert steth_token.balanceOf(holder_1) > 0

        log.ok('holder_1 balance', steth_token.balanceOf(holder_1))
        assert_equals('holder_2 balance', steth_token.balanceOf(holder_2), 0)

        log.h('Submitting stETH...')

        terra_recipient_1 = '0x0000000000000000000000008badf00d8badf00d8badf00d8badf00d8badf00d'
        steth_token.approve(vault, 2 * 10**18, {'from': holder_1})
        tx = vault.submit(2 * 10**18, terra_recipient_1, b'', vault.version(), {'from': holder_1})
        # tx.info()

        assert 'Deposited' in tx.events
        assert tx.events['Deposited'][0].address == vault.address
        log.ok('Deposited event emitted')

        deposited_amount = tx.events['Deposited']['amount']
        assert deposited_amount >= 1.999 * 10**18 and deposited_amount <= 2 * 10**18
        log.ok('Deposited.amount', deposited_amount)

        assert_equals('holder_1 balance', beth_token.balanceOf(holder_1), 0)

        beth_supply = beth_token.totalSupply()
        assert beth_supply == beth_supply_before + deposited_amount
        assert_equals('bETH total supply', beth_supply, beth_supply_before + deposited_amount)

        bridge_balance = beth_token.balanceOf(c.wormhole_token_bridge_addr)
        assert bridge_balance == bridge_balance_before + deposited_amount
        assert_equals('bridge bETH balance', bridge_balance, bridge_balance_before + deposited_amount)

        assert 'LogMessagePublished' in tx.events
        assert tx.events['LogMessagePublished'][0].address == c.wormhole_addr
        log.ok('LogMessagePublished event emitted')

        expected_payload = wh.assemble_transfer_payload(
            token_address=beth_token.address,
            normalized_amount=wh.normalize_amount(deposited_amount, 18),
            to_address=terra_recipient_1,
            token_chain_id=wh.CHAIN_ID_ETHERUM,
            to_chain_id=wh.CHAIN_ID_TERRA,
            fee=0
        )

        assert tx.events['LogMessagePublished'][0]['payload'] == expected_payload
        log.ok('LogMessagePublished.payload', expected_payload)

        log.h('Submitting ETH...')

        bridge_balance_before = bridge_balance
        beth_supply_before = beth_supply

        terra_recipient_2 = '0x000000000000000000000000deadbeefdeadbeefdeadbeefdeadbeefdeadbeef'
        tx = vault.submit(1 * 10**18, terra_recipient_2, b'', vault.version(), {'from': holder_2, 'value': 1 * 10**18})
        # tx.info()

        assert 'Deposited' in tx.events
        assert tx.events['Deposited'][0].address == vault.address
        log.ok('Deposited event emitted')

        deposited_amount = tx.events['Deposited']['amount']
        assert deposited_amount >= 0.999 * 10**18 and deposited_amount <= 1 * 10**18
        log.ok('Deposited.amount', deposited_amount)

        assert_equals('holder_2 balance', beth_token.balanceOf(holder_2), 0)

        beth_supply = beth_token.totalSupply()
        assert beth_supply == beth_supply_before + deposited_amount
        assert_equals('bETH total supply', beth_supply, beth_supply_before + deposited_amount)

        bridge_balance = beth_token.balanceOf(c.wormhole_token_bridge_addr)
        assert bridge_balance == bridge_balance_before + deposited_amount
        assert_equals('bridge bETH balance', bridge_balance, bridge_balance_before + deposited_amount)

        assert 'LogMessagePublished' in tx.events
        assert tx.events['LogMessagePublished'][0].address == c.wormhole_addr
        log.ok('LogMessagePublished event emitted')

        expected_payload = wh.assemble_transfer_payload(
            token_address=beth_token.address,
            normalized_amount=wh.normalize_amount(deposited_amount, 18),
            to_address=terra_recipient_2,
            token_chain_id=wh.CHAIN_ID_ETHERUM,
            to_chain_id=wh.CHAIN_ID_TERRA,
            fee=0
        )

        assert tx.events['LogMessagePublished'][0]['payload'] == expected_payload
        log.ok('LogMessagePublished.payload', expected_payload)

        log.h('Rebasing stETH by 0.02%...')

        lido_oracle_report(steth_rebase_percent=0.02)
        assert_equals('AnchorVault.can_deposit_or_withdraw', vault.can_deposit_or_withdraw(), False)

        log.h('Selling rewards...')

        liquidations_admin = accounts.at(vault.liquidations_admin(), force=True)
        tx = vault.collect_rewards({'from': liquidations_admin})
        # tx.info()

        assert 'RewardsCollected' in tx.events
        assert tx.events['RewardsCollected'][0].address == vault.address
        log.ok('RewardsCollected event emitted')

        ust_amount = tx.events['RewardsCollected'][0]['ust_amount']
        assert ust_amount > 0
        log.ok('RewardsCollected.ust_amount', ust_amount)

        assert 'LogMessagePublished' in tx.events
        assert tx.events['LogMessagePublished'][0].address == c.wormhole_addr
        log.ok('LogMessagePublished event emitted')

        expected_payload = wh.assemble_transfer_payload(
            # See https://github.com/certusone/wormhole/blob/aff369f/ethereum/contracts/bridge/Bridge.sol#L97-L103
            # For wrapped tokens, the "token address" field is set to the address of the token on its native chain
            token_address=str(ust_token.nativeContract()),
            normalized_amount=wh.normalize_amount(ust_amount, ust_token.decimals()),
            to_address=terra_rewards_distributor_addr,
            token_chain_id=ust_token.chainId(),
            to_chain_id=wh.CHAIN_ID_TERRA,
            fee=0
        )

        assert tx.events['LogMessagePublished'][0]['payload'] == expected_payload
        log.ok('LogMessagePublished.payload', expected_payload)


def lido_oracle_report(steth_rebase_percent):
    lido = interface.Lido(c.steth_token_addr)
    dao_voting = accounts.at(c.lido_dao_voting_addr, force=True)
    lido_oracle = accounts.at(lido.getOracle(), force=True)
    lido.setFee(0, {'from': dao_voting})
    (deposited_validators, beacon_validators, beacon_balance) = lido.getBeaconStat()
    total_supply = lido.totalSupply()
    beacon_balance += int(total_supply * steth_rebase_percent / 100)
    assert beacon_balance > 0
    lido.pushBeacon(beacon_validators, beacon_balance, {'from': lido_oracle})
