import pytest
from brownie import accounts, interface, Contract, AnchorVault, BridgeConnectorWormhole, reverts

from utils.config import wormhole_token_bridge_addr

MAINNET_VAULT = '0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf'
TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'

def as_vault_v3(addr):
    return Contract.from_abi('AnchorVault', addr, AnchorVault.abi)

@pytest.fixture(scope='module')
def vault_proxy(AnchorVaultProxy):
    proxy = AnchorVaultProxy.at(MAINNET_VAULT)
    vault = as_vault_v3(proxy)
    assert vault.version() == 2
    assert vault.admin() == proxy.proxy_getAdmin()
    return proxy


def upgrade_vault_to_v4(vault_proxy, impl_deployer, emergency_admin):
    proxy_admin = accounts.at(vault_proxy.proxy_getAdmin(), force=True)

    new_impl = AnchorVault.deploy({'from': impl_deployer})
    new_impl.petrify_impl({'from': impl_deployer})

    setup_calldata = new_impl.finalize_upgrade_v3.encode_input(emergency_admin)
    return vault_proxy.proxy_upgradeTo(new_impl, setup_calldata, {'from': proxy_admin})


def test_disable_mint(vault_proxy, stranger, steth_token, lido_oracle_report, emergency_admin): 
    state_history = {}

    stranger_deposit_amount = 10 * 10 ** 18

    vault = as_vault_v3(vault_proxy)
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


    #simulate rebase
    liquidations_admin = accounts.at(vault.liquidations_admin(), force=True)
    lido_oracle_report(steth_rebase_mult=1.01)
    vault.collect_rewards({'from': liquidations_admin})
    assert vault.can_deposit_or_withdraw()

    #
    # Upgrade contract with disabled deposits
    #
    upgrade_vault_to_v4(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    vault_v4 = as_vault_v3(vault_proxy)

    prev_beth_total_supply = beth_token.totalSupply()
    prev_steth_total_supply = steth_token.totalSupply()

    with reverts("Minting is closed. Context: https://research.lido.fi/t/sunsetting-lido-on-terra/2367"): 
        vault_v4.submit(
            stranger_deposit_amount,
            TERRA_ADDRESS,
            '0x8bada2e',
            vault_v4.version(),
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
    vault_v4.withdraw(stranger_beth_amount, vault.version(), {'from': stranger})

    beth_balance_after_withdrawals = beth_token.balanceOf(stranger)
    assert beth_balance_after_withdrawals == 0



    