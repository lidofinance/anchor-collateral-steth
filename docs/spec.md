# stETH+Anchor integration spec

In this document we propose a solution which main difference is that the vault sells and distributes rewards from all locked stETH tokens to Anchor protocol. This means that any user that has locked their stETH but hasn't deposited their bETH to Anchor would lose their rewards. The motivation is described in the sections below.

## Requirements

* No balance rebases for bETH token holders.
* stETH rewards are converted to UST and sent to Anchor on a regular basis.
* stETH rewards are sold on the Ethereum side.
* During normal operation, bETH is 1:1 redeemable to stETH. Exchange rate temporarily becomes less than 1 only in cases of beacon chain penalties/slashings.


## High-level overview

The proposed solution relies on the following components (assets on the Terra side are in italics):

* The Wormhole bridge.
* A pair of token contracts managed by Shuttle: bETH in Ethereum and a wrapper _bETH_ in Terra.
* The vault contract in Ethereum. We propose to implement the vault functionality in the bETH token contract.
* The rewards distributor contract in Terra, `BEthRewardsDistributor`.

Upon stETH reception, the vault mints the equivalent amount of bETH tokens and sends them to the specified Terra address (provided by the stETH sender) in the form of _bETH_ tokens.

From that moment, all rewards accrued from the received stETH tokens are sold to UST on a periodic basis (on the Ethereum side) and sent to the `BEthRewardsDistributor` contract (on the Terra side) which allows _bETH_ holhers to claim their rewards. Anchor will interact with the same contract to obtain the rewards for _bETH_ used as a collateral in the protocol.

It's the vault user's responsibility to deposit the received _bETH_ tokens to Anchor. A UI will be impemented to assess in the whole process. Automatic depositing may be added via an upgrade in the future, when a bridge that supports passing arbitrary messages to the Terra side is deployed.


## Alternative approaches

A different approach has been proposed in the [bETH: Wrapping Derivative around Lido stETH] document. The main difference is that UST from sold stETH rewards are distributed between vault token holders on the Ethereum side. This is a desired property, but, unfortunately, it won't work in the multichain setup since the portion of the tokens that are on the Terra side cannot be practically tracked by the vault on the Ethereum side, so the vault can't tell between tokens on Terra that are staked to Anchor and those that aren't.

[bETH: Wrapping Derivative around Lido stETH]: https://quip.com/3QdwASTSJ5IW

Yet another approach is to implement the main vault logic on the Terra side. This would solve the problem with tracking the tokens, however, it would require having stETH/UST pool and stETH wrapper on Terra which, in turn, requires a mechanism to pass beacon chain data to Terra. This data is pushed by Lido oracles to the `Lido` Ethereum smart contract, and this contract should be the single source of truth to prevent de-synchronization and possible attacks it may enable. Passing arbitrary data from Ethereum to Terra is not supported yet by any deployed bridge.


## Components: Terra

### _bETH_

A wrapper CW20 smart contract managed by the bridge.

### BEthRewardsDistributor

A smart contract responsible for receiving all staking rewards accrued by the stETH tokens held inside the bETH vault on the Ethereum side. These rewards are sold to UST and forwarded to this contract using the bridge.

The contract may be implemented in a way that enables all holders of _bETH_ wrapped tokens to claim their UST rewards. For example, see the [Synthetix rewards contract] that implements this logic in Solidity. The _bETH_ wrapper contract will be required to notify the distributor contract on each _bETH_ balance change. In this scheme, Anchor will periodically claim the rewards for _bETH_ deposited to the protocol.

Alternatively, the contract may just forward all received rewards to Anchor, in which case it becomes the responsilitily of the bETH vault user to deposit their _bETH_ to Anchor in order to continue receiving their staking rewards.

[Synthetix rewards contract]: https://github.com/Synthetixio/synthetix/blob/develop/contracts/StakingRewards.sol


## Components: Ethereum

### bETH

A contract implementing both bETH token and vault functionality.

Token-related interface:

* Standard ERC20 interface defined in [EIP-20].
* Signed approvals interface defined in [EIP-2612].

[EIP-2612]: https://eips.ethereum.org/EIPS/eip-2612
[EIP-20]: https://eips.ethereum.org/EIPS/eip-20

Vault interface:

* `submit(amount: uint256, terra_address: bytes32, extra_data: bytes32)` locks `amount` of caller's stETH in exchange for `amount` _bETH_ tokens on `terra_address` in Terra.
* `withdraw(amount: uint256, recipient: address)` burns `amount` of caller's bETH tokens in exchange for `stETH` tokens sent to the `recipient` address.

Admin interface:

* `collect_rewards()` sells stETH rewards to UST and forwards them to the Terra side using the `RewardsLiquidator` contract. Only callable by the whitelisted addresses. May be called by e.g. Lido oracles after each beacon balance report.
* `configure(bridge_connector: address, rewards_liquidator: address)` sets `BridgeConnector` and `RewardsLiquidator` contracts, allowing upgradeability. Only callable by the vault admin (e.g. Lido DAO `Agent` contract).

Pseudo-code:

```python
def submit(amount, terra_address, extra_data):
    ERC20(STETH_TOKEN).transferFrom(msg.sender, self, amount)
    self._mint(self.bridge_connector, amount)
    BridgeConnector(self.bridge_connector).forward_beth(terra_address, amount, extra_data)

def withdraw(amount, recipient = msg.sender):
    self._burn(msg.sender, amount)
    # will be less than 1 after beacon chain
    # penalties or slashings, otherwise 1
    steth_rate = self._get_withdraw_rate()
    steth_amount = amount * steth_rate
    ERC20(STETH_TOKEN).transfer(recipient, steth_amount)

def collect_rewards():
    assert(self._is_whitelisted(msg.sender))
    steth_amount = self._get_rewards_amount()
    if steth_amount < self._min_rewards_to_sell:
        return
    ERC20(STETH_TOKEN).transfer(self.liquidator, steth_amount)
    return RewardsLiquidator(self.liquidator).liquidate()

def _get_rewards_amount():
    steth_balance = ERC20(STETH_TOKEN).balanceOf(self)
    beth_supply = self.totalSupply()
    if steth_balance > beth_supply:
        return steth_balance - beth_supply
    else:
        return 0

def _get_withdraw_rate():
    steth_balance = ERC20(STETH_TOKEN).balanceOf(self)
    beth_supply = self.totalSupply()
    if steth_balance > beth_supply:
        return 1
    else:
        return steth_balance / beth_supply
```

### BridgeConnector

A smart contract that interacts with the bridge, transferring bETH and UST from Etereum to Terra.

Provides the following interface:

* `forward_beth(terra_address, amount, extra_data)` transfers bETH tokens from Ethereum to Terra, forwarding them to the specified address. The `extra_data` argument is currently unused.
* `forward_ust(terra_address, amount, extra_data)` transfers UST tokens from Ethereum to Terra, forwarding them to the specified address. The `extra_data` argument is currently unused.

### RewardsLiquidator

A smart contract that liquidates stETH rewards to UST and transfers them to the `BEthRewardsDistributor` smart contract on the Terra side.

Provides the following interface:

* `liquidate() -> uint256` sells the whole self balance of stETH to UST and transfers the received tokens to Anchor. Returns the transferred UST amount.

Pseudo-code:

```python
def liquidate():
    ust_amount = self._sell_steth_balance(self.bridge_connector)
    BridgeConnector(self.bridge_connector).forward_ust(REWARDS_DISTR_ADDRESS, ust_amount, b"")
    return ust_amount

def _sell_steth_balance(recipient):
    # sells on 1inch
    steth_amount = ERC20(STETH_TOKEN).balanceOf(self)
    ust_amount = self._get_expected_ust_return(steth_amount)
    min_return = ust_amount * (1 - self.max_slippage_percent / 100)
    return self._swap_to_ust(steth_amount, recipient, min_return)
```

### InsuranceConnector

A smart contract that takes into account stETH shares burnt for the coverage application purposes.

Provides the following interface:

* `total_shares_burnt() -> uint256` gets the total ever burnt stETH shares amount (not token amount) for the coverage application purposes.

See also: https://github.com/lidofinance/lido-improvement-proposals/blob/develop/LIPS/lip-6.md
