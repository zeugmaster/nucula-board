"""Small S-expression reader for checking KiCad libraries (Python stdlib only)."""
import json
import re


def parse(text):
    stack = [[]]
    for token in re.findall(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+', text):
        if token == '(':
            node = []
            stack[-1].append(node)
            stack.append(node)
        elif token == ')':
            stack.pop()
        else:
            stack[-1].append(token)
    assert len(stack) == 1 and len(stack[0]) == 1, 'Malformed S-expression'
    return stack[0][0]


def uq(value):
    return json.loads(value) if value.startswith('"') else value


def children(node, key):
    return [item for item in node if isinstance(item, list) and item[0] == key]


def child(node, key):
    return children(node, key)[0]


def dump(node, depth=0):
    """Write parsed tokens without altering quoted values."""
    if not isinstance(node, list):
        return node
    if not any(isinstance(x, list) for x in node):
        return '(' + ' '.join(node) + ')'
    text = '('
    for i, item in enumerate(node):
        text += ('\n' + '  ' * (depth + 1) if isinstance(item, list)
                 else (' ' if i else '')) + dump(item, depth + 1)
    return text + '\n' + '  ' * depth + ')'
