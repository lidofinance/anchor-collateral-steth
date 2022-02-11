# @version 0.3.1

total_shares_burnt: public(uint256)

@external
@view
def getCoverSharesBurnt() -> uint256:
    return self.total_shares_burnt

@external
def increment_total_shares_burnt(inc: uint256):
    self.total_shares_burnt += inc
