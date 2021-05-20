import pytest
from brownie import ZERO_ADDRESS


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
def stranger(accounts):
    return accounts[9]


@pytest.fixture(scope='module')
def steth_token(interface):
    return interface.ERC20('0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')


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
def mock_bridge_connector(beth_token, deployer, admin, mock_bridge, MockBridgeConnector):
    return MockBridgeConnector.deploy(beth_token, mock_bridge, {'from': deployer})


@pytest.fixture(scope='function')
def withdraw_from_terra(mock_bridge_connector, mock_bridge, beth_token):
  def withdraw(TERRA_ADDRESS, to_address, amount):
    beth_token.approve(mock_bridge_connector, amount, {"from": mock_bridge})
    tx = mock_bridge_connector.mock_beth_withdraw(TERRA_ADDRESS, to_address, amount, {"from": mock_bridge})
    print(tx.events['Test__TerraWithdraw'])
  return withdraw


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
