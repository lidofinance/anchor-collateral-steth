# @version 0.2.12

total_shares_burnt: public(uint256)

@external
def increment_total_shares_burnt(inc: uint256):
    self.total_shares_burnt += inc
