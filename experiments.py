import string

from hive import types_match


class DataInfo:

    def __init__(self, data_type=(), interfaces=None):
        self.data_type = data_type
        if interfaces is None:
            interfaces = {}

        self.interfaces = interfaces

    def __repr__(self):
        return "DataInfo({}, {})".format(self.data_type, self.interfaces)


punctuation = set(string.punctuation)


def tokenise(data):
    data = data.replace(" ", "")

    tokens = []
    state = 'ready'

    in_progress = []

    i = 0
    while i < len(data):
        char = data[i]

        if state == 'ready':
            if char in punctuation:
                token = Token('symbol', char)
                tokens.append(token)
                i += 1

            elif char.isalpha():
                state = 'identifier'

            else:
                raise ValueError(char)

        elif state == 'identifier':
            create_token = True

            if char.isalpha():
                in_progress.append(char)
                i += 1

                # Only create token on last char
                create_token = i == len(data)

            if create_token:
                identifier = "".join(in_progress)
                token = Token('identifier', identifier)
                tokens.append(token)

                in_progress.clear()
                state = 'ready'

    return tokens


class Token:

    def __init__(self, type_, value):
        self.type = type_
        self.value = value

    def __repr__(self):
        return "Token({}, {})".format(self.type, self.value)


# Of AND or OR to combine typing
# Major minor? iterable AND int or iterable.int ?
# Interfaces order doesn't matter!
# define default interfaces (for types?)
# iterable, subscriptable, add, sub, mul, xor, hash

"str.identifier"
iterable_add_int = "@(iterable, add).int"
iterable_int = "@iterable.int"
iterable_of_int = "@iterable[int]"
iterable_of_iterable_ints = "@iterable[@iterable.number.int]"


class Interface:

    def __init__(self, name, argument=None):
        self.name = name
        self.argument = argument

    def __repr__(self):
        return "Interface({}, {})".format(self.name, self.argument)


class Parser:

    def __init___(self):
        self.interfaces = []
        self.data_type = None

    def parse_interface(self, tokens, i):
        token = tokens[i]
        i += 1

        assert token.type == "identifier"
        identifier = token.value

        # More tokens to process
        if i < len(tokens):
            following_token = tokens[i]

            if following_token.value == "[":
                i += 1

                parser = Parser()
                i, argument = parser.parse_tokens(tokens, i)
                i += 1
                return i, (identifier, argument)

        return i, (identifier, DataInfo())

    def parse_interfaces(self, tokens, i):
        token = tokens[i]
        interfaces = {}

        # Single interface
        if token.type == "identifier":
            i, (interface, argument) = self.parse_interface(tokens, i)
            interfaces[interface] = argument

        # Multiple interface
        else:
            assert token.value == "("
            i += 1
            while i < len(tokens):
                i, (interface, argument) = self.parse_interface(tokens, i)
                interfaces[interface] = argument

                token = tokens[i]
                assert token.type == "symbol"
                i += 1

                if token.value == ")":
                    break

                assert token.value == ","

        return i, interfaces

    def parse_tokens(self, tokens, i=0):
        first_token = tokens[i]

        parse_interfaces = first_token.value == '@'
        if parse_interfaces:
            i += 1

            i, interfaces = self.parse_interfaces(tokens, i)

        else:
            interfaces = {}

        data_type_elements = []
        for token in tokens[i:]:
            if token.type == "identifier":
                data_type_elements.append(token.value)

            elif token.value != ".":
                break

            i += 1

        data_type = tuple(data_type_elements)
        data_info = DataInfo(data_type, interfaces)

        return i, data_info


def data_match(a, b):
    if not types_match(a.data_type, b.data_type):
        return False

    a_interfaces = a.interfaces
    b_interfaces = b.interfaces

    common_interfaces = set(a_interfaces) & set(b_interfaces)
    if (len(common_interfaces) < len(a_interfaces)) or (len(common_interfaces) < len(b_interfaces)):
        return False

    for interface in common_interfaces:
        if not data_match(a_interfaces[interface], b_interfaces[interface]):
            return False

    return True
#
# for info in (iterable_add_int, iterable_int, iterable_of_int, iterable_of_iterable_ints):
#     parser = Parser()
#     print(info)
#     tokens = tokenise(info)
#     for token in tokens:
#         print(token)
#
#     i, data = parser.parse_tokens(tokens)
#     print(data, "\n")


obj = Parser().parse_tokens(tokenise("@iterable[int].list"))[1]
obj2 = Parser().parse_tokens(tokenise("@(iterable[int], add[list])"))[1]
print(data_match(obj, obj2))
print(obj2)
# TODO input needs to be satisfied by output, only (asymmetrical)