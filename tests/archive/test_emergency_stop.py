import pytest
from brownie import Contract, ZERO_ADDRESS, chain, reverts, ETH_ADDRESS

from utils.mainnet_fork import chain_snapshot
from test_vault import deploy_and_initialize_vault, resume_vault, TERRA_ADDRESS


@pytest.fixture(scope='module')
def actors(admin, deployer, stranger, lido_dao_agent, emergency_admin, liquidations_admin):
    return {
        'admin': admin,
        'deployer': deployer,
        'stranger': stranger,
        'lido_dao_agent': lido_dao_agent,
        'emergency_admin': emergency_admin,
        'liquidations_admin': liquidations_admin
    }


@pytest.fixture(
    scope='module',
    params=['admin', 'deployer', 'stranger', 'emergency_admin', 'liquidations_admin']
)
def non_governance_actor(actors, request):
    return actors[request.param]


@pytest.fixture(scope='module', params=['admin', 'emergency_admin'])
def emergency_admin_role(actors, request):
    return actors[request.param]


@pytest.fixture(scope='module', params=['deployer', 'stranger', 'lido_dao_agent', 'liquidations_admin'])
def non_emergency_admin_role(actors, request):
    return actors[request.param]


@pytest.fixture(scope='module')
def new_emergency_admin(accounts, deployer):
    emergency_admin = accounts.add()
    deployer.transfer(emergency_admin, 10 * 10**18)
    return emergency_admin


def test_vault_is_initialized_in_a_stopped_state(
    AnchorVault,
    admin,
    beth_token,
    steth_token,
    mock_bridge_connector,
    mock_rewards_liquidator,
    mock_insurance_connector,
):
    # deploying from admin instead of deployer to work around a brownie bug
    # leading to the brownie.exceptions.ContractNotFound
    new_vault = AnchorVault.deploy({'from': admin})
    assert not new_vault.operations_allowed()
    assert not new_vault.can_deposit_or_withdraw()

    new_vault.initialize(beth_token, steth_token, admin, admin, {'from': admin})
    assert not new_vault.operations_allowed()
    assert not new_vault.can_deposit_or_withdraw()

    new_vault.configure(
        mock_bridge_connector,
        mock_rewards_liquidator,
        mock_insurance_connector,
        admin,
        0,
        60 * 60 * 26,
        '0x1234123412341234123412341234123412341234123412341234123412341234',
        {'from': admin}
    )

    assert not new_vault.operations_allowed()
    assert not new_vault.can_deposit_or_withdraw()


@pytest.fixture(scope='module')
def initialized_vault_proxy(
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
    return deploy_and_initialize_vault(**locals())


def test_dao_gov_can_set_emergency_admin(
    initialized_vault_proxy,
    lido_dao_agent,
    new_emergency_admin,
    helpers
):
    tx = initialized_vault_proxy.set_emergency_admin(new_emergency_admin, {'from': lido_dao_agent})

    assert initialized_vault_proxy.emergency_admin() == new_emergency_admin

    helpers.assert_single_event_named('EmergencyAdminChanged', tx,
        source=initialized_vault_proxy,
        evt_keys_dict={'new_emergency_admin': new_emergency_admin}
    )


def test_non_gov_cannot_set_emergency_admin(
    initialized_vault_proxy,
    non_governance_actor,
    new_emergency_admin
):
    with reverts():
        initialized_vault_proxy.set_emergency_admin(new_emergency_admin, {'from': non_governance_actor})


def test_dao_gov_can_resume_deployed_contract(initialized_vault_proxy, lido_dao_agent, helpers):
    tx = initialized_vault_proxy.resume({'from': lido_dao_agent})
    assert initialized_vault_proxy.operations_allowed()
    assert initialized_vault_proxy.can_deposit_or_withdraw()
    helpers.assert_single_event_named('OperationsResumed', tx, source=initialized_vault_proxy)


def test_non_gov_cannot_resume_deployed_contract(initialized_vault_proxy, non_governance_actor):
    with reverts():
        initialized_vault_proxy.resume({'from': non_governance_actor})


@pytest.fixture(scope='function')
def vault(initialized_vault_proxy, lido_dao_agent):
    initialized_vault_proxy.resume({'from': lido_dao_agent})
    return initialized_vault_proxy


def test_emergency_admin_role_can_stop_running_contract(vault, emergency_admin_role, helpers):
    tx = vault.emergency_stop({'from': emergency_admin_role})
    assert not vault.operations_allowed()
    assert not vault.can_deposit_or_withdraw()
    helpers.assert_single_event_named('OperationsStopped', tx, source=vault)


def test_non_emergency_admin_role_cannot_stop_running_contract(vault, non_emergency_admin_role):
    with reverts():
        vault.emergency_stop({'from': non_emergency_admin_role})


def test_dao_gov_can_resume_stopped_contract(vault, emergency_admin, lido_dao_agent, helpers):
    vault.emergency_stop({'from': emergency_admin})
    assert not vault.operations_allowed()
    assert not vault.can_deposit_or_withdraw()

    tx = vault.resume({'from': lido_dao_agent})
    assert vault.operations_allowed()
    assert vault.can_deposit_or_withdraw()
    helpers.assert_single_event_named('OperationsResumed', tx, source=vault)


def test_new_emergency_admin_can_stop_running_contract(
    vault,
    new_emergency_admin,
    lido_dao_agent,
    helpers
):
    vault.set_emergency_admin(new_emergency_admin, {'from': lido_dao_agent})
    tx = vault.emergency_stop({'from': new_emergency_admin})
    assert not vault.operations_allowed()
    assert not vault.can_deposit_or_withdraw()
    helpers.assert_single_event_named('OperationsStopped', tx, source=vault)


def test_stopped_contract_allows_no_deposits(vault, vault_user, emergency_admin, steth_token):
    vault.emergency_stop({'from': emergency_admin})

    amount = 10**18
    steth_token.approve(vault, amount, {'from': vault_user})

    assert not vault.can_deposit_or_withdraw()

    with reverts('contract stopped'):
        vault.submit(amount, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user})

    with reverts('contract stopped'):
        vault.submit(amount, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user, 'value': amount})


def test_stopped_contract_allows_no_withdrawals(
    vault,
    vault_user,
    emergency_admin,
    withdraw_from_terra
):
    tx = vault.submit(10**18, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user, 'value': 10**18})
    beth_amount = tx.events['Deposited']['beth_amount_received']

    vault.emergency_stop({'from': emergency_admin})
    assert not vault.can_deposit_or_withdraw()

    withdraw_from_terra(TERRA_ADDRESS, vault_user, beth_amount)

    with reverts('contract stopped'):
        vault.withdraw(beth_amount, vault.version(), {'from': vault_user})


def test_stopped_contract_allows_no_rewards_collection(
    vault,
    vault_user,
    emergency_admin,
    liquidations_admin,
    lido_oracle_report
):
    vault.submit(10**18, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user, 'value': 10**18})
    vault.emergency_stop({'from': emergency_admin})

    lido_oracle_report(steth_rebase_mult=1.01)

    with reverts('contract stopped'):
        vault.collect_rewards({'from': liquidations_admin})



def test_unhappy_path(
    initialized_vault_proxy,
    vault_user,
    steth_token,
    lido_dao_agent,
    emergency_admin,
    liquidations_admin,
    lido_oracle_report,
    withdraw_from_terra,
    helpers
):
    vault = initialized_vault_proxy
    assert not vault.operations_allowed()
    assert not vault.can_deposit_or_withdraw()

    def assert_operations_revert():
        steth_token.approve(vault, 10**18, {'from': vault_user})

        with reverts('contract stopped'):
            vault.submit(10**18, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user})

        with reverts('contract stopped'):
            vault.submit(10**18, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user, 'value': 10**18})

        with chain_snapshot():
            lido_oracle_report(steth_rebase_mult=1.01)
            with reverts('contract stopped'):
                vault.collect_rewards({'from': liquidations_admin})

    assert_operations_revert()

    vault.resume({'from': lido_dao_agent})
    assert vault.operations_allowed()
    assert vault.can_deposit_or_withdraw()

    tx = vault.submit(10**18, TERRA_ADDRESS, '0xab', vault.version(), {'from': vault_user, 'value': 10**18})
    beth_amount = tx.events['Deposited']['beth_amount_received']

    vault.emergency_stop({'from': emergency_admin})
    assert not vault.operations_allowed()
    assert not vault.can_deposit_or_withdraw()

    withdraw_from_terra(TERRA_ADDRESS, vault_user, beth_amount)
    assert_operations_revert()

    vault.resume({'from': lido_dao_agent})
    assert vault.operations_allowed()
    assert vault.can_deposit_or_withdraw()

    lido_oracle_report(steth_rebase_mult=1.01)
    tx = vault.collect_rewards({'from': liquidations_admin})
    helpers.assert_single_event_named('RewardsCollected', tx, source=vault)
    assert vault.can_deposit_or_withdraw()

    tx = vault.withdraw(beth_amount, vault.version(), {'from': vault_user})
    evt = helpers.assert_single_event_named('Withdrawn', tx, source=vault)
    assert evt['amount'] == beth_amount
