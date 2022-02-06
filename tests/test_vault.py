import pytest
from brownie import Contract, ZERO_ADDRESS, chain, reverts, ETH_ADDRESS

ANCHOR_REWARDS_DISTRIBUTOR = '0x1234123412341234123412341234123412341234123412341234123412341234'
ZERO_BYTES32 = '0x0000000000000000000000000000000000000000000000000000000000000000'
TERRA_ADDRESS = '0xabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcdefabcd'
BETH_DECIMALS = 18

# no rewards liquidations for 24h since previous liquidation
NO_LIQUIDATION_INTERVAL = 60 * 60 * 24

# only admin can liquidate rewards for the first 2h after that
RESTRICTED_LIQUIDATION_INTERVAL = NO_LIQUIDATION_INTERVAL + 60 * 60 * 2

VAULT_VERSION = 3


def test_init_cannot_be_called_twice(beth_token, steth_token, deployer, admin, stranger, AnchorVault):
    vault = AnchorVault.deploy({'from': deployer})

    vault.initialize(beth_token, steth_token, admin, admin, {'from': stranger})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, admin, admin, {'from': stranger})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, admin, admin, {'from': deployer})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, admin, admin, {'from': admin})


def test_init_fails_on_zero_token_address(beth_token, steth_token, deployer, admin, AnchorVault):
    vault = AnchorVault.deploy({'from': deployer})

    with reverts('dev: invalid bETH address'):
        vault.initialize(ZERO_ADDRESS, steth_token, admin, admin, {'from': deployer})

    with reverts('dev: invalid stETH address'):
        vault.initialize(beth_token, ZERO_ADDRESS, admin, admin, {'from': deployer})


def test_init_fails_on_non_zero_beth_total_supply(
    beth_token,
    steth_token,
    admin,
    deployer,
    AnchorVault
):
    beth_token.set_minter(admin, {'from': admin})
    beth_token.mint(admin, 10**18, {'from': admin})

    vault = AnchorVault.deploy({'from': deployer})

    with reverts('dev: non-zero bETH total supply'):
        vault.initialize(beth_token, steth_token, admin, admin, {'from': deployer})


def test_initialized_vault_cannot_be_petrified(
    beth_token,
    steth_token,
    deployer,
    admin,
    stranger,
    AnchorVault
):
    vault = AnchorVault.deploy({'from': deployer})
    vault.initialize(beth_token, steth_token, admin, admin, {'from': stranger})

    with reverts('dev: already initialized'):
        vault.petrify_impl({'from': stranger})

    with reverts('dev: already initialized'):
        vault.petrify_impl({'from': deployer})

    with reverts('dev: already initialized'):
        vault.petrify_impl({'from': admin})


def test_petrified_vault_cannot_be_initialized(
    beth_token,
    steth_token,
    deployer,
    stranger,
    AnchorVault
):
    vault = AnchorVault.deploy({'from': deployer})
    vault.petrify_impl({'from': stranger})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, stranger, stranger, {'from': stranger})

    with reverts('dev: already initialized'):
        vault.initialize(beth_token, steth_token, deployer, deployer, {'from': deployer})


def deploy_and_initialize_vault(
    beth_token,
    steth_token,
    mock_bridge_connector,
    mock_rewards_liquidator,
    mock_insurance_connector,
    deployer,
    stranger,
    admin,
    emergency_admin,
    liquidations_admin,
    lido_dao_agent,
    AnchorVault,
    AnchorVaultProxy,
    helpers
):
    impl = AnchorVault.deploy({'from': deployer})
    impl.petrify_impl({'from': stranger})

    assert impl.admin() == ZERO_ADDRESS
    assert impl.beth_token() == ZERO_ADDRESS
    assert impl.steth_token() == ZERO_ADDRESS

    with reverts('dev: already initialized'):
        impl.initialize(beth_token, steth_token, stranger, stranger, {'from': stranger})

    with reverts('dev: already initialized'):
        impl.initialize(beth_token, steth_token, deployer, deployer, {'from': deployer})

    proxy = AnchorVaultProxy.deploy(impl, admin, {'from': deployer})
    vault = Contract.from_abi('AnchorVault', proxy.address, AnchorVault.abi)

    tx = vault.initialize(beth_token, steth_token, admin, emergency_admin, {'from': stranger})

    helpers.assert_single_event_named('AdminChanged', tx, source=vault, evt_keys_dict={
        'new_admin': admin
    })

    helpers.assert_single_event_named('EmergencyAdminChanged', tx, source=vault, evt_keys_dict={
        'new_emergency_admin': emergency_admin
    })

    helpers.assert_single_event_named('VersionIncremented', tx, source=vault, evt_keys_dict={
        'new_version': VAULT_VERSION
    })

    vault.configure(
        mock_bridge_connector,
        mock_rewards_liquidator,
        mock_insurance_connector,
        liquidations_admin,
        NO_LIQUIDATION_INTERVAL,
        RESTRICTED_LIQUIDATION_INTERVAL,
        ANCHOR_REWARDS_DISTRIBUTOR,
        {'from': admin}
    )

    beth_token.set_minter(vault, {'from': admin})

    return vault


def resume_vault(vault, lido_dao_agent):
    assert not vault.operations_allowed()
    vault.resume({'from': lido_dao_agent})
    assert vault.operations_allowed()
    return vault



@pytest.fixture(scope='module')
def vault(
    beth_token,
    steth_token,
    mock_bridge_connector,
    mock_rewards_liquidator,
    mock_insurance_connector,
    deployer,
    stranger,
    admin,
    emergency_admin,
    liquidations_admin,
    lido_dao_agent,
    AnchorVault,
    AnchorVaultProxy,
    helpers
):
    vault = deploy_and_initialize_vault(**locals())
    resume_vault(vault, lido_dao_agent)
    return vault


@pytest.fixture(scope='function')
def vault_no_proxy(
    beth_token,
    steth_token,
    mock_bridge_connector,
    mock_rewards_liquidator,
    mock_insurance_connector,
    deployer,
    admin,
    emergency_admin,
    liquidations_admin,
    lido_dao_agent,
    AnchorVault
):
    vault = AnchorVault.deploy({'from': deployer})

    vault.initialize(beth_token, steth_token, admin, emergency_admin, {'from': deployer})

    vault.configure(
        mock_bridge_connector,
        mock_rewards_liquidator,
        mock_insurance_connector,
        liquidations_admin,
        NO_LIQUIDATION_INTERVAL,
        RESTRICTED_LIQUIDATION_INTERVAL,
        ANCHOR_REWARDS_DISTRIBUTOR,
        {'from': admin}
    )

    beth_token.set_minter(vault, {'from': admin})
    resume_vault(vault, lido_dao_agent)

    return vault


def test_initial_config_correct(
    vault,
    admin,
    emergency_admin,
    beth_token,
    lido,
    mock_bridge_connector,
    mock_rewards_liquidator,
    mock_insurance_connector,
    liquidations_admin
):
    assert vault.admin() == admin
    assert vault.emergency_admin() == emergency_admin
    assert vault.version() == VAULT_VERSION
    assert vault.beth_token() == beth_token
    assert vault.bridge_connector() == mock_bridge_connector
    assert vault.rewards_liquidator() == mock_rewards_liquidator
    assert vault.insurance_connector() == mock_insurance_connector
    assert vault.liquidations_admin() == liquidations_admin
    assert vault.no_liquidation_interval() == NO_LIQUIDATION_INTERVAL
    assert vault.restricted_liquidation_interval() == RESTRICTED_LIQUIDATION_INTERVAL


def test_finalize_upgrade_v3_cannot_be_called_on_v3_vault(vault, admin):
    with reverts('unexpected contract version'):
        vault.finalize_upgrade_v3(admin, {'from': admin})


def test_version_can_be_bumped_by_admin(vault, admin, helpers):
    version = vault.version()
    tx = vault.bump_version({'from': admin})
    assert vault.version() == version + 1
    helpers.assert_single_event_named('VersionIncremented', tx, source=vault, evt_keys_dict={
        'new_version': version + 1
    })


# FIXME: use vault instead of vault_no_proxy after brownie learns to parse
# dev revert reasons from behind a proxy
def test_version_cannot_be_bumped_by_a_non_admin(
    vault_no_proxy,
    stranger,
    liquidations_admin,
    emergency_admin
):
    with reverts('dev: unauthorized'):
        vault_no_proxy.bump_version({'from': stranger})
    with reverts('dev: unauthorized'):
        vault_no_proxy.bump_version({'from': liquidations_admin})
    with reverts('dev: unauthorized'):
        vault_no_proxy.bump_version({'from': emergency_admin})


def test_finalize_upgrade_v3_cannot_be_called_on_v4_vault(vault, admin):
    vault.bump_version({'from': admin})
    assert vault.version() == 4
    with reverts('unexpected contract version'):
        vault.finalize_upgrade_v3(admin, {'from': admin})


@pytest.mark.parametrize('amount', [1 * 10**18, 1 * 10**18 + 10])
def test_deposit(
    vault,
    vault_user,
    steth_token,
    beth_token,
    mock_bridge_connector,
    helpers,
    steth_adjusted_ammount,
    amount
):
    steth_balance_before = steth_token.balanceOf(vault_user)
    terra_balance_before = mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)

    steth_token.approve(vault, amount, {'from': vault_user})
    tx = vault.submit(amount, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user})

    adjusted_amount = steth_adjusted_ammount(amount)

    helpers.assert_single_event_named('Deposited', tx, source=vault, evt_keys_dict={
        'sender': vault_user,
        'amount': adjusted_amount,
        'terra_address': TERRA_ADDRESS
    })

    helpers.assert_single_event_named('Test__Forwarded', tx, source=mock_bridge_connector, evt_keys_dict={
        'asset_name': 'bETH',
        'terra_address': TERRA_ADDRESS,
        'amount': adjusted_amount,
        'extra_data': '0xab'
    })

    assert beth_token.balanceOf(vault_user) == 0

    assert mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS) == terra_balance_before + adjusted_amount

    steth_balance_decrease = steth_balance_before - steth_token.balanceOf(vault_user)
    assert helpers.equal_with_precision(steth_balance_decrease, adjusted_amount, max_diff=1)


@pytest.mark.parametrize('amount', [1 * 10**18, 1 * 10**18 + 10])
def test_deposit_eth(
    vault,
    vault_user,
    steth_token,
    beth_token,
    mock_bridge_connector,
    helpers,
    steth_adjusted_ammount,
    amount
):
    steth_balance_before = steth_token.balanceOf(vault_user)
    terra_balance_before = mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)

    tx = vault.submit(amount, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user, 'value': amount})

    deposited_amount = tx.events['Deposited']['amount']
    assert deposited_amount <= amount

    helpers.assert_single_event_named('Deposited', tx, source=vault, evt_keys_dict={
        'sender': vault_user,
        'amount': deposited_amount,
        'terra_address': TERRA_ADDRESS
    })

    helpers.assert_single_event_named('Test__Forwarded', tx, source=mock_bridge_connector, evt_keys_dict={
        'asset_name': 'bETH',
        'terra_address': TERRA_ADDRESS,
        'amount': deposited_amount,
        'extra_data': '0xab'
    })

    assert beth_token.balanceOf(vault_user) == 0
    assert mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS) == terra_balance_before + deposited_amount

    steth_balance_increase = steth_token.balanceOf(vault_user) - steth_balance_before
    assert steth_balance_increase >= 0

    assert helpers.equal_with_precision(
        steth_balance_increase + deposited_amount,
        amount,
        max_diff=10
    )


# FIXME: use vault instead of vault_no_proxy after brownie learns to parse
# dev revert reasons from behind a proxy
def test_deposit_eth_fails_on_unexpected_amount(vault_no_proxy, vault_user):
    with reverts('dev: unexpected ETH amount sent'):
        vault_no_proxy.submit(10**18, TERRA_ADDRESS, '0xab', vault_no_proxy.version(), {'from': vault_user, 'value': 10**18 - 1})

    with reverts('dev: unexpected ETH amount sent'):
        vault_no_proxy.submit(10**18, TERRA_ADDRESS, '0xab', vault_no_proxy.version(), {'from': vault_user, 'value': 10**18 + 1})

    with reverts('dev: unexpected ETH amount sent'):
        vault_no_proxy.submit(0, TERRA_ADDRESS, '0xab', vault_no_proxy.version(), {'from': vault_user, 'value': 10**18})


def test_withdraw(
    vault, 
    vault_user, 
    steth_token, 
    beth_token, 
    helpers, 
    withdraw_from_terra, 
    mock_bridge_connector, 
    deposit_to_terra
):
    amount = 1 * 10**18

    steth_balance_before = steth_token.balanceOf(vault_user)

    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)

    terra_balance_before = mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS)

    withdraw_from_terra(TERRA_ADDRESS, vault_user, amount)

    assert beth_token.balanceOf(vault_user) == amount
    assert mock_bridge_connector.terra_beth_balance_of(TERRA_ADDRESS) == terra_balance_before - amount

    tx = vault.withdraw(amount, vault.version(), {'from': vault_user})

    assert helpers.equal_with_precision(steth_token.balanceOf(vault_user), steth_balance_before, 10)

    helpers.assert_single_event_named('Withdrawn', tx, source=vault, evt_keys_dict={
        'recipient': vault_user,
        'amount': amount
    })


def test_withdraw_fails_on_balance(vault, vault_user, steth_token, withdraw_from_terra, deposit_to_terra):
    amount = 1 * 10**18

    steth_balance_before = steth_token.balanceOf(vault_user)

    deposit_to_terra(TERRA_ADDRESS, vault_user, amount)

    withdraw_from_terra(TERRA_ADDRESS, vault_user, amount)

    with reverts():
        vault.withdraw(amount + 1, vault.version(), {'from': vault_user})


def test_change_admin(vault, stranger, admin, helpers):
    with reverts():
        vault.change_admin(stranger, {"from": stranger})

    tx = vault.change_admin(stranger, {"from": admin})

    helpers.assert_single_event_named('AdminChanged', tx, source=vault, evt_keys_dict={
        'new_admin': stranger
    })


def test_configuration(vault, stranger, admin, helpers):
    with reverts():
        vault.configure(
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            ZERO_ADDRESS,
            0,
            0,
            ZERO_BYTES32,
            {"from": stranger}
        )

    tx = vault.configure(
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        ZERO_ADDRESS,
        0,
        0,
        ZERO_BYTES32,
        {"from": admin}
    )

    helpers.assert_single_event_named('BridgeConnectorUpdated', tx, source=vault, evt_keys_dict={
        'bridge_connector': ZERO_ADDRESS
    })
    helpers.assert_single_event_named('RewardsLiquidatorUpdated', tx, source=vault, evt_keys_dict={
        'rewards_liquidator': ZERO_ADDRESS
    })
    helpers.assert_single_event_named('InsuranceConnectorUpdated', tx, source=vault, evt_keys_dict={
        'insurance_connector': ZERO_ADDRESS
    })
    helpers.assert_single_event_named('LiquidationConfigUpdated', tx, source=vault, evt_keys_dict={
        'liquidations_admin': ZERO_ADDRESS,
        'no_liquidation_interval': 0,
        'restricted_liquidation_interval': 0
    })
    helpers.assert_single_event_named('AnchorRewardsDistributorUpdated', tx, source=vault, evt_keys_dict={
        'anchor_rewards_distributor': ZERO_BYTES32
    })


def test_set_bridge_connector(vault, stranger, admin, helpers):
    with reverts():
        vault.set_bridge_connector(ETH_ADDRESS, {"from": stranger})

    tx = vault.set_bridge_connector(ETH_ADDRESS, {"from": admin})

    helpers.assert_single_event_named('BridgeConnectorUpdated', tx, source=vault, evt_keys_dict={
        'bridge_connector': ETH_ADDRESS
    })


def test_set_rewards_liquidator(vault, stranger, admin, helpers):
    with reverts():
        vault.set_rewards_liquidator(ETH_ADDRESS, {"from": stranger})

    tx = vault.set_rewards_liquidator(ETH_ADDRESS, {"from": admin})

    helpers.assert_single_event_named('RewardsLiquidatorUpdated', tx, source=vault, evt_keys_dict={
        'rewards_liquidator': ETH_ADDRESS
    })


def test_set_insurance_connector(vault, stranger, admin, helpers):
    with reverts():
        vault.set_insurance_connector(ETH_ADDRESS, {"from": stranger})

    tx = vault.set_insurance_connector(ETH_ADDRESS, {"from": admin})

    helpers.assert_single_event_named('InsuranceConnectorUpdated', tx, source=vault, evt_keys_dict={
        'insurance_connector': ETH_ADDRESS
    })


def test_set_liquidation_config(vault, stranger, admin, helpers):
    with reverts():
        vault.set_liquidation_config(ETH_ADDRESS, 100, 200, {"from": stranger})

    with reverts():
        vault.set_liquidation_config(ETH_ADDRESS, 100, 99, {"from": admin})

    tx = vault.set_liquidation_config(ETH_ADDRESS, 100, 200, {"from": admin})

    helpers.assert_single_event_named('LiquidationConfigUpdated', tx, source=vault, evt_keys_dict={
        'liquidations_admin': ETH_ADDRESS,
        'no_liquidation_interval': 100,
        'restricted_liquidation_interval': 200
    })


def test_rate_after_rebase(vault, steth_token, beth_token, vault_user, lido_oracle_report, helpers):
    assert steth_token.balanceOf(vault) == 0
    assert beth_token.totalSupply() == 0
    assert vault.get_rate() == 10**18

    steth_token.approve(vault, 10**18, {'from': vault_user})
    vault.submit(10**18, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user})

    steth_locked = steth_token.balanceOf(vault)

    assert steth_locked > 0
    assert beth_token.totalSupply() > 0
    assert helpers.equal_with_precision(vault.get_rate(), 10**18, max_diff=10)

    lido_oracle_report(steth_rebase_mult=1.01)

    assert steth_token.balanceOf(vault) > steth_locked
    assert helpers.equal_with_precision(vault.get_rate(), 10**18, max_diff=10)


def test_rate_after_direct_transfer(vault, steth_token, beth_token, vault_user, helpers):
    steth_token.approve(vault, 10**18, {'from': vault_user})
    vault.submit(10**18, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user})

    assert helpers.equal_with_precision(vault.get_rate(), 10**18, max_diff=10)

    steth_token.transfer(vault, 10**18, {"from": vault_user})

    assert helpers.equal_with_precision(vault.get_rate(), 10**18, max_diff=10)
