# stETH as Anchor collateral

This repo contains Ethereum contracts for integrating stETH as a collateral into the [Anchor protocol] in the form of bETH token. Currently it assumes the deployed [Wormhole v2 bridge] between Ethereum and Terra networks.

[Anchor protocol]: http://anchorprotocol.com
[Wormhole v2 bridge]: https://github.com/certusone/wormhole

## Contracts

* [`bEth`](./contracts/bEth.vy) bETH token contract
* [`AnchorVault`](./contracts/AnchorVault.vy) a contract allowing to convert between stETH and bETH
* [`RewardsLiquidator`](./contracts/RewardsLiquidator.vy) a contract for selling stETH rewards to UST
* [`InsuranceConnector`](./contracts/InsuranceConnector.vy) a contract for obtaining the total number of shares burnt for the purpose of insurance/cover application from the Lido protocol
* [`BridgeConnectorWormhole`](./contracts/BridgeConnectorWormhole.vy) an adapter contract for communicating with the Wormhole v2 bridge

`RewardsLiquidator`, `InsuranceConnector` and `BridgeConnectorWormhole` contracts are installed as delegates to the `AnchorVault` contract and can be replaced by the vault admin.
