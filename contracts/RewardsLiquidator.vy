# @version 0.3.0
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
    def exchange(i: int128, j: int128, dx: uint256, min_dy: uint256) -> uint256: payable

interface CurveMetaPool:
    def exchange_underlying(i: int128, j: int128, dx: uint256, min_dy: uint256) -> uint256: nonpayable


event SoldStethToUST:
    steth_amount: uint256
    eth_amount: uint256
    usdc_amount: uint256
    ust_amount: uint256
    steth_eth_price: uint256
    eth_usdc_price: uint256
    usdc_ust_price: uint256

event AdminChanged:
    new_admin: address

event PriceDifferenceChanged:
    max_steth_eth_price_difference_percent: uint256
    max_eth_usdc_price_difference_percent: uint256
    max_usdc_ust_price_difference_percent: uint256
    max_steth_ust_price_difference_percent: uint256

event PoolsChanged:
    curve_steth_pool: address
    curve_ust_pool: address
    uniswap_router_v3: address
    uniswap_usdc_pool_fee: uint256
    curve_eth_index: int128
    curve_steth_index: int128
    curve_usdc_index: int128
    curve_ust_index: int128


UST_TOKEN: constant(address) = 0xa47c8bf37f92aBed4A126BDA807A7b7498661acD
UST_TOKEN_DECIMALS: constant(uint256) = 18
USDC_TOKEN: constant(address) = 0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48
USDC_TOKEN_DECIMALS: constant(uint256) = 6
STETH_TOKEN: constant(address) = 0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84
STETH_TOKEN_DECIMALS: constant(uint256) = 18
WETH_TOKEN: constant(address) = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2
WETH_TOKEN_DECIMALS: constant(uint256) = 18

CHAINLINK_STETH_ETH_FEED: constant(address) = 0x86392dC19c0b719886221c78AB11eb8Cf5c52812
CHAINLINK_UST_ETH_FEED: constant(address) = 0xa20623070413d42a5C01Db2c8111640DD7A5A03a
CHAINLINK_USDC_ETH_FEED: constant(address) = 0x986b5E1e1755e3C2440e960477f25201B0a8bbD4

# An address that is allowed to configure the liquidator settings.
admin: public(address)

# An address that is allowed to sell.
vault: public(address)

# Maximum difference (in percents multiplied by 10**18) between the resulting
# stETH/ETH price and the stETH/ETH anchor price obtained from the oracle.
max_steth_eth_price_difference_percent: public(uint256)

# Maximum difference (in percents multiplied by 10**18) between the resulting
# ETH/USDC price and the ETH/USDC anchor price obtained from the oracle.
max_eth_usdc_price_difference_percent: public(uint256)

# Maximum difference (in percents multiplied by 10**18) between the resulting
# USDC/UST price and the USDC/USD anchor price obtained from the oracle.
max_usdc_ust_price_difference_percent: public(uint256)

# Maximum difference (in percents multiplied by 10**18) between the resulting
# stETH/UST price and the stETH/USD anchor price obtained from the oracle.
max_steth_ust_price_difference_percent: public(uint256)

# Pools addresses, pools paramters, coin indeces inside pools
curve_steth_pool: public(address)
curve_ust_pool: public(address)
uniswap_router_v3: public(address)
uniswap_usdc_pool_fee: public(uint256)
curve_eth_index: public(int128)
curve_steth_index: public(int128)
curve_usdc_index: public(int128)
curve_ust_index: public(int128)


@external
def __init__(
    vault: address,
    admin: address,
    max_steth_eth_price_difference_percent: uint256,
    max_eth_usdc_price_difference_percent: uint256,
    max_usdc_ust_price_difference_percent: uint256,
    max_steth_ust_price_difference_percent: uint256
):
    assert ERC20Decimals(USDC_TOKEN).decimals() == USDC_TOKEN_DECIMALS
    assert ERC20Decimals(UST_TOKEN).decimals() == UST_TOKEN_DECIMALS
    assert ERC20Decimals(STETH_TOKEN).decimals() == STETH_TOKEN_DECIMALS

    self.vault = vault
    self.admin = admin
    log AdminChanged(self.admin)

    self.curve_steth_pool = 0xDC24316b9AE028F1497c275EB9192a3Ea0f67022
    self.curve_ust_pool = 0x890f4e345B1dAED0367A877a1612f86A1f86985f
    self.uniswap_router_v3 = 0xE592427A0AEce92De3Edee1F18E0157C05861564
    self.uniswap_usdc_pool_fee = 3000 # using pool with fee 0.3%
    self.curve_eth_index = 0
    self.curve_steth_index = 1
    self.curve_usdc_index = 2
    self.curve_ust_index = 0

    log PoolsChanged(
        self.curve_steth_pool, 
        self.curve_ust_pool,
        self.uniswap_router_v3,
        self.uniswap_usdc_pool_fee,
        self.curve_eth_index,
        self.curve_steth_index,
        self.curve_usdc_index,
        self.curve_ust_index
    )

    assert max_steth_eth_price_difference_percent <= 10**18, "invalid percentage"
    assert max_eth_usdc_price_difference_percent <= 10**18, "invalid percentage"
    assert max_usdc_ust_price_difference_percent <= 10**18, "invalid percentage"
    assert max_steth_ust_price_difference_percent <= 10**18, "invalid percentage"

    self.max_steth_eth_price_difference_percent = max_steth_eth_price_difference_percent
    self.max_eth_usdc_price_difference_percent = max_eth_usdc_price_difference_percent
    self.max_usdc_ust_price_difference_percent = max_usdc_ust_price_difference_percent
    self.max_steth_ust_price_difference_percent = max_steth_ust_price_difference_percent

    log PriceDifferenceChanged(
        self.max_steth_eth_price_difference_percent, 
        self.max_eth_usdc_price_difference_percent,
        self.max_usdc_ust_price_difference_percent,
        self.max_steth_ust_price_difference_percent
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
def set_pools(
    curve_steth_pool: address,
    curve_ust_pool: address,
    uniswap_router_v3: address,
    uniswap_usdc_pool_fee: uint256,
    curve_eth_index: int128,
    curve_steth_index: int128,
    curve_usdc_index: int128,
    curve_ust_index: int128
):
    assert msg.sender == self.admin
    assert curve_steth_pool != ZERO_ADDRESS, "invalid curve_steth_pool"
    assert curve_ust_pool != ZERO_ADDRESS, "invalid curve_ust_pool"
    assert uniswap_router_v3 != ZERO_ADDRESS, "invalid uniswap_router_v3"
    assert uniswap_usdc_pool_fee > 0, "invalid uniswap_usdc_pool_fee"

    self.curve_steth_pool = curve_steth_pool
    self.curve_ust_pool = curve_ust_pool
    self.uniswap_router_v3 = uniswap_router_v3
    self.uniswap_usdc_pool_fee = uniswap_usdc_pool_fee
    self.curve_eth_index = curve_eth_index
    self.curve_steth_index = curve_steth_index
    self.curve_usdc_index = curve_usdc_index
    self.curve_ust_index = curve_ust_index

    log PoolsChanged(
        self.curve_steth_pool, 
        self.curve_ust_pool,
        self.uniswap_router_v3,
        self.uniswap_usdc_pool_fee,
        self.curve_eth_index,
        self.curve_steth_index,
        self.curve_usdc_index,
        self.curve_ust_index
    )


@external
def configure(
    max_steth_eth_price_difference_percent: uint256,
    max_eth_usdc_price_difference_percent: uint256,
    max_usdc_ust_price_difference_percent: uint256,
    max_steth_ust_price_difference_percent: uint256
):
    assert msg.sender == self.admin
    assert max_steth_eth_price_difference_percent <= 10**18, "invalid percentage"
    assert max_eth_usdc_price_difference_percent <= 10**18, "invalid percentage"
    assert max_usdc_ust_price_difference_percent <= 10**18, "invalid percentage"
    assert max_steth_ust_price_difference_percent <= 10**18, "invalid percentage"

    self.max_steth_eth_price_difference_percent = max_steth_eth_price_difference_percent
    self.max_eth_usdc_price_difference_percent = max_eth_usdc_price_difference_percent
    self.max_usdc_ust_price_difference_percent = max_usdc_ust_price_difference_percent
    self.max_steth_ust_price_difference_percent = max_steth_ust_price_difference_percent

    log PriceDifferenceChanged(
        self.max_steth_eth_price_difference_percent, 
        self.max_eth_usdc_price_difference_percent,
        self.max_usdc_ust_price_difference_percent,
        self.max_steth_ust_price_difference_percent
    )


@internal
@view
def _get_chainlink_price(chainlink_price_feed: address, reverse: bool = False) -> uint256:
    price_decimals: uint256 = ChainlinkAggregatorV3Interface(chainlink_price_feed).decimals()
    assert 0 < price_decimals and price_decimals <= 18

    round_id: uint256 = 0
    answer: int256 = 0
    started_at: uint256 = 0
    updated_at: uint256 = 0
    answered_in_round: uint256 = 0

    (round_id, answer, started_at, updated_at, answered_in_round) = \
        ChainlinkAggregatorV3Interface(chainlink_price_feed).latestRoundData()

    assert updated_at != 0
    if reverse:
        return  (10 ** (18 + price_decimals)) / convert(answer, uint256)
    return convert(answer, uint256) * (10 ** (18 - price_decimals))


@internal
@view
def _get_chainlink_cross_price(priceA: uint256, priceB: uint256) -> uint256:
    return (priceA * priceB) / (10 ** 18)
    

@internal
def _uniswap_v3_sell_eth_to_usdc(
    eth_amount_in: uint256,
    usdc_amount_out_min: uint256,
    usdc_recipient: address
) -> uint256:

    result: Bytes[32] = raw_call(
        self.uniswap_router_v3,
        concat(
            method_id("exactInputSingle((address,address,uint24,address,uint256,uint256,uint256,uint160))"),
            convert(WETH_TOKEN, bytes32),
            convert(USDC_TOKEN, bytes32),
            convert(self.uniswap_usdc_pool_fee, bytes32), #pool fee
            convert(usdc_recipient, bytes32), #recipient
            convert(block.timestamp, bytes32), #deadline
            convert(eth_amount_in, bytes32),
            convert(usdc_amount_out_min, bytes32),
            convert(0, bytes32), #sqrtPriceLimitX96
        ),
        value=eth_amount_in,
        max_outsize=32
    )
    return convert(result, uint256)


@internal
@pure
def _get_min_amount_out(
    amount: uint256,
    price: uint256,
    max_diff_percent: uint256,
    decimal_token_in: uint256,
    decimal_token_out: uint256
) -> uint256:
    amount_out: uint256 = (amount * price) / (10 ** decimal_token_in) # = (amount * (10 ** (18 - decimal_token_in)) * price) / 10 ** 18
    min_mult: uint256 = 10**18 - max_diff_percent
    return (amount_out * min_mult) / (10 ** (36 - decimal_token_out)) # = ((amount_out * min_mult) / 10**18) / (10 ** (18 - decimal_token_out))

# 1) stETH -> ETH (Curve)
# 2) ETH -> USDC (Uniswap v3)
# 3) USDC -> UST (Curve)
@external
def liquidate(ust_recipient: address) -> uint256:
    assert msg.sender == self.vault, "unauthorized"

    steth_amount: uint256 = ERC20(STETH_TOKEN).balanceOf(self)
    assert steth_amount > 0, "zero stETH balance"

    # steth -> eth
    steth_eth_price: uint256 = self._get_chainlink_price(CHAINLINK_STETH_ETH_FEED, False)
    min_eth_amount: uint256 = self._get_min_amount_out(
        steth_amount,
        steth_eth_price,
        self.max_steth_eth_price_difference_percent,
        STETH_TOKEN_DECIMALS,
        WETH_TOKEN_DECIMALS
    )

    ERC20(STETH_TOKEN).approve(self.curve_steth_pool, steth_amount)

    eth_amount: uint256 = CurvePool(self.curve_steth_pool).exchange(
        self.curve_steth_index,
        self.curve_eth_index,
        steth_amount,
        min_eth_amount
    )
    assert eth_amount >= min_eth_amount, "insuff. ETH return"
    assert self.balance >= eth_amount, "ETH balance mismatch"

    # eth -> usdc
    eth_usdc_price: uint256 = self._get_chainlink_price(CHAINLINK_USDC_ETH_FEED, True)
    min_usdc_amount: uint256 = self._get_min_amount_out(
        eth_amount,
        eth_usdc_price,
        self.max_eth_usdc_price_difference_percent,
        WETH_TOKEN_DECIMALS,
        USDC_TOKEN_DECIMALS
    )

    usdc_amount: uint256 = self._uniswap_v3_sell_eth_to_usdc(
        eth_amount,
        min_usdc_amount,
        self
    )

    assert usdc_amount >= min_usdc_amount, "insuff. USDC return"
    assert ERC20(USDC_TOKEN).balanceOf(self) >= usdc_amount, "USDC balance mismatch"

    # usdc -> ust
    usdc_eth_price: uint256 = self._get_chainlink_price(CHAINLINK_USDC_ETH_FEED, False)
    eth_ust_price: uint256 = self._get_chainlink_price(CHAINLINK_UST_ETH_FEED, True)
    usdc_ust_price: uint256 = self._get_chainlink_cross_price(usdc_eth_price, eth_ust_price)
    min_ust_amount: uint256 = self._get_min_amount_out(
        usdc_amount,
        usdc_ust_price,
        self.max_usdc_ust_price_difference_percent,
        USDC_TOKEN_DECIMALS,
        UST_TOKEN_DECIMALS
    )

    ERC20(USDC_TOKEN).approve(self.curve_ust_pool, usdc_amount)

    ust_amount: uint256 = CurveMetaPool(self.curve_ust_pool).exchange_underlying(
        self.curve_usdc_index,
        self.curve_ust_index,
        usdc_amount,
        min_ust_amount
    )

    assert ust_amount >= min_ust_amount, "insuff. UST return"
    assert ERC20(UST_TOKEN).balanceOf(self) >= ust_amount, "UST balance mismatch"

    # final overall check
    steth_ust_price: uint256 = self._get_chainlink_cross_price(steth_eth_price, eth_ust_price)
    min_ust_amount = self._get_min_amount_out(
        steth_amount,
        steth_ust_price,
        self.max_steth_ust_price_difference_percent,
        STETH_TOKEN_DECIMALS,
        UST_TOKEN_DECIMALS
    )

    assert ust_amount >= min_ust_amount, "insuff. overall UST"
    assert ERC20(UST_TOKEN).balanceOf(self) >= ust_amount, "UST balance mismatch"

    ERC20(UST_TOKEN).transfer(ust_recipient, ust_amount)

    log SoldStethToUST(
        steth_amount,
        eth_amount,
        usdc_amount,
        ust_amount,
        steth_eth_price,
        eth_usdc_price,
        usdc_ust_price
    )

    return ust_amount
