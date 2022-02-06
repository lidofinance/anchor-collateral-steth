import pytest
from collections import namedtuple
from brownie import accounts, interface, Contract, AnchorVault, BridgeConnectorWormhole, chain

from utils.mainnet_fork import chain_snapshot
from utils.config import beth_token_addr, wormhole_token_bridge_addr


MAINNET_VAULT = '0xA2F987A546D4CD1c607Ee8141276876C26b72Bdf'
REFUND_BETH_AMOUNT = 4449999990000000000 + 439111118580000000000
TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'


def as_vault_v2(addr):
    return Contract.from_abi('AnchorVault_v2', addr, interface.AnchorVault_v2.abi)


def as_vault_v3(addr):
    return Contract.from_abi('AnchorVault', addr, AnchorVault.abi)


@pytest.fixture(scope='module')
def vault_proxy(AnchorVaultProxy):
    proxy = AnchorVaultProxy.at(MAINNET_VAULT)
    vault = as_vault_v2(proxy)
    assert vault.version() == 2
    assert vault.admin() == proxy.proxy_getAdmin()
    return proxy


@pytest.fixture(scope='module')
def beth_token(bEth):
    return bEth.at(beth_token_addr)


def upgrade_vault_to_v3(vault_proxy, impl_deployer, emergency_admin):
    proxy_admin = accounts.at(vault_proxy.proxy_getAdmin(), force=True)

    new_impl = AnchorVault.deploy({'from': impl_deployer})
    new_impl.petrify_impl({'from': impl_deployer})

    setup_calldata = new_impl.finalize_upgrade_v3.encode_input(emergency_admin)
    return vault_proxy.proxy_upgradeTo(new_impl, setup_calldata, {'from': proxy_admin})


def record_vault_state(vault, steth_token):
    state = {}

    state['admin'] = vault.admin()
    state['beth_token'] = vault.beth_token()
    state['steth_token'] = vault.steth_token()
    state['bridge_connector'] = vault.bridge_connector()
    state['rewards_liquidator'] = vault.rewards_liquidator()
    state['insurance_connector'] = vault.insurance_connector()
    state['anchor_rewards_distributor'] = vault.anchor_rewards_distributor()

    state['liquidations_admin'] = vault.liquidations_admin()
    state['no_liquidation_interval'] = vault.no_liquidation_interval()
    state['restricted_liquidation_interval'] = vault.restricted_liquidation_interval()

    state['last_liquidation_time'] = vault.last_liquidation_time()
    state['last_liquidation_share_price'] = vault.last_liquidation_share_price()
    state['last_liquidation_shares_burnt'] = vault.last_liquidation_shares_burnt()

    state['version'] = vault.version()

    state['get_rate'] = vault.get_rate()
    state['can_deposit_or_withdraw'] = vault.can_deposit_or_withdraw()

    state['steth_balance'] = steth_token.balanceOf(vault.address)

    return state


def record_vault_state_at(vault, steth, beth, wormhole_token_bridge, stranger, another_stranger, state_history, time_step):
    state_history[time_step + '_stranger_steth_balance'] = steth.balanceOf(stranger)
    state_history[time_step + '_stranger_beth_balance'] = beth.balanceOf(stranger)

    state_history[time_step + '_another_stranger_steth_balance'] = steth.balanceOf(another_stranger)
    state_history[time_step + '_another_stranger_beth_balance'] = beth.balanceOf(another_stranger)

    state_history[time_step + '_wormhole_token_bridge_balance'] = beth.balanceOf(wormhole_token_bridge)


def record_vault_state_history(vault, steth_token, beth_token, wormhole_token_bridge, stranger, another_stranger, liquidations_admin, lido_oracle_report):
    state_history = {}

    stranger_deposit_amount = 10 * 10 ** 18
    another_stranger_deposit_amount = 0.42 * 10**18

    record_vault_state_at(
        vault,
        steth_token,
        beth_token,
        wormhole_token_bridge,
        stranger,
        another_stranger,
        state_history,
        '0'
    )

    prev_beth_total_supply = beth_token.totalSupply()
    vault.submit(
        stranger_deposit_amount,
        TERRA_ADDRESS,
        '0x8bada2e',
        vault.version(),
        {'from': stranger, 'value': stranger_deposit_amount}
    )
    stranger_beth_amount = beth_token.totalSupply() - prev_beth_total_supply
    
    record_vault_state_at(
        vault,
        steth_token,
        beth_token,
        wormhole_token_bridge,
        stranger,
        another_stranger,
        state_history,
        '1'
    )

    lido_oracle_report(steth_rebase_mult=1.01)
    vault.collect_rewards({'from': liquidations_admin})
    assert vault.can_deposit_or_withdraw()

    record_vault_state_at(
        vault,
        steth_token,
        beth_token,
        wormhole_token_bridge,
        stranger,
        another_stranger,
        state_history,
        '2'
    )

    prev_beth_total_supply = beth_token.totalSupply()
    vault.submit(
        another_stranger_deposit_amount,
        TERRA_ADDRESS,
        '0x8bada2e',
        vault.version(),
        {'from': another_stranger, 'value': another_stranger_deposit_amount}
    )
    another_stranger_beth_amount = beth_token.totalSupply() - prev_beth_total_supply

    record_vault_state_at(
        vault,
        steth_token,
        beth_token,
        wormhole_token_bridge,
        stranger,
        another_stranger,
        state_history,
        '3'
    )

    lido_oracle_report(steth_rebase_mult=0.98)
    vault.collect_rewards({'from': liquidations_admin})
    assert vault.can_deposit_or_withdraw()

    record_vault_state_at(
        vault,
        steth_token,
        beth_token,
        wormhole_token_bridge,
        stranger,
        another_stranger,
        state_history,
        '4'
    )

    # simulate bridging from Terra
    token_bridge = accounts.at(wormhole_token_bridge_addr, force=True)
    beth_token.transfer(stranger, stranger_beth_amount, {'from': token_bridge})
    beth_token.transfer(another_stranger, another_stranger_beth_amount, {'from': token_bridge})
    
    # withdraw from stranger
    vault.withdraw(stranger_beth_amount, vault.version(), {'from': stranger})

    record_vault_state_at(
        vault,
        steth_token,
        beth_token,
        wormhole_token_bridge,
        stranger,
        another_stranger,
        state_history,
        '5'
    )

    # withdraw from another_stranger
    vault.withdraw(another_stranger_beth_amount, vault.version(), {'from': another_stranger})

    record_vault_state_at(
        vault,
        steth_token,
        beth_token,
        wormhole_token_bridge,
        stranger,
        another_stranger,
        state_history,
        '6'
    )

    return state_history


ValueChanged = namedtuple('ValueChanged', ['from_val', 'to_val'])


def dictdiff(from_dict, to_dict):
  result = {}
  
  all_keys = from_dict.keys() | to_dict.keys()
  for key in all_keys:
    if from_dict.get(key) != to_dict.get(key):
      result[key] = ValueChanged(from_dict.get(key), to_dict.get(key))
  
  return result


def test_upgrade_affects_only_expected_contract_fields(
    vault_proxy,
    steth_token,
    emergency_admin,
    stranger,
    helpers
):
    state_before = record_vault_state(as_vault_v2(vault_proxy), steth_token)
    upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    
    vault_v3 = as_vault_v3(vault_proxy)
    state_after = record_vault_state(vault_v3, steth_token)
    
    state_diff = dictdiff(state_before, state_after)

    # check the number of elements in the diff 
    assert len(state_diff) == 2

    # state differ because of withdrawal rate rounding errors, but not greater than 100000 wei
    assert helpers.equal_with_precision(
        state_after['steth_balance'],
        state_before['steth_balance'] - REFUND_BETH_AMOUNT,
        1000
    )

    assert state_diff['version'] == ValueChanged(2, 3)

    # check that added field equals REFUND_BETH_AMOUNT after v3 upgrade
    assert vault_v3.total_beth_refunded() == REFUND_BETH_AMOUNT


def test_rebases(
    vault_proxy,
    steth_token,
    stranger,
    another_stranger,
    emergency_admin,
    lido_oracle_report,
    interface,
    helpers
):
    vault = as_vault_v3(vault_proxy)
    beth_token = interface.ERC20(vault.beth_token())
    wormhole_token_bridge = Contract.from_abi(
        'BridgeConnectorWormhole',
        vault.bridge_connector(),
        BridgeConnectorWormhole.abi
    ).wormhole_token_bridge()
    liquidations_admin = accounts.at(vault.liquidations_admin(), force=True)

    assert vault.version() == 2 

    state_history_before = {}
    state_history_after = {}
    with chain_snapshot():
        state_history_before = record_vault_state_history(
            vault,
            steth_token,
            beth_token,
            wormhole_token_bridge,
            stranger,
            another_stranger,
            liquidations_admin,
            lido_oracle_report
        )

    upgrade_vault_to_v3(vault_proxy, impl_deployer=stranger, emergency_admin=emergency_admin)
    
    with chain_snapshot():
        state_history_after = record_vault_state_history(
            vault,
            steth_token,
            beth_token,
            wormhole_token_bridge,
            stranger,
            another_stranger,
            liquidations_admin,
            lido_oracle_report
        )

    # no diff in v2 and v3 versions in vaults math
    assert dictdiff(state_history_before, state_history_after) == {}
