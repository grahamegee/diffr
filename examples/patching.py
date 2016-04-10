from differ import diff, patch

a = [1, 2, 3]
b = [2, 1, 3, 4]
d = diff(a, b)
print(d)
should_be_b = patch(a, d)
print(should_be_b)
print(b == should_be_b)
a = {
    'first_name': 'John',
    'last_name': 'Smith',
    'age': 24
}
b = {
    'first_name': 'Jenny',
    'last_name': 'Smith',
    'age': 32
}
d = diff(a, b)
print(d)
should_be_b = patch(a, d)
print(should_be_b)
print(b == should_be_b)
