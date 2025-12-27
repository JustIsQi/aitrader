import pandas as pd
from deap import gp
from deap_factor.deap_patch import *
def dummy(*args):
    # 由于生成后的表达计算已经被map和evaluate接管，所以这里并没有用到，可随便定义
    return 1


class EXPR:
    pass


def add_operators_base(pset):
    """基础算子"""
    # 无法给一个算子定义多种类型，只好定义多个不同名算子，之后通过helper.py中的convert_inverse_prim修正
    pset.addPrimitive(dummy, [EXPR, EXPR], EXPR, name='fadd')
    pset.addPrimitive(dummy, [EXPR, EXPR], EXPR, name='fsub')
    pset.addPrimitive(dummy, [EXPR, EXPR], EXPR, name='fmul')
    pset.addPrimitive(dummy, [EXPR, EXPR], EXPR, name='fdiv')

    pset.addPrimitive(dummy, [EXPR, int], EXPR, name='iadd')
    pset.addPrimitive(dummy, [EXPR, int], EXPR, name='isub')
    pset.addPrimitive(dummy, [EXPR, int], EXPR, name='imul')
    pset.addPrimitive(dummy, [EXPR, int], EXPR, name='idiv')
    return pset


def _random_int_():
    import random
    return random.choice([5, 10, 20, 25,30, 40, 60, 120])


def add_ops(pset):
    from datafeed import factor_qlib
    from typing import get_type_hints
    for method_name in dir(factor_qlib):
        if not method_name.startswith('_'):
            method = getattr(factor_qlib, method_name)
            if callable(method):
                type_hints = get_type_hints(method)
                #print(method_name,type_hints)
                inputs = []
                for p_name,p_type in type_hints.items():

                    if p_type is pd.Series:
                        inputs.append(EXPR)
                    else:
                        inputs.append(int)
                #print(inputs)
                pset.addPrimitive(dummy, inputs, EXPR, name=method_name)



def get_pset():
    pset = gp.PrimitiveSetTyped("MAIN", [], EXPR)
    pset = add_operators_base(pset)
    add_ops(pset)


    pset.addEphemeralConstant('_random_int_', _random_int_, int)

    pset.addTerminal(1, EXPR, name='open')
    pset.addTerminal(1, EXPR, name='high')
    pset.addTerminal(1, EXPR, name='low')
    pset.addTerminal(1, EXPR, name='close')
    pset.addTerminal(1, EXPR, name='volume')

    return pset

if __name__ == '__main__':
    add_ops(None)