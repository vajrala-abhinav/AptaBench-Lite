from itertools import permutations
import random
from aptabench_lite.resolver import maximize


def test_integer_assignment_against_bruteforce():
    rng=random.Random(18)
    for n in range(1,5):
        for _ in range(15):
            matrix=[[rng.randrange(-1,10)*10**25 for _ in range(n+2)] for _ in range(n)]
            actual=maximize(matrix)
            expected=max(sum(matrix[i][p[i]] for i in range(n)) for p in permutations(range(n+2),n))
            assert sum(matrix[i][actual[i]] for i in range(n))==expected
            assert len(set(actual))==n
