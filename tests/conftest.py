import pytest
from brownie import ZERO_ADDRESS


BETH_DECIMALS = 18
UST_TOKEN = '0xa47c8bf37f92aBed4A126BDA807A7b7498661acD'


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
def liquidations_admin(accounts):
    return accounts[2]


@pytest.fixture(scope='module')
def vault_user(accounts, interface, steth_token):
    user = accounts[3]
    lido = interface.Lido(steth_token.address)
    lido.submit(ZERO_ADDRESS, {'from': user, 'value': 99 * 10**18})
    assert steth_token.balanceOf(user) > 98 * 10**18
    return user


@pytest.fixture(scope='module')
def another_vault_user(accounts, interface, steth_token):
    user = accounts[4]
    lido = interface.Lido(steth_token.address)
    lido.submit(ZERO_ADDRESS, {'from': user, 'value': 99 * 10**18})
    assert steth_token.balanceOf(user) > 98 * 10**18
    return user


@pytest.fixture(scope='module')
def stranger(accounts):
    return accounts[9]


@pytest.fixture(scope='module')
def steth_token(interface):
    return interface.ERC20('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')


@pytest.fixture(scope='module')
def lido(interface, steth_token):
    return interface.Lido(steth_token.address)


@pytest.fixture(scope='module')
def ust_token(interface):
    return interface.ERC20('0xa47c8bf37f92aBed4A126BDA807A7b7498661acD')


@pytest.fixture(scope='module')
def beth_token(deployer, admin, bEth):
    return bEth.deploy("bETH", ZERO_ADDRESS, admin, {'from': deployer})


@pytest.fixture(scope='module')
def mock_bridge(accounts):
    return accounts.add()


@pytest.fixture(scope='function')
def mock_bridge_connector(beth_token, deployer, mock_bridge, MockBridgeConnector, interface):
    mock_bridge_connector =  MockBridgeConnector.deploy(beth_token, mock_bridge, {'from': deployer})
    ust_token = interface.ERC20(UST_TOKEN)
    ust_balance = ust_token.balanceOf(UST_TOKEN)
    interface.ERC20(UST_TOKEN).transfer(mock_bridge_connector.address, ust_balance, {"from": UST_TOKEN})
    return mock_bridge_connector


@pytest.fixture(scope='function')
def mock_rewards_liquidator(MockRewardsLiquidator, deployer):
    return MockRewardsLiquidator.deploy({'from': deployer})


@pytest.fixture(scope='function')
def withdraw_from_terra(mock_bridge_connector, mock_bridge, beth_token):
  def withdraw(terra_address, to_address, amount):
    terra_balance_before = mock_bridge_connector.terra_beth_balance_of(terra_address)
    beth_token.approve(mock_bridge_connector, amount, {"from": mock_bridge})
    mock_bridge_connector.mock_beth_withdraw(terra_address, to_address, amount, {"from": mock_bridge})
    assert mock_bridge_connector.terra_beth_balance_of(terra_address) == terra_balance_before - amount
  return withdraw


@pytest.fixture(scope='module')
def rebase_steth_by(interface, accounts, steth_token):
    lido = interface.Lido(steth_token.address)
    lido_oracle = accounts.at(lido.getOracle(), force=True)
    dao_voting = accounts.at('0x2e59A20f205bB85a89C53f1936454680651E618e', force=True)
    def rebase(mult):
        lido.setFee(0, {'from': dao_voting})
        (deposited_validators, beacon_validators, beacon_balance) = lido.getBeaconStat()
        total_supply = steth_token.totalSupply()
        total_supply_inc = (mult - 1) * total_supply
        beacon_balance += total_supply_inc
        assert beacon_balance > 0
        lido.pushBeacon(beacon_validators, beacon_balance, {'from': lido_oracle})
    return rebase


@pytest.fixture(scope="function")
def steth_adjusted_ammount(vault, mock_bridge_connector):
    def adjust_amount(amount):
        beth_rate = vault.get_rate()
        beth_amount = int((amount * beth_rate) / 10**18)
        beth_amount = mock_bridge_connector.adjust_amount(beth_amount, BETH_DECIMALS)
        steth_amount_adj = int((beth_amount * 10**18) / beth_rate)
        return steth_amount_adj
    return adjust_amount


@pytest.fixture(scope='function')
def deposit_to_terra(vault, mock_bridge_connector, steth_token, helpers, steth_adjusted_ammount):
    def deposit(terra_address, sender, amount):
        terra_balance_before = mock_bridge_connector.terra_beth_balance_of(terra_address)
        steth_balance_before = steth_token.balanceOf(sender)

        steth_amount_adj = steth_adjusted_ammount(amount)

        steth_token.approve(vault, amount, {'from': sender})
        tx = vault.submit(amount, terra_address, '0xab', {'from': sender})

        steth_balance_decrease = steth_balance_before - steth_token.balanceOf(sender)
        assert helpers.equal_with_precision(steth_balance_decrease, steth_amount_adj, max_diff=10**10)

        beth_amount = int(steth_balance_decrease * vault.get_rate() / 10**18)

        assert helpers.equal_with_precision(
            mock_bridge_connector.terra_beth_balance_of(terra_address),
            terra_balance_before + beth_amount,
            max_diff=100
        )
        return tx
    return deposit


class Helpers:
    @staticmethod
    def filter_events_from(addr, events):
        return list(filter(lambda evt: evt.address == addr, events))

    @staticmethod
    def assert_single_event_named(evt_name, tx, evt_keys_dict = None, source = None):
        receiver_events = tx.events[evt_name]
        if source is not None:
            receiver_events = Helpers.filter_events_from(source, receiver_events)
        assert len(receiver_events) == 1
        if evt_keys_dict is not None:
            assert dict(receiver_events[0]) == evt_keys_dict
        return receiver_events[0]

    @staticmethod
    def assert_no_events_named(evt_name, tx):
        assert evt_name not in tx.events

    @staticmethod
    def equal_with_precision(x, y, max_diff):
        return abs(x - y) <= max_diff



@pytest.fixture(scope='module')
def helpers():
    return Helpers
