# stETH as Anchor collateral

This repo contains Ethereum contracts for integrating stETH as a collateral into the [Anchor protocol] in the form of bETH token. Currently it assumes the deployed [Wormhole v2 bridge] between Ethereum and Terra networks.

[Anchor protocol]: http://anchorprotocol.com
[Wormhole v2 bridge]: https://github.com/certusone/wormhole

## 🏁 Getting started

- This project uses Brownie development framework. Learn more about
[Brownie](https://eth-brownie.readthedocs.io/en/stable/index.html).
- [Poetry](https://python-poetry.org/) dependency and packaging manager is used
to bootstrap environment and keep the repo sane.

### Prerequisites

- Python >= 3.10, <3.11
- Pip >= 20.0
- Node >= 16.0
- yarn >= 1.22

#### Step 1. Install Poetry

Use the following command to install poetry:

```shell
pip install --user poetry==1.5.0
```

alternatively, you could proceed with `pipx`:

```shell
pipx install poetry==1.5.0
```

#### Step 2. Setup dependencies with poetry

Ensure that poetry bin path is added to your `$PATH` env variable.
Usually it's `$HOME/.local/bin` for most Unix-like systems.

```shell
poetry install
```

Notes: if you have some problems on `poetry install` (too slow, or too long) try to clear cache:
```shell
poetry cache clear --all pypi
```

## Contracts

* [`bEth`](./contracts/bEth.vy) bETH token contract
* [`AnchorVault`](./contracts/AnchorVault.vy) a contract allowing to convert between stETH and bETH
* [`RewardsLiquidator`](./contracts/RewardsLiquidator.vy) a contract for selling stETH rewards to UST
* [`InsuranceConnector`](./contracts/InsuranceConnector.vy) a contract for obtaining the total number of shares burnt for the purpose of insurance/cover application from the Lido protocol
* [`BridgeConnectorWormhole`](./contracts/BridgeConnectorWormhole.vy) an adapter contract for communicating with the Wormhole v2 bridge

`RewardsLiquidator`, `InsuranceConnector` and `BridgeConnectorWormhole` contracts are installed as delegates to the `AnchorVault` contract and can be replaced by the vault admin.
