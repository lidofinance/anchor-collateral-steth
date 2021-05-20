DEFAULT_EPSILON = 10

def equal_with_epsilon(balance1, balance2, epsilon=DEFAULT_EPSILON):
    return abs(balance1 - balance2) <= epsilon