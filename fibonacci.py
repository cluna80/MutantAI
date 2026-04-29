def fibonacci(n):
    a, b = 0, 1
    result = []
    while a <= n:
        result.append(a)
        a, b = b, a + b
    return result

if __name__ == '__main__':
    print(fibonacci(100))
