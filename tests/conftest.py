import pytest
from brownie import ZERO_ADDRESS, chain, interface

from scripts.deploy import deploy

from utils.config import (
    ldo_vote_executors_for_tests,
    lido_dao_voting_addr,
    lido_accounting_oracle,
    lido_accounting_oracle_hash_consensus,
    lido_dao_token_manager_address
)

from utils.dao import (
    create_vote,
    encode_proxy_upgrade,
    encode_finalize_upgrade_v4,
    encode_call_script
)

BETH_DECIMALS = 18
UST_TOKEN = "0xa693B19d2931d498c5B318dF961919BB4aee87a5"
STETH_TOKEN = "0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84"
USDC_TOKEN = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
CHAINLINK_STETH_ETH_FEED = "0x86392dC19c0b719886221c78AB11eb8Cf5c52812"
CHAINLINK_UST_ETH_FEED = "0xa20623070413d42a5C01Db2c8111640DD7A5A03a"
CHAINLINK_USDC_ETH_FEED = "0x986b5E1e1755e3C2440e960477f25201B0a8bbD4"

@pytest.fixture(scope='function', autouse=True)
def shared_setup(fn_isolation):
    pass


@pytest.fixture(scope='module')
def deployer(accounts):
    return accounts[0]


@pytest.fixture(scope='module')
def admin(accounts):
    return accounts[1]


@pytest.fixture(scope='module')
def emergency_admin(accounts, deployer):
    emergency_admin = accounts.add()
    deployer.transfer(emergency_admin, 10 * 10**18)
    return emergency_admin


@pytest.fixture(scope='module')
def liquidations_admin(accounts):
    return accounts[2]


@pytest.fixture(scope='module')
def vault_user(accounts, lido):
    user = accounts[3]
    lido.submit(ZERO_ADDRESS, {'from': user, 'value': 99 * 10**18})
    assert lido.balanceOf(user) > 98 * 10**18
    return user


@pytest.fixture(scope='module')
def another_vault_user(accounts, lido):
    user = accounts[4]
    lido.submit(ZERO_ADDRESS, {'from': user, 'value': 99 * 10**18})
    assert lido.balanceOf(user) > 98 * 10**18
    return user


@pytest.fixture(scope='module')
def stranger(accounts):
    return accounts[9]


@pytest.fixture(scope='module')
def another_stranger(accounts, deployer):
    acct = accounts.add()
    deployer.transfer(acct, 10**18)
    return acct


@pytest.fixture(scope='module')
def steth_token(interface):
    return interface.ERC20(STETH_TOKEN)

@pytest.fixture(scope='module')
def lido(interface, steth_token):
    return interface.Lido(steth_token.address)


@pytest.fixture(scope='module')
def lido_dao_agent(accounts):
    return accounts.at('0x3e40D73EB977Dc6a537aF587D48316feE66E9C8c', force=True)

@pytest.fixture(scope='module')
def beth_token(deployer, admin, bEth):
    return bEth.deploy("bETH", ZERO_ADDRESS, admin, {'from': deployer})

@pytest.fixture(scope='module')
def hash_consensus_for_accounting_oracle(interface):
    return interface.HashConsensus(lido_accounting_oracle_hash_consensus)

@pytest.fixture(scope='module')
def mock_bridge(accounts):
    return accounts.add()

@pytest.fixture(scope='module')
def mock_bridge_connector(beth_token, deployer, mock_bridge, MockBridgeConnector, interface, accounts):
    mock_bridge_connector =  MockBridgeConnector.deploy(beth_token, mock_bridge, {'from': deployer})

    ust_token = interface.UST(UST_TOKEN)
    ust_owner = accounts.at(ust_token.owner(), force=True)
    ust_amount = 10_000_000 * 10**18

    ust_token.mint(mock_bridge_connector, ust_amount, {'from': ust_owner})
    assert ust_token.balanceOf(mock_bridge_connector) == ust_amount

    return mock_bridge_connector

@pytest.fixture(scope='module')
def withdraw_from_terra(mock_bridge_connector, mock_bridge, beth_token):
  def withdraw(terra_address, to_address, amount):
    terra_balance_before = mock_bridge_connector.terra_beth_balance_of(terra_address)
    beth_token.approve(mock_bridge_connector, amount, {"from": mock_bridge})
    mock_bridge_connector.mock_beth_withdraw(terra_address, to_address, amount, {"from": mock_bridge})
    assert mock_bridge_connector.terra_beth_balance_of(terra_address) == terra_balance_before - amount
  return withdraw

ONE_DAY = 1 * 24 * 60 * 60

"""
The mechanism of oracles in Lido V2 has changed. Now AccountingOracle has push data changes on each report.

We use a simple version of `simulate_report` from here:
https://github.com/lidofinance/scripts/blob/master/utils/test/oracle_report_helpers.py#L239
"""
@pytest.fixture(scope='module')
def lido_oracle_report(interface, accounts, steth_token, hash_consensus_for_accounting_oracle):
    lido = interface.Lido(steth_token.address)
    accounting_oracle = accounts.at(lido_accounting_oracle, force=True)

    (refSlot, _) = hash_consensus_for_accounting_oracle.getCurrentFrame()
    (_, SECONDS_PER_SLOT, GENESIS_TIME) = hash_consensus_for_accounting_oracle.getChainConfig()
    reportTime = GENESIS_TIME + refSlot * SECONDS_PER_SLOT

    (_, beaconValidators, beaconBalance) = lido.getBeaconStat()

    withdrawalVaultBalance = 0
    elRewardsVaultBalance = 0

    def report_beacon_state(cl_diff):
        postCLBalance = beaconBalance + cl_diff
        postBeaconValidators = beaconValidators

        assert beaconBalance > 0

        return lido.handleOracleReport(
            reportTime,
            ONE_DAY,
            postBeaconValidators,
            postCLBalance,
            withdrawalVaultBalance,
            elRewardsVaultBalance,
            0,
            [],
            0,
            {"from": accounting_oracle.address}
        )
    return report_beacon_state

@pytest.fixture(scope='module')
def ldo_holder(accounts):
    return accounts.at('0xAD4f7415407B83a081A0Bee22D05A8FDC18B42da', force=True)

@pytest.fixture(scope='module')
def dao_voting(interface):
    return interface.Voting(lido_dao_voting_addr)

class Helpers:
    accounts = None
    dao_voting = None

    @staticmethod
    def filter_events_from(addr, events):
        return list(filter(lambda evt: evt.address == addr, events))

    @staticmethod
    def assert_single_event_named(evt_name, tx, evt_keys_dict = None, source = None):
        receiver_events = tx.events[evt_name]
        if source is not None:
            receiver_events = Helpers.filter_events_from(source, receiver_events)
        print (receiver_events)
        assert len(receiver_events) == 1
        if evt_keys_dict is not None:
            assert dict(receiver_events[0]) == evt_keys_dict
        return receiver_events[0]

    @staticmethod
    def assert_no_events_named(evt_name, tx):
        assert evt_name not in tx.events

    @staticmethod
    def equal_with_precision(actual, expected, max_diff = None, max_diff_percent = None):
        if max_diff is None:
            max_diff = (max_diff_percent / 100) * expected
        return abs(actual - expected) <= max_diff

    @staticmethod
    def get_price(feed, inverse = False):
        decimals = feed.decimals()
        answer = feed.latestAnswer()
        if inverse:
            return  (10 ** decimals) / answer
        return answer / (10 ** decimals)

    @staticmethod
    def get_cross_price(priceA, priceB):
        return (priceA * priceB)

    @staticmethod
    def pass_and_exec_dao_vote(vote_id):
        print(f'executing vote {vote_id}')

        # together these accounts hold 15% of LDO total supply
        # ldo_vote_executors_for_tests

        helper_acct = Helpers.accounts[0]

        for holder_addr in ldo_vote_executors_for_tests:
            print(f'voting from {holder_addr}')
            helper_acct.transfer(holder_addr, '0.1 ether')
            account = Helpers.accounts.at(holder_addr, force=True)
            Helpers.dao_voting.vote(vote_id, True, False, {'from': account})

        # wait for the vote to end
        chain.sleep(3 * 60 * 60 * 24)
        chain.mine()

        assert Helpers.dao_voting.canExecute(vote_id)
        Helpers.dao_voting.executeVote(vote_id, {'from': helper_acct})

        print(f'vote {vote_id} executed')

@pytest.fixture(scope='module')
def helpers(accounts, dao_voting):
    Helpers.accounts = accounts
    Helpers.dao_voting = dao_voting
    return Helpers

def deploy_and_start_dao_vote(tx_params):
    voting = interface.Voting(lido_dao_voting_addr)
    token_manager = interface.TokenManager(lido_dao_token_manager_address)

    anchor_new_vault = deploy(tx_params)

    evm_script = encode_call_script([
        encode_proxy_upgrade(
            new_impl_address=anchor_new_vault,
            setup_calldata=b''
        ),
        encode_finalize_upgrade_v4()
    ])

    (vote_id, tx) = create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=f"1. Update anchor vault implementation {anchor_new_vault}\n2. Increase vault version to v4",
        evm_script=evm_script,
        tx_params=tx_params
    )

    return (anchor_new_vault, vote_id)

@pytest.fixture(scope='module')
def deploy_vault_and_pass_dao_vote(ldo_holder, helpers):
    def deploy():
        (vault, vote_id) = deploy_and_start_dao_vote({'from': ldo_holder})
        helpers.pass_and_exec_dao_vote(vote_id)
        return vault

    return deploy