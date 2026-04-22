# 论文解析：2604.12197

- 标题: Emergence of Statistical Financial Factors by a Diffusion Process
- 作者: Jose Negrete, Jaime Joel Ramos
- 分类: `q-fin.CP`, `nlin.CD`
- 创建日期: 2026-04-14
- 更新日期: 2026-04-15
- ArXiv 摘要页: https://arxiv.org/abs/2604.12197
- PDF: https://arxiv.org/pdf/2604.12197.pdf

## 摘要

Factor models characterize the joint behavior of large sets of financial assets through a smaller number of underlying drivers. We develop a network-based framework in which factors emerge naturally from the structure of interactions among assets rather than being imposed statistically. The market is modeled as a system of coupled iterated maps, where assets' return depends on its own past returns and those of related assets. Effectively modeling the influence of irrational traders whose decisions are based on the past movements of a collection of stocks. The interaction structure between stock returns is defined by a coupling matrix derived from an orthogonal transformation of a Laplacian matrix that gradually links initially isolated clusters into a fully connected network. Within this structure, stable patterns of co-movement arise and can be interpreted as financial factors. The relationship between the initial clustering and the number of observed factors is consistent with a center manifold reduction. We identify an optimal regime in which assets' variance is effectively explained by the set of factors produced by the network. Our framework offers a structural perspective based on interaction-based factor formation and dimension reduction in financial markets.

## 研究要点

- 因子不一定是统计上先验给定，也可以从资产交互网络中自然涌现。
- 论文把市场建模为资产相互影响的耦合系统，强调交互结构决定共同波动。
- 网络簇结构与最终观测到的因子数量存在对应关系。

## A股映射

- 用60日收益相关矩阵构建股票网络。
- 用特征向量中心性度量股票处于核心共同因子中的程度。
- 将中心性作为选股主排序，再用短期动量做实盘化约束。
