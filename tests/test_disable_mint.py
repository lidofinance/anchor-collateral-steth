from re import A
import pytest
from brownie import accounts, interface, Contract, AnchorVault, AnchorVaultProxy, BridgeConnectorWormhole, reverts

from utils.config import (
    wormhole_token_bridge_addr,
    vault_proxy_addr,
    lido_dao_agent_address,
    vault_liquidations_admin_addr,
    bridge_connector_addr,
    rewards_liquidator_addr,
    insurance_connector_addr,
    vault_impl_addr
)

TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'


def test_disable_mint(stranger, steth_token, lido_oracle_report, deploy_vault_and_pass_dao_vote): 
    vault_proxy = Contract.from_abi('AnchorVaultProxy', vault_proxy_addr, AnchorVaultProxy.abi)
    vault = Contract.from_abi('AnchorVault', vault_proxy_addr, AnchorVault.abi)

    stranger_deposit_amount = 10 * 10 ** 18

    beth_token = interface.ERC20(vault.beth_token())
    liquidations_admin = accounts.at(vault.liquidations_admin(), force=True)

    #try to submit deposit
    prev_beth_total_supply = beth_token.totalSupply()
    vault.submit(
        stranger_deposit_amount,
        TERRA_ADDRESS,
        '0x8bada2e',
        vault.version(),
        {'from': stranger, 'value': stranger_deposit_amount}
    )

    stranger_beth_amount = beth_token.totalSupply() - prev_beth_total_supply
    assert stranger_beth_amount > 0

    #check version before update
    assert vault_proxy.implementation() == vault_impl_addr
    assert vault.version() == 3, "invalid version"

    #simulate rebase
    liquidations_admin = accounts.at(vault.liquidations_admin(), force=True)
    lido_oracle_report(steth_rebase_mult=1.01)
    vault.collect_rewards({'from': liquidations_admin})
    assert vault.can_deposit_or_withdraw()

    #
    # Upgrade contract with disabled deposits
    #
    v = deploy_vault_and_pass_dao_vote()

    #check configuration
    assert vault_impl_addr != v.address, "old and new impl are equal"
    assert vault_proxy.implementation() == v.address, "proxy impl not updated"
    assert vault.version() == 4, "invalid version"
    assert vault.admin() == lido_dao_agent_address
    assert vault.beth_token() == beth_token
    assert vault.steth_token() == steth_token
    assert vault.bridge_connector() == bridge_connector_addr
    assert vault.rewards_liquidator() == rewards_liquidator_addr
    assert vault.insurance_connector() == insurance_connector_addr
    assert vault.liquidations_admin() == vault_liquidations_admin_addr

    prev_beth_total_supply = beth_token.totalSupply()
    prev_steth_total_supply = steth_token.totalSupply()

    with reverts("Minting is closed. Context: https://research.lido.fi/t/sunsetting-lido-on-terra/2367"): 
        vault.submit(
            stranger_deposit_amount,
            TERRA_ADDRESS,
            '0x8bada2e',
            vault.version(),
            {'from': stranger, 'value': stranger_deposit_amount}
        )

    stranger_beth_amount_after = beth_token.totalSupply() - prev_beth_total_supply
    steth_amount_after = prev_steth_total_supply - steth_token.totalSupply()

    #check that no new beth were minted
    assert stranger_beth_amount_after == 0
    assert steth_amount_after == 0

    beth_balance_before = beth_token.balanceOf(stranger)
    assert beth_balance_before == 0

    # simulate bridging from Terra
    token_bridge = accounts.at(wormhole_token_bridge_addr, force=True)
    beth_token.transfer(stranger, stranger_beth_amount, {'from': token_bridge})

    beth_balance_after = beth_token.balanceOf(stranger)
    assert beth_balance_after == stranger_beth_amount

    # check that withdrawals are working
    # withdraw from stranger
    vault.withdraw(stranger_beth_amount, vault.version(), {'from': stranger})

    beth_balance_after_withdrawals = beth_token.balanceOf(stranger)
    assert beth_balance_after_withdrawals == 0


def test_negative_rebase(stranger, steth_token, deploy_vault_and_pass_dao_vote, lido_oracle_report, helpers):
    vault = Contract.from_abi('AnchorVault', vault_proxy_addr, AnchorVault.abi)
    beth_token = interface.ERC20(vault.beth_token())

    stranger_deposit_amount = 10 * 10 ** 18
    
    #try to submit deposit
    prev_beth_total_supply = beth_token.totalSupply()
    vault.submit(
        stranger_deposit_amount,
        TERRA_ADDRESS,
        '0x8bada2e',
        vault.version(),
        {'from': stranger, 'value': stranger_deposit_amount}
    )

    stranger_beth_amount = beth_token.totalSupply() - prev_beth_total_supply
    assert stranger_beth_amount > 0

    withdrawal_rate = steth_token.balanceOf(vault) * 10**18 / (beth_token.totalSupply() - vault.total_beth_refunded())

    assert vault.version() == 3
    assert vault.get_rate() == withdrawal_rate

    #deploy
    deploy_vault_and_pass_dao_vote()

    assert vault.version() == 4

    beth_balance_before = beth_token.balanceOf(stranger)
    assert beth_balance_before == 0

    # simulate bridging from Terra
    token_bridge = accounts.at(wormhole_token_bridge_addr, force=True)
    beth_token.transfer(stranger, stranger_beth_amount, {'from': token_bridge})

    beth_balance_after = beth_token.balanceOf(stranger)
    assert beth_balance_after == stranger_beth_amount

    #simulate negative rebase
    liquidations_admin = accounts.at(vault.liquidations_admin(), force=True)
    lido_oracle_report(steth_rebase_mult=0.9)
    vault.collect_rewards({'from': liquidations_admin})
    assert vault.can_deposit_or_withdraw()

    withdrawal_rate = steth_token.balanceOf(vault) * 10**18 / (beth_token.totalSupply() - vault.total_beth_refunded())

    #withdrawal rate decreased
    assert withdrawal_rate < 10**18

    #check steth balance
    vault.withdraw(stranger_beth_amount, vault.version(), {'from': stranger})

    #if there some penalty
    stranger_steth_after = steth_token.balanceOf(stranger)
    assert stranger_steth_after < stranger_deposit_amount

    #check
    beth_balance_after_withdrawals = beth_token.balanceOf(stranger)
    assert beth_balance_after_withdrawals == 0
    
