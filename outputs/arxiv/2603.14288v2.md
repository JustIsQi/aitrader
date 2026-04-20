# Beyond Prompting: An Autonomous Framework for Systematic Factor Investing via Agentic AI

| 字段 | 内容 |
|------|------|
| ArXiv ID | 2603.14288v2 |
| 发布日期 | 2026-03-15 |
| 作者 | Allen Yikuan Huang, Zheqi Fan |
| 分类 | q-fin.PM, q-fin.GN, q-fin.PR |
| PDF | https://arxiv.org/pdf/2603.14288v2 |

## 摘要

This paper develops an autonomous framework for systematic factor investing via agentic AI. Rather than relying on sequential manual prompts, our approach operationalizes the model as a self-directed engine that endogenously formulates interpretable trading signals. To mitigate data snooping biases, this closed-loop system imposes strict empirical discipline through out-of-sample validation and economic rationale requirements. Applying this methodology to the U.S. equity market, we document that long-short portfolios formed on the simple linear combination of signals deliver an annualized Sharpe ratio of 3.11 and a return of 59.53%. Finally, our empirics demonstrate that self-evolving AI offers a scalable and interpretable paradigm.

---

## 正文

<!-- page 1 -->
Beyond Prompting: Autonomous Factor Investing via Agentic AI
Allen Yikuan Huang a,b,c, Zheqi Fan b,c,∗
a Guanghua School of Management, Peking University, Beijing, China
b Division of EMIA, Hong Kong University of Science and Technology, Hong Kong SAR
c Thrust of FinTech, Hong Kong University of Science and Technology, Guangzhou, China
Abstract
This paper develops an autonomous framework for systematic factor investing via agentic AI.
Rather than relying on sequential manual prompts, our approach operationalizes the model as
a self-directed engine that endogenously formulates interpretable trading signals. To mitigate
data snooping biases, this closed-loop system imposes strict empirical discipline through out-of-
sample validation and economic rationale requirements. Applying this methodology to the U.S.
equity market, we document that long-short portfolios formed on the simple linear combination
ofsignalsdeliveranannualizedSharperatioof2.75andareturnof54.81%. Finally,ourempirics
demonstrate that self-evolving AI offers a scalable and interpretable paradigm.
Keywords: Generative AI; Agentic AI; Large language models (LLMs); Factor investing; Au-
tonomous alpha generation
JEL Codes: G12; G13
Practical implications:
• Autonomous Alpha Generation: Introduces an Agentic AI framework that acts as a quant
researcher to iteratively discover economically interpretable factors.
• Overfitting Mitigation: Systematically combats data mining and p-hacking by enforcing
strict out-of-sample testing and requiring clear economic rationale.
• Robust Practical Returns: Delivers significant risk-adjusted performance that remains
economically meaningful net of realistic transaction costs and turnover constraints.
∗Corresponding author
Email addresses: yhuangfi@connect.ust.hk (Allen Yikuan Huang ),
zheqi.fan@connect.ust.hk (Zheqi Fan )
Project homepage: https://allenh16.github.io/agentic-factor-investing/
TheauthorsthankIvanBlanco(CUNEF),KaiqiHu(RutgersBusinessSchool),BolongWang(CITIC
Securities),YifanYe(BNBU),ChaoZhang(HKUSTGuangzhou),YiZhang(HKUSTGuangzhou),and
Yibin Zhang (Bosera Asset Management), and internal seminar participants at X Asset Management
for helpful discussions, comments, and support. These discussions, particularly those drawing upon
practical industry insights, were conducted solely for academic purposes; the views expressed are those
of the individuals and do not necessarily represent their employers. The authors also thank the editorial
teamsofQuantMLandLLMQuantfortheirinsightfulcoverageandsummaryofthisresearchacrosstheir
leading Chinese practitioner-oriented social media platforms, which helped facilitate broader academic
and industry exchange. Any remaining errors or oversights are the responsibility of the authors.
6202
rpA
6
]MP.nif-q[
2v88241.3062:viXra

<!-- page 2 -->
1. Introduction
Thelandscapeofquantitativeinvestmentisundergoingaprofoundtransformation,driven
by the rapid evolution of artificial intelligence (AI) and machine learning. Historically,
the discovery of systematic return predictors—often referred to as the “factor zoo”—has
relied heavily on human intuition, economic hypotheses, and labor-intensive manual test-
ing. While traditional machine learning models have significantly enhanced our ability to
process high-dimensional datasets and capture non-linear relationships, they remain fun-
damentally passive tools. They require researchers to manually engineer features, define
explicit rules, and continuously prompt the models to generate insights. This human-
dependent paradigm not only creates a severe bottleneck in research efficiency but also
structurally exacerbates the risks of data mining and backtest overfitting.
To overcome these limitations, this paper introduces a novel framework that leverages
the paradigm shift from Traditional AI to Agentic AI within the context of quantitative
portfolio management. As illustrated in Exhibit 1, traditional AI systems function pri-
marily as passive analytical engines. They excel at pattern recognition, prediction, and
classification within structured datasets, but their utility is strictly bounded by human
prompts and predefined rules. In contrast, Agentic AI represents a leap toward au-
tonomous, goal-driven systems. Rather than merely answering queries, an Agentic AI
system perceives its environment (e.g., market dynamics), engages in multi-step reason-
ing, executes actions, and continuously learns from the outcomes of its decisions with
minimal human intervention.
We apply this autonomous agentic framework to the complex domain of alpha gener-
ation and factor mining. In our proposed system, the Agentic AI acts as an autonomous
quantitative researcher. Given a high-level objective—such as maximizing risk-adjusted
returns while strictly controlling for turnover and transaction costs—the agent indepen-
dently navigates a vast hypothesis space. It formulates novel mathematical expressions
for alpha factors using symbolic regression, tests them against historical market data,
assesses their economic rationale, and dynamically updates its internal memory based on
empirical feedback.
2

<!-- page 3 -->
Exhibit 1: Core Capabilities Comparison: Traditional vs. Agentic AI
ThisfigureillustratesthetransitionfrompassiveAIsystems, whichrelyonhumanpromptsandexplicit
rules,toautonomousagenticsystems. WhiletraditionalAIfocusesonpatternrecognitionandprediction
within structured datasets, agentic AI is characterized by its ability to perceive environments, reason,
execute actions, and learn from outcomes to achieve defined goals independently.
This transition from a “prompt-driven” to an “autonomous-agent” workflow offers
profound advantages for portfolio managers. First, it systematically mitigates human
behavioral biases and the pervasive issue of p-hacking. The agent evaluates factors based
on rigorous, out-of-sample statistical properties and structural robustness rather than
mere narrative appeal. Second, to translate these machine-generated signals into a co-
hesive, investable portfolio, our framework integrates advanced non-linear aggregation
techniques (e.g., LightGBM). This two-stage approach—autonomous signal discovery fol-
lowed by non-linear synthesis—ensures that the final portfolio captures complex factor
interactions while remaining practically executable.
In this paper, we demonstrate the empirical efficacy of the Agentic AI framework
using extensive historical market data. We show that the autonomously generated factor
portfolios yield highly significant risk-adjusted returns (alpha) that cannot be explained
by traditional asset pricing models. Crucially for practitioners, we rigorously evaluate
the strategy’s out-of-sample performance net of realistic transaction costs, market mi-
crostructure impacts, and turnover constraints. Our findings suggest that Agentic AI
is not merely a theoretical computer science concept, but a transformative, scalable en-
3

<!-- page 4 -->
gine for modern quantitative asset management—one capable of discovering resilient,
investable sources of alpha that traditional human-led research might overlook.
We begin our empirical evaluation by isolating the performance of individual agent-
generated signals. Decile portfolio sorts reveal that the top AI-discovered factors generate
statistically significant and economically meaningful long-short return spreads. Crucially,
these signals exhibit broadly monotonic rank ordering for several factors and deliver pos-
itive risk-adjusted returns for the stronger signals against standard asset pricing models
(e.g., the Fama-French factors). This confirms that the agent does not merely repack-
age known risk premia, but autonomously discovers genuine, standalone alpha from raw
market data.
Because individual signals often capture distinct, complementary dimensions of mar-
ket inefficiencies, we next evaluate their efficacy within a cohesive multi-factor portfolio.
To aggregate the discovered signals, we evaluate both a transparent linear combination
and a nonlinear LightGBM integrator. The linear specification serves as the main bench-
mark because it is simple, interpretable, and easy to audit, while LightGBM is used as a
complementary specification to capture interaction effects and conditional nonlinearities.
This design allows us to separate the economic value of the discovered factors from the
incremental contribution of model flexibility. The resulting composite strategy delivers
encouraging out-of-sample performance. More importantly for institutional practition-
ers, this outperformance retains substantial performance net of transaction costs, market
impact, and strict turnover constraints, proving the strategy’s viability for real-world
capital deployment.
A pervasive challenge in modern quantitative finance—particularly within automated
machine learning—is the acute risk of backtest overfitting and the proliferation of the
“factor zoo.” To directly address this, we subject our framework to stringent tests for
false discoveries. By applying multiple hypothesis testing adjustments and evaluating
out-of-sample signal decay, we demonstrate that the Agentic AI systematically resists
p-hacking. The agent’s requirement to articulate economic rationale, combined with
its dynamic memory updates, enforces a strict research discipline. This ensures that
4

<!-- page 5 -->
the generated alphas are rooted in persistent structural market dynamics rather than
spurious data mining.
Finally, wesubjectourfindingstoanextensivebatteryofrobustnesscheckstoconfirm
their reliability across varying market environments. The Agentic AI-driven portfolios
maintain consistent profitability across distinct market regimes, demonstrating resilience
during periods of elevated volatility and macroeconomic stress. Furthermore, the per-
formance holds firm across alternative asset universes, extended holding periods, and
varied hyperparameter specifications. This comprehensive validation provides institu-
tional investors with confidence that the autonomous alpha generation is structurally
sound, regime-resilient, and not an artifact of sample-specific curve fitting.
Ultimately, our core contribution extends beyond merely deploying AI for empiri-
cal factor mining. We propose an auditable and economically constrained paradigm for
automated investment research. This framework directly addresses two prominent con-
cerns in modern empirical finance: the proliferation of spurious signals in the “factor zoo”
(Cochrane, 2011; Harvey et al., 2016) and the opacity of black-box machine learning mod-
els. By enforcing economic logic at the generation stage and maintaining transparent,
human-readable audit trails, our agentic approach bridges the gap between unconstrained
computational power and rigorous financial intuition.
The remainder of this paper is organized as follows. Section 2 reviews the related lit-
erature on financial factor models, machine learning in asset pricing, and the application
of large language models in finance. Section 3 details the methodology of our Agentic AI
framework, outlining the closed-loop workflow and evaluation protocols for autonomous
factor generation. Section 4 describes the data, sample construction, and the predictor
set. Section 5 presents the core empirical results, evaluating the performance of both
single-factor portfolios and their multivariate combinations. Section 6 addresses data-
mining concerns by examining the economic rationale, statistical hurdles, and structural
anatomy of the agent-generated factors. Section 7 provides extensive robustness tests,
including longer-horizon predictability, transaction costs, turnover analysis, and a com-
parison against traditional AI frameworks. Finally, Section 8 concludes the paper.
5

<!-- page 6 -->
2. Related literature
This paper contributes to the vast literature by situating itself at the nexus of three
primary research streams: the traditional search for empirical anomalies and techni-
cal signals, the application of machine learning in cross-sectional asset pricing, and the
emerging frontier of Large Language Models (LLMs) and agentic AI in financial research.
By synthesizing these domains, we move beyond static factor discovery toward an au-
tonomous,closed-loopresearchenginethatbridgesthegapbetweenhuman-ledhypothesis
formulation and automated empirical validation.
2.1. Financial Factor Models and Technical Signals
The quest to explain the cross-section of expected returns began with the Capital Asset
Pricing Model (CAPM, Sharpe (1964)) and evolved into the multi-factor frameworks of
Fama and French (1993, 2015) and Carhart (1997). While fundamental accounting-based
factors dominated early research, a parallel and robust literature explored the predictive
power of price-based anomalies and market microstructure signals. Brock et al. (1992)
and Lo et al. (2000) provided foundational evidence that technical analysis, such as mov-
ing average rules and chart patterns, possesses significant predictive power that cannot be
fully explained by random walk hypotheses. Building on this, Han et al. (2013) demon-
stratedthattechnicalsignalsareparticularlyprofitableinportfolioscharacterizedbyhigh
volatility and high information uncertainty, suggesting that price-volume data captures
investor overreaction or underreaction to news. Han et al. (2016) further unified these in-
sights by constructing a “trend factor” that captures short-, intermediate-, and long-term
price signals, justifying its existence through a general equilibrium model where investors
have heterogeneous beliefs. Recent evidence further extends these findings, showing that
technical signals serve as a powerful sentiment barometer (Ding et al., 2023), capture
cross-stock predictability (Chen and Fan, 2026), predict returns via moving average devi-
ations (Ko et al., 2025), and even outperform traditional characteristics in the corporate
bond market (Chin et al., 2025). Collectively, these advancements reinforce the growing
synergy between academic research and the implementation of systematic, rules-based in-
vestmentstrategiesinpractice(Giamouridis,2017). Despitetheirempiricalsuccess, these
6

<!-- page 7 -->
traditional models rely heavily on human-defined rules and static factor constructions.
Such manual heuristics are increasingly limited by the “Factor Zoo” problem (Cochrane,
2011), where the sheer dimensionality of potential price-volume combinations exceeds
human cognitive capacity and fails to adapt to rapidly evolving market environments.
Relative to this strand of literature, our paper moves beyond manually defined or
theoretically-derived static factors. We establish an autonomous agentic loop that dis-
covers, tests, and refines factor hypotheses dynamically. By focusing on raw price and
volume data, our framework allows for the emergence of complex, non-linear technical
signals that are not pre-constrained by traditional linear factor theory.
2.2. Machine Learning in Asset Pricing
The transition from linear shrinkage models to machine learning (ML) has fundamentally
reshaped the landscape of empirical asset pricing3. This evolution mirrors the shift in
industry practice toward systematic, data-driven investment frameworks that leverage
ML to integrate diverse predictive signals (Giamouridis, 2017).4 Gu et al. (2020) pro-
vided a landmark comparison, showing that deep neural networks and gradient-boosted
trees significantly outperform traditional OLS regressions by capturing latent non-linear
risk exposures and high-dimensional interactions. Further innovations, such as the In-
strumented Principal Component Analysis (IPCA) by Kelly et al. (2019), allowed latent
factors to depend on observable firm characteristics in a time-varying manner, which
offers a more dynamic view of risk premia.
However, the application of ML in asset pricing is not without significant challenges.
As noted by Avramov et al. (2023), many ML models are highly susceptible to overfitting
in the presence of low signal-to-noise ratios and often lack economic interpretability,
functioning as black boxes that offer little insight into the underlying economic drivers.
3We refer the readers to Giglio et al. (2022); Kelly and Xiu (2023) for comprehensive surveys that
synthesize the recent advancements and methodological shifts in this strand of literature.
4Cerniglia and Fabozzi (2020) emphasize that this shift does not create a conflict with traditional
econometrics,butratherprovidesacomplementarytoolkitforintegratingfinancialtheorywithcomputa-
tionalinnovation. Foracomprehensivetreatmentofengineeringprotocolsandpracticalimplementation
challenges in financial machine learning that complements the broader literature, see López de Prado
(2018).
7

<!-- page 8 -->
Moreover, the iron law of active management, involving transaction costs and capacity
constraints, often erodes the gains from high-frequency ML strategies, as documented
by Novy-Marx and Velikov (2016). A recurring limitation in this literature, echoing the
factor zoo problem, is that the information set for feature engineering is still largely pre-
selectedbyhumans. WhiletheMLmodeloptimizestheweights,thefunctionalformofthe
features remains fixed. Early attempts to bypass this human constraint utilized genetic
programming to search for optimal trading rules in a non-differentiable functional space
(Neely et al., 1997). Recent evidence from Brogaard and Zareei (2023) further suggests
that such evolutionary algorithms can outperform strict loss-minimization ML by directly
optimizing economic objectives and maintaining flexibility in complex search spaces.5
Our paper contributes to this field by reframing factor discovery as an automated
machine learning (AutoML) and symbolic regression problem. While sharing the goal
of exploring functional spaces with genetic programming, our approach leverages the
semantic reasoning of large language models to overcome the search efficiency and inter-
pretability limits often associated with traditional evolutionary heuristics. This generally
aligns with the broader industry trend of integrating AI foundation models into asset
management (Fabozzi and López de Prado, 2025). We categorize our approach as a
next-generation ML framework where the learner is an LLM-based agent that optimizes
over the space of mathematical functional forms. This addresses the black-box concern
by producing explicit, interpretable factor formulas while subjecting them to transpar-
ent selection gates and explicit anti-overfitting constraints through an iterative empirical
feedback loop.
2.3. Large Language Models and Agentic AI in Finance
The integration of Natural Language Processing (NLP) in finance has progressed from
simple dictionary-based sentiment analysis (Tetlock, 2007; Loughran and McDonald,
2011) to the sophisticated reasoning capabilities of Large Language Models (LLMs).
Lopez-Lira and Tang (2023) demonstrated that ChatGPT can predict stock returns by
5Alternatively, neural networks can accelerate structural estimation of derivatives pricing models by
leveraging their universal approximation properties (Ye et al., 2025; Fan et al., 2025, 2026).
8

<!-- page 9 -->
analyzingnewsheadlines, significantlyoutperformingtraditionalsentimentscores. Build-
ing on this, Chen et al. (2022) demonstrate that high-dimensional embeddings extracted
from financial news by LLMs (such as ChatGPT and LLaMA) capture deep semantic in-
formation that substantially improves cross-sectional return predictability across global
markets. This predictive capacity is further refined by Chen et al. (2025), who provide
a comparative analysis of ChatGPT and DeepSeek, noting that ChatGPT’s extensive
training allows for more effective extraction of macro-level signals from English financial
news.
Beyond textual analysis, recent studies have begun to use LLM architectures to en-
code structural financial data. Chai et al. (2025) introduce Risk Premia BERT (RP-
BERT), which reframes the market cross-section as characteristic-ordered sequences to
learn context-dependent firm representations. To ensure the empirical validity of such
models, He et al. (2025) develop ChronoBERT, emphasizing chronological consistency to
mitigate lookahead bias and training leakage, which are critical for credible backtesting in
financial domains. This creative and inferential capacity was further exploited by Cheng
and Tang (2024), who showed that GPT-4 can autonomously generate high-return fac-
torsthroughknowledgeinference. Thismethodologywasextendedtospecializedmarkets,
such as the Chinese futures market (Cheng et al., 2026), proving the cross-asset appli-
cability of LLM-generated insights. For a comprehensive review of LLM applications in
finance, see Kong et al. (2024a,b)6. Most recently, Chen and Pu (2026) introduced a fully
agentic nowcasting framework that utilizes real-time web search to evaluate stock attrac-
tiveness. From an institutional perspective, Chen (2025) examines how agentic AI can
redefine the operating models of asset management through autonomous data analysis
and investment decision-making. However, the transition to fully autonomous AI agents
introduces new challenges. As documented by Xu et al. (2025), AI agents can mislead
investors through a reliance on outdated training data or web-searching bias, highlighting
the reliability risks in automated investment advice.
6Their survey papers categorize the literature into several key domains, including linguistic tasks,
sentiment analysis, financial time series, financial reasoning, and agent-based modeling.
9

<!-- page 10 -->
Relative to these studies, our paper advances from treating AI as a one-off factor gen-
erator or nowcaster toward a fully operationalized, closed-loop research engine. Unlike
existing frameworks that produce static outputs, our agentic system autonomously pro-
poses construction logic, executes code for backtesting, and adaptively refines its search
space based on empirical performance. By automating this iterative cycle of hypothesis
formulation, code execution, and empirical validation, we transform the role of AI from
a passive assistant into an autonomous researcher. This empirical grounding directly
mitigates the aforementioned reliability risks by ensuring that all generated insights are
strictly validated against historical market data. We thus create an extensible, logically
transparent, and empirically accountable factor library. To the best of our knowledge,
this is the first study, at least in the finance literature, to apply agentic AI to factor
investing.
3. Methodology: Agentic AI for Factor Generation
This section describes the methodological framework for systematic factor discovery. The
process integrates hypothesis generation with empirical validation through an iterative
research cycle. By imposing a fixed set of functional primitives and standardized evalua-
tion protocols, the framework maintains statistical discipline and ensures reproducibility.
This structure formalizes the search for asset pricing signals into an auditable sequence
whereeverycandidatefollowsaconsistentpathfrominitialspecificationtofinalselection.
3.1. System Design and Closed-Loop Workflow
We design the agent as an autonomous research system for systematic factor investing,
rather than as a one-shot language interface. The key design goal is to convert factor
discovery into a reproducible closed loop with stable rules. In each round, the system
generateshypotheses,computesfactorvalues,evaluatescandidatesunderafixedprotocol,
applies promotion gates, and updates the next search policy using accumulated evidence.
Thisclosed-loopstructureisimportantbecauseitseparatesautonomousexplorationfrom
ad hoc discretion: the agent can search broadly, but it must pass through the same
measurement and selection mechanism in every round. Formally, we define the discovery
10

<!-- page 11 -->
cycle at iteration k as a sequence of functional mappings:
C : H − G − e → n F − E − v → al M − G − a → te D (3.1)
k k k k k
where H represents the set of hypotheses, F the generated factor candidates, M the
k k k
performance metrics, and D the final promotion decisions. This formalization ensures
k
that every factor follows an identical, auditable path from conception to selection.
Two principles govern the workflow. First, constrained autonomy: the agent is free
to propose new ideas only within explicit scientific constraints, including a fixed vari-
able universe, bounded expression complexity, and strict no-look-ahead rules. Second,
evidence accumulation: every round leaves a structured trace, and future proposals are
conditioned on past outcomes rather than prompt-level intuition. Together, these prin-
ciples make the process scalable without giving up empirical discipline. In contrast to
conventional prompting pipelines, where the model outputs a static list of factors once,
our system learns through repeated interaction with objective performance feedback.
3.2. Agent Architecture and Functional Modules
The architecture contains five operational modules that jointly implement the loop. The
first module is a constrained hypothesis generator. It builds candidate factors from in-
terpretable primitives (such as return dynamics, price-relative transforms, volume and
liquidity information, and volatility states) under a predefined factor grammar. Specifi-
cally, a candidate factor f for asset i at time t is defined as a symbolic composition:
i,t
f = G(X ,X ,...,X ;O) (3.2)
i,t i,t i,t−1 i,t−k
where X denotes the vector of raw primitives (e.g., closing price, trading volume) and
i,t
O is the set of predefined operators (e.g., moving averages, or other technical indicators).
Operatorchoicesareintentionallytransparent, andexpressiondepthisbounded, sofactor
definitions remain readable and auditable.
The second module is a deterministic execution layer that maps each recipe to a
panel-consistent factor series. Cross-sectional transformations are applied within each
11

<!-- page 12 -->
date, while time-series transformations are applied within each asset history. This strict
separation between language-based proposal and code-based computation prevents hid-
den numerical drift and guarantees reproducibility under identical inputs. The third
module is a unified evaluator, which computes a common metric set for every candidate;
no factor receives customized scoring logic.
The fourth module is a transparent gatekeeper that converts evaluation outputs into
explicit decisions: promote, hold for review, or retire. This avoids unbounded candidate
expansion and reallocates research capacity toward empirically promising regions. The
fifth module is memory and policy update. It reads structured logs from prior rounds and
generates the next candidate set with a balance between exploitation (local variants of
survivors) and exploration (new hypotheses from different signal families). This memory-
guided diversification is central to reducing search myopia and mitigating factor crowding
inside a narrow subspace.
The complete operational flow of this closed-loop discovery is formally summarized in
Algorithm 1. The specific statistical metrics used in Step 3 and the gatekeeping logic in
Step 4 are further detailed in subsequent sections.
3.3. Evaluation and Selection Protocol
Our evaluation protocol is pre-committed before iterative search begins. We use strict
time-based separation between in-sample screening and out-of-sample validation, and
only in-sample results are allowed to influence promotion decisions. This temporal dis-
cipline ensures that policy updates are based on historically available information and
prevents contamination from future returns. Because the same protocol is reused across
rounds, gains in performance can robustly attributed to the superiority of the generated
hypotheses rather than data-snooping via dynamic evaluation rules.
To further control data leakage, we impose information-availability constraints at
both the feature and decision layers. At the feature layer, all candidate factors are con-
structed from contemporaneously observable or lagged inputs only; no forward return,
future window statistic, or post-date transformation is allowed in the factor grammar.
Cross-sectional preprocessing (such as ranking, z-scoring, and winsorization) is performed
12

<!-- page 13 -->
Algorithm 1 Agentic Closed-Loop Factor Discovery
Input: Raw primitives X, operator set O, factor grammar G, evaluation thresholds Θ =
{τ ,τ ,τ }, and in-sample window T .
sig econ fail IS
Output: Promoted Alpha Library L .
final
1: Initialization:
2: L ←∅
final
3: S ←Prior research heuristics and financial intuitions
0
4: for k =1 to K do
5: Step 1: Alpha Hypothesis Synthesis
6: Agent generates candidate factors F ={f ,...,f } via G based on state S
k 1 n k−1
7: f =G(X ;O) ▷ Symbolic formulation of trading signals
i,t i,t...t−k
8: Step 2: Factor Construction & Data Alignment
9: for each f ∈F do
k
10: Compute raw signal values f for universe N over T
i,t IS
11: f˜ ←Z-score(winsorize(f )) ▷ Cross-sectional normalization
i,t i,t
12: end for
13: Step 3: Statistical Backtesting & Metric Estimation ▷ Detailed in subsection 3.3
14: for each f ∈F do
k
15: Estimate Information Coefficient t and Long-Short Sharpe Ratio SR
IC LS
16: m ←[t ,SR ,...]⊤ ▷ Performance vector
f IC LS
17: end for
18: Step 4: Alpha Selection & Quality Control
19: for each f ∈F do
k
20: if t ≥τ and SR ≥τ then
IC sig LS econ
21: D(f)←Promote to Library; L ←L ∪{f}
final final
22: else if t <τ then
IC fail
23: D(f)←Redundant/Discard
24: else
25: D(f)←Re-evaluate/Hold
26: end if
27: end for
28: Step 5: Research Heuristic Evolution ▷ Detailed in subsection 3.4
29: E ←{m |f ∈F }; L ←{(f,D(f))|f ∈F }
k f k k k
30: S ←LLM(S ,E ,L ) ▷ Update search policy via reflection
k k−1 k k
31: end for
32: return L
final
13

<!-- page 14 -->
date by date7, so each day is transformed using only same-day cross-sectional informa-
tion rather than full-sample moments. Time-series operators (such as lags and rolling
moments) are applied within each asset history using historical observations up to that
date, preventing accidental look-ahead through panel-level operations. To formalize the
no-look-ahead constraint, we define the information set F available at time t. Any can-
t
didate factor f must be measurable with respect to this filtration:
i,t
f ∈ F = σ({X } ) (3.4)
i,t t j,s j∈N,s≤t
where N is the universe of assets and σ(·) denotes the σ-algebra generated by historical
observations. This ensures that the factor value at t is strictly a function of the past and
present, with no dependency on any s > t.
At the decision layer, leakage control is enforced by design: promotion gates are
computed exclusively on the in-sample segment, and out-of-sample outcomes are never
used to revise thresholds, re-rank candidates, or update the next-round search policy.
This separation is critical in an autonomous loop, where repeated iteration can otherwise
create implicit test-set feedback. In our workflow, out-of-sample data are used only for
final validation and reporting after candidate selection has been fixed. The separation
between in-sample (IS) and out-of-sample (OOS) periods is defined by the set of dates
T = T ∪T , where max(T ) < min(T ). The promotion decision D is a mapping
IS OOS IS OOS
that depends only on the IS history:
D(f) = Ψ({f ,R } ) (3.5)
i,t i,t+1 t∈TIS
where Ψ represents the gatekeeping logic. Thus, the OOS performance {f ,R }
i,t i,t+1 t∈TOOS
7Toensurethecomparabilityoffactorsacrossdifferenttimeperiods,weapplyacross-sectionalZ-score
transformation to the raw factor values:
winsorize(f )−µ
f˜ = i,t t (3.3)
i,t σ
t
where µ and σ are the cross-sectional mean and standard deviation of the factor values at time t,
t t
respectively. The winsorization process caps extreme outliers at the 1st and 99th percentiles to ensure
the robustness of the subsequent statistical estimations.
14

<!-- page 15 -->
remains a “blind” test set that does not enter the mapping Ψ, thereby preventing the
implicit overfitting that often plagues iterative search processes.
Statistical evaluation is anchored by daily cross-sectional rank IC and its associated
t-statistic. Rank IC is preferred as the primary statistical criterion because it directly
captures ordering ability and is less sensitive to scaling artifacts. The daily rank IC
is computed as the Spearman correlation between the factor scores and the subsequent
forward returns:
IC = Corr(rank(f ),rank(R )) (3.6)
t i,t i,t+1
where R represents the cross-section of asset returns in the next period. The system
i,t+1
then aggregates these into a t-statistic,
¯
IC
t = √ (3.7)
IC
σ / T
IC
to ensure statistical significance. Economic evaluation is conducted through sorted-
portfolio tests. On each date, assets are sorted by factor score into quantiles; we compute
quantile returns and a long-short spread (top minus bottom quantile) as the tradable
representation of each signal. The return of the long-short portfolio R is defined as
LS,t
the difference between the mean returns of the top and bottom quantiles:
1 (cid:88) 1 (cid:88)
R = R − R (3.8)
LS,t i,t i,t
|Q | |Q |
top bottom
i∈Qtop i∈Q
bottom
where Q and Q represent the sets of assets in the highest and lowest factor score
top bottom
quantiles, respectively. This spread serves as the basis for calculating the annualized
Sharpe ratio8 and drawdown metrics. From these return series, we report annualized
returnandSharperatio, andwealsoinspectfullquantileprofilestodetectnon-monotonic
8TheannualizedSharperatioofthelong-shortstrategyisthenderivedfromthedailyspreadreturns:
√ E[R ]
SR = 252· LS,t (3.9)
LS Std(R )
LS,t
whereE[R ]andStd(R )representthesamplemeanandstandarddeviationofthedailylong-short
LS,t LS,t
returns, respectively.
15

<!-- page 16 -->
patterns.
Selection is rule-based rather than discretionary. A candidate is promoted only if it
satisfies minimum statistical thresholds under the fixed protocol. Formally, the gatekeep-
ing decision D for a candidate factor f is determined by a set of pre-defined thresholds
Θ = {τ ,τ ,τ }:
sig econ fail

    Promote if t IC ≥ τ sig and SR LS ≥ τ econ



D(f) = Retire if t < τ (3.10)
IC fail




 Hold otherwise

where τ , τ , and τ denote the thresholds for statistical significance, economic
sig econ fail
viability, and outright failure, respectively. This formalization ensures that only factors
exhibiting both robust predictive power and practical profitability enter the final library,
while borderline cases are retained for further scrutiny. Borderline cases are flagged for
targeted robustness checks, and clear failures are retired with explicit annotations. This
gatekeeping process serves as the control layer of autonomous discovery: it limits false
positives, improves computational efficiency, and creates an auditable rationale for every
selection decision.
3.4. Iterative Learning, Governance, and Extensibility
At the end of each round, the system writes a structured experiment record containing
candidate definitions, metric outputs, gate outcomes, and next-step actions. This record
is not only a logging artifact but also the state representation of the agent. The evolution
of the search policy can be formalized as a state-space update:
S = LLM(S ,E ,L ) (3.11)
t+1 t t t
where S is the current knowledge state, E represents the empirical feedback from the
t t
evaluator, and L is the structured log of failed and successful hypotheses. This ensures
t
that the next generation of factors is conditioned on the cumulative evidence rather than
16

<!-- page 17 -->
independent random draws. The next policy update uses this state to avoid redundant
trials, identify successful operator-variable patterns, and deliberately propose diverse al-
ternatives when the current frontier becomes crowded. As a result, the search process
behaves as sequential evidence-based learning rather than repeated random generation.
This governance layer also supports replication and post-hoc diagnostics. Because
each round is fully documented, researchers can reconstruct how a factor entered the
library, which tests it passed, and why competing candidates were rejected. Such trace-
ability is essential for empirical finance applications where model risk and selection bias
must be explicitly managed. Finally, the architecture is modular by design: new opera-
tors, stricter gate criteria, additional risk controls, or richer transaction-cost models can
be integrated without changing the core loop. This modularity allows the framework to
adapt across market regimes while retaining methodological continuity.
Exhibit 2: The Workflow of Agentic AI in Factor Generation
This figure illustrates an Agentic AI framework for automated factor generation. The pipeline processes
rawdataintostandardizedpanels, utilizesanautonomousagentwithamemory-updatelooptodiscover
validfactors,andappliesmachinelearningmodelstotheresultingfactorlibrarytoevaluateout-of-sample
(OOS) performance.
4. Data and Factor Overview
4.1. Source Data and Sample Construction
Our raw equity data are daily stock-level records from the Center for Research in Security
Prices, covering January 2004 through December 2024. We construct a unified stock-date
17

<!-- page 18 -->
panel through a deterministic preprocessing workflow that standardizes identifiers, aligns
trading dates, and enforces a consistent structure for downstream factor construction and
portfolio evaluation.
ThebaselinesampledesignfollowsstandardempiricalscreeningrulesforU.S.common
equities. Following standard data preprocessing conventions in the literature (e.g., Gu
et al. (2020)), we restrict our universe to common stocks listed on the NYSE, AMEX,
and NASDAQ. To mitigate the influence of microcap anomalies and stale-price effects,
we further impose a minimum price filter of 5 USD. In addition, we require at least
252 observations per stock to preserve stability for rolling transformations. The target
return is winsorized cross-sectionally at the 1st and 99th percentiles by date before model
estimation.
Exhibit 3: Sample Construction: Daily U.S. Equity Panel, January 2004 to December 2024
ThistablesummarizesthesequentialsampleselectionprocessforthedailyU.S.equitypanel. Thesample
spans January 2004 through December 2024. Each row reports the remaining observations in millions
and unique stocks in thousands after applying the corresponding screen. The filters include exchange
eligibility, common share classification, a minimum price threshold of 5 USD, and a minimum trading
history of 252 days.
Screen Obs (M) Stocks (K)
Raw universe 39.59 20.37
Eligible exchanges 32.91 15.69
Common shares 21.78 10.10
Price >= USD 5 16.66 9.57
History >= 252 days 16.51 8.05
Exhibit 3 shows that screening is economically meaningful and not mechanically triv-
ial. The largest contraction occurs at the common-share filter and price filter stages,
which is consistent with excluding non-common securities and thinly traded low-price
names. Importantly, even after conservative screens, the final panel remains broad, with
8,052 stocks and 16.5 million stock-day observations, providing sufficient cross-sectional
depth for daily ranking tests.
For evaluation windows, we use strict time separation to avoid look-ahead bias. The
iterative promotion gate is determined using data through December 2020, and the main
out-of-sample results reported in the subsequent sections use the full window from Jan-
18

<!-- page 19 -->
uary 2021 to December 2024. In addition, we report the post-January 2023 period as a
stricter subsample check to assess robustness in a more recent environment.
Exhibit 4: Evolution of the Stock Universe: Raw CRSP Data vs. Screened Sample
ThisfigureplotsthedailynumberofstocksavailableintherawCRSPdatabase(blueline)andthefinal
sample remaining after applying data screening criteria (purple line). The sample period spans from
January 2004 to December 2024. Shaded areas represent the respective universe sizes over time.
4.2. Target and Predictor Set
Thepredictiontargetistheone-day-aheadstockreturnatthedailyfrequency. Candidate
signals are generated from a compact and interpretable set of stock-native and market-
state primitives derived from standard CRSP fields, including stock return, price, trading
volume, and broad market return series.
The baseline predictor set includes ten variables: lagged stock return, market re-
turn, absolute stock price, trading volume, volume ratio to recent history, 20-day realized
volatility, price-to-moving-average ratio, market volatility, volume growth, and a spread
proxy when quote data are available. These variables are transformed through trans-
parent operators such as lags, rolling moments, cross-sectional ranks, and arithmetic
combinations to form candidate factors.
This constrained design is deliberate. First, it keeps factor definitions auditable and
economically interpretable. Second, it limits expression complexity, reducing the risk
of overfitting through unconstrained symbolic search. Third, it creates a stable bench-
mark environment in which improvements can be attributed to better hypotheses and
19

<!-- page 20 -->
combination logic, rather than to changing data definitions.
Exhibit 5: Descriptive Statistics of Key Variables, January 2004 to December 2024
This table reports descriptive statistics for key variables from January 2004 to December 2024. N (M)
denotes observations in millions. Returns are reported in percentage points, and share volume is in
millions. The statistics include the mean, standard deviation (SD), median, and 99th percentile (P99).
Variable Unit N (M) Mean SD Median P99
Daily stock return % 16.50 0.086 3.499 0.000 8.885
Stock price USD 16.51 118.05 5051.21 23.12 327.95
Share volume million shares 16.51 1.280 5.333 0.246 16.817
VW market return % 16.51 0.043 1.150 0.080 2.980
S&P return % 16.51 0.038 1.153 0.070 2.986
Exhibit 5 indicates several features typical of daily equity panels. First, stock returns
exhibit substantial dispersion and heavy tails, motivating robust rank-based evaluation
and controlled winsorization of the target variable. Second, both price and volume are
strongly right-skewed, with medians far below means, highlighting pronounced firm-size
heterogeneity in the cross section. Third, the two market benchmarks display closely
aligned first and second moments, indicating that either series provides a stable proxy
for aggregate daily market conditions in our predictor set.
4.3. Data Pipeline and Reproducibility
Our empirical pipeline is designed around reproducibility as an identification requirement
rather than a software convenience. The complete sequence from raw records to model-
ready panels, factor construction, and evaluation outputs is deterministic, so identical
inputs generate identical results. This property ensures that cross-round comparisons in
the agentic loop reflect changes in hypotheses rather than accidental variation in prepro-
cessing or reporting.
A second principle is information-set consistency. The same variable definitions, sam-
ple screens, and transformation rules are maintained across rounds, and the selection
stage is always computed on the in-sample segment only. Out-of-sample observations are
reserved for validation and are excluded from promotion decisions. Combined with the
non-forward factor grammar described above, this structure limits leakage channels and
preserves the causal ordering of the research process.
20

<!-- page 21 -->
Finally, the framework is fully auditable at the experiment level. Each round records
candidate definitions, evaluation statistics, and selection outcomes, allowing the full re-
search path to be reconstructed ex post. This record-keeping makes it possible to verify
that reported performance is tied to a specific information set, a fixed protocol, and
a transparent sequence of decisions, which is essential for credible empirical claims in
systematic factor research.
5. Empirical Results
5.1. Single-Factor Portfolios
We start the empirical analysis with single-factor portfolio tests as a disciplined bench-
mark for the broader factor-discovery framework. The key objective at this stage is to
establish whether each candidate signal carries economically interpretable and statisti-
callyassessablestandaloneinformationaboutnext-daycross-sectionalstockreturns. This
benchmark is essential because any subsequent multi-factor improvement is meaningful
only if the incremental gains can be evaluated relative to clearly documented single-factor
baselines.
This design also serves an identification purpose. By first evaluating one factor at
a time under a common portfolio-construction protocol, we separate signal-level content
from combination-level engineering and obtain a transparent mapping from factor defini-
tion to return-sorting behavior. In this sense, single-factor portfolios provide the minimal
empirical unit for understanding where predictability comes from before studying how
predictability is combined. A second motivation is comparability and internal validity.
Dailyreturnpredictionisparticularlyexposedtomicrostructureeffectsandshort-horizon
noise. We therefore adopt a common ranking-based evaluation framework for all can-
didate factors and assess their signal quality under consistent conventions. This design
combines rank-correlation metrics with portfolio-sort evidence, so that cross-factor differ-
ences can be interpreted as differences in signal content rather than artifacts of changing
evaluation rules. Finally, this section establishes the empirical bridge to the next part
of the paper. Once the single-factor baseline is in place, the multi-factor analysis can be
21

<!-- page 22 -->
framed as a test of incremental value: whether combining signals improves stability and
risk-adjusted performance beyond what is visible at the individual-factor level.
Exhibit 6: Performance Metrics of Agentic AI-Generated Factors
ThistablereportsmultipleperformancemetricsforsinglefactorsgeneratedbyouragenticAIframework
(see Exhibit 2 and Algorithm 1 for methodological details). The long-short portfolios are constructed
by going long on stocks in the top 50% and shorting those in the bottom 50% based on factor rankings.
Reported metrics include the Sharpe ratio, Information Coefficient (IC), IC Information Ratio (ICIR),
Long-only IC (ICL), Long-only ICIR (ICLIR), Sortino ratio, Calmar ratio, annualized returns (Ann.
Ret.), and maximum drawdown (Max DD). The factor evaluation period is from 2021.01 to 2024.12.
The portfolios are rebalanced at each market day.
Sharpe IC ICIR ICL ICLIR Sortino Calmar AnnualRet MaxDD
Factor1 2.8593 0.0068 4.8432 0.0033 1.0371 3.7811 3.5915 0.1754 -0.0488
Factor2 -0.1767 0.0011 0.7986 -0.0022 -0.6969 -0.2528 -0.0898 -0.0107 -0.1190
Factor3 2.4140 0.0098 5.1572 0.0061 3.4130 3.1564 2.3044 0.2402 -0.1042
Factor4 0.6535 0.0051 2.0167 0.0003 0.1371 0.9670 0.4057 0.0768 -0.1894
Factor5 1.4069 0.0059 3.4047 0.0003 0.1080 2.0108 1.3124 0.1196 -0.0911
Factor6 2.2597 0.0071 4.9613 0.0036 1.5999 3.2242 1.8383 0.1543 -0.0839
Factor7 0.7182 -0.0003 -0.1433 -0.0000 -0.0045 1.0096 0.5023 0.0527 -0.1048
Factor8 1.6628 0.0271 5.3121 0.0131 2.6462 2.7148 1.9476 0.3928 -0.2017
Factor9 1.9421 0.0055 3.3963 -0.0008 -0.3131 2.8600 2.2886 0.1317 -0.0575
Factor10 1.4424 0.0049 2.9661 0.0004 0.1513 2.1149 1.5943 0.1078 -0.0676
Factor11 0.6228 0.0016 0.4784 -0.0000 -0.0012 0.9339 0.5539 0.0817 -0.1475
Factor12 0.8362 0.0033 2.3195 -0.0002 -0.1094 1.2785 0.6246 0.0541 -0.0867
Exhibit6providesacomprehensivesingle-factordiagnosticfortheagenticAI-generated
signals over the 2021.01–2024.12 window. To formally evaluate these signals, we utilize
standard performance and risk metrics, including the Information Coefficient (IC), IC
Information Ratio (ICIR), Sortino ratio, Maximum Drawdown (MaxDD), and Calmar
ratio, which are defined as follows:
IC = ρ (f ,R )
rank t t+1
µ
ICIR = IC
σ
IC
R −R
Sortino = p f (5.1)
σ
d
max P −P
MaxDD = max t∈(0,τ) t τ
τ∈(0,T) max t∈(0,τ) P t
R
Calmar = p
MaxDD
Exhibit 6 shows that standalone signal quality is heterogeneous rather than uniformly
strong. Several factors exhibit attractive long-short profiles with strong Sharpe ratios and
economically meaningful annualized returns, while the highest-IC factor (Factor 8) also
22

<!-- page 23 -->
stands out on ranking ability. By contrast, several other factors appear materially weaker
out of sample, including at least one case (Factor 2) with poor portfolio monetization
despite a small positive IC. This pattern suggests that the agentic framework is capable
of generating genuinely useful signals, but it does not imply that every promoted factor is
equally investable on a standalone basis. The heterogeneity in IC, Sharpe, and drawdown
profiles motivates the multi-factor aggregation analysis that follows.
23

<!-- page 24 -->
Exhibit 7: Univariate Portfolio Sorts: Decile Returns of Agentic AI-Generated Factors
This table presents the average equal-weighted returns for decile portfolios sorted by factors discovered by our agentic AI framework. At each rebalancing date,
stocks are ranked by their respective factor scores and partitioned into ten portfolios. “Low” and “High” denote the bottom and top deciles, respectively. The
“High−Low” column reports the return spread between the top and bottom deciles. All returns are expressed in decimal form. The portfolios are rebalanced at
each market day.
Deciles
Factor Low 2 3 4 5 6 7 8 9 High High-Low
Factor 1 7.6080 9.3167 11.5033 9.1529 12.3174 12.6893 13.7833 12.6944 13.9916 23.9337 16.3258
(1.1435) (0.9004) (1.0936) (0.8718) (1.1946) (1.2270) (1.3190) (1.2090) (1.3539) (3.5077) (5.7073)
Factor 2 12.7183 10.5950 12.0842 12.7672 11.3010 13.7137 12.8309 15.3788 13.8296 11.7832 -0.9351
(1.9314) (1.0272) (1.1426) (1.2142) (1.0916) (1.3273) (1.2288) (1.4678) (1.3441) (1.7285) (-0.3526)
Factor 3 5.5370 7.4050 9.4599 11.6211 11.5141 9.7888 12.5611 15.7002 15.9265 27.4833 21.9463
(0.8371) (0.7320) (0.9123) (1.2202) (1.1812) (0.9453) (1.2198) (1.5242) (1.5420) (3.0366) (4.8185)
Factor 4 10.8439 10.0526 9.0151 11.5517 11.7319 14.1782 13.1807 11.5061 15.9148 19.0283 8.1844
(2.0288) (1.0472) (0.8604) (1.0963) (1.1223) (1.3544) (1.2762) (1.1177) (1.5488) (1.9991) (1.3043)
Factor 5 8.8644 8.3713 7.8395 11.2448 11.8396 12.5005 14.1687 14.2334 17.4292 20.5067 11.6424
(1.3531) (0.8181) (0.7503) (1.0800) (1.1480) (1.2306) (1.3855) (1.4026) (1.7279) (2.4144) (2.8083)
Factor 6 6.5800 9.1634 11.6692 11.6242 13.0579 12.3224 11.9336 12.3290 17.1525 21.1415 14.5615
(0.7852) (1.0063) (1.1449) (1.1298) (1.2778) (1.2132) (1.1613) (1.2157) (1.8851) (2.4920) (4.5105)
Factor 7 12.5296 11.5006 10.8795 12.0201 11.0813 12.0757 11.4794 13.8562 13.6509 17.9456 5.4160
(1.4147) (1.1236) (1.0538) (1.1733) (1.0781) (1.1758) (1.1434) (1.3972) (1.4839) (2.5567) (1.4335)
Factor 8 -13.7849 -0.1989 7.2228 12.6352 22.0386 21.0944 17.6189 19.6974 19.2048 21.6353 35.4202
(-1.0195) (-0.0171) (0.6602) (1.1520) (1.9228) (2.0029) (1.9113) (2.4984) (2.8172) (3.3056) (3.3190)
Factor 9 7.7250 5.7652 9.8208 12.3451 12.0076 13.8103 14.2841 15.4949 15.4298 20.3107 12.5857
(1.0693) (0.5589) (0.9452) (1.2059) (1.1722) (1.3628) (1.4140) (1.5359) (1.5458) (2.4836) (3.8764)
Factor 10 8.6473 8.2489 10.1795 11.2505 12.5063 12.9636 12.1496 14.9647 16.9427 19.1523 10.5051
(1.2554) (0.8022) (0.9705) (1.0942) (1.2188) (1.2692) (1.2009) (1.4807) (1.6848) (2.3136) (2.8791)
Factor 11 8.2225 9.1330 11.2494 10.7664 13.8119 13.5295 11.0894 13.7121 18.3941 17.0931 8.8706
(0.8459) (0.8546) (1.0584) (1.0137) (1.2979) (1.2584) (1.0298) (1.3099) (2.0924) (3.9138) (1.2432)
Factor 12 11.4317 9.9040 10.9462 11.5047 12.2840 12.8936 12.0737 14.1727 14.8922 16.9192 5.4875
(1.3371) (1.0853) (1.0853) (1.1321) (1.2090) (1.2800) (1.1864) (1.4098) (1.6299) (1.9329) (1.6691)
24

<!-- page 25 -->
Exhibit 7 provides a cross-sectional portfolio-sort view of each factor and reveals
meaningful but uneven sorting ability across the signal set. Several factors generate
economically large and statistically credible High–Low spreads, while monotonicity is not
universal across all candidates and a subset of factors shows weak or statistically fragile
spreadreturns,includingatleastonecasewithanegativeHigh–Lowspread. Theevidence
therefore supports a selective interpretation: the framework discovers multiple useful
ranking signals, but their standalone sorting quality varies enough to justify subsequent
multi-factor integration.
Exhibit 8: Risk-Adjusted Alphas of Agentic AI-Generated Factors
This table presents annualized out-of-sample alphas and corresponding t-statistics for factors discovered
by our agentic AI framework. Alphas are estimated via time-series regressions of long-short portfolio
returnsontheCAPM(Sharpe,1964),FF3(FamaandFrench,1993),FF5(FamaandFrench,2015),and
FF6 models (FF5 plus momentum factor proposed by Jegadeesh and Titman (1993)). The long-short
portfoliosareconstructedbysortingstocksintodecilesbasedonfactorrankings. Allalphasarereported
in percentages, and t-statistics (in parentheses) are adjusted for heteroskedasticity and autocorrelation
following Newey and West (1987).
Factor CAPM α FF3 α FF5 α FF6 α
Factor 1 0.134 0.137 0.138 0.138
(4.57) (4.71) (4.74) (4.74)
Factor 2 -0.037 -0.038 -0.040 -0.040
(-1.30) (-1.34) (-1.43) (-1.43)
Factor 3 0.190 0.196 0.195 0.196
(4.22) (4.30) (4.33) (4.37)
Factor 4 0.054 0.058 0.056 0.057
(0.88) (0.95) (0.93) (0.95)
Factor 5 0.088 0.089 0.088 0.088
(2.18) (2.21) (2.18) (2.23)
Factor 6 0.115 0.118 0.115 0.115
(3.61) (3.70) (3.64) (3.65)
Factor 7 0.023 0.021 0.021 0.022
(0.62) (0.57) (0.57) (0.59)
Factor 8 0.331 0.320 0.315 0.318
(3.32) (3.26) (3.24) (3.26)
Factor 9 0.098 0.099 0.100 0.100
(3.08) (3.11) (3.17) (3.21)
Factor 10 0.077 0.077 0.077 0.078
(2.14) (2.15) (2.18) (2.23)
Factor 11 0.060 0.052 0.053 0.053
(0.90) (0.77) (0.80) (0.80)
Factor 12 0.028 0.026 0.021 0.022
(0.83) (0.78) (0.65) (0.67)
Exhibit 8 evaluates whether the single-factor portfolios survive standard risk adjust-
25

<!-- page 26 -->
ment. The evidence is concentrated rather than universal. The stronger factors retain
positive and statistically meaningful alpha across the benchmark models, while several
weaker candidates lose significance after controlling for standard market and style expo-
sures. ThestabilityofthestrongeralphasacrossCAPM,FF3, FF5, andFF6nevertheless
suggeststhatthebestagent-generatedsignalsarenotmerelyrepackagingcanonicalequity
factors.
Overall, the single-factor evidence supports three conclusions. First, the agentic
pipelinecanidentifyfactorswitheconomicallymeaningfulandstatisticallycrediblespread
returns, but the quality of those factors is heterogeneous. Second, the stronger signals
retain alpha under standard risk adjustment, which suggests that they contain informa-
tion beyond canonical factor exposures. Third, precisely because standalone performance
varies across candidates, disciplined multi-factor integration is essential for improving ag-
gregate out-of-sample performance.
5.2. Multivariate combination
Having established the standalone properties of individual signals, we next evaluate
whether combining agentic AI-generated factors can produce more stable and economi-
cally meaningful out-of-sample performance. The motivation is straightforward: single-
factor evidence is informative but heterogeneous, and practical portfolio construction
typically relies on aggregation to reduce idiosyncratic noise, diversify factor-specific risks,
and improve implementation robustness. In this subsection, we therefore move from
univariate sorting diagnostics to integrated portfolio formation, and test whether a disci-
plined multi-factor design can deliver incremental value beyond what is attainable from
any single signal in isolation.
While individual factors demonstrate standalone predictive power, they may capture
overlapping market dynamics. The purpose of aggregation is to exploit their orthogonal
information. To achieve this, we employ both a linear model (to capture independent
additive premiums) and a tree-based LightGBM model (to capture complex, conditional
interactions among these signals) for complementary reasons. The linear specification
providesatransparentbenchmarkwithlowestimationvarianceanddirectlyinterpretable
26

<!-- page 27 -->
Exhibit 9: Out-of-Sample Performance of the Composite Long-Short Strategy
This table reports out-of-sample performance of the (linear) composite long-short strat-
egy. Panel A summarizes full-window gross results for 2021 January–2024 December.
Panel B reports gross performance by calendar quarter to assess temporal stability. Ann.
Return and Ann. Vol. denote annualized return and annualized volatility. Max DD
denotes maximum drawdown. The portfolios are rebalanced at each market day.
Period Ret. (%) Ann. Ret. (%) Ann. Vol. (%) Sharpe Max DD (%) N
Panel A: OOS 2021 January-2024 December
Long-Short 470.43 54.81 16.40 2.75 -13.41 1004
Panel B: Quarterly gross
2021Q1 9.68 46.49 22.65 1.80 -6.18 61
2021Q2 12.61 60.81 15.22 3.20 -6.90 63
2021Q3 12.04 56.45 12.38 3.68 -5.88 64
2021Q4 24.00 133.29 12.43 6.89 -2.67 64
2022Q1 21.25 118.82 22.03 3.67 -5.80 62
2022Q2 18.38 98.53 22.20 3.20 -6.46 62
2022Q3 1.42 5.71 23.13 0.35 -10.70 64
2022Q4 14.08 69.39 19.94 2.74 -4.40 63
2023Q1 1.37 5.69 17.88 0.40 -10.04 62
2023Q2 3.03 12.89 10.86 1.17 -5.08 62
2023Q3 18.04 94.17 10.92 6.14 -2.52 63
2023Q4 4.76 20.45 14.93 1.32 -9.70 63
2024Q1 5.92 26.84 11.11 2.20 -3.49 61
2024Q2 17.29 89.25 10.35 6.22 -1.88 63
2024Q3 17.85 90.92 15.37 4.29 -5.97 64
2024Q4 5.85 25.55 11.26 2.08 -2.89 63
27

<!-- page 28 -->
factor loadings, which is useful for identifying broad directional contributions of each
signal. The tree-based specification is introduced to capture potential nonlinearities,
interaction effects, and regime-dependent thresholds that are difficult to represent in
a purely additive linear structure. Evaluating both models under the same train–test
protocol allows us to distinguish robust information that survives across model classes
from gains that are model-specific.
Exhibit 9 reports strong gross out-of-sample performance for the linear composite
long-short strategy over the main 2021–2024 evaluation window. The strategy delivers
a gross annualized return of 54.81%, annualized volatility of 16.40%, and a Sharpe ratio
of 2.75. The quarterly breakdown suggests that performance is not concentrated in
a single short episode, as the reported gross return remains positive throughout the
sample. At the same time, quarterly annualized-return figures should be interpreted with
caution because annualization mechanically amplifies short-window outcomes. Overall,
the evidence indicates that combining the discovered signals materially improves stability
and tradability relative to the more uneven standalone factor results.
Exhibit 10: Risk-adjusted alpha (annualized) and t-statistics: combination portfolios
The table presents equal-weighted portfolio returns sorted by composite factor scores. We present the
classic CAPM (Sharpe, 1964) alpha with Newey and West (1987)’s adjusted t-statistics in parentheses
below the corresponding alphas. The three- and five-factor models correspond to the classical factor
models by Fama and French (1993, 2015)
Portfolio CAPM α FF3 α FF5 α FF6 α
Linear long-short 0.425 0.417 0.412 0.414
(5.334) (5.304) (5.315) (5.324)
Linear long-only 0.293 0.302 0.300 0.300
(4.170) (4.327) (4.340) (4.338)
LGBM long-short 0.315 0.311 0.310 0.311
(6.986) (6.871) (6.917) (6.904)
LGBM long-only 0.240 0.251 0.251 0.250
(3.248) (3.438) (3.451) (3.441)
Exhibit 10 provides strong evidence that the combination portfolios retain substan-
tial abnormal performance after standard risk adjustment. Across CAPM, FF3, FF5,
and FF6, all reported portfolio constructions deliver positive and statistically significant
annualized alphas. For the linear long-short portfolio, the alpha remains stable as the
28

<!-- page 29 -->
benchmark model becomes richer, ranging from 0.425 (t = 5.33) under CAPM to 0.414
(t = 5.32) under FF6. The nonlinear LightGBM specification has a lower point estimate
(e.g., 0.311 under FF6), but its t-statistics remain consistently high across specifications
(around 6.90). Taken together, these results suggest that the multi-factor signals are not
simply repackaging exposures to standard equity risk factors.
Exhibit 11: Cumulative Returns of Multi-factor Portfolios: Linear vs. LightGBM Factor
Aggregation
This figure displays the out-of-sample cumulative returns of portfolios constructed by aggregating mul-
tiple Agentic AI-generated factors. The left panel illustrates the performance using a linear aggregation
model,whiletherightpanelshowstheresultsusingaLightGBM(LGBM)model. Eachplotdepictsfour
series: the long-only portfolio (Decile 10), the short-only portfolio (Decile 1), the resulting long-short
portfolio (High-Low), and the maximum drawdown of the long-short portfolio (numbers in percentage
%).
Exhibit11comparestheout-of-samplecumulativereturnpathsundertwoaggregation
schemes. Two patterns are central. First, both aggregation methods generate persistent
upward trends in the long and short legs, indicating that the discovered factor set remains
monetizableaftercombination. Second,thespreadportfolioremainsbroadlypositiveover
the sample, but its trajectory differs across models: the linear specification exhibits larger
interim drawdown episodes, whereas LightGBM shows a smoother drawdown profile and
faster stabilization after stress periods. This is consistent with nonlinear aggregation
better capturing interaction effects among factors.
Exhibit 12 compares IC dynamics and provides mechanism-level support for the port-
29

<!-- page 30 -->
Exhibit 12: Information Coefficient (IC) Diagnostics: Linear vs. LightGBM Aggregation
This figure presents the diagnostic analysis of daily rank Information Coefficients (IC) for the composite
signals. The upper panel displays the IC metrics for the linear aggregation model, while the lower panel
shows the results for the LightGBM (LGBM) aggregation model. The left plot illustrates the daily IC
time series with rolling averages, and the right plot displays the empirical distribution of the daily IC
values.
30

<!-- page 31 -->
folio outcomes. The linear model shows ICs fluctuating around zero, whereas the Light-
GBM model maintains a systematically higher IC level over most of the sample, with its
rolling means remaining predominantly above zero. The distributional panels reinforce
this, showing the LightGBM daily IC distribution shifted to the right with a thicker posi-
tive tail. This implies that nonlinear aggregation improves both the level and persistence
of predictive information.
Exhibit 13 reports the out-of-sample performance of decile portfolios. The results
reveal a broadly monotonic relationship for the composite signal: the cumulative period
return increases from -47.01% for D1 to 245.72% for D10, while the annualized Sharpe
ratio rises from -0.505 to 2.313. This confirms the model’s cross-sectional predictive
power. The D10-D1 long-short spread yields a cumulative gross return of 465.07% with
an annualized Sharpe ratio of 2.715. After applying a one-way turnover cost of 3 bps, the
corresponding net long-short spread remains economically meaningful, with a cumulative
return of 305.57% and an annualized Sharpe ratio of 2.211.
Exhibit 13: Decile Portfolio Performance in the Out-of-Sample Window
Thistablereportsdecile-levelperformanceforscore-sortedportfoliosandtheD10-D1long-shortspread.
Panel A reports decile portfolios. Panel B reports long-short performance. The Gross row reports the
long-short spread (D10-D1) using gross daily returns. The Net row deducts a one-way transaction cost
of 3 bps from daily turnover: c =0.0003×Turnover , and rnet =rgross−c . Turnover is one-way daily
t t t t t t
(cid:81)
long-short turnover in decimal form (1.0 = 100%). Period Return is (1+r )−1, and Ann. Sharpe is
√ t t
252r¯/σ(r) based on daily returns.
Portfolio Period Return (%) Ann. Sharpe N Days
Panel A: Decile (gross)
D1 -47.01 -0.505 1004
D2 6.14 0.180 1004
D3 35.72 0.466 1004
D4 38.48 0.507 1004
D5 48.75 0.616 1004
D6 65.33 0.777 1004
D7 83.99 0.934 1004
D8 87.94 0.973 1004
D9 133.03 1.290 1004
D10 245.72 2.313 1004
Panel B: Long-short spread (D10-D1)
Gross 465.07 2.715 1004
Net 305.57 2.211 1004
31

<!-- page 32 -->
Exhibit 14 illustrates the cumulative returns of the decile portfolios, revealing a strik-
ing “fan-out” effect. The top decile (D10) exhibits a consistent upward trajectory, while
the bottom decile (D1) shows a persistent decline. This clear separation throughout the
1004-day out-of-sample period demonstrates encouraging cross-sectional discrimination
and signal stability, validating the effectiveness of the factor aggregation methodology.
Exhibit 14: Cumulative Performance of Decile Portfolios Sorted by Aggregated Signal
This figure displays the cumulative returns of ten decile portfolios (D1 to D10) constructed by sorting
assetsbasedontheiraggregatedfactorscores. Theperformanceistrackedovertheout-of-sampleperiod
from 2021 to 2024.
6. Mitigation of Data-Mining Concerns and Economic Rationale
Given the substantial out-of-sample alpha reported in Section 5, a natural concern is
whether such performance stems from extensive data-mining or genuine economic reg-
ularities. A central challenge in automated factor discovery is data-mining bias—the
tendency to uncover spurious patterns that lack economic substance and fail to persist
out-of-sample (Harvey et al., 2016). In the era of the “Factor Zoo,” the risk of p-hacking
is particularly acute for AI-driven methods. This section validates the integrity of our
discovery process through two complementary lenses. First, we detail the stringent sta-
tistical hurdles, multi-objective filters, and strict temporal isolation protocols designed
to suppress spurious discoveries. Second, we move beyond numerical performance to an-
alyze the “anatomy” of the agent-generated signals, demonstrating that the framework’s
32

<!-- page 33 -->
output aligns with established market microstructure and behavioral finance theories. By
synthesizing statistical rigor with economic interpretability, we ensure that the reported
alpha represents structural market insights rather than transient noise.
6.1. Economic Regularization and the “Lucky Factor” Filter
Akeyconcerninautonomousfactordiscoveryistheidentificationofluckyfactors—signals
that appear significant due to extensive search rather than genuine economic mechanisms
(Harvey et al., 2016). The proliferation of these spurious signals is not merely a statis-
tical artifact, but is deeply rooted in human behavioral biases. As conceptualized in the
scientific outlook of financial economics (Harvey, 2017), human cognition is evolutionar-
ily wired to tolerate high Type I errors (false positives). In a primal environment, the
energetic cost of reacting to a false alarm (e.g., fleeing from rustling grass that turns out
to be wind) is negligible compared to the fatal cost of a Type II error (e.g., ignoring the
rustling grass that conceals a predator). In empirical finance, this asymmetric survival
heuristic translates into a pervasive psychological urge to over-interpret random noise as
profitable patterns, inevitably driving human researchers toward data mining and the
expansion of the “factor zoo.”
Our Agentic AI framework provides a structural safeguard against this human cog-
nitive flaw. Unlike human researchers who are prone to HARKing (Hypothesizing After
the Results are Known)—where a high Sharpe ratio is retrospectively used to justify a
spurious narrative—our framework enforces a strict deductive process. By leveraging the
vast prior knowledge embedded in Large Language Models, the agent operates within a
semanticsearchspaceratherthanapurelymathematicalone. Tomitigatetheriskofspu-
rious discoveries, our framework embeds economic interpretability directly into the factor
generation process. Specifically, the agent generates candidate factors under explicit in-
terpretability constraints. The mathematical expression of a factor and its economic
rationale are produced jointly rather than sequentially. This ensures that each proposed
signal is accompanied by a plausible economic explanation for why the transformation
of price–volume information may predict future returns, fundamentally constraining the
brute-force data mining that plagues traditional quantitative research.
33

<!-- page 34 -->
This design effectively introduces economic regularization on the symbolic search
space. Unlike traditional automated machine learning methods (such as genetic program-
ming) that conduct unconstrained random walks across a vast mathematical landscape
(Neely et al., 1997; Brogaard and Zareei, 2023)9, our Agentic AI leverages the prior fi-
nancial knowledge embedded in its pre-trained weights. By restricting the admissible set
of transformations to economically interpretable ones, the framework reduces the likeli-
hood of discovering spurious patterns that arise purely from combinatorial exploration
of mathematical operators. In essence, the requirement of an explicit economic rationale
acts as a Bayesian prior that drastically shrinks the hypothesis search space to an eco-
nomically meaningful subspace. This fundamentally reduces the multiple-testing burden
before any statistical hurdles are even applied. As a result, the agent prioritizes signals
that are both statistically predictive and economically meaningful, filtering out a large
class of purely data-mined candidates (Harvey and Liu, 2020).
6.2. Strict Statistical Hurdles and Multiple Testing Adjustment
To account for the thousands of implicit regressions performed during the discovery pro-
cess, we eschew the traditional t > 2.0 threshold. Instead, we adopt the more stringent
significance level recommended by Harvey et al. (2016) for the current research era:
|t-statistic| > 3.0 (6.1)
This high hurdle is designed to control the Type I error rate (false discoveries) in a
multiple testing environment. By requiring a t-stat of 3.0, we ensure that the discovered
factors represent genuine market anomalies rather than transient data-mining artifacts.
Furthermore, we evaluate the factor’s contribution to reducing pricing errors, a concept
aligned with the Scaled Intercept (SI) metric in Harvey and Liu (2021), ensuring that
new factors provide incremental explanatory power relative to established benchmarks.
9Specifically, arbitrarily combining mathematical functions and operators often generates economi-
callymeaninglessrules,whichmerelyinflatesthecomputationalcostofthesearchprocess. Thisislargely
becausethesizeofthesearchspaceisastronomicallylargeduetothemultitudeofpossiblemathematical
combinations.
34

<!-- page 35 -->
6.3. Multi-Dimensional Robustness Checks
A human QR does not rely solely on t-statistics; they evaluate alpha quality through
multiple lenses (López de Prado, 2018). This skepticism is rooted in the "False Strategy
Theorem," which warns that most backtested discoveries are merely artifacts of multiple
testing on finite datasets. Our agent emulates this skepticism by incorporating a multi-
objective promotion gate, shifting the focus from mere curve-fitting to the identification
of robust statistical properties:
• Information Redundancy: Using a memory-update mechanism, the agent en-
sures that new factors provide significant marginal information over existing bench-
marks (e.g., the Fama-French five-factor model Fama and French (2015)). This
approach aligns with the principle of “Feature Importance” over "Backtest Perfor-
mance" López de Prado (2018), ensuring the agent seeks unique structural drivers
of returns. By filtering for marginal information gain, the framework avoids the
“substitution effect” where redundant features inflate in-sample significance with-
out adding genuine predictive value.
• Implementation Feasibility: Factors are penalized for excessive turnover and
rapid alpha decay. This ensures the discovered signals are captureable in practice
and not just artifacts of high-frequency noise. This reflects the “Economic Real-
ity” constraint emphasized by López de Prado (2018), which argues that a valid
strategy must possess a clear economic rationale and survive the frictions of market
microstructure, rather than exploiting non-tradable statistical anomalies.10
6.4. Strict Temporal and Policy Isolation
To formally quantify the extent of data-mining, we adhere to a strict Out-of-Sample
(OOS) protocol. All factor discovery and agent learning are finalized using data prior
to December 2020. During the OOS period (2021–2024), the agent’s internal state and
10AccordingtoLópezdePrado(2018),thehighfailurerateofquantitativestrategiesoftenstemsfrom
"p-hacking" during the discovery phase. Our multi-objective gate acts as a functional heuristic for the
Deflated Sharpe Ratio, implicitly accounting for the hidden trials involved in automated factor search
by imposing stringent non-performance hurdles.
35

<!-- page 36 -->
factor library are frozen. This blind test ensures that the performance reported is not a
result of look-ahead bias or iterative over-fitting to recent market regimes.
6.5. The Anatomy and Economic Logic of Agent-Generated Factors
This section provides an analysis of the factors synthesized by the autonomous agent,
examining both their structural architecture and their underlying financial rationale. By
transitioning from human-led prompting to an agentic discovery process, the framework
identifies signals that are not only statistically robust but also deeply rooted in market
microstructure and behavioral finance. We first delineate the self-iterative mechanism of
autonomous synthesis and subsequently provide a thematic taxonomy of the discovered
factors, demonstrating how the framework bridges the gap between machine-driven alpha
extraction and economic interpretability.
6.5.1. Mechanisms of Autonomous Factor Synthesis
The evolution of factor discovery has moved progressively toward reducing human bias
and increasing computational autonomy. This trajectory began with the application of
machinelearningtoautomatefactorconstruction. Forinstance,Fangetal.(2020)utilized
deeplearningarchitecturestocapturecomplexnon-linearitiesandtemporaldependencies,
moving beyond the limitations of traditional Genetic Programming (GP). More recently,
the advent of Large Language Models (LLMs) introduced a semantic dimension to this
automation. Cheng and Tang (2024) and Cheng et al. (2026) demonstrated that LLMs
could conceptualize innovative factors by leveraging their vast internal knowledge bases
throughhuman-ledprompting, applyingthislogicacrossdiversedatasetstoextractalpha
from textual and numerical insights.
Ourmethodologyinheritsthecorestrengthsofthesepioneeringapproaches—specifically
the high-dimensional pattern recognition of neural frameworks and the creative hypoth-
esis generation of LLMs. However, we propose a paradigmatic shift from these “Tradi-
tional AI” applications to an “Agentic AI” framework. This transition aligns with the
emerging industry consensus, as noted by Chen (2025), who argues that the future of
institutional asset management lies in the evolution from generative tools to autonomous
36

<!-- page 37 -->
agentic systems capable of independent data analysis and decision-making. While the
neural approach of Fang et al. (2020) remains tethered to fixed, human-engineered ar-
chitectures, and the prompting methodology of Cheng and Tang (2024) requires manual
intervention to guide the model’s reasoning, our agentic framework operates with true
functional autonomy. By moving beyond the "passive respondent" model, our approach
realizes the "human-AI" collaborative paradigm envisioned in recent literature, where the
AI agent functions as an autonomous researcher that systematically explores the factor
zoo, rather than a mere tool for executing human-led prompts.
The defining advantage of this architecture is its role as a self-iterative researcher
rather than a passive respondent. Unlike traditional models that function as opaque op-
timizers or "prompt-dependent" generators, our agent executes a continuous, closed-loop
cycle of hypothesis formulation, empirical validation, and policy reflection. By utilizing
a memory-update mechanism, the agent refines its search strategy based on accumulated
backtesting evidence, allowing it to explore the "factor zoo" more systematically with-
out being restricted by a specific network topology or a static set of instructions. This
meta-autonomy ensures that the discovery process is not merely a product of pre-defined
parameters but an evolving intelligence that adapts to market feedback, ensuring both
statistical significance and economic persistence in the synthesized factors.
6.5.2. Thematic Taxonomy and Financial Rationale: Economic Insights
The factors synthesized by the autonomous agent exhibit a high degree of economic inter-
pretability, focusing primarily on market microstructure, investor attention, and liquidity
dynamics. As detailed in Exhibit 15, the agent demonstrates a sophisticated under-
standing of how turnover and flow shocks influence cross-sectional returns. A significant
portion of the factor library is dedicated to capturing turnover-related anomalies across
various temporal horizons. For instance, Factor 7 (Delayed Turnover Pressure) and Fac-
tor 10 (Medium Horizon Turnover Pressure) suggest that the agent has identified market
crowding and capital rotation as primary drivers of price reversals or trend persistence.
The nature of these discovered signals offers a distinct advantage over the “black-
box” outputs typical of the neural construction methods discussed by Fang et al. (2020).
37

<!-- page 38 -->
While neural-based frameworks are highly proficient at extracting alpha through high-
dimensional feature mapping, the resulting signals are often embedded within opaque
weight matrices, rendering them difficult for institutional investors to validate economi-
cally. In contrast, our agentic framework synthesizes transparent symbolic formulas that
bridge the gap between high predictive power and rigorous interpretability. A unique an-
alytical finding from the agent’s output is the integration of execution frictions directly
into the factor logic. Factor 2 (Friction Adjusted Flow Shock) exemplifies this by adjust-
ing volume shocks for estimated trading costs, thereby prioritizing signals that remain
profitable after accounting for market impact. This level of practical awareness is a direct
result of the agent’s iterative reflection on backtesting results, where it learns to penalize
high-turnover signals that offer thin alpha cushions. Furthermore, factors such as Flow
Volatility Imbalance (Factor 1) and Price Level Persistence (Factor 8) indicate that the
agent can distinguish between steady buying interest and speculative noise, confirming
that the autonomous discovery process aligns with established financial theories while
identifying novel interaction effects.
7. Robustness Tests
In this section, we conduct a comprehensive series of robustness checks to evaluate the
practical viability and structural properties of our agentic framework. Specifically, our
analysis spans four critical dimensions: (i) the persistence of predictive power over longer
holding horizons, (ii) the economic viability of the strategy net of transaction costs, (iii)
the stability of portfolio turnover, and (iv) the comparison between our autonomous
agent and traditional AI configurations. Together, these tests show that the framework
generates statistically significant and implementable alpha that survives real-world trad-
ing frictions, while cross-framework relative performance remains sensitive to factor-set
construction and model specification.
7.1. Longer-horizon predictability
Exhibit 16 presents the out-of-sample performance of twelve individual Agentic-AI gen-
erated factors and their composite models over 1- to 7-day holding horizons. Both com-
38

<!-- page 39 -->
Exhibit 15: Autonomous Agentic AI-generated Factors and Economic Interpretation
This table lists the constituent factors used in the composite factor construction and provides a concise
economic interpretation for each factor. The first column reports the factor index, the second column
reports the factor name, and the third column summarizes the signal intuition and intended economic
channel. Factorsaredefinedfromprice,tradingactivity,andturnover-relatedinformationandareusedto
predict next-day cross-sectional stock returns. Descriptions are conceptual and implementation-neutral,
intended to clarify variable meaning rather than to present performance evaluation.
No. Factorname Factorexplanation
3 CompositeLiquidityDemand This factor combines turnover level and turnover acceleration to
proxyforcontemporaneousorder-imbalancedemand. Economically,
strongerandbroaderbuyingpressureismorelikelytoreflectslow-
moving information and limits-to-arbitrage, creating short-horizon
returncontinuation.
8 DefensiveMean-ReversionSignal This factor is higher for stocks trading below recent trend anchors
with relatively low realized risk. Economically, it targets underre-
acted, temporarily discounted names where mispricing correction
canoccurwithoutextremevolatilityrisk.
12 DelayedFlowPersistence This factor focuses on lagged and smoothed turnover shocks, so
it captures persistent order flow rather than one-day noise. Eco-
nomically, it reflects gradual information diffusion and segmented
liquidityprovision.
11 FlowAcceleration-Concave This factor emphasizes persistent flow acceleration while down-
weightingextremespikes. Economically,itmapstoinvestoratten-
tionwaveswheremarginalpriceimpactdecaysatveryhightrading
activitylevels.
1 FlowShock-Winsorized This factor captures abnormal cross-sectional trading-demand
shocks while limiting the influence of extreme outliers. Economi-
cally, it isolates broad attention or liquidity shocks that can move
pricesbeforefullincorporation.
2 LaggedFlowPressure This factor uses prior-day flow surprise to test whether liquidity-
drivenpricepressurereversesorpersists. Economically,persistence
canarisewhenmarketmakersandconstrainedarbitrageursabsorb
inventorygradually.
9 Medium-HorizonAttention Thisfactormeasuressustainedturnoveroveramediumhorizonand
proxies for persistent investor attention and crowding. Economi-
cally,prolongedattentioncanproducepredictabledemandpressure
anddelayedrepricing.
5 PersistentTurnoverIntensity This factor highlights relative liquidity-demand intensity across
stocks over a short rolling horizon. Economically, names with per-
sistentlyhighturnovertendtocarrystrongerinformationarrivalor
speculativedemand.
6 SmoothedFlowShock This factor is a denoised flow-shock measure designed to suppress
transitoryspikes. Economically,itcapturesshort-rundemandpres-
sure that survives smoothing filters and is therefore more likely to
bepricedwithdelay.
4 StableTurnoverTrend This factor rewards high but stable turnover and penalizes erratic
liquidity bursts. Economically, stable participation often indicates
institutional flow and lower adverse-selection uncertainty, support-
ingstrongersignalreliability.
10 SustainedLiquidityAttention Thisfactorcapturespersistenttradinginterestwhilepreventingex-
tremely active names from dominating the signal. Economically,
it reflects gradual attention-driven capital reallocation rather than
one-offnoisetrades.
7 TurnoverVolatilityRisk This factor measures short-window instability in liquidity demand
and inventory risk transfer. Economically, high turnover volatility
islinkedtofragileliquiditystatesandtime-varyingriskpremia.
39

<!-- page 40 -->
posite models deliver economically meaningful and statistically significant returns across
horizons. At H1, the Linear model reports an annualized return of 44.87% (t = 5.42),
while the LGBM model reports 34.24% (t = 7.23). At H7, the corresponding annual-
ized returns are 18.95% (t = 6.20) for Linear and 12.90% (t = 7.61) for LGBM. These
results indicate that machine-learning aggregation improves statistical stability, while
return magnitude and inference strength can differ across model classes.
As expected, the predictive power generally decays as the holding horizon extends,
with returns for most portfolios dropping monotonically from H1 to H7. However, the
individual factors exhibit notable cross-sectional variation in their decay rates. While
strong standalone predictors like Factors 6 and 10 show a steady decline in returns, their
t-statistics remain highly significant across all seven days. Interestingly, Factors 5 and 9
exhibit lower initial returns but demonstrate remarkable persistence, with their statistical
significance actually increasing over longer horizons (e.g., Factor 9’s t-statistic rises from
3.80 at H1 to 5.37 at H7), suggesting they capture slower-moving, longer-lasting market
inefficiencies.
40

<!-- page 41 -->
Exhibit 16: Long-Horizon Predictability of Factor Returns
This table reports the average daily (annualized) returns and associated t-statistics for hedge portfolios (Decile 10 minus Decile 1) formed based on the signals
of twelve Agentic-AI generated factors and a composite linear model as outlined in Appendix B. At the end of each day, stocks are ranked into deciles based
on their respective factor scores. We report the average daily performance for holding horizons (H) ranging from 1 day (1d) to 7 days (7d) after the portfolio
formation. Returns are in percentages; Newey and West (1987) adjusted t-statistics are in parentheses.
Portfolio H1 H2 H3 H4 H5 H6 H7
Linear 44.87 33.98 28.45 25.08 22.89 20.55 18.95
(5.42) (5.69) (5.92) (6.07) (6.24) (6.18) (6.20)
LGBM 34.24 26.20 21.50 19.23 16.69 14.62 12.90
(7.23) (7.81) (8.02) (8.33) (8.20) (7.97) (7.61)
Factor1 16.33 7.91 5.35 3.73 3.70 2.51 1.83
(5.71) (4.06) (3.56) (2.94) (3.30) (2.49) (1.95)
Factor2 -0.94 -0.53 -0.80 0.31 -0.44 -0.81 -0.86
(-0.35) (-0.29) (-0.55) (0.25) (-0.40) (-0.80) (-0.91)
Factor3 21.95 12.93 9.64 8.22 7.24 5.83 4.82
(4.82) (4.16) (3.91) (4.01) (4.05) (3.68) (3.36)
Factor4 8.18 7.30 7.23 6.92 6.13 5.54 5.10
(1.30) (1.66) (2.08) (2.37) (2.43) (2.46) (2.49)
Factor5 11.64 8.42 6.97 5.99 5.55 5.75 5.72
(2.81) (2.98) (3.10) (3.10) (3.29) (3.85) (4.24)
Factor6 14.56 10.14 8.75 7.16 5.07 3.34 2.44
(4.51) (4.69) (5.03) (4.77) (3.70) (2.71) (2.16)
Factor7 5.42 3.97 3.82 2.91 2.34 1.97 2.53
(1.43) (1.53) (1.91) (1.72) (1.57) (1.43) (1.99)
Factor8 35.42 28.65 24.68 21.71 19.51 18.01 17.05
(3.32) (3.81) (4.08) (4.16) (4.24) (4.34) (4.48)
Factor9 12.59 10.00 8.83 7.68 6.88 6.56 6.63
(3.88) (4.42) (4.88) (4.99) (5.05) (5.25) (5.75)
Factor10 10.51 8.93 8.20 7.50 6.88 6.31 6.00
(2.88) (3.50) (4.04) (4.35) (4.53) (4.64) (4.88)
Factor11 8.87 5.58 3.84 3.07 3.36 3.11 3.32
(1.24) (1.10) (0.95) (0.89) (1.11) (1.15) (1.35)
Factor12 5.49 2.39 0.90 0.47 0.28 0.09 0.56
(1.67) (0.99) (0.47) (0.29) (0.20) (0.07) (0.49)
41

<!-- page 42 -->
7.2. Transaction Costs and Economic Viability
A common criticism of high-frequency price-volume factors is that their alpha may be
thin and easily eroded by trading frictions. We assume a linear transaction cost model
of 3 basis points per dollar traded (one-way), which accounts for commission and spread.
Exhibit 17 presents the cumulative returns of the composite long-short strategy on both
a gross and net basis from January 2021 to December 2024. The results reveal a robust
alpha cushion. While the gap between the blue (gross) and red (dashed, net) lines repre-
sents the cumulative impact of transaction costs, the net curve maintains a remarkably
steady upward trajectory. Even after accounting for costs, the strategy achieves a sub-
stantial cumulative return (approximately 75% net vs. 139% gross). The fact that the
net curve’s slope remains consistently positive across different market regimes suggests
that the agentic AI is not merely capturing transient noise, but is identifying structural
premiums with sufficient magnitude to survive institutional-level execution costs.
Exhibit 17: Out-of-Sample Cumulative Returns: Gross vs. Net Performance
This figure illustrates the out-of-sample cumulative performance of the composite long-short portfolio,
constructed by aggregating multiple Agentic AI-generated factors as detailed in Appendix B. The blue
solid line represents the gross cumulative return (top-minus-bottom deciles), while the red dashed line
depictsthenetcumulativereturnafteraccountingfortransactioncosts. Theresultsareplottedoverthe
main out-of-sample window from January 2021 to the end of the sample period.
7.3. Turnover Analysis and Implementation Feasibility
Exhibit 18 details quarterly turnover and risk-adjusted performance. The strategy ex-
hibits high daily turnover, ranging from 105.73% to 114.43%, reflecting the fast-decaying
42

<!-- page 43 -->
nature of the agent-discovered signals. Net returns remain positive in 14 of 16 quarters.
In strong periods such as 2021Q4 and 2024Q2, the Net Sharpe ratio reaches 6.032 and
5.354, respectively. In the weakest quarter (2023Q1), the Net Sharpe is -0.075. Overall,
theresultsindicatethatthesignalremainseconomicallymeaningfulafterimplementation
costs, while net performance is still time-varying across regimes.
Exhibit 18: Quarterly Cost and Turnover Diagnostics (Out-of-Sample)
This table reports quarterly gross-versus-net performance together with turnover diagnostics for the
composite long-short strategy. Avg Turnover denotes average daily long-short turnover within each
quarter.
Quarter Avg Turnover (%) Gross Ret (%) Net Ret (%) Gross Sharpe Net Sharpe
2021Q1 105.7314 9.3807 7.2873 1.7429 1.3914
2021Q2 113.0857 12.6903 10.3115 3.2089 2.6491
2021Q3 112.3283 12.1322 9.7434 3.6917 3.0085
2021Q4 112.7979 23.7459 21.1027 6.7062 6.0322
2022Q1 114.4251 21.5852 19.0321 3.7013 3.3114
2022Q2 113.6247 18.3216 15.8532 3.1561 2.7742
2022Q3 108.3577 1.6639 -0.4296 0.3929 0.0426
2022Q4 108.8101 13.5125 11.2048 2.6226 2.2123
2023Q1 108.2341 1.2970 -0.7221 0.3805 -0.0752
2023Q2 108.4066 3.0243 0.9678 1.1675 0.4135
2023Q3 109.3437 18.0783 15.6682 6.0817 5.3309
2023Q4 108.6696 4.5059 2.3825 1.2451 0.6996
2024Q1 109.9185 6.2288 4.1142 2.2884 1.5450
2024Q2 111.1760 17.2556 14.8230 6.1602 5.3539
2024Q3 109.9314 17.6036 15.1524 4.2061 3.6689
2024Q4 109.5543 5.4931 3.3327 1.9548 1.2195
7.4. Comparison of Agentic vs. Traditional AI Frameworks
To isolate the source of alpha, we compare factors generated by the agentic framework
against those from traditional AI factor mining. For each factor set, we apply two ag-
gregation methods: a simple linear combination and a LightGBM (LGBM) integrator
as detailed in Appendix B. Exhibit 19 shows the out-of-sample cumulative long-short
returns for these four combinations from 2021 to 2024.
Exhibit 19 reports the out-of-sample cumulative long-short performance of four port-
folio construction frameworks over the 2021–2024 period. Three main results emerge.
First, the agentic framework outperforms the traditional benchmark under both aggrega-
tion schemes. Within the linear specification, the agentic portfolio achieves an annualized
43

<!-- page 44 -->
Exhibit 19: Out-of-Sample Comparison: Agentic vs. Traditional Factor Frameworks
Thisfigurecomparesout-of-samplelong–shortcumulativereturns(D10−D1)acrossfourmodelspecifica-
tionsover2021-01-01to2024-12-31atdailyfrequency. Ateachdate, stocksaresortedbymodel-implied
scores, with D10 denoting the highest-score decile and D1 the lowest-score decile; the long–short return
is the daily return spread between the two deciles. Each line reports the cumulative long–short return
obtained by compounding daily spreads through time, and the legend reports the corresponding annu-
alized return for each specification. The horizontal axis is calendar time, the vertical axis is long–short
cumulative return (D10−D1), and the dashed horizontal line marks the zero-return benchmark.
return of 58.80%, compared with 30.91% for the traditional linear portfolio. Within the
nonlinear specification, the agentic LightGBM portfolio delivers the strongest overall per-
formance, with an annualized return of 65.42%, exceeding the 50.84% achieved by the
traditional LightGBM benchmark. This pattern indicates that the incremental value of
theagenticpipelineisnotconfinedtoaspecificdownstreamcombiner, butinsteadreflects
the superior quality of the underlying discovered signal set.
Second, the performance advantage of the agentic framework is persistent rather than
episodic. The cumulative return curves begin to separate meaningfully from 2022 onward
and remain well above their traditional counterparts through the end of the sample.
This sustained spread suggests that the improvement is not driven by a single short-lived
market episode, but instead reflects a more stable enhancement in cross-sectional signal
extraction and factor organization.
Third, the nonlinear aggregation layer adds further value once higher-quality factors
are available. Among all four specifications, agentic LightGBM produces the highest
44

<!-- page 45 -->
cumulative return trajectory, followed by agentic linear, traditional LightGBM, and tra-
ditional linear. This ranking suggests a complementary relationship between factor dis-
covery and model flexibility: better upstream factor generation improves the opportunity
set, while nonlinear aggregation helps capture residual interaction effects across discov-
ered signals. Overall, Exhibit 19 provides direct out-of-sample evidence that the agentic
factor framework delivers a materially stronger and more scalable return profile than
traditional factor construction pipelines.
8. Conclusion
This paper presents an autonomous framework for systematic factor investing driven by
agentic artificial intelligence. We shift the focus from static machine learning applications
to a self-iterative research process. The system formulates factor hypotheses, evaluates
them under a strict empirical protocol, and updates its search policy based on accu-
mulated evidence. By requiring economic interpretability and enforcing strict temporal
isolation, the framework systematically mitigates data mining risks and the proliferation
of spurious signals typically associated with automated discovery.
Empirical evaluations in the US equity market confirm the validity of this method-
ology. The autonomously generated factors deliver statistically significant risk-adjusted
returns that are not spanned by standard asset pricing models. When integrated through
a linear aggregation model, the composite portfolio achieves an annualized Sharpe ratio
of2.75andanannualizedgrossreturnof54.81percentinthemainout-of-samplewindow.
These results remain robust after accounting for market microstructure frictions, trans-
action costs, and turnover constraints. Comparative tests indicate that cross-framework
performanceissensitivetofactorsetcompositionandmodelchoiceacrossmarketregimes.
The evidence indicates that autonomous agentic systems offer a practical and scal-
able solution for modern quantitative asset management. By combining computational
efficiency with scientific discipline, the framework provides a transparent method for dis-
covering persistent market anomalies. Future research can build upon this foundation
by expanding the empirical universe to include fundamental accounting data, macroe-
45

<!-- page 46 -->
conomic indicators, and alternative asset classes, broadening the scope of autonomous
financial research.
46

<!-- page 47 -->
Acknowledgement
The authors thank Ivan Blanco (CUNEF), Kaiqi Hu (Rutgers Business School), Bolong
Wang (CITIC Securities), Yifan Ye (BNBU), Chao Zhang (HKUST Guangzhou), Yi
Zhang (HKUST Guangzhou), and Yibin Zhang (Bosera Asset Management), and inter-
nal seminar participants at X Asset Management for helpful discussions, comments, and
support. These discussions, particularly those drawing upon practical industry insights,
were conducted solely for academic purposes; the views expressed are those of the in-
dividuals and do not necessarily represent their employers. The authors also thank the
editorial teams of QuantML and LLMQuant for their insightful coverage and summary
of this research across their leading Chinese practitioner-oriented social media platforms,
which helped facilitate broader academic and industry exchange. Any remaining errors
or oversights are the responsibility of the authors.
Disclosure of interest
There are no interests to declare.
Data availability
Data will be made available on request. Additional interactive results, methodological
documentation, and replication details are available at the project homepage https:
//allenh16.github.io/agentic-factor-investing/.
47

<!-- page 48 -->
References
Avramov,D.,Cheng,S.,Metzker,L.,2023. Machinelearningvs.economicrestrictions: Evidence
from stock return predictability. Management Science 69, 2587–2619.
Blitz, D., Hanauer, M.X., Honarvar, I., Huisman, R., van Vliet, P., 2023. Beyond Fama-French
factors: Alpha from short-term signals. Financial Analysts Journal 79, 96–117.
Brock, W., Lakonishok, J., LeBaron, B., 1992. Simple technical trading rules and the stochastic
properties of stock returns. The Journal of Finance 47, 1731–1764.
Brogaard, J., Zareei, A., 2023. Machine learning and the stock market. Journal of Financial
and Quantitative Analysis 58, 1431–1472.
Carhart, M.M., 1997. On persistence in mutual fund performance. The Journal of Finance 52,
57–82.
Cerniglia, J.A., Fabozzi, F.J., 2020. Selecting computational models for asset management:
Financial econometrics versus machine learning-is there a conflict? The Journal of Portfolio
Management 47, 107–118.
Chai, B., Jiang, F., Meng, L., You, T., Zhou, G., 2025. Generative AI for finance: A new
framework. Available at SSRN 6276278 .
Chen, J., Tang, G., Zhou, G., Zhu, W., 2025. ChatGPT and DeepSeek: Can they predict the
stock market and macroeconomy? arXiv preprint arXiv:2502.10008 .
Chen, M., 2025. Agentic AI and the future of institutional asset management. Journal of
Portfolio Management 51.
Chen, Y., Fan, Z., 2026. On cross-stock predictability of peer return gaps in China. Finance
Research Open 2, 100088.
Chen, Y., Kelly, B.T., Xiu, D., 2022. Expected returns and large language models. Available at
SSRN 4416687 .
Chen, Z., Pu, D., 2026. Autonomous market intelligence: Agentic AI nowcasting predicts stock
returns. Available at SSRN 6134446 .
Cheng, Y., Liu, Y., Zhou, H., 2026. Large language models and futures price factors in China.
Journal of Futures Markets 46, 262–282.
Cheng, Y., Tang, K., 2024. GPT’s idea of stock factors. Quantitative Finance 24, 1301–1326.
Chin, J.T., Guo, X., Lin, H., Mei, Y., 2025. Technical indicators and the cross-section of
48

<!-- page 49 -->
corporate bond returns in a machine learning era. Journal of Financial Markets , 101029.
Choi, D., Jiang, W., Zhang, C., 2025. Alpha go everywhere: Machine learning and international
stock returns. The Review of Asset Pricing Studies 15, 288–331.
Cochrane, J.H., 2011. Presidential address: Discount rates. The Journal of Finance 66, 1047–
1108.
Ding, W., Mazouz, K., Ap Gwilym, O., Wang, Q., 2023. Technical analysis as a sentiment
barometer and the cross-section of stock returns. Quantitative Finance 23, 1617–1636.
Fabozzi, F.A., López de Prado, M., 2025. Implementing AI foundation models in asset manage-
ment: A practical guide. Journal of Portfolio Management 52.
Fama, E.F., French, K.R., 1993. Common risk factors in the returns on stocks and bonds.
Journal of Financial Economics 33, 3–56.
Fama, E.F., French, K.R., 2015. A five-factor asset pricing model. Journal of Financial Eco-
nomics 116, 1–22.
Fan, Z., Ruan, X., Ye, Y., 2026. Deep surrogate for non-affine stochastic volatility option
valuation models. Available at SSRN 6489158 .
Fan,Z.,Wang,M.M.,Ye,Y.,2025. Onoptions-drivenrealizedvolatilityforecasting: Information
gains via rough volatility model. Available at SSRN 5974814 .
Fang, J., Lin, J., Xia, S., Xia, Z., Hu, S., Liu, X., Jiang, Y., 2020. Neural network-based
automatic factor construction. Quantitative Finance 20, 2101–2114.
Giamouridis, D., 2017. Systematic investment strategies. Financial Analysts Journal 73, 10–14.
Giglio, S., Kelly, B., Xiu, D., 2022. Factor models, machine learning, and asset pricing. Annual
Review of Financial Economics 14, 337–368.
Gu, S., Kelly, B., Xiu, D., 2020. Empirical asset pricing via machine learning. The Review of
Financial Studies 33, 2223–2273.
Han, Y., Yang, K., Zhou, G., 2013. Anewanomaly: Thecross-sectionalprofitabilityoftechnical
analysis. Journal of Financial and Quantitative Analysis 48, 1433–1461.
Han, Y., Zhou, G., Zhu, Y., 2016. A trend factor: Any economic gains from using information
over investment horizons? Journal of Financial Economics 122, 352–375.
Harvey, C.R., 2017. Presidential address: The scientific outlook in financial economics. The
Journal of Finance 72, 1399–1440.
49

<!-- page 50 -->
Harvey, C.R., Liu, Y., 2020. False (and missed) discoveries in financial economics. The Journal
of Finance 75, 2503–2553.
Harvey, C.R., Liu, Y., 2021. Lucky factors. Journal of Financial Economics 141, 413–435.
Harvey, C.R., Liu, Y., Zhu, H., 2016. ... and the cross-section of expected returns. The Review
of Financial Studies 29, 5–68.
He, S., Lv, L., Manela, A., Wu, J., 2025. Chronologically consistent large language models.
arXiv preprint arXiv:2502.21206 .
Jegadeesh, N., Titman, S., 1993. Returns to buying winners and selling losers: Implications for
stock market efficiency. The Journal of Finance 48, 65–91.
Kelly, B., Malamud, S., Zhou, K., 2024. The virtue of complexity in return prediction. Journal
of Finance 79, 459–503.
Kelly, B., Xiu, D., 2023. Financial machine learning. Foundations and Trends® in Finance 13,
205–363.
Kelly, B.T., Pruitt, S., Su, Y., 2019. Characteristics are covariances: A unified model of risk
and return. Journal of Financial Economics 134, 501–524.
Ko,K.C.,Wang,Y.,Yang,N.T.,2025. Short-termmovingaveragedistanceandthecross-section
of stock returns. Financial Analysts Journal 81, 121–141.
Kong, Y., Nie, Y., Dong, X., Mulvey, J.M., Poor, H.V., Wen, Q., Zohren, S., 2024a. Large
language models for financial and investment management: Applications and benchmarks.
Journal of Portfolio Management 51.
Kong, Y., Nie, Y., Dong, X., Mulvey, J.M., Poor, H.V., Wen, Q., Zohren, S., 2024b. Large
language models for financial and investment management: Models, opportunities, and chal-
lenges. Journal of Portfolio Management 51.
Lo, A.W., Mamaysky, H., Wang, J., 2000. Foundations of technical analysis: Computational
algorithms, statistical inference, and empirical implementation. The Journal of Finance 55,
1705–1765.
Lopez-Lira, A., Tang, Y., 2023. Can ChatGPT forecast stock price movements? return pre-
dictability and large language models. arXiv preprint arXiv:2304.07619 .
Loughran, T., McDonald, B., 2011. When is a liability not a liability? textual analysis, dictio-
naries, and 10-Ks. The Journal of Finance 66, 35–65.
50

<!-- page 51 -->
Neely, C., Weller, P., Dittmar, R., 1997. Is technical analysis in the foreign exchange market
profitable? a genetic programming approach. Journal of Financial and Quantitative Analysis
32, 405–426.
Newey, W.K., West, K.D., 1987. A simple, positive semi-definite, heteroskedasticity and auto-
correlationconsistent covariance matrix. Econometrica 55, 703–708.
Novy-Marx, R., Velikov, M., 2016. A taxonomy of anomalies and their trading costs. The
Review of Financial Studies 29, 104–147.
López de Prado, M., 2018. Advances in financial machine learning. John Wiley & Sons.
Rapach, D.E., Strauss, J.K., Tu, J., Zhou, G., 2019. Industry return predictability: A machine
learning approach. The Journal of Financial Data Science 3, 9.
Sharpe, W.F., 1964. Capital asset prices: A theory of market equilibrium under conditions of
risk. The Journal of Finance 19, 425–442.
Tetlock,P.C.,2007. Givingcontenttoinvestorsentiment: Theroleofmediainthestockmarket.
The Journal of Finance 62, 1139–1168.
Wei, J., Wang, X., Schuurmans, D., Bosma, M., Xia, F., Chi, E., Le, Q.V., Zhou, D., et al.,
2022. Chain-of-thought prompting elicits reasoning in large language models. Advances in
Neural Information Processing Systems (NeurIPS) 35, 24824–24837.
Xu, Y., Xuan, Y., Zheng, G., 2025. AI agent misinformation when assisting financial decision-
making: Early evidence from stock recommendations. Available at SSRN 5651130 .
Yao, S., Zhao, J., Yu, D., Du, N., Shafran, I., Narasimhan, K., Cao, Y., 2023. ReAct: Syn-
ergizing reasoning and acting in language models. International Conference on Learning
Representations (ICLR) , 1–33.
Ye, Y., Fan, Z., Ruan, X., 2025. Modeling the implied volatility smirk in China: Do non-affine
two-factor stochastic volatility models work? Journal of Futures Markets 45, 612–636.
51

<!-- page 52 -->
Appendix
A. A Conceptual Framework for Agentic Factor Discovery
The methodology in this study extends traditional automated machine learning by adopting
an autonomous agent-based framework. Unlike conventional methods that rely on brute-force
combinatorial search and are consequently susceptible to p-hacking, this approach replicates the
iterativeheuristicanddisciplinedhypothesistestingofaquantitativeresearcher. Theframework
integrateslogicalreasoning(Weiet al., 2022) withsequentialactionexecution(Yaoetal.,2023).
By requiring the formulation of an economic rationale prior to empirical validation, the system
is structured to mitigate the risk of data-mining in high-dimensional factor spaces.
A.1. The Reasoning-Action (ReAct) Framework
The core logic of the factor discovery agent follows the ReAct paradigm (Yao et al., 2023),
which interleaves reasoning traces and task-specific actions. In our framework, the agent’s
decision-making process at each step t is formalized as:
(r ,a ) ∼ π(s ,h ) (A.1)
t t t t
wherer isareasoningtrace(the"thought"oreconomicrationale),a istheaction(thegenerated
t t
factor code), s is the current state of the factor library, and h is the historical trajectory of
t t
previous attempts.
By incorporating “Chain-of-Thought” (CoT) prompting (Wei et al., 2022), the agent is re-
quired to verbalize an economic rationale r before producing the mathematical expression a .
t t
This ensures that the search space is constrained to factors that are a priori economically plau-
sible. The probability of generating a specific action can be conceptually decomposed as shown
in Eq. A.2:
(cid:88)
P(a |s ) = P(a |r ,s )P(r |s ) (A.2)
t t t t t t t
rt
The decomposition in Eq. A.2 illustrates that the probability of discovering a high-quality
factor a is conditioned on the quality of the latent reasoning r , thereby acting as a structural
t t
regularizer against data-mining and spurious correlations.
52

<!-- page 53 -->
A.2. Interaction with the Backtesting Environment
Following the execution of action a , the agent receives an observation o from the environ-
t t
ment E (e.g., Sharpe ratio, information coefficient, or execution errors). The state for the next
iteration is updated via a transition function T defined in Eq. A.3:
s = T(s ,a ,o ) (A.3)
t+1 t t t
Thisclosed-loopsystemallowstheagenttoadjustitssubsequentreasoningr basedonthe
t+1
empiricalperformanceofa . Theobjectiveoftheagentistomaximizetheexpectedrisk-adjusted
t
utility of the discovered factor set over a finite horizon T, as formulated in Eq. A.4:
(cid:34) T (cid:35)
(cid:88)
maxE γtR(s ,a ,o ) (A.4)
π t t t
π
t=1
where R(·) is the reward function and γ is the discount factor.
A.3. Note on the Conceptual Framework
It is important to emphasize that Eq. A.1 through Eq. A.4 serve as a conceptual framework
to formalize the generative process of the Large Language Model (LLM), rather than an analyt-
ically tractable econometric model. In our implementation, the probability distributions, such
as P(r |s ) in Eq. A.2, are implicitly parameterized by the pre-trained weights of the LLM and
t t
the contextual prompts, rather than being explicitly estimated via maximum likelihood meth-
ods. The value of this formalization lies in illustrating how the agentic workflow simulates the
scientific method—formulating hypotheses, executing empirical tests, and updating beliefs—to
mitigate the risk of p-hacking in high-dimensional factor spaces.
B. Factor Aggregation and Portfolio Construction
The transition from individual factor discovery to portfolio construction follows a structured
“forecast-then-sort” framework. The methodology for synthesizing high-dimensional signals,
constructing rank-based portfolios, and evaluating their economic significance follows the es-
tablished literature (Han et al., 2016; Rapach et al., 2019; Choi et al., 2025).11 This section
11While these studies share the same “forecast-then-sort” philosophy, the underlying predictive en-
gines vary: Han et al. (2016) employ linear cross-sectional regressions for trend signals, Rapach et al.
53

<!-- page 54 -->
details the technical implementation of these steps.
B.1. Signal Synthesis and Expected Return Proxies
For each asset i at time t, we aggregate the information from the M discovered factors x
i,t
into a single composite score, S . This score serves as our proxy for the conditional expected
i,t
return in the next period:
S ≡ Eˆ[r |x ] = M(x ;Θ) (B.1)
i,t i,t+1 i,t i,t
where M(·) represents the predictive aggregation model. This formulation provides a flexi-
ble alternative to heuristic aggregation methods. For instance, Blitz et al. (2023) argues for
the robustness of simple equal-weighted Z-score averaging,12 noting that it effectively mitigates
overfitting and selection bias in high-turnover signal contexts. While such a parsimonious ap-
proach avoids the estimation risks inherent in complex models, our predictive framework M(·)
is designed to account for the varying predictive strength and cross-correlation structure of the
underlying factors, thereby mapping the high-dimensional signal space more directly to the eco-
nomic scale of expected returns. This approach effectively captures information across multiple
investment horizons by condensing a high-dimensional set of signals into a singular predictive
proxy.
B.2. Cross-Sectional Sorting and Portfolio Formation
To translate these continuous forecasts into a tradable strategy, we employ a non-parametric
sorting procedure. In each period t, we rank all assets in the cross-section based on their
predicted returns S and partition the universe into P quantile portfolios:
i,t
P = {i : Rank(S ) ∈ Quantile }, p = 1,...,P (B.3)
p,t i,t p
(2019) apply machine learning to industry-level sorting, and Choi et al. (2025) utilize machine learning
frameworks to evaluate the economic value of discovered alphas.
12Specifically, the equal-weighted composite score is defined as:
M
1 (cid:88)
S = z (B.2)
i,t M i,t,m
m=1
where z is the cross-sectionally standardized value of factor m. This approach implicitly assumes
i,t,m
uniformpredictivepoweracrossallsignalsandignorestheircovariancestructuretominimizeestimation
risk.
54

<!-- page 55 -->
The portfolio return for each quantile is calculated as the weighted average of its constituents,
R = (cid:80) w r . This procedure allows us to evaluate the monotonicity of returns
p,t+1 i∈Pp,t i,t i,t+1
across different levels of forecasted alpha.
B.3. The Long-Short Spread and Economic Value
The primary object of interest is the zero-investment long-short portfolio (High-minus-Low),
which captures the return spread between the top and bottom quantiles:
R = R −R (B.4)
HML,t+1 P,t+1 1,t+1
The performance of such ranked portfolios provides a robust measure of the economic value of
return predictability. We further evaluate this spread using risk-adjusted alphas to ensure that
the agent’s discovered signals extract information that is not spanned by existing common risk
factors.
C. Non-linear Factor Aggregation via LightGBM
To aggregate the high-dimensional factor candidates discovered by our agent, we employ
the Light Gradient Boosting Machine (LightGBM) framework. As noted by recent emerging
machine learning in asset pricing literature (Gu et al., 2020; Kelly et al., 2024; Choi et al.,
2025), the cross-section of stock returns is characterized by complex non-linearities and high-
dimensional interactions that traditional linear models are ill-equipped to capture. LightGBM
addresses these challenges through a regularized, additive tree-based approach.
C.1. The Boosting Estimator
We model the conditional expected return E[r |x ] as an ensemble of K regression trees:
i,t+1 i,t
K
(cid:88)
rˆ = ηf (x ;θ ) (C.1)
i,t+1 k i,t k
k=1
where η ∈ (0,1] is the learning rate (or "shrinkage" parameter) that controls the contribution of
each individual tree, and f (·) is a decision tree with parameters θ (representing split variables,
k k
split points, and leaf weights). This additive structure allows the model to learn the predictive
function sequentially, with each subsequent tree fitting the residuals of the previous ensemble.
55

<!-- page 56 -->
C.2. Regularized Objective and Splitting Logic
The model is optimized by minimizing a loss function that balances fit and parsimony. At
each iteration k, the new tree f is chosen to minimize:
k
J
L(k) = (cid:88) L(r ,rˆ (k−1) +f (x ))+γJ + 1 λ (cid:88) w2 (C.2)
i,t+1 i,t+1 k i,t 2 j
i,t j=1
whereJ isthenumberofleavesandw aretheleafweights. TheinclusionofL andL penalties
j 1 2
(γ and λ) is crucial in a finance context to prevent the model from over-fitting to idiosyncratic
noise.
The optimal split for any node is determined by maximizing the gain in the second-order
Taylorapproximationofthelossfunction. Forapotentialsplitintoleft(I )andright(I )child
L R
nodes, the gain G is defined as:
G = 1 (cid:34) ( (cid:80) i∈IL g i )2 + ( (cid:80) i∈IR g i )2 − ( (cid:80) i∈I g i )2 (cid:35) −γ (C.3)
(cid:80) (cid:80) (cid:80)
2 h +λ h +λ h +λ
i∈IL i i∈IR i i∈I i
where g and h are the first and second-order gradients of the loss function. This criterion
i i
ensures that the model prioritizes splits that offer the most significant reduction in forecast
error relative to the increased model complexity.
C.3. Handling High-Dimensional Factor Spaces
LightGBM introduces two specific algorithmic innovations that are particularly beneficial
for the "factor zoo" problem:
• Gradient-based One-Side Sampling (GOSS): By down-sampling observations with
small gradients and focusing on those with large gradients, GOSS ensures that the es-
timator is driven by the most informative (and often hardest to predict) states of the
economy.
• Exclusive Feature Bundling (EFB): Financial factors often exhibit high degrees of
collinearity. EFB bundles mutually exclusive features to reduce the effective dimensional-
ity of the search space, which enhances the robustness of the split selection process.
C.4. Implementation and Out-of-Sample Guardrails
To ensure the economic validity of our results, we implement several safeguards:
56

<!-- page 57 -->
1. Temporal Validation: We use a rolling-window training scheme (e.g., training on years
1 to t to predict t+1). This ensures that the model only uses information available at
the time of the forecast, strictly avoiding look-ahead bias.
2. Hyper-parameter Tuning: The complexity of the trees (e.g., maximum depth, number
ofleaves)andtheshrinkagerate(η)aretunedviatime-seriescross-validation. Thisprocess
ensures that the model’s non-linear capacity is appropriately scaled to the signal-to-noise
ratio of the data.
3. Feature Importance: Beyond the portfolio sorts, we analyze the "Gain" and "Fre-
quency"ofeachfactorwithintheLightGBMensembletoidentifywhichdiscoveredsignals
are the primary drivers of the non-linear predictive power.
D. Addtional tables and figures
This section provides supplementary figures to support the main empirical analysis. Exhibit 20
illustrates the cumulative performance across ten decile portfolios for each factor generated by
the autonomous system. Exhibit 21 details the cumulative returns of the corresponding long-
short, long-only, and short-only portfolio legs. Finally, Exhibit 22 displays the diagnostic grid
for the Information Coefficient (IC), featuring both rolling averages and daily distributions.
57

<!-- page 58 -->
Exhibit 20: Univariate portfolio sort: Cumulative performance of ten decile portfolios
This figure reports univariate portfolio-sort results for Factor 1–Factor 11 over the out-of-sample period
2021-01-01to2024-12-31atdailyfrequency. Foreachdateandfactor,stocksaresortedintotenportfolios
by cross-sectional factor scores, where D1 is the lowest-score decile and D10 is the highest-score decile;
each decile return is the cross-sectional equal-weight mean of next-day returns y. Within each factor
panel,thetenlines(D1–D10)plotcumulativedecileperformancetransformedaslog(1+CumRet),where
(cid:81)
CumRet = (1+r )−1. Thehorizontalaxisiscalendartime, theverticalaxisislog(1+CumRet),
t τ≤t τ
and the dashed horizontal line indicates the zero-cumulative-return benchmark.
58

<!-- page 59 -->
Exhibit 21: Univariate portfolio sort: Cumulative performance of long-short, long-only,
short-only portfolios
This figure reports per-factor cumulative portfolio returns for Factor 1–Factor 11 over the test period
2021-01-01 to 2024-12-31 at daily frequency. On each date, stocks are sorted into deciles by factor score
inthecross-section;D10denotesthetop-scoredecileandD1denotesthebottom-scoredecile,withdecile
daily returns defined as cross-sectional equal-weight means of next-day returns y. Within each factor
panel, long is the cumulative return of D10, short is the cumulative return of the short leg (−D1), and
(cid:81)
ls is the cumulative return of D10−D1, each formed by compounding daily returns as (1+r )−1.
t t
The horizontal axis is calendar time, the vertical axis is cumulative return, and the dashed horizontal
line indicates the zero-return benchmark in every subplot.
59

<!-- page 60 -->
Exhibit 22: IC Diagnostics Grid: Top Rolling IC, Bottom Daily IC
ThisgridreportstheDailyRankICforeachfactor. Uppersubplotsshow20-dayand60-dayrollingmeans;lowersubplots
showthecorrespondingdensitydistributions. Thezero-benchmarkisindicatedbyverticaldashedlines.
60
