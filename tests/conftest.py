import pytest
from brownie import ZERO_ADDRESS, Contract


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
def ust_token(interface):
    return interface.UST(UST_TOKEN)


@pytest.fixture(scope='module')
def usdc_token(interface):
    return interface.USDC(USDC_TOKEN)


@pytest.fixture(scope='module')
def feed_steth_eth(interface):
    return interface.Chainlink(CHAINLINK_STETH_ETH_FEED)


@pytest.fixture(scope='module')
def feed_usdc_eth(interface):
    return interface.Chainlink(CHAINLINK_USDC_ETH_FEED)


@pytest.fixture(scope='module')
def feed_ust_eth(interface):
    return interface.Chainlink(CHAINLINK_UST_ETH_FEED)


@pytest.fixture(scope='module')
def beth_token(deployer, admin, bEth):
    return bEth.deploy("bETH", ZERO_ADDRESS, admin, {'from': deployer})


@pytest.fixture(scope='module')
def mock_bridge(accounts):
    return accounts.add()


@pytest.fixture(scope='module')
def mock_wormhole_token_bridge(deployer, MockWormholeTokenBridge):
    return MockWormholeTokenBridge.deploy({'from': deployer})


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
def mock_rewards_liquidator(MockRewardsLiquidator, deployer):
    return MockRewardsLiquidator.deploy({'from': deployer})


@pytest.fixture(scope='module')
def mock_insurance_connector(MockInsuranceConnector, deployer):
    return MockInsuranceConnector.deploy({'from': deployer})


@pytest.fixture(scope='module')
def withdraw_from_terra(mock_bridge_connector, mock_bridge, beth_token):
  def withdraw(terra_address, to_address, amount):
    terra_balance_before = mock_bridge_connector.terra_beth_balance_of(terra_address)
    beth_token.approve(mock_bridge_connector, amount, {"from": mock_bridge})
    mock_bridge_connector.mock_beth_withdraw(terra_address, to_address, amount, {"from": mock_bridge})
    assert mock_bridge_connector.terra_beth_balance_of(terra_address) == terra_balance_before - amount
  return withdraw


@pytest.fixture(scope='module')
def lido_oracle_report(interface, accounts, steth_token):
    lido = interface.Lido(steth_token.address)
    lido_oracle = accounts.at(lido.getOracle(), force=True)
    dao_voting = accounts.at('0x2e59A20f205bB85a89C53f1936454680651E618e', force=True)
    def report_beacon_state(steth_rebase_mult):
        lido.setFee(0, {'from': dao_voting})
        (deposited_validators, beacon_validators, beacon_balance) = lido.getBeaconStat()
        total_supply = steth_token.totalSupply()
        total_supply_inc = (steth_rebase_mult - 1) * total_supply
        beacon_balance += total_supply_inc
        assert beacon_balance > 0
        lido.pushBeacon(beacon_validators, beacon_balance, {'from': lido_oracle})
    return report_beacon_state


@pytest.fixture(scope="module")
def steth_burner(lido, accounts, deployer, interface):
    burner = accounts.add()
    deployer.transfer(burner, 10**18)
    voting_app = accounts.at('0x2e59A20f205bB85a89C53f1936454680651E618e', force=True)
    acl = interface.ACL('0x9895F0F17cc1d1891b6f18ee0b483B6f221b37Bb')
    acl.grantPermission(burner, lido, lido.BURN_ROLE(), {'from': voting_app})
    return burner


@pytest.fixture(scope="module")
def burn_steth(steth_burner, lido):
    def burn(holder, amount):
        shares_amount = lido.getSharesByPooledEth(amount)
        lido.burnShares(holder, shares_amount, {'from': steth_burner})
    return burn


@pytest.fixture(scope="module")
def steth_adjusted_ammount(vault, mock_bridge_connector):
    def adjust_amount(amount):
        beth_rate = vault.get_rate()
        beth_amount = int((amount * beth_rate) / 10**18)
        beth_amount = mock_bridge_connector.adjust_amount(beth_amount, BETH_DECIMALS)
        steth_amount_adj = int((beth_amount * 10**18) / beth_rate)
        return steth_amount_adj
    return adjust_amount


@pytest.fixture(scope='module')
def deposit_to_terra(vault, mock_bridge_connector, steth_token, helpers, steth_adjusted_ammount):
    def deposit(terra_address, sender, amount):
        terra_balance_before = mock_bridge_connector.terra_beth_balance_of(terra_address)
        steth_balance_before = steth_token.balanceOf(sender)

        steth_amount_adj = steth_adjusted_ammount(amount)

        steth_token.approve(vault, amount, {'from': sender})
        tx = vault.submit(amount, terra_address, '0xab', vault.version(), {'from': sender})

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



@pytest.fixture(scope='module')
def helpers():
    return Helpers
