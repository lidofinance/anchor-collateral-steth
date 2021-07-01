# stETH as Anchor collateral

This repo contains Ethereum contracts for integrating stETH as a collateral into the
[Anchor protocol] in the form of bETH token. Currently it assumes the deployed [Shuttle bridge] between Ethereum
and Terra networks.

[Anchor protocol]: http://anchorprotocol.com
[Shuttle bridge]: https://github.com/terra-money/shuttle

## Contracts

* [`bEth`](./contracts/bEth.vy) bETH token contract
* [`AnchorVault`](./contracts/AnchorVault.vy) a contract allowing to convert between stETH and bETH
* [`RewardsLiquidator`](./contracts/RewardsLiquidator.vy) a contract for selling stETH rewards to UST
* [`InsuranceConnector`](./contracts/InsuranceConnector.vy) a contract for obtaining the total number of shares burnt for the purpose of insurance/cover application from the Lido protocol
* [`BridgeConnectorShuttle`](./contracts/BridgeConnectorShuttle.vy) an adapter contract for communicating with the Terra Shuttle bridge

`RewardsLiquidator`, `InsuranceConnector` and `BridgeConnectorShuttle` contracts are installed as delegates to the `AnchorVault` contract and can be replaced by the vault admin.
