# @version 0.2.15
# @author skozin <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20


interface ERC20Decimals:
    def decimals() -> uint256: view


interface ChainlinkAggregatorV3Interface:
    def decimals() -> uint256: view
    # (roundId: uint80, answer: int256, startedAt: uint256, updatedAt: uint256, answeredInRound: uint80)
    def latestRoundData() -> (uint256, int256, uint256, uint256, uint256): view


interface CurvePool:
    def get_dy(i: int128, j: int128, dx: uint256) -> uint256: view
    def exchange(i: int128, j: int128, dx: uint256, min_dy: uint256) -> uint256: payable
    def exchange_underlying(i: int128, j: int128, dx: uint256, min_dy: uint256) -> uint256: nonpayable

# struct ExactInputSingleParams:
#     tokenIn: address
#     tokenOut: address
#     fee: uint256
#     recipient: address
#     amountIn: uint256
#     amountOutMinimum: uint256
#     sqrtPriceLimitX96: uint256

# interface IV3SwapRouter:
#     # @notice Swaps `amountIn` of one token for as much as possible of another token
#     # @param params The parameters necessary for the swap, encoded as `ExactInputSingleParams` in calldata
#     # @return amountOut The amount of the received token
#     def exactInputSingle(params: ExactInputSingleParams) -> uint256: payable
#     def fee() -> uint256: view

event SoldStethToUST:
    steth_amount: uint256
    eth_amount: uint256
    usdc_amount: uint256
    ust_amount: uint256
    steth_eth_anchor_price: uint256
    eth_usdc_anchor_price: uint256
    usdc_usd_anchor_price: uint256


event AdminChanged:
    new_admin: address


event PriceDifferenceChanged:
    max_steth_eth_price_difference_percent: uint256
    max_eth_usdc_price_difference_percent: uint256
    max_usdc_usd_price_difference_percent: uint256
    max_steth_usd_price_difference_percent: uint256


UST_TOKEN: constant(address) = 0xa47c8bf37f92aBed4A126BDA807A7b7498661acD
USDC_TOKEN: constant(address) = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
STETH_TOKEN: constant(address) = 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84
WETH_TOKEN: constant(address) = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2

CHAINLINK_STETH_ETH_FEED: constant(address) = 0x86392dC19c0b719886221c78AB11eb8Cf5c52812
CHAINLINK_STETH_USD_FEED: constant(address) = 0xCfE54B5cD566aB89272946F602D76Ea879CAb4a8 #for final check

# CHAINLINK_ETH_USD_FEED: constant(address) = 0x5f4eC3Df9cbd43714FE2740f5E3616155c5b8419
# CHAINLINK_ETH_UST_FEED: constant(address) = 0xa20623070413d42a5C01Db2c8111640DD7A5A03a
CHAINLINK_ETH_USDC_FEED: constant(address) = 0x986b5E1e1755e3C2440e960477f25201B0a8bbD4
CHAINLINK_USDC_USD_FEED: constant(address) = 0x8fFfFfd4AfB6115b954Bd326cbe7B4BA576818f6

CURVE_STETH_POOL: constant(address) = 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022
CURVE_UST_POOL: constant(address) = 0x890f4e345B1dAED0367A877a1612f86A1f86985f #TODO: check
UNISWAP_ROUTER_V2: constant(address) = 0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D
UNISWAP_ROUTER_V3: constant(address) = 0xE592427A0AEce92De3Edee1F18E0157C05861564

CURVE_ETH_INDEX: constant(uint256) = 0
CURVE_STETH_INDEX: constant(uint256) = 1
CURVE_USDC_INDEX: constant(uint256) = 2
CURVE_UST_INDEX: constant(uint256) = 0

# An address that is allowed to configure the liquidator settings.
admin: public(address)

# An address that is allowed to sell.
vault: public(address)

# Maximum difference (in percents multiplied by 10**18) between the resulting
# ETH/USDC price and the ETH/USDC anchor price obtained from the oracle.
max_eth_usdc_price_difference_percent: public(uint256)

# Maximum difference (in percents multiplied by 10**18) between the resulting
# USDC/UST price and the USDC/USD anchor price obtained from the oracle.
max_usdc_usd_price_difference_percent: public(uint256)

# Maximum difference (in percents multiplied by 10**18) between the resulting
# stETH/UST price and the stETH/USD anchor price obtained from the oracle.
max_steth_usd_price_difference_percent: public(uint256)

# Maximum difference (in percents multiplied by 10**18) between the resulting
# stETH/ETH price and the stETH/ETH anchor price obtained from the oracle.
max_steth_eth_price_difference_percent: public(uint256)


@external
def __init__(
    vault: address,
    admin: address,
    max_steth_eth_price_difference_percent: uint256,
    max_eth_usdc_price_difference_percent: uint256,
    max_usdc_usd_price_difference_percent: uint256,
    max_steth_usd_price_difference_percent: uint256
):
    assert ERC20Decimals(USDC_TOKEN).decimals() == 6
    assert ERC20Decimals(UST_TOKEN).decimals() == 18
    assert ERC20Decimals(STETH_TOKEN).decimals() == 18

    assert max_steth_eth_price_difference_percent <= 10**18, "invalid percentage"
    assert max_eth_usdc_price_difference_percent <= 10**18, "invalid percentage"
    assert max_usdc_usd_price_difference_percent <= 10**18, "invalid percentage"
    assert max_steth_usd_price_difference_percent <= 10**18, "invalid percentage"

    self.vault = vault
    self.admin = admin
    self.max_steth_eth_price_difference_percent = max_steth_eth_price_difference_percent
    self.max_eth_usdc_price_difference_percent = max_eth_usdc_price_difference_percent
    self.max_usdc_usd_price_difference_percent = max_eth_usdc_price_difference_percent
    self.max_steth_usd_price_difference_percent = max_steth_usd_price_difference_percent

    log AdminChanged(self.admin)

    log PriceDifferenceChanged(
        self.max_steth_eth_price_difference_percent, 
        self.max_eth_usdc_price_difference_percent,
        self.max_usdc_usd_price_difference_percent,
        self.max_steth_usd_price_difference_percent
    )


@external
@payable
def __default__():
    pass


@external
def change_admin(new_admin: address):
    assert msg.sender == self.admin
    self.admin = new_admin
    log AdminChanged(self.admin)


@external
def configure(
    max_steth_eth_price_difference_percent: uint256,
    max_eth_usdc_price_difference_percent: uint256,
    max_usdc_usd_price_difference_percent: uint256,
    max_steth_usd_price_difference_percent: uint256
):
    assert msg.sender == self.admin
    assert max_steth_eth_price_difference_percent <= 10**18, "invalid percentage"
    assert max_eth_usdc_price_difference_percent <= 10**18, "invalid percentage"
    assert max_usdc_usd_price_difference_percent <= 10**18, "invalid percentage"
    assert max_steth_usd_price_difference_percent <= 10**18, "invalid percentage"

    self.max_steth_eth_price_difference_percent = max_steth_eth_price_difference_percent
    self.max_eth_usdc_price_difference_percent = max_eth_usdc_price_difference_percent
    self.max_usdc_usd_price_difference_percent = max_usdc_usd_price_difference_percent
    self.max_steth_usd_price_difference_percent = max_steth_usd_price_difference_percent

    log PriceDifferenceChanged(
        self.max_steth_eth_price_difference_percent, 
        self.max_eth_usdc_price_difference_percent,
        self.max_usdc_usd_price_difference_percent,
        self.max_steth_usd_price_difference_percent
    )


@internal
@view
def _get_steth_eth_anchor_price() -> uint256:
    round_id: uint256 = 0
    answer: int256 = 0
    started_at: uint256 = 0
    updated_at: uint256 = 0
    answered_in_round: uint256 = 0

    (round_id, answer, started_at, updated_at, answered_in_round) = \
        ChainlinkAggregatorV3Interface(CHAINLINK_STETH_ETH_FEED).latestRoundData()

    assert updated_at != 0

    return convert(answer, uint256)


@internal
@view
def _get_eth_usdc_anchor_price() -> uint256:
    eth_price_decimals: uint256 = ChainlinkAggregatorV3Interface(CHAINLINK_ETH_USDC_FEED).decimals()
    assert 0 < eth_price_decimals and eth_price_decimals <= 18

    round_id: uint256 = 0
    answer: int256 = 0
    started_at: uint256 = 0
    updated_at: uint256 = 0
    answered_in_round: uint256 = 0

    (round_id, answer, started_at, updated_at, answered_in_round) = \
        ChainlinkAggregatorV3Interface(CHAINLINK_ETH_USDC_FEED).latestRoundData()

    assert updated_at != 0

    return convert(answer, uint256) * (10 ** (18 - eth_price_decimals))

@internal
@view
def _get_usdc_usd_anchor_price() -> uint256:
    eth_price_decimals: uint256 = ChainlinkAggregatorV3Interface(CHAINLINK_ETH_USDC_FEED).decimals()
    assert 0 < eth_price_decimals and eth_price_decimals <= 18

    round_id: uint256 = 0
    answer: int256 = 0
    started_at: uint256 = 0
    updated_at: uint256 = 0
    answered_in_round: uint256 = 0

    (round_id, answer, started_at, updated_at, answered_in_round) = \
        ChainlinkAggregatorV3Interface(CHAINLINK_ETH_USDC_FEED).latestRoundData()

    assert updated_at != 0

    return convert(answer, uint256) * (10 ** (18 - eth_price_decimals))

@internal
@view
def _get_steth_usd_anchor_price() -> uint256:
    eth_price_decimals: uint256 = ChainlinkAggregatorV3Interface(CHAINLINK_STETH_USD_FEED).decimals()
    assert 0 < eth_price_decimals and eth_price_decimals <= 18

    round_id: uint256 = 0
    answer: int256 = 0
    started_at: uint256 = 0
    updated_at: uint256 = 0
    answered_in_round: uint256 = 0

    (round_id, answer, started_at, updated_at, answered_in_round) = \
        ChainlinkAggregatorV3Interface(CHAINLINK_STETH_USD_FEED).latestRoundData()

    assert updated_at != 0

    return convert(answer, uint256) * (10 ** (18 - eth_price_decimals))


@internal
def _uniswap_v2_sell_eth_to_usdc(
    eth_amount_in: uint256,
    usdc_amount_out_min: uint256,
    usdc_recipient: address
) -> uint256:
    result: Bytes[128] = raw_call(
        UNISWAP_ROUTER_V2,
        concat(
            # uint256 amountOutMin, address[] calldata path, address to, uint256 deadline
            method_id("swapExactETHForTokens(uint256,address[],address,uint256)"),
            convert(usdc_amount_out_min, bytes32),
            convert(128, bytes32), #offset
            convert(usdc_recipient, bytes32),
            convert(MAX_UINT256, bytes32),
            convert(2, bytes32), #array size
            convert(WETH_TOKEN, bytes32),
            convert(UST_TOKEN, bytes32)
        ),
        value=eth_amount_in,
        max_outsize=128
    )
    # The return type is uint256[] and the actual length of the array is 2, so the
    # layout of the data is (pad32(64) . pad32(2) . pad32(arr[0]) . pad32(arr[1])).
    # We need the second array item, thus the byte offset is 96.
    return convert(extract32(result, 96), uint256)

@internal
def _uniswap_v3_sell_eth_to_usdc(
    eth_amount_in: uint256,
    usdc_amount_out_min: uint256,
    usdc_recipient: address
) -> uint256:

    result: Bytes[32] = raw_call(
        UNISWAP_ROUTER_V3,
        concat(
            method_id("exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))"),
            convert(WETH_TOKEN, bytes32),
            convert(USDC_TOKEN, bytes32),
            convert(500, bytes32), #TODO: get pool fee
            convert(usdc_recipient, bytes32),
            convert(eth_amount_in, bytes32),
            convert(usdc_amount_out_min, bytes32),
            convert(0, bytes32),
        ),
        value=eth_amount_in,
        max_outsize=32
    )
    return convert(result, uint256)

@internal
@pure
def _get_min_amount_out(amount_in: uint256, price: uint256, max_diff_percent: uint256) -> uint256:
    amount_out: uint256 = (amount_in * price) / 10**18
    min_mult: uint256 = 10**18 - max_diff_percent
    return (amount_out * min_mult) / 10**18

# 1) stETH -> ETH (Curve)
# 2) ETH -> USDC (Uniswap v2)
# 3) USDC -> UST (Curve)
@external
def liquidate(ust_recipient: address) -> uint256:
    assert msg.sender == self.vault, "unauthorized"

    steth_amount: uint256 = ERC20(STETH_TOKEN).balanceOf(self)
    assert steth_amount > 0, "zero stETH balance"

    # steth -> eth
    steth_eth_anchor_price: uint256 = self._get_steth_eth_anchor_price()

    min_eth_amount: uint256 = self._get_min_amount_out(
        steth_amount,
        steth_eth_anchor_price,
        self.max_steth_eth_price_difference_percent
    )

    ERC20(STETH_TOKEN).approve(CURVE_STETH_POOL, steth_amount)

    eth_amount: uint256 = CurvePool(CURVE_STETH_POOL).exchange(
        CURVE_STETH_INDEX,
        CURVE_ETH_INDEX,
        steth_amount,
        min_eth_amount
    )

    assert eth_amount >= min_eth_amount, "insuff. ETH return"
    assert self.balance >= eth_amount

    # eth -> usdc
    eth_usdc_anchor_price: uint256 = self._get_eth_usdc_anchor_price()

    min_usdc_amount: uint256 = self._get_min_amount_out(
        eth_amount,
        eth_usdc_anchor_price,
        self.max_eth_usdc_price_difference_percent
    )

    usdc_amount: uint256 = self._uniswap_v2_sell_eth_to_usdc(
        eth_amount,
        min_usdc_amount,
        self
    )

    assert usdc_amount >= min_usdc_amount, "insuff. USDC return"
    assert ERC20(USDC_TOKEN).balanceOf(self) >= usdc_amount

    # usdc -> ust
    # assuming the usd is almost the same as ust
    usdc_usd_anchor_price: uint256 = self._get_usdc_usd_anchor_price()

    min_ust_amount: uint256 = self._get_min_amount_out(
        usdc_amount,
        usdc_usd_anchor_price,
        self.max_usdc_usd_price_difference_percent
    )

    ERC20(USDC_TOKEN).approve(CURVE_UST_POOL, usdc_amount)

    ust_amount: uint256 = CurvePool(CURVE_UST_POOL).exchange_underlying(
        CURVE_USDC_INDEX,
        CURVE_UST_INDEX,
        usdc_amount,
        min_ust_amount
    )

    assert ust_amount >= min_ust_amount, "insuff. UST return"
    assert ERC20(UST_TOKEN).balanceOf(self) >= ust_amount

    # final overall check
    steth_usd_anchor_price: uint256 = self._get_steth_usd_anchor_price()
    min_usd_amount: uint256 = self._get_min_amount_out(
        steth_amount,
        steth_usd_anchor_price,
        self.max_steth_usd_price_difference_percent
    )
    assert ust_amount >= min_usd_amount, "insuff. overall UST"

    log SoldStethToUST(
        steth_amount,
        eth_amount,
        usdc_amount,
        ust_amount,
        steth_eth_anchor_price,
        eth_usdc_anchor_price,
        usdc_usd_anchor_price
    )

    return ust_amount
