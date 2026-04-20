# Emergence of Statistical Financial Factors by a Diffusion Process

| 字段 | 内容 |
|------|------|
| ArXiv ID | 2604.12197v1 |
| 发布日期 | 2026-04-14 |
| 作者 | Jose Negrete, Jaime Joel Ramos |
| 分类 | q-fin.CP, nlin.CD |
| PDF | https://arxiv.org/pdf/2604.12197v1 |

## 摘要

Factor models characterize the joint behavior of large sets of financial assets through a smaller number of underlying drivers. We develop a network-based framework in which factors emerge naturally from the structure of interactions among assets rather than being imposed statistically. The market is modeled as a system of coupled iterated maps, where assets' return depends on its own past returns and those of related assets. Effectively modeling the influence of irrational traders whose decisions are based on the past movements of a collection of stocks. The interaction structure between stock returns is defined by a coupling matrix derived from an orthogonal transformation of a Laplacian matrix that gradually links initially isolated clusters into a fully connected network. Within this structure, stable patterns of co-movement arise and can be interpreted as financial factors. The relationship between the initial clustering and the number of observed factors is consistent with a center manifold reduction. We identify an optimal regime in which assets' variance is effectively explained by the set of factors produced by the network. Our framework offers a structural perspective based on interaction-based factor formation and dimension reduction in financial markets.

---

## 正文

<!-- page 1 -->
Emergence of Statistical Financial Factors by a Diffusion Process
Jose Negrete Jr1 and Jaime Joel Ramos2
1)Instituto de Ciencias Sociales y Administraci´on (ICSA),
Universidad Aut´onoma de Ciudad Ju´arez (UACJ), Ciudad Ju´arez, Chihuahua,
M´exico.
2)School of Business, University of North Texas at Dallas (UNTD),
Dallas, Texas, USA.
Factor models characterize the joint behavior of large sets of financial assets through
a smaller number of underlying drivers. We develop a network-based framework in
which factors emerge naturally from the structure of interactions among assets rather
than being imposed statistically. The market is modeled as a system of coupled
iterated maps, where assets’ return depends on its own past returns and those of
related assets. Effectively modeling the influence of irrational traders whose decisions
are based on the past movements of a collection of stocks. The interaction structure
between stock returns is defined by a coupling matrix derived from an orthogonal
transformation of a Laplacian matrix that gradually links initially isolated clusters
intoafullyconnectednetwork. Withinthisstructure, stablepatternsofco-movement
arise and can be interpreted as financial factors. The relationship between the initial
clustering and the number of observed factors is consistent with a center manifold
reduction. We identify an optimal regime in which assets’ variance is effectively
explained by the set of factors produced by the network. Our framework offers a
structural perspective based on interaction-based factor formation and dimension
reduction in financial markets.
Keywords: Factor models; Network dynamics; Chaotic systems; Dimensionality re-
duction; Financial markets
1
6202
rpA
41
]PC.nif-q[
1v79121.4062:viXra

<!-- page 2 -->
Factors corresponds to a reduced number of signals that describes the time evo-
lution of a large cross-section of stocks. Here we wonder what might be their
possible origin. One possibility is that stocks reflect the movements dictated by
exogenous signals, this would be in agreement with the efficient market hypoth-
esis (EMH) where movements in the stock prices reflect the random movements
in the economy. An opposing view of the EMH is that traders are irrational and
make their decisions given the previous movements of a stock i.e. behaving as
a dynamical system. We use a combination of dynamical systems and network
theory to propose that factors might emerge from the activity given by irrational
traders.
I. INTRODUCTION
Factor models are central to empirical finance. They summarize co-movements across
many assets through a small set of underlying drivers. These underlying drivers determine
the systemic risk behind an investment portfolio i.e. the noise that cannot be mitigated by
(cid:104) (cid:105)
diversification1. A cross-section of K stocks with returns r = r(1),r(2),··· ,r(K) is reduced
t t t t
(cid:104) (cid:105)
to M common factors f = f(1),f(2),··· ,f(M) . The relationship between stock returns
t t t t
and latent factors is given by
r = Bf +ξ . (1)
t t t
Here M ≪ K, and B is an M ×K loading matrix whose elements β quantify the exposure
mk
of each stock to a given factor. The vector ξ accounts for any time deviations (or noise)
t
not explained by the factors. Factors are divided into two classes: economic and statistical
factors.
Thefirst economic factormodelproposed was theCapitalAssetPricing Model(CAPM)2,
wherestockreturnsdependonthemarketfactor. Thismodelgivesamathematicaldefinition
for the risk premium, which is the excess return a stock has as a function of risk. However,
independent tests with empirical data does not fulfill the CAPM predictions between risk
and return3. Extensions to CAPM have been proposed where different fundamentals like
firm size and book-to-market equity are taken to construct different factors4,5.
Alternatively, statistical factors correspond to a set of common orthogonal signals that
2

<!-- page 3 -->
are intrinsic to a cross section of stocks6,7. Techniques like principal components analysis
(PCA) and variations of it are used to infer factors from observed returns without explaining
their structural origin. Several authors have used random matrix theory to determine the
number M of factors behind a given cross section of stocks8–10. Interestingly, the CAPM
market factor displays a strong correlation with the first component extracted via PCA11.
Hereweponderonwhyfactorsemergeinthefirstplace? Accordingtotheefficientmarket
hypothesis (EMH) stock prices depend only on the fundamentals behind a firm. In EMH the
stock prices are only driven by random exogenous signals defined by the economy1. Still,
deviations from fundamental values are observed in trading markets which are driven by
investors exhibiting herding behavior or by the use of investment strategies like hedging 12.
These instances creates feedback mechanisms between investors and the market that are well
described by dynamical systems. Several works have explored the effect of different feedback
mechanisms such as trend following13, adaptation of expectations14,15 and leverage16. This
perspective motivates a shift: rather than treating factors as externally imposed or purely
statistical artifacts, we treat and understand them as emergent properties of a dynamical
system.
Modern financial markets are densely interconnected via shared information channels,
overlappinginvestorbases, sectoralrelationships, andcommoneconomicexposures. Ifassets
influence one another over time, coherent return patterns (i.e. factors) can arise naturally
from these interactions. Matrices can be used to define the structure of the interconnections
between stocks. Previous works suggest the existence of self-organization in finance17,18, as
transitions to a highly coordinated states were observed in both the dot-com and housing
crisis. These are instances of dimensionality reduction that can be achieved by two differ-
ent connectivity structures. In one case the structure is described by a low-rank matrix19
where the rank equals the reduced dimension20. The alternative case is a center manifold
reduction21 where the matrix nullity equals to the reduced dimension. The specific nonlin-
earities of a system determines if the rank or the nullity of a matrix determines the reduced
dimension20,21. We propose a network-based model that formalizes this structure and offers
insight into why certain factors appear from the perspective of dimensionality reduction.
3

<!-- page 4 -->
II. THE MODEL
A. A Chaotic Model For Asset Returns
Inter-day returns time series typically exhibit an absence of autocorrelation and heavy-
tailed distributions22. Also there is evidence that financial time series evolve with some
degree of chaotic dynamics23,24. Motivated by these, we model the evolution of r using cou-
t
pled iterative maps, which provide a suitable structural approach to deterministic dynamics
in interacting systems. A general coupled iterative map25,26 takes the form
ε
r = (1−ε)g(r )+ Cg(r ) (2)
t+1 t t
N
where C is a K × K connectivity matrix that determines how the K components of r
t
influence each component of r . The parameter N denotes the number of elements within
t+1
each cluster (defined below). The coupling parameter ε controls the components’ degree of
independence/dependence: when ε = 0 each asset evolves independently according to
(cid:16) (cid:17)
r(k) = g r(k) , (3)
t+1 t
whereas for ε = 1, every component is fully influenced by all other through a given weight
and the following mapping
C
r = g(r ). (4)
t+1 t
N
B. The Local Map g(r )
t
The mapping g(r ) is defined by the following steps:
t
u = h(r ) (5)
t t
u (cid:106)u (cid:107)
t t
u = − (6)
t+1
δ δ
r = h−1(u ). (7)
t+1 t+1
Inthisconstruction, Eq.(6)correspondstotheBernoullimap, awell-knownsourceofchaotic
dynamics27. The variable u is uniformly distributed on [0,1], and therefore its probability
t
4

<!-- page 5 -->
density function (pdf) is ρ(u ) = U [0,1]. This allows full control of the pdf of r when
t t
ε = 0, since
dh(r )
t
ρ(r ) = , (8)
t
dr
t
allowing us to specify desired properties through the choice of the transformation h(·). To
generate a heavy-tailed distribution the following mapping is chosen:
γ
ρ(r ) = sech(γ(r −r )). (9)
t t 0
π
This function produces a distribution with mean µ = r , variance σ2 = π2/4γ2 and excess
0
kurtosis κ = 2.
As a result, it reproduces two key stylized facts commonly observed in daily returns: (i)
absence of auto correlations and (ii) heavy-tailed probability densities. Fig. 1 illustrates
the wide tail distribution from Eq. 9, along with the effect of initial parameters γ (Fig. 1
(a)) and r (Fig. 1 (b)). Fig. 1 (c-d) shows the influence of the parameter δ in the chaotic
0
map of Eqs. 5-7, where smaller δ generate faster fluctuation and negligible auto correlation;
larger δ values yield smoother auto correlated time series.
To guide the selection of initial parameters, we computed the mean square error:
T
1 (cid:88)
MSE = (r − R )2, (10)
t t
T
t=1
between the generated series r and the Netflix (NFLX) return series R over T = 251 trading
days (25/07/2022 - 25/07/2023). Using a fixed random seed, we generated returns over a
parameter grid consisting of:
r ∈ seq(−0.02,0.02,by = 0.001) γ ∈ seq(5,100,by = 1)
0
δ ∈ seq(0.005,0.02,by = 0.001)∪c(0.25,0.03,0.04,0.05,0.75,0.1).
Each resulting series was evaluated using the MSE, the Ljung-Box test (H : no autocorre-
0
lation), and the Durbin-Watson statistic (DW) which jointly provide insight into autocor-
relation and overall fit.
A total of 86,591 series were generated. Approximately 15% produced unstable series to
a with less than 251 observations. Among the 73,438 fully generated series, 75% achieved an
MSE ≤ 0.0042, indicating that the model can match empirical returns with high accuracy
5

<!-- page 6 -->
FIG. 1. Properties of the distribution in Eq. (9). (a) demonstrates the effects of γ in the variance
σ2 = π2/4γ2: large γ produces smaller variance. (b) the effect of µ = r ; shifting the distribution
0
from µ = −0.02 (red) to µ = 0.02 (blue). (c) Illustrates the chaotic map effect of δ from Eq.
6: larger values of δ produces less noisy series when compared to small values producing rapid
changes. In particular, (c) compares the chaotic folding for δ = 0.5 (red) and noisy δ = 0.1 (green).
Consequently, δ impactssimulatedreturnsautocorrelation. (d)and(e)showtwosimulatedreturns
with γ = 60, r = 0.001 but different δ. In general, larger δ values produce auto correlated
0
series. (d), using δ = 0.5, produced a series with the Ljung-Box test p−value < 2.2e − 16 and
DW statistic of 0.0499 supporting auto correlation. (e), using δ = 0.1 produces negligible auto
correlated series with the Ljung-Box test p−value = 0.9905 and DW statistic of 2.0076 ideal to
support no autocorrelation.
across a broad range of initial parameters. Low values of δ generally yielded negligible
autocorrelation, consistent with observations on stock returns22. Focusing on δ, roughly
86% of the complete series had a Ljung-Box p−value ≥ 0.05 and a DW statistic in the
interval (1.75,2.25), both of which indicate the absence of autocorrelation. Specifically, δ
valuesof0.005,0.010,0.020and0.050producetendedtoproduceserieswithMSE> 0.005or
incomplete trajectories. These conclusions held robustly across all values of r . Accordingly,
0
and without loss of generality, the remainder of this work adopts the parameter values
6

<!-- page 7 -->
δ = 0.011, γ = 60 and r = 0.001. These are the values used in Fig. 2 (b), accurately
0
representing NFLX (Fig. 2 (e)) with a MSE of 0.0016.
(cid:16) (cid:17)
Fig. 2 (a) displays the mapping r(k) = g r(k) for ε = 0 along with its cobweb
t+1 t
diagram. (b) - (d) display the associated time trace of the return r(k), the associated price
t
(cid:16) (cid:17) (cid:16) (cid:17)
series p(k) = 1+r(k) p(k), and the estimated pdf ρˆ r(k) . For comparison, (e) - (g)
t+1 t+1 t t
present the same quantities for NFLX. It is significant to highlight how simulated traces
exhibit NFLX behavior, including sudden large jumps, which manifest as heavy tails in the
estimated pdf. Our model produces these jumps endogenously rather than being driven by
external stress, consistent with studies showing that large return movements are intrinsic to
asset dynamics rather than triggered by external news28.
Fig. 3 (a) further compares the model-implied heavy-tail density produced by Eq. 9
using randomly drawn r and, as previously stated, fixed δ = 0.011 and γ = 60, over
0
100,000 iterations with a Gaussian distribution benchmark. With the chosen parameters,
the resulting pdf ρ(r ) has a mean of µ = 0.001 and a standard deviation of σ = 0.026 (Fig.
t
3(a)), arelationshipconsistentwithempiricalfinancialdatainwhichthestandarddeviation
exceeds the mean by an order of magnitude29. As a result of the slow decay in the tails, the
(k)
FIG. 2. (a) Iterative map followed by each unit r when ϵ = 0, along with cobweb trajectory for
t
(k)
a single realization. (b) Single realization for r that corresponds to the cobweb trajectory from
t
(i)
(a). (c) Time evolution of the price trajectory that corresponds to the single realization of r .
t
(d) Estimate of probability distribution function ρˆ
(cid:0) r(k)(cid:1)
for single trajectory. (e) Returns for the
Netflix stock (NFLX) between 25/07/2022 and 25/07/2023. (f) Corresponding price evolution for
NFLX. (g) Estimate of probability distribution function for NFLX returns.
7

<!-- page 8 -->
FIG. 3. Probability density functions given by Eq. (9). (a) compares ρ(r) (blue line) with a
Gaussian distribution (red dashed line) showing that the model has an excess kurtosis κ = 2. (b) -
(e) display the sampling distribution of the mean µˆ, standard deviation σˆ, skewness sˆ, and kurtosis
κˆ of 100,000 generated returns.
√
convergence to the population mean is slower than ∼ 1/ T30. The sampling distributions
of mean µˆ, standard deviation σˆ, skewness sˆ, and kurtosis κˆ (Fig. 3 (b) -(e)) are also wider
than those expected for a normal distribution. Essentially, our model produces a universe of
returns with realistic levels of variability and heavy-tailed behavior, though the variability
is lower than that observed in actual markets29.
C. Network Interactions
The coupling matrix C is constructed by first defining a K ×K block matrix L of the
form
 
L 0 ··· 0
1
 
 0 L ··· 0 
 2 
L =   . . . . . . ... . . .   (11)
 
 
0 0 ··· L
M
which represents a network composed of M isolated clusters (Fig. 4 (a)). Each cluster
8

<!-- page 9 -->
contains N nodes that are fully interconnected through a block N ×N Laplacian matrix
 
1−N 1 ··· 1
 
 1 1−N ··· 1 
 
L i =   . . . . . . ... . . .   (12)
 
 
1 1 ··· 1−N
so that L has M eigenvalues λ = 0 and N −M eigenvalues λ = −N. Next, we generate a
random matrix A of size M ×N whose entries are drawn independently by the standard
normal distribution a ∼ N (0,1). Then, a QR decomposition is performed,
ij
A = QR, (13)
and the orthogonal matrix Q is retained. Finally, we apply a random rotation to L to define
the coupling matrix
C = QLQT. (14)
The resulting matrix C preserves the same eigenvalues as L but no longer exhibits a block-
diagonal structure. Instead, it corresponds to a fully interconnected network with nullity =
M and rank = K −M (Fig. 4 (b)).
III. RESULTS
A. Factor Detection and Quantifying the Balance of Loadings
In this work, we investigate how the number of factors given by Eq. (2) depends on both
the coupling strength ε and the structural properties of the coupling matrix C. Statistical
factors f are defined as the principal components of r whose signals exceed a given thresh-
t t
old. The main question, therefore, is how many principal components should be considered
as factors.
Previous studies addressed this question using random matrix theory (RMT)8,10,31. In
thatframework, anyeigenvalueofthecovariancematrixthatliesoutsidetheRMT-predicted
bounds is deemed significant. We propose a different methodology taking advantage of the
ability to simulate Eq. (2) for the uncoupled system (ε = 0). We compare the normalized
eigenvalue spectra ϕ(Λ ;ϵ) obtained from PCA between the uncoupled case (ε = 0) and a
k
9

<!-- page 10 -->
ˆ
coupled case (0 < ε ≤ 1). The number of significant factors M is defined as
(cid:88)
ˆ
M = θ(ϕ(Λ ;ε)−ϕ(Λ ;0)) (15)
k k
k
where θ(·) corresponds to the Heaviside step function.
The second question concerns the balance of factors loadings β for a given asset. For
mk
example, when a system is coupled into isolated clusters, as in the graph shown in Fig. 4
(a), each return r(k) may load primarily on the factor associated with its own cluster. In
t
such cases, the factor loadings are clearly imbalanced, with |β | > 0 for within clusters and
mk
|β | = 0 for between the others. We therefore require a measure that determines whether
mk
an asset’s loadings are balanced or biased towards only a few factors.
To capture this, we use the normalized Shannon entropy, defined as
(cid:0) (cid:1) 1 (cid:88)
H r(k) = − α log(α ) (16)
(cid:16) (cid:17) mk mk
ˆ
log M
m
where the factor weights α are given by
mk
ˆ
β
mk
α = (17)
mk (cid:80) ˆ
β
m mk
FIG. 4. Network representation of matrices. (a) Initial Laplacian matrix L is composed of block
matrices corresponding to fully interconnected networks of N = 4 components and M = 3
isolated clusters. (b) Coupling matrix obtained after rotating the original Laplacian matrix C =
QLQT. This corresponds to a fully interconnected network with pair wise symmetric connections.
10

<!-- page 11 -->
FIG. 5. Results from a single realization where L was initially composed with three clusters of 10
components each. (a) Normalized eigenvalues from PCA from the uncoupled system (ε = 0) that
serves as the noise floor for the coupled system (0 < ε ≤ 1). (b) Entropy H obtained for each
k
(k) (m) (k)
r , a measure of H = 0 means that a single factor f fits with r and H = 1 means that all
t k t t k
(k)
factors available fit r with the same weight for the loading.
t
ˆ
and the estimated loadings β are obtained with an ordinary least squares regression:
mk
(cid:88)
rˆ(k) = β ˆ f(m). (18)
t mk t
m
(cid:0) (cid:1) (cid:0) (cid:1)
A value of H r(k) = 1 indicates perfectly balanced loadings, while H r(k) = 0 corresponds
to relations only to a single factor.
Fig. 5 illustrates our approach to above mentioned questions, involving C for a generated
series composed initially of M = 3 clusters, K = 30, ε = 0.45, and 251 points. Fig. 5(a)
(cid:0) (cid:1)
displays ϕ(Λ ;ϵ) for the uncoupled and couple case. Fig. 5 (b) displays H r(k) values. For
k
this case, most assets exhibit H close to 1, and none are equal to zero, showing that the
k
resulting factors are non-trivial and that loadings are generally well balanced.
B. Emergence of factors
ˆ
With the definition for the number of significant factors M and the normalized Shannon
(cid:0) (cid:1)
entropy H r(k) as a measure of the balance of factor weights, we now examine the behavior
of the system Eq. 2 as a function of M and ε. Several realizations of Eq. 2 were simulated
11

<!-- page 12 -->
for 1 ≤ M ≤ 6 in steps of ∆M = 1, and for 0.2 ≤ ε ≤ 0.7 in steps of ∆ε = 0.01. The
number of elements per cluster was fixed to N = 10, and for each (M,ε) pair we performed
200 repetitions.
ˆ
Since we have proposed a method to identify M, the following analysis is carried out as
ˆ
a function of ε. For each iteration, we record the value of M and calculate, for each ε, the
corresponding sampling mean µ and the standard deviation σ . A summary of the results
Mˆ Mˆ
for the number of relevant factors is shown in Fig. 6. Panel (a) displays error bars for each ε
ˆ
to illustrate M estimation performance. For most values of M and ε, there is a clear region
where the error bars go to zero. In this region, the number of initial clusters M (i.e. the
ˆ
nullity of C) coincides exactly with the number of relevant factors M. This sharp dramatic
reduction in the error bar indicates the presence of a critical phase transition. However, for
M = 1 and M = 2, there are many error bars, unlike the cases for M > 3, where there are
none.
To understand the behavior of observation error bars, consider a simple model in which
ˆ ˆ
the number of relevant factors isM = M with probabilityp and M = M+1 with probability
1−p. Under this simple binary model, the relationship between the standard deviation σ
Mˆ
and the mean µ is given by
Mˆ
(cid:113)
σ = (M −µ )(µ +1−M). (19)
Mˆ Mˆ Mˆ
Fig. 6 (b) compares this theoretical relationship (i.e. Eq. 19, dashed line) with σ and
Mˆ
µ numerically calculated from the 200 iterations at each value of ε. The agreement is
Mˆ
strong up to the maximum value σ = 0.5 given by the model. Thus, cases with σ < 0.5
Mˆ Mˆ
ˆ ˆ
in Fig. 6 (a) can be interpreted as parameter regions where either M = M or M = M +1
is detected.
As mentioned above, when we observe an attractor of dimension M, each asset may follow
a common factor f(m) related to its initial cluster in the Laplacian matrix L. To examine
t
this possibility, we evaluated the mean µ and standard deviation σ of the normalized
H H
Shannon entropy. Again, the normalized Shannon entropy (Eq. 16) provides a measure of
how balanced the factor loadings β are for each return r(k).
mk t
Fig. 7 illustrates how factors indeed emerge within a specific region of the parameter
space, namely 0.36 < ϵ ≤ 0.58. For M = 1 this emergence is not consistent (Fig. 7 (a)),
whereas for M = 2 through 6, the behavior is highly consistent across simulations (Fig. 7
12

<!-- page 13 -->
FIG. 6. (a) Detected number of Mˆ factors from different ensembles. (b) Relationship between
the mean value µ and the error bars σ from panel (a). The dotted line corresponds to the
Mˆ Mˆ
relationship in a binary system where Mˆ = M is found with probability p and Mˆ = M+1 is found
with probability 1−p.
FIG. 7. Standard deviation in number of factors Mˆ as a function of ε. (a) M = 1, in the region
0.35 < ε ≤ 0.6 the standard deviation fluctuates between 0.0 < σ ≤ 0.5. (b) M = 2−6, there
Mˆ
is a universal region 0.36 < ε ≤ 0.58 where σ = 0.0.
Mˆ
(b)).
13

<!-- page 14 -->
FIG. 8. (a) Mean value µ of normalized Shannon entropy. (b) Standard deviation σ of normal-
H H
ized Shannon entropy. (c) Explained variance σ by factors f .
f t
C. Balance of Factor Weights
Fig. 8 (a) shows that in the same region where σ = 0, the mean Shannon entropy is
Mˆ
reduced to a non-zero value. Moreover, the mean entropy µ increases with M: systems
H
with a large number of clusters exhibit higher average entropy. At the same time, as the
standard deviation σ also increases, but its magnitude decreases as a function of M. For
H
example, variations are approximately 25% for M = 2, while for M = 6 they decrease to
about 7.5% (Fig. 8 (b)). Therefore, these observations conclude that the factor loadings in
this model are well balanced.
D. Variance Given by Factors
Finally, we examine the fluctuations around the manifold in phase space. This manifold,
ˆ
spanned by M common factors, attracts all initial trajectories. However, the existence of
these attractors does not automatically imply that the original phase-space dimension has
been reduced K → M. A proper measure of this reduction is the explained variance σ2
f
contributed by the factors in the relation given by Eq.(1). This quantity is the sum of the
eigenvalues associated with the observed factors from the spectra ϕ(Λ ;ε) (e.g., the three
k
initial values for ε = 0.45 in Fig. 5 (b) ). The explained variance is given by
Mˆ
(cid:88)
σ2 = Λ (20)
f k
k=0
14

<!-- page 15 -->
Fig. 8(c)showsthattheexplainedvariancereachesitsoptimalvalueσ2 = 1.0atε = 0.5.
f
At this point, 100% of the variance of each asset r(k) is given by the emergent factors. This
t
corresponds to the regime in which the phase space of dimension is strictly reduced from
K → M. Thus, although with small fluctuations, there exists an attracting region in phase
space corresponding to f(m). Indeed, this would correspond to the noise term in Eq. (1)
t
from factor analysis.
IV. DISCUSSION AND CONCLUSION
We explored the possibility that statistical factors emerge from a diffusive process among
interacting assets. Within this dynamic structure, stable patterns of co-movement emerge.
These patterns serve as latent dimensions of the system, analogous to factors in standard
financial models. Crucially, the number and structure of these latent dimensions are deter-
minedbytheunderlyingnetworkconnectivityratherthanbystatisticalselectionprocedures.
Our numerical findings highlight several key results. First, for M > 2 the number of
factors that emerge in the critical region (0.36 < ε ≤ 0.58) coincides with the number of
initial clusters, or equivalently, with the nullity of the coupling matrix C. This suggests
that the emergence of factors is governed more strongly by a center-manifold reduction than
by the low-rank hypothesis. Second, the factor loadings across assets are well balanced: no
asset is dominated by a single factor. Instead, each asset is influenced by multiple drivers,
consistent with the diverse risks present in real markets. Finally, we identify an optimal
coupling strength ε at which the factors generated by the system explain the total variance
of each asset in a coherent and interpretable manner.
From a Bayesian perspective, the relationship given by Eq.(1) denotes a direct and causal
link between factors f and returns r . A large body of research seeks to infer Bayesian
t t
network connectivity among assets32–37. Recent work emphasizes the need to understand
the Bayesian causal network between factors f themselves in order to reduce biases in
t
factor analysis and improve buy-sell decisions38,39. However, Bayesian networks permit only
one-way casual connections between elements and prohibit feedback loops. In contrast, our
modeladmitsfeedbackloopsthroughthecouplingmatrixC, therebyrelaxingthisrestriction
and offering a more general representation of causal networks.
Inaddition,thedynamicalstructureofourmodelmakesitwellsuitedforfrequency-domain
15

<!-- page 16 -->
network applications, where connectivity is studied across different temporal scales40–42. Be-
cause our factors emerge from an iterative and interconnected process, the co-movement
patterns they generate can be interpreted as dominant spectral modes of the system43.
This makes our model compatible with modern techniques that analyze financial contagion,
synchronization, and cyclical dependence in the frequency domain41,44–46. As a result, the
framework can be used not only for causal-network inference and factor modeling, but also
for applications such as detecting regime shifts, analyzing time-scale–specific spillovers, and
identifying structural channels of influence in financial markets40,41,47,48.
Takentogether, thepresenceoffeedbackloops, endogenousfactorformation, andspectral
interpretability make our model a general and versatile tool that can support many of the
most current and popular approaches for studying network structure in finance.
CONTRIBUTIONS STATEMENT
J. Negrete Jr. conceived the study. All authors performed calculations, developed
R/Python code, analyzed simulations, and wrote the manuscript. All authors discussed
the results and contributed to the final manuscript.
DATA ACCESS STATEMENT
DatasupportingthefindingsofthisstudyareopenlyavailableinYahooFinance,retrieved
using Python’s package yfinance. The Jupyter notebook used to perform the analysis and
figures of this paper is available in Google Colab https://colab.research.google.com/
drive/1NrQKD1ibd9M9t3S5f7-7BoHWocIkz2aO?usp=sharing.
REFERENCES
1B. Malkiel, A Random Walk Down Wall Street: The Best Investment Guide That Money
Can Buy (W. W. Norton, 2023).
2W. F. Sharpe, “Capital asset prices: A theory of market equilibrium under conditions of
risk,” The journal of finance 19, 425–442 (1964).
3M. C. Jensen, F. Black, and M. S. Scholes, “The capital asset pricing model,” Some
empirical tests (1972).
16

<!-- page 17 -->
4E. F. Fama and K. R. French, “The capital asset pricing model: Theory and evidence,”
Journal of economic perspectives 18, 25–46 (2004).
5E. F. Fama and K. R. French, “A five-factor asset pricing model,” Journal of Financial
Economics 116, 1–22 (2015).
6G. Chamberlain and M. Rothschild, “Arbitrage, factor structure, and mean-variance
analysis on large asset markets,” NBER Working Paper 0996 (1982) (1982),
https://doi.org/10.3386/w0996.
7G. Connor and R. A. Korajczyk, “A test for the number of factors in an approximate
factor model,” the Journal of Finance 48, 1263–1291 (1993).
8L. Laloux, P. Cizeau, M. Potters, and J.-P. Bouchaud, “Random matrix theory and
financial correlations,” International Journal of Theoretical and Applied Finance 3, 391–
397 (2000).
9V. Plerou, P. Gopikrishnan, B. Rosenow, L. A. N. Amaral, and H. E. Stanley, “Universal
and nonuniversal properties of cross correlations in financial time series,” Physical Review
Letters 83, 1471 (1999).
10V. Plerou, P. Gopikrishnan, B. Rosenow, L. A. N. Amaral, T. Guhr, and H. E. Stanley,
“Random matrix approach to cross correlations in financial data,” Physical Review E 65,
066126 (2002).
11M. Avellaneda, B. Healy, A. Papanicolaou, and G. Papanicolaou, “Principal eigenportfo-
lios for US equities,” SIAM Journal on Financial Mathematics 13, 702–744 (2022).
12D. Sornette and P. Cauwels, “Financial bubbles: mechanisms and diagnostics,” Review of
Behavioral Economics 2, 279–305 (2015).
13R.G.Palmer,W.B.Arthur,J.H.Holland,B.LeBaron, andP.Tayler,“Artificialeconomic
life: a simple model of a stockmarket,” Physica D: Nonlinear Phenomena 75, 264–274
(1994).
14W. B. Arthur, J. H. Holland, B. LeBaron, R. Palmer, and P. Taylor, “Asset pricing under
endogenous expectation in an artificial stock market,” Tech. Rep. (Santa Fe Institute,
1996).
15W.A.BrockandC.H.Hommes,“Arationalroutetorandomness,”Econometrica: Journal
of the Econometric Society , 1059–1095 (1997).
16S. Thurner, J. D. Farmer, and J. Geanakoplos, “Leverage causes fat tails and clustered
volatility,” Quantitative Finance 12, 695–707 (2012).
17

<!-- page 18 -->
17L. Borland, “Statistical signatures in times of panic: markets as a self-organizing system,”
Quantitative Finance 12, 1367–1379 (2012).
18J.-P. Bouchaud, “The self-organized criticality paradigm in economics & finance,” Avail-
able at SSRN 5657431 (2024).
19V.Thibeault,A.Allard, andP.Desrosiers,“Thelow-rankhypothesisofcomplexsystems,”
Nature Physics 20, 294–302 (2024).
20F. Mastrogiuseppe and S. Ostojic, “Linking connectivity, dynamics, and computations in
low-rank recurrent neural networks,” Neuron 99, 609–623 (2018).
21J. Guckenheimer and P. Holmes, Nonlinear oscillations, dynamical systems, and bifurca-
tions of vector fields, Vol. 42 (Springer Science & Business Media, 2013).
22R.Cont,“Empiricalpropertiesofassetreturns: stylizedfactsandstatisticalissues,”Quan-
titative finance 1, 223 (2001).
23J. Ho(cid:32)lyst, M. Z ˙ ebrowska, and K. Urbanowicz, “Observations of deterministic chaos in
financial time series by recurrence plots, can one control chaotic economy?” The European
Physical Journal B-Condensed Matter and Complex Systems 20, 531–535 (2001).
24M. Krishnadas, K. Harikrishnan, and G. Ambika, “Recurrence measures and transitions
in stock market dynamics,” Physica A: Statistical Mechanics and its Applications 608,
128240 (2022).
25A. Pikovsky, M. Rosenblum, J. Kurths, and A. Synchronization, “A universal concept in
nonlinear sciences,” Self 2, 10.1017 (2001).
26T. Yamada and H. Fujisaka, “Stability theory of synchronized motion in coupled-oscillator
systems.II:Themappingapproach,”ProgressofTheoreticalPhysics70,1240–1248(1983).
27E. Ott, Chaos in dynamical systems (Cambridge university press, 2002).
28A. Joulin, A. Lefevre, D. Grunberg, and J.-P. Bouchaud, “Stock price jumps: news and
volume play a minor role,” arXiv preprint arXiv:0803.1769 (2008).
29J.-P. Bouchaud and M. Potters, Theory of financial risk and derivative pricing: from
statistical physics to risk management (Cambridge university press, 2003).
30N. N. Taleb, “Statistical consequences of fat tails: Real world preasymptotics, epistemol-
ogy, and applications,” arXiv preprint arXiv:2001.10488 (2020).
31M. M. L. D. Prado, Machine learning for asset managers (Cambridge University Press,
2020).
18

<!-- page 19 -->
32R. Scaramozzino, P. Cerchiello, and T. Aste, “Information theoretic causality detection
between financial and sentiment data,” Entropy 23, 621 (2021).
33X. Guo, H. Zhang, and T. Tian, “Development of stock correlation networks using mutual
information and financial big data,” PloS one 13, e0195941 (2018).
34L. S. Chan, A. M. Chu, and M. K. So, “A moving-window bayesian network model for
assessing systemic risk in financial markets,” PloS one 18, e0279888 (2023).
35L. C. Bernardelli, C. E. CARRASCO GUTIERREZ, and T. Christiano, “The dynamic
interdependence of global financial markets: an analysis through dynamic bayesian net-
works,” Available at SSRN 4872632 (2024).
36M. Mroua, N. Souissi, and M. Donia, “Dependency and causal relationship between
‘bitcoin’and financial asset classes: A bayesian network approach,” International Journal
of Finance & Economics 29, 4888–4901 (2024).
37J. Y. Choi, C. Y. Lee, and M.-S. Oh, “Discovering causal relationships among financial
variables associated with firm value using a dynamic bayesian network,” Data Science in
Finance and Economics 5, 1 (2025).
38M. Lopez de Prado and V. Zoonekynd, “Correcting the factor mirage: A research protocol
for causal factor investing,” Available at SSRN 5931616 (2024).
39M. Lopez de Prado, A. Lipton, and V. Zoonekynd, “Causal factor analysis is a necessary
condition for investment efficiency,” Available at SSRN 5131050 (2025).
40J. Barun´ık and T. Kˇrehl´ık, “Measuring the frequency dynamics of financial connectedness
and systemic risk,” Journal of Financial Econometrics 16, 271–296 (2018).
41C. F. Jim´enez-Var´on and M. I. Knight, “A gnar-based framework for spectral estimation
of network time series: Application to global bank network connectedness,” arXiv preprint
arXiv:2510.06157 (2025).
42M. Barigozzi, M. Hallin, S. Soccorsi, and R. von Sachs, “Time-varying general dynamic
factor models and the measurement of financial connectedness,” Journal of Econometrics
222, 324–343 (2021).
43E. Laurence, N. Doyon, L. J. Dub´e, and P. Desrosiers, “Spectral dimension reduction of
complex dynamical networks,” Physical Review X 9, 011042 (2019).
44M. S ˇ kare and M. Porada-Rochon´, “The synchronisation between financial and business cy-
cles: a cross spectral analysis view,” Technological and economic development of economy
26, 907–919 (2020).
19

<!-- page 20 -->
45T. H. Le, H. X. Do, D. K. Nguyen, and A. Sensoy, “Covid-19 pandemic and tail-
dependency networks of financial assets,” Finance research letters 38, 101800 (2021).
46M.M.Burzala,“Contagioneffectsinselectedeuropeancapitalmarketsduringthefinancial
crisis of 2007–2009,” Research in International Business and Finance 37, 556–571 (2016).
47S. An, X. Gao, F. An, and T. Wu, “Early warning of regime switching in a complex
financial system from a spillover network dynamic perspective,” Iscience 28 (2025).
48T.Ando, M.Greenwood-Nimmo, andY.Shin,“Quantileconnectedness: modelingtailbe-
havior in the topology of financial networks,” Management Science 68, 2401–2431 (2022).
20
