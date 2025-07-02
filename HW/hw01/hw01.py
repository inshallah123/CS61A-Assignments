from operator import add, sub

def square(x):
    return x * x


def a_plus_abs_b(a, b):
    """Return a+abs(b), but without calling abs.

    >>> a_plus_abs_b(2, 3)
    5
    >>> a_plus_abs_b(2, -3)
    5
    >>> a_plus_abs_b(-1, 4)
    3
    >>> a_plus_abs_b(-1, -4)
    3
    """
    if b < 0:
        f = sub
    else:
        f = add
    return f(a, b)

def a_plus_abs_b_syntax_check():
    """Check that you didn't change the return statement of a_plus_abs_b.

    >>> # You aren't expected to understand the code of this test.
    >>> import inspect, re
    >>> re.findall(r'^\s*(return .*)', inspect.getsource(a_plus_abs_b), re.M)
    ['return f(a, b)']
    """
    # You don't need to edit this function. It's just here to check your work.


def two_of_three(i, j, k):
    """Return m*m + n*n, where m and n are the two smallest members of the
    positive numbers i, j, and k.

    >>> two_of_three(1, 2, 3)
    5
    >>> two_of_three(5, 3, 1)
    10
    >>> two_of_three(10, 2, 8)
    68
    >>> two_of_three(5, 5, 5)
    50
    """
    return square(sorted([i, j, k])[0]) + square(sorted([i, j, k])[1])

def two_of_three_syntax_check():
    """Check that your two_of_three code consists of nothing but a return statement.

    >>> # You aren't expected to understand the code of this test.
    >>> import inspect, ast
    >>> [type(x).__name__ for x in ast.parse(inspect.getsource(two_of_three)).body[0].body]
    ['Expr', 'Return']
    """
    # You don't need to edit this function. It's just here to check your work.


def largest_factor(n):
    """Return the largest factor of n that is smaller than n.

    >>> largest_factor(15) # factors are 1, 3, 5
    5
    >>> largest_factor(80) # factors are 1, 2, 4, 5, 8, 10, 16, 20, 40
    40
    >>> largest_factor(13) # factor is 1 since 13 is prime
    1
    """
    "*** YOUR CODE HERE ***"
    factors = [x for x in range(1, n + 1) if n % x == 0 and x < n]
    return max(factors)


def hailstone(n):
    """Print the hailstone sequence(冰雹序列，Collatz序列） starting at n and return its
    length.
生成规则：
初始值：选择一个正整数 n 作为序列的起点。
递推规则：
如果当前数 n 是偶数，则下一个数为 n/2；
如果当前数 n 是奇数，则下一个数为 3n+1。
终止条件：当序列达到数字 1 时结束（因为之后会进入无限循环 1→4→2→1）。
    >>> a = hailstone(10)
    10
    5
    16
    8
    4
    2
    1
    >>> a
    7
    >>> b = hailstone(1)
    1
    >>> b
    1
    """
    "*** YOUR CODE HERE ***"
    loop_time = 0
    print(int(n))
    while n > 1:
        if n % 2 == 0:
            n = n // 2
            print(int(n))
            loop_time += 1
            continue
        else:
            n = 3 * n + 1
            print(int(n))
            loop_time += 1
            continue
    return loop_time + 1


