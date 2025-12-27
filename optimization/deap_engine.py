from deap import base, creator, gp


creator.create("FitnessMax", base.Fitness, weights=(1.0,))
def init_tool_box():

        # creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMax)

        from deap import base, creator, tools

        creator.create("Individual", gp.PrimitiveTree, fitness=creator.FitnessMax)

        toolbox = base.Toolbox()
        from deap_factor.init_pset import get_pset

        pset = get_pset()
        toolbox.register("expr", gp.genHalfAndHalf, pset=pset, min_=1, max_=5)
        toolbox.register("individual", tools.initIterate, creator.Individual, toolbox.expr)
        # print(toolbox.individual())
        toolbox.register("population", tools.initRepeat, list, toolbox.individual)

        toolbox.register("evaluate", print)  # 在map中一并做了

        toolbox.register("select", tools.selTournament, tournsize=3)  # 目标优化
        # toolbox.register("select", tools.selNSGA2)  # 多目标优化 FITNESS_WEIGHTS = (1.0, 1.0)
        toolbox.register("mate", gp.cxOnePoint)
        toolbox.register("expr_mut", gp.genFull, min_=0, max_=2)
        toolbox.register("mutate", gp.mutUniform, expr=toolbox.expr_mut, pset=pset)

        from deap_factor.backtest import backtester
        toolbox.register('map', backtester)

        import operator

        toolbox.decorate("mate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
        toolbox.decorate("mutate", gp.staticLimit(key=operator.attrgetter("height"), max_value=17))
        return toolbox

if __name__ == '__main__':
    from deap_factor import utils
    from deap import tools
    import numpy as np
    my_tool_box = init_tool_box()
    # 这里定义初始化的因子数，可以得行修改
    print('开始生成因子...')
    pop = my_tool_box.population(10)
    for p in pop:
            print(utils.stringify_for_sympy(p))

    hof = tools.HallOfFame(10)
    # 只统计一个指标更清晰
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    # 打补丁后，名人堂可以用nan了，如果全nan会报警
    stats.register("avg", np.nanmean, axis=0)
    stats.register("std", np.nanstd, axis=0)
    stats.register("min", np.nanmin, axis=0)
    stats.register("max", np.nanmax, axis=0)
    #print(stats)
    from deap_factor.deap_patch import *  # noqa
    population, logbook = eaMuPlusLambda(pop, my_tool_box,
                                         # 选多少个做为下一代，每次生成多少新个体
                                         mu=150, lambda_=100,
                                         # 交叉率、变异率，代数
                                         cxpb=0.5, mutpb=0.1, ngen=3,
                                         # 名人堂参数
                                         # alpha=0.05, beta=10, gamma=0.25, rho=0.9,
                                         stats=stats, halloffame=hof, verbose=True,
                                         # 早停
                                         early_stopping_rounds=5)