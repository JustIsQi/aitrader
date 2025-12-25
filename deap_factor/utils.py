import copy


def convert_inverse_prim(prim, args):
    """
    Convert inverse prims according to:
    [Dd]iv(a,b) -> Mul[a, 1/b]
    [Ss]ub(a,b) -> Add[a, -b]
    We achieve this by overwriting the corresponding format method of the sub and div prim.
    """
    prim = copy.copy(prim)


    converter = {
        'Add': lambda *args_: "{}+{}".format(*args_),
        'Mul': lambda *args_: "{}*{}".format(*args_),
        'fsub': lambda *args_: "{}-{}".format(*args_),
        'fdiv': lambda *args_: "{}/{}".format(*args_),
        'fmul': lambda *args_: "{}*{}".format(*args_),
        'fadd': lambda *args_: "{}+{}".format(*args_),
        # 'fmax': lambda *args_: "max_({},{})".format(*args_),
        # 'fmin': lambda *args_: "min_({},{})".format(*args_),

        'isub': lambda *args_: "{}-{}".format(*args_),
        'idiv': lambda *args_: "{}/{}".format(*args_),
        'imul': lambda *args_: "{}*{}".format(*args_),
        'iadd': lambda *args_: "{}+{}".format(*args_),
        # 'imax': lambda *args_: "max_({},{})".format(*args_),
        # 'imin': lambda *args_: "min_({},{})".format(*args_),
    }

    prim_formatter = converter.get(prim.name, prim.format)

    return prim_formatter(*args)




def stringify_for_sympy(f):
    """Return the expression in a human readable string.
    """
    string = ""
    stack = []
    for node in f:
        stack.append((node, []))
        while len(stack[-1][1]) == stack[-1][0].arity:
            prim, args = stack.pop()
            string = convert_inverse_prim(prim, args)
            if len(stack) == 0:
                break  # If stack is empty, all nodes should have been seen
            stack[-1][1].append(string)
    # print(string)
    return string