from diffr import diff


a = [0] * 5 + ['-' * 5 + 'a' + '-' * 5] + [0] * 5
b = [0] * 5 + ['-' * 5 + 'b' + '-' * 5] + [0] * 5
d = diff(a, b)
print('Print out the diff in full by default')
print(d)
print()
print('Reduce the context by formatting with context_limit = 3')
print('{:3c}'.format(d))
print()
print('Reduce the context further (context_limit = 1)')
print(format(d, '1c'))
