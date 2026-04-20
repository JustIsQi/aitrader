# Interpretable Systematic Risk around the Clock

| 字段 | 内容 |
|------|------|
| ArXiv ID | 2604.13458v1 |
| 发布日期 | 2026-04-15 |
| 作者 | Songrun He |
| 分类 | q-fin.GN, q-fin.PM, q-fin.RM |
| PDF | https://arxiv.org/pdf/2604.13458v1 |

## 摘要

In this paper, I present the first comprehensive, around-the-clock analysis of systematic jump risk by combining high-frequency market data with contemporaneous news narratives identified as the underlying causes of market jumps. These narratives are retrieved and classified using a state-of-the-art open-source reasoning LLM. Decomposing market risk into interpretable jump categories reveals significant heterogeneity in risk premia, with macroeconomic news commanding the largest and most persistent premium. Leveraging this insight, I construct an annually rebalanced real-time Fama-MacBeth factor-mimicking portfolio that isolates the most strongly priced jump risk, achieving a high out-of-sample Sharpe ratio and delivering significant alphas relative to standard factor models. The results highlight the value of around-the-clock analysis and LLM-based narrative understanding for identifying and managing priced risks in real time.

---

## 正文

<!-- page 1 -->
Interpretable Systematic Risk around the Clock*
Songrun He
First draft: July 2025. This draft: April 2026.
Abstract
In this paper, I present the first comprehensive, around-the-clock analysis of systematic jump risk
bycombininghigh-frequencymarketdatawithcontemporaneousnewsnarrativesidentifiedasthe
underlying causes of market jumps. These narratives are retrieved and classified using a state-of-
the-art open-source reasoning LLM. Decomposing market risk into interpretable jump categories
revealssignificantheterogeneityinriskpremia,withmacroeconomicnewscommandingthelargest
and most persistent premium. Leveraging this insight, I construct an annually rebalanced real-
time Fama-MacBeth factor-mimicking portfolio that isolates the most strongly priced jump risk,
achieving a high out-of-sample Sharpe ratio and delivering significant alphas relative to standard
factor models. The results highlight the value of around-the-clock analysis and LLM-based
narrativeunderstandingforidentifyingandmanagingpricedrisksinrealtime.
JELClassification: C58,G11,G12,G14
Keywords: Systematic jump risk, High-frequency data, Around-the-clock analysis, Large lan-
guagemodels,Fama-MacBethregression
*SongrunHeisatWashingtonUniversityinSt.Louis(h.songrun@wustl.edu).Iamindebtedtomyadvisors,AsafManela(co-chair),Guofu
Zhou(co-chair),andNicolaeGaˆrleanu,fortheirinvaluableguidance,help,andsupport. IamalsoverygratefultoDarioCaldara,SidChib,Julie
ZhiyuFu,BrettGreen,ZhiguoHe,ArmandoGomes,ApoorvGupta,BrittanyLewis,KaiLi,SophiaZhengziLi,HongLiu,LinyingLv,Maarten
Meeuwis,XiaoliMeng,LorenzoNaranjo,KellyShue,andRenZhang,aswellastoseminarparticipantsatWashingtonUniversityinSt.Louis,City
UniversityofHongKong,TheChineseUniversityofHongKong,theABFRDoctoralResearchSymposium,andtheIMIMRisingStarsSeminar
Series,andtoconferenceparticipantsatthe21stAnnualOlinFinanceConference,fortheirveryhelpfulcomments.IacknowledgetheWellsFargo
AdvisorsCenterforFinanceandAccountingResearchforgenerousfinancialsupport.
6202
rpA
51
]NG.nif-q[
1v85431.4062:viXra

<!-- page 2 -->
1 Introduction
Understanding the sources and pricing of aggregate market systematic risk is one central question
in financial economics. There has been significant progress in using textual analysis to better
understand systematic risk and ex-ante compensation (Manela and Moreira, 2017; Bybee et al.,
2023,2024). Oneprominentcharacteristicandcomponentofsystematicriskisthatitfeatureslarge
jumps,whichtypicallyresultfromrealizationsofmajornewsevents,andjumpsareacontinuous-
timeconstructandthereforecanonlybeidentifiedusinghigh-frequencydata.
AletiandBollerslev(2025)providethefirsthigh-frequencyanalysisofnewseventsdrivingthe
high-frequency systematic jumps during the intraday trading period from 9:30 a.m. to 4:00 p.m.,
usingatraditionalNLPapproach. However,focusingonlyontheintradayperiodmightsufferfrom
an omitted variable bias, where a significant component of systematic risk materializes during the
overnight period (Hendershott et al., 2020; Boyarchenko et al., 2023; Glasserman et al., 2025).
Whatremainsmissingintheliteratureisacomprehensive,around-the-clockanalysisthatcaptures
all systematic jump events and their associated news drivers with more advanced large language
models. Suchaholisticapproachisessentialforforminganunbiasedandcompleteunderstanding
ofsystematicjumpriskanditsex-antepricing.
This gap is increasingly important in light of recent market developments. Both the NYSE
and Nasdaq have applied to extend their sessions to 22 and 24 hours, respectively, with Nasdaq
planning to trade “all night” as early as 2026.1 With this pending fundamental shift in the
architectureofthefinancialmarket,aclearunderstandingofsystematicriskbeyondthe9:30–4:00
windowismoreimportantthanever.
Inthispaper,Icombinethreerecentadvancestoprovidethefirstcomprehensiveanalysisofall
systematic jump events linked to contemporaneous real-time high-frequency news text from Dow
Jones Newswires in the U.S. equity market. First, I exploit around-the-clock high-frequency data
onboththecashequitymarketandtheS&P500E-minifutures,achievingnearly24-hourcoverage
1SeeNasdaq, March7, 2025onTheMarketsNeverSleep, ShouldTrading?, FinancialTimes, July20, 2025on
London Stock Exchange Group Considers Launch of 24-hour Trading, and The Economist, July 23, 2025 on Why
24/7TradingisaBadIdea.
1

<!-- page 3 -->
oftheU.S.marketover1997–2020.
Second, I adapt the continuous-time Fama-MacBeth regression of A¨ıt-Sahalia, Jacod, and
Xiu (2025) to decompose systematic risk into continuous and topic-specific jump components,
constructing “pure-play” factor-mimicking portfolios whose betas isolate each component using
a large panel of high-frequency S&P 1500 stock returns. I focus on jump risks for three reasons.
Firstly, these systematic jump events are interpretable. They provide a sharp identification with
a limited number of news events that modern LLMs can effectively process. Secondly, jumps
offer great efficiency for estimating risk loadings as the signal-to-noise ratio is high. Thirdly,
previous literature documents significant compensation for jump risks relative to the continuous
part (Bollerslev et al., 2016). As such, a clear understanding of systematic jump risk yields
substantial insights into the overall structure of the risk premium. The idea of using jumps to
identify interpretable risk sources is also linked to the high-frequency identification literature in
macroeconomics(RomerandRomer,1989,2000;NakamuraandSteinsson,2018a,b).
Third, I harness state-of-the-art open-source reasoning LLM Qwen (Yang et al., 2025) to
retrieve contemporaneous high-frequency news narratives triggering each jump and assign each
jumptooneofthefivemutuallyexclusiveeconomictopicsidentifiedbytheLLM:macroeconomic
news, corporate bellwethers, international spillovers, policy announcements, and geopolitical
events.
The new and more advanced analytical tools, along with the comprehensive analytical
framework,yieldseveralnewfindings.
Firstly, there is significant heterogeneity in risk premia in jumps belonging to different
economic categories. Unlike Aleti and Bollerslev (2025), who uncover the monetary policy as the
mostimportantcomponentforriskpremia,thecomprehensiveanalysis,includingovernightnews,
reveals the significant role played by macroeconomic news and large macro data surprises. The
factor-mimicking portfolio for macro jump risk earns an annual premium of 3.65% and a Sharpe
ratio of 0.78, which surpasses the market’s Sharpe ratio of 0.53 in the same period. Other types
of jump risks, including the monetary policy jump risk, earn smaller or statistically insignificant
2

<!-- page 4 -->
premiaoncemacrojumpsarecontrolledfor.
To highlight why the overnight window cannot be ignored, I directly quantify the costs of
focusing only on intraday returns: estimating jump risk premia with intraday data alone produces
markedly noisier and sometimes even mis-signed estimates, while the full around-the-clock
specification restores statistical significance and delivers a threefold improvement in risk-adjusted
investmentperformanceinrealtime.
Secondly, because of the enhanced language understanding and reasoning ability of the LLM,
classifyingjumpsintodistincteconomiccategoriesaddssignificantvaluetoinvestors. Areal-time
strategy that, each December, selects the pure-play jump-topic factor-mimicking portfolio with
the most significant risk premia and holds it for the next year attains an out-of-sample Sharpe
ratio of 0.95 with highly significant alphas against Fama and French (2018) six-factor model.
Placebo strategies with randomly assigned topics never match this performance, highlighting the
incrementalvaluecreatedbyLLM-basednarrativeunderstanding.
Moreover, I use the ChronoBERT model from He et al. (2025a) to show that such superior
performance does not come from lookahead bias or LLM memorizing major economic events.
Compared to the traditional NLP method benchmark, which assigns topics based on word count,
andtheLDAmodel(Bybeeetal.,2024),theLLM-basedapproachgeneratesriskpremiaestimates
with smaller standard errors and yields triple the Sharpe ratios in the real-time jump-risk factor-
mimickingportfolio.
These findings contribute to the asset pricing literature in three distinct ways. First, I offer
the first around-the-clock empirical decomposition of priced systematic jump risk using high-
frequency market data, complementing and extending prior studies that focus solely on intraday
movementsandmayoverlookovernightdynamics.
Second, I introduce a new way of integrating large language models into asset pricing,
demonstrating that reasoning LLMs can provide economically meaningful causal narrative
retrieval and classification of news-based systematic jump risk in a manner that enhances both
interpretability and out-of-sample investment performance. Third, I develop a fully automated
3

<!-- page 5 -->
frameworkforcontemporaneousidentificationoftheeconomicnarrativedrivingeachmarketjump
using open-source LLMs, enabling transparent and replicable mapping from raw high-frequency
newstointerpretablesourcesofsystematicrisk.
My work also relates to three broad strands of literature. First, a rich body of research in
high-frequency financial econometrics investigates the differential risk premia associated with
variousbetaestimates(Bollerslevetal.,2016;A¨ıt-Sahaliaetal.,2025;AletiandBollerslev,2025;
Bollerslev et al., 2025). High-frequency asset returns enable precise identification of betas, as the
probability of idiosyncratic jumps vanishes with finer sampling intervals (Li et al., 2017). This
literature documents significant risk compensation for jump betas. Building on these insights, my
paperextendshigh-frequencyanalysistotheovernightperiod,whichistypicallytreatedasasingle
observation or excluded in prior studies. I show that linking around-the-clock high-frequency
return jumpsto news narratives, andclassifying them intointerpretable categories usingadvanced
LLMs, uncovers heterogeneous risk premia. This categorization improves the design of real-time
investmentstrategies,whichoutperformportfoliosconstructedusingtheoriginalsystematicfactor.
Second, there is a large literature that contrasts the intraday period versus the overnight in the
equity market to examine different information channels or investor behaviors. French and Roll
(1986)andBoudoukhetal.(2019)studytheimplicationsofprivateinformation,revealedintraday
through trading, versus public information, disseminated overnight through announcements, for
stock volatility. Bogousslavsky (2021) documents that many equity anomalies earn positive
returns during the trading day but falter overnight, linking the pattern to higher overnight margin
requirements, lending fees, and the resulting limits to arbitrage. My paper extends this literature
focusing on the high-frequency dynamics of systematic risk overnight and providing a full
decompositionoftheinformationdrivingmarketjumpsinboththeintradayandovernightperiods.
Third, the growing adoption of LLMs in asset pricing has given rise to a rapidly expanding
literature focused on their use for interpretable financial insights. One line of research leverages
textual embeddings derived from LLMs to represent rich information and build downstream
models on these quantitative inputs (Jha et al., 2025; Chen et al., 2023; Sarkar, 2024; Lv, 2024,
4

<!-- page 6 -->
2025; He et al., 2025a). Another line of research uses prompt-based methods to directly instruct
LLMstoperformspecifictasks(Lopez-LiraandTang,2023;Bybee,2023;Beckmannetal.,2024;
Chen et al., 2025; He et al., 2025b). Building on this emerging literature, my paper highlights
a new application of LLMs for narrative retrieval in the context of high-frequency return jumps,
showingthatthisapproachnotonlyrevealsheterogeneityinriskpricingbutalsoyieldssubstantial
improvementsinportfolioperformance.
Taken together, I combine around-the-clock analysis with state-of-the-art LLMs to offer
a comprehensive perspective on systematic risk. The ability to fully attribute market jumps
to specific types of economic news in real time opens up new possibilities for constructing
interpretableandadaptiveinvestmentstrategies.
The rest of the paper is organized as follows. Section 2 introduces the methodology. Section 3
describes the data used in my study. Section 4 presents the main empirical results of my analysis.
Section5concludes.
2 Methodology
Inthissection,Ifirstdescribetheorganizingframeworkforanalyzingjumpriskpremiaassociated
with different systematic news topics in Subsection 2.1. Next, I present the methodology for
empirical estimation of the model in Subsection 2.2. Finally, I provide details on the use of the
QwenmodelforjumpnarrativeretrievalandtopicassignmentinSubsection2.3.
2.1 Organizing Framework
To study systematic risk and link it precisely to news events, I consider a continuous-time setting
withalargepanelofassetsdrivenbyasystematicriskfactor,dF,followingthesetupinA¨ıt-Sahalia
t
etal.(2025).
Firstly, the dF can be decomposed into the continuous part and the jump part in a continuous-
t
5

<!-- page 7 -->
timescenario:
K K
dF =λ Cdt+ ∑λ J,k dt+dFC+ ∑dF J,k , (1)
t t t t t
k=1 k=1
where λC and λJ are the risk premia associated with continuous movement (dFC) and discontin-
t t t
uous movement (dFJ) in the factor. The superscript k indexes different categories of jump risks
t
triggeredbydifferenttypesofnews.
Withthesetupoffactors,Icanmodeltheindividualasset’sexcessreturnsas:
(cid:32) (cid:33)
K K
dR = β C λ C+ ∑β J,k λ J,k dt+β CdFC+ ∑β J,k dF J,k +dRI, (2)
t t t t t t t t t t
k=1 k=1
where βC ∈ RN×1 and βJ ∈ RN×K are the betas of the individual asset with the continuous and
t t
jump movements of the factor, and dRI represents the idiosyncratic return movement of the asset
t
unspannedbythefactor. InAppendix6.2,Iprovideamicrofoundationforhowthestructureofrisk
premiawouldariseinequilibriumofanICAPMeconomywhenjumpscaptureshockstostochastic
investmentopportunities.
Since dFJ and dFC are non-tradable factors, I use the continuous Fama-MacBeth regression
t t
developed by A¨ıt-Sahalia et al. (2025) to build factor-mimicking portfolios for these distinct
sourcesofrisk.
Specifically, once βC and βJ are known, let β = [1,βC,βJ] ∈ RN×(K+2), I can construct the
t t t t t
factor-mimickingportfoliosas:
(β ′ β )−1β ′dR ≡W′dR , (3)
t t t t t t
where W ∈ RN×(K+2) is the portfolio weight matrix of the K+2 factors. The last K+1 factors
t
(excluding the intercept) satisfy the unique ‘pure-play’ property following the argument of Fama
6

<!-- page 8 -->
andFrench(2020)andChibetal.(2023):
w′1=0, ∀j=2,···K+2,
j
w′ β j =1, ∀j, (4)
j t
w′ β k =0, ∀j̸=k,
j t
wherew isthe j-thcolumnofW matrixandβ j isthe j-thcolumnofβ .2
j t t t
Equation 4 states that each factor-mimicking portfolio: (1) has portfolio weights summing to
0; (2) has unit β exposure to its own sources of risk; (3) has zero β exposure to other sources of
risk. Therefore, the Fama-MacBeth regression provides a way to isolate pure-play risk-exposure
andjointlycontrolalltheothertypesofrisks.
Moreover, if news text can provide context for the reasons for systematic jumps, the Fama-
MacBeth framework allows for interpretable attribution of systematic risks grouped into different
categories.
2.2 Empirical Estimation
TheprevioussectionoffersarationaleforstudyingFama-MacBethfactor-mimickingportfoliosat
thepopulationlevel. Inthispart,Idiscussindetailtheempiricalestimationofthecontinuous-time
Fama-MacBethmodels.
In the first-pass time-series regression, I estimate the factor loadings. There is an important
aspect of continuous-time models compared to the low-frequency counterpart. That is to
distinguish the jump movement from the continuous movements in the factor, as the exposure
andriskcompensationcanbedifferentforthetwocomponents.
For this task, I follow the convention in high-frequency econometrics (A¨ıt-Sahalia and Jacod,
2014). Ifthemovementinfactorreturnsislargerthanthefollowingthreshold,Iclassifythereturn
2Iprovideaproofofthesepure-playpropertiesoftheFama-MacBethfactorsinAppendix6.1.
7

<!-- page 9 -->
asajump:
F(cid:98)
t
J
,i
=F
t,i
×1
{|F t,i |≥un
√
τi TVt∆ϖ n }
, (5)
where u is a scaling constant, τ is the time-of-the-day volatility adjustment factor, TV stands
n i t
for truncated variance for trading day t, ∆ is the sampling interval length, and ϖ is the exponent
n
parameter. TheTV isestimatedbyconsideringfactorreturns,truncatinglargemovements:
t
n
TV = ∑|F |21 √ , (6)
t t,i {|F t,i |≤un τi BVt∆ϖ n }
i=1
where BV t = π 2n− n 1 ∑ n i=2 |F t,i−1 ||F t,i |. Following Aleti and Bollerslev (2025), I use a truncation
thresholdu =3andanexponentϖ =0.49intheempiricalidentificationofjumpmovements.
n
After identifying the jump movement, I can link it to contemporaneous news text and identify
economically meaningful groups of jumps triggered by different types of news events. I leave the
discussionofusingtextualanalysistoidentifymeaningfulgroupsofjumpstothenextsubsection.
Fornow,takethesetopicgroupsasgiven,andIcanwritethetopic-specificjumpsas:
F(cid:98)
t
J
,i
,k =F(cid:98)
t
J
,i
×1
{JumpNews t,i ∈Topic k }
. (7)
J,k
Because jumps are rare, I exploit every jump observed up to and including t to estimate β ,
t
followingtheprocedureproposedinLietal.(2017). Let
(cid:110) (cid:111)
J,k
J
t
(k)= (τ,i):τ ≤t,F(cid:98)
τ,i
̸=0 ,
andstackthecorrespondingfactorandreturnvectors:
F
t
J,k =(F(cid:98)
τ
J
,
,
i
k )
(τ,i)∈Jt(k)
, ∆nRJ
m,t
=(∆nR
m,τ,i
)
(τ,i)∈Jt(k)
.
Thereal-timejumpbetaforassetmandtopick attimet isthen:
(cid:16) (cid:17)−1
β(cid:98) J,k = F J,k⊤ F J,k F J,k⊤ ∆nRJ . (8)
m,t t t t m,t
8

<!-- page 10 -->
Effectively, the estimator isolates the observations where the systematic factor jumps and uses
thesetimeperiodstouncovertheβ fortheassets.
These jump movements in factors enable precise identification of βs because, at such times,
nearly all large asset-level price changes are driven by the corresponding large move in the
factor. As the sampling interval shrinks, the probability that an idiosyncratic jump coincides
with a systematic one converges to zero. As a result, even if the observations used are small,
the estimates can be very tight with low standard errors. I then concatenate everything together
and let β(cid:98) J ∈ RNt×K denote the matrix of jump betas for the total number of N assets at time t
t t
acrossK differentjumpcategories.
On the other hand, I estimate the continuous βC of assets using a local window, which
t
is similar to the low-frequency counterpart as in Lewellen and Nagel (2006). Different from
the jump betas, continuous betas can be estimated using a rolling window because there are
hundreds of observations each month that provide sufficient statistical power. A shorter window
captures evolving betas without oversmoothing. The use of high-frequency data also facilitates
precise estimation with low standard errors—a theoretical advantage noted in Merton (1980) and
empiricallyvalidatedbyA¨ıt-Sahaliaetal.(2020).
Definetheset:
(cid:112)
C ={(τ,i):t−l <τ ≤t,|F |<u τTV ∆ϖ},
t τ,i n i τ n
wherel istheparametercontrollingtherollingwindowlength. Stackallcontinuousmovementsin
factorsandassetreturns:
(cid:16) (cid:17)
FC =(F ) , ∆nRC = ∆nRC .
t τ,i (τ,i)∈Ct m,t m,τ,i
(τ,i)∈Ct
Thecontinuousbetacanbeestimatedas:
(cid:16) (cid:17)−1
β(cid:98) C = FC⊤FC FC⊤∆nRC . (9)
m,t t t t m,t
Afterthisstep,letβ(cid:98) C bethevectorstackingallcontinuousbetaestimates.
t
9

<!-- page 11 -->
In the second-pass cross-sectional regression, I use real-time β estimates as the portfolio
weights to form the Fama-MacBeth factor-mimicking portfolios as in Equation (3). Let β(cid:98) =
t
[1,β(cid:98) C,β(cid:98) J]bethestackedβ matrixofallassetsavailableattimet. Thefactor-mimickingportfolio
t t
canbeformedas:
(β(cid:98) ′ β(cid:98))−1β(cid:98) ′∆nR ∈R(K+2)×1. (10)
t t t i t
As shown in Fama and French (2020), these (K+2)-dimensional factor-mimicking portfolios
exhibit unique pure-play properties: each portfolio is specifically designed to isolate a particular
sourceofsystematicriskwhileminimizingexposuretoallotherriskfactors.
Another key advantage of the high-frequency analytical framework lies in the inference on
the risk premia. Unlike the low-frequency models, where Shanken adjustment (Shanken, 1992) is
typicallyrequiredtoaccountforestimationerrorsinβs,asthesamplingintervalshrinks,according
to the double asymptotic theory developed by A¨ıt-Sahalia et al. (2025), I can treat β as if they are
observedwithouterrors.
After obtaining these factor-mimicking portfolios, I can form estimates and conduct inference
for the unconditional risk premia of different interpretable risk factors. Specifically, use λC ≡
E[λC] and λJ ≡E[λJ] to denote the unconditional continuous risk premia and jump risk premia,
t t
respectively. The estimates for these unconditional risk premia can be obtained by averaging the
factor-mimickingportfolios’returns:
1 T n (cid:104) (cid:105)
(cid:98)λ C = ∑ ∑ (β(cid:98) ′ β(cid:98))−1β(cid:98) ′∆nR ,
T t t t i t 2
t=1i=1
(11)
1 T n (cid:104) (cid:105)
(cid:98)λ J,k = ∑ ∑ (β(cid:98) ′ β(cid:98))−1β(cid:98) ′∆nR ,
T t t t i t k+2
t=1i=1
where the subscripts index for the second entry and (k+2)-th entry, respectively, in factor return
vector. The standard error and confidence interval can be constructed with the volatility of the
factor-mimicking portfolio, and the final t-stat is proportional to the Sharpe ratio of the topic-
specificfactor-mimickingportfolio.
10

<!-- page 12 -->
2.3 Narrative Retrieval and Topic Classification
The previous section discusses the empirical estimation of the Fama-MacBeth regression model
assuming a given categorization of jumps. Obtaining an economically meaningful division of the
jumpcategoriescanbecriticalforgeneratingheterogeneityinriskexposureandriskprices.
To achieve this goal, I link market jumps to high-frequency newswire data and apply state-of-
the-artlargelanguagemodelstoanalyzetheconcurrentnewsinthe15-minuteintervalatthejump
time.
Even though the high-frequency data is helpful for reducing the volume of concurrent news,
therecanstillbehundredsofnewsstoriesreleasedinthetimewindowofthemarketjump. Tosift
through the large amount of text, the language model needs to possess strong reasoning skills to
identifynewsstoriesthatarebothsystematicandalignedwiththemovementinthemarket.
Moreover, proprietary LLMs present a significant hurdle for replication studies, and feeding
newswire text to these models through the API may violate the copyright agreement of the data
vendor.
Withthesetwoconsiderations,Iself-hostanddeploythestate-of-the-artopen-sourcereasoning
languagemodel,theQwen3-235B-A22B(Yangetal.,2025),toanalyzetheconcurrentnewsduring
the market jump. The Qwen model is a 235-billion-parameter mixture of experts model with 22
billion active parameters per query. A key feature of this model is its ability to toggle reasoning
(thinking) on and off, allowing me to directly study the value of test-time compute for financial
textanalysis.3
I then feed the model with concurrent news events, time, market response direction, and
magnitude, and ask the model to identify the likely cause of the jump from the news stories using
thefollowingprompt.
3IdiscussinmoredetailonhostingthemodelintheOnlineAppendix6.3.
11

<!-- page 13 -->
Prompt 1 (Narrative Retrieval): From {event start time} to {event end time} ET, the US
market {increases/decreases} by {event ret}%. Listed below are the news headlines in this
period from the Dow Jones Newswires. Can you find what is likely causing the jump? Output
your answer in JSON in the format of {“News id”: list[int], “Explanation”: str}. If there is no
plausiblenewsaccountingforthejump,output“News id”asanemptylist.
{NewsIDsfollowedbynewsheadlines.}
The retrieved news narratives and explanations offer interpretable signals for what is moving
the market. With this narrative retrieval step, I obtain the list of news relevant to explaining the
contemporaneousmarketjumpandthereasoninglogicbehindsuchattributionthroughtheLLM.
After the narrative retrieval step, I apply the language model to obtain the topic categories for
eachjumpevent. Thetopic’soverallcategoriesshouldsatisfythreegoals: (1)nearlyalljumpscan
be classified as one of the categories; (2) the categories should be broad so that there are enough
jumpswithinthecategoryforidentifyingjumpβs;(3)thecategoriesshouldbemutuallyexclusive.
Withthethreegoals,Idesignthefollowingprompttoobtainoveralltopiccategoriesforallthe
jumpevents.
Prompt 2 (Overall Jump Topic Categories): Please read the provided explanations and
narratives for why the U.S. market jumps. Help me classify them into comprehensive and
mutually exclusive topics. Ensure nearly all jumps can be classified into one of the topics.
Output a JSON file in the format of {“Topic Name”: str, “Topic Definition”: str, “Text ID”:
list[int]}.
{NarrativeIDsfollowedbyexplanationtextgeneratedinPrompt1.}
I feed all explanations with a non-empty news ID list generated from Prompt 1 to this topic
categorization step through the same Qwen model. After merging related topics, the procedure
yields five distinct broad topic categories for all the jump events in the market. To allow for non-
12

<!-- page 14 -->
classified jumps, I include a ‘None of the Above’ category. I provide details on these categories
andtheirdefinitionsintheTable1.
After obtaining the overall jump categories, I use the same Qwen model to zoom in on each
individualjumpandclassifythemintooneofthecategories. Thismorefocusedclassificationstep
enablesthemodeltoproducemoreaccurateandconsistentclassificationresults.
Prompt 3 (Jump Classification): Please read the provided explanation and narrative, as well
as the relevant news for a U.S. equity market jump event, and classify the jump into one of the
followingsixtopics:
{TopicIDs,TopicNames,TopicDefinitionslistedinTable1,identifiedwithPrompt2}
Output your response in JSON in the format of {“Topic Category”: int, “Explanation”: str}.
Hereistheexplanationfollowedbytherelevantnews:
{Explanation: Explanation text generated using Prompt 1. Relevant News: News identified as
relevantusingPrompt1.}
Afterthisstep,Iassigneachmarketjumptooneoftheeconomicallydistinctcategoriesdefined
in Table 1. This categorization enables me to apply the decomposition framework in Equation (2)
to break down asset exposures across different sources of risk. As a result, I can construct factor-
mimicking portfolios that yield interpretable risk premia, fully decomposing the overall market
risk.
3 Data
In this section, I present the dataset used in my study. The first part (Subsection 3.1) introduces
thecross-sectionofassetsIuseforuncoveringthefactorriskpremia,i.e.,thehigh-frequencydata
on S&P 1500 constituents’ returns. The second part (Subsection 3.2) presents the construction
of the around-the-clock market factor. The third part (Subsection 3.3) shows the high-frequency
newswire data from the Dow Jones. The fourth part (Subsection 3.4) describes the data on pre-
13

<!-- page 15 -->
scheduledmacroeconomicnewsreleases.
3.1 High Frequency Return Panel Data
Successfully recovering risk premia requires access to a long time span of data, as well as a broad
cross-section of liquid assets to construct factor-mimicking portfolios that accurately mimic jump
risks. To this end, I compile a large panel of high-frequency return data for S&P 1500 constituent
companies using TAQ millisecond data from WRDS, covering an extensive sample period from
September1997toMay2020—nearly23years.4
Crucially, the S&P 1500 membership for each firm is determined using the Compustat
idxcst his table, which records historical index constituents.5 This ensures that, at each point
in time, only firms that were actually included in the S&P 1500 are used for constructing returns,
reflecting the real-time available investment universe. After merging the index membership with
CRSP and applying standard exchange and share code filters, my final sample contains 3,488
unique companies, providing both a long time-series and a rich cross-section for robust asset
pricinganalysis.
IuseindividualstocksratherthanportfoliosastestassetsfollowingtheinsightsfromAngetal.
(2020). The choice of testing factor models using portfolios or individual stocks entails a bias-
variance tradeoff. Portfolios allow the estimation error in β to cancel out, which results in lower
bias in risk premia estimates in the second-stage regression. However, shrinking the cross-section
into portfolios also shrinks the information in cross-sectional dispersion of βs, which results in
lessefficientestimatesofriskpremia.
To study which forces dominate empirically, Ang et al. (2020) conduct extensive simulations
andempiricalstudies. Theyfindthattheefficiencygainsfromusingindividualstocksastestassets
dominate the losses in bias. Recent studies support this finding (Giglio et al., 2022). Moreover,
4IstartthesamplefromSeptember1997because,aswillbeintroducedlater,theS&P500E-minifuturesproduct
wasintroducedtothemarketsincethen.
5Theidxcst histablewasremovedfromWRDSinJuly2020,whichlimitsmysampleperiodtodatespriorto
itsremoval.
14

<!-- page 16 -->
choosingindividualstocksastestassetsalsoalleviatesdatasnoopingbiaswhenformingportfolios
basedonobservablecharacteristics(LoandMacKinlay,1990).
Following these insights, I use the cross-section of real-time available S&P 1500 stocks as
the test assets to uncover the risk premia corresponding to different types of interpretable market
jumps.
To clean the high-frequency data and mitigate the effects of market microstructure noise, I
follow the procedure outlined in Da and Xiu (2021). Appendix 6.4 provides further details on the
datapreprocessing,includingtheaggregationofmillisecond-leveltradesto15-minuteintervalsfor
themainempiricalanalysis.
Finally, because the TAQ data only cover intraday observations during regular trading hours
(9:30 a.m. to 4:00 p.m. ET), I supplement these data by linking TAQ with CRSP to construct a
comprehensive panel of returns that incorporates stock splits, dividend payments, and overnight
price movements. Specifically, I use the daily open and close prices from CRSP—rather than
TAQ—to ensure accurate measurement of daily returns. The overnight return is then computed as
the ratio of the CRSP close-to-close gross return to the open-to-close gross return. This approach
ensures that all adjustments for splits and dividends are fully captured in the overnight return
component. Further details on this procedure and the linking process are provided in Appendix
6.4.
3.2 High Frequency Market Returns and S&P 500 E-mini Futures
Toobtainthesystematicfactor,IconsiderthemarketreturnoftheU.S.equities. Itisalsocriticalto
havefullhigh-frequencyobservationsofthesystematicfactor. Thisallowsforafulldecomposition
ofthesystematicriskswithoutleavinganyjumprisksoutsidethepicture.
Tothispurpose,Iconstructboththehigh-frequencymarketreturnsforintradayvariations,and
I use the S&P 500 E-mini futures returns to obtain the overnight variations of the index because
thisproductistradedaroundtheclock.
15

<!-- page 17 -->
Figure1 IntradayandOvernightJumpIdentificationTimeline
This figure presents the timeline and instruments I use to identify the market jumps for the intraday and overnight
periods.
Firstly, for the intraday market return factor, I follow the construction procedure of Mkt-Rf
factorfromFamaandFrench(1993),whichisbasedonvalue-weightedreturnsofcommonstocks
listedontheNYSE,NASDAQ,andAMEX.
For the overnight market return factor, I leverage the S&P 500 E-mini futures data from the
CME DataMine database, which provides the tick-level high-frequency data of the product with a
long span of history.6 The E-mini futures contract is the most liquid equity index futures product
globally,tradingnearly24hoursadayandfacilitatingcontinuouspricediscoveryoutsideofregular
U.S. equity market hours. Its deep liquidity and global participation make it a primary venue
for incorporating and reflecting new information—especially systematic news events—during
periods when the underlying cash equity market is closed. By utilizing E-mini futures, I capture
the overnight market response to news releases, geopolitical developments, and macroeconomic
events, ensuring a comprehensive measure of market-wide return dynamics around the clock.
Similar to the intraday market factor, I sample the S&P 500 E-mini futures at a 15-minute
frequency.
Figure1providesanillustrationofthetimelineIusedtoidentifyintradayandovernightjumps.
Specifically, I divide each trading day into two parts: the intraday observations from 9:30 a.m. to
4:00p.m. ETandtheovernightperiodthatspansfrom4:00p.m. tothenextday’sopeningat9:30
a.m. I then calculate the truncated estimator for realized volatility defined in Equation (6) using
theintradayandovernightobservationsseparately. Ithenusethetworealizedvolatilityestimators
6Idiscussindetailtheprocedurefordatacleaningandconstructingacontinuouslyrolling-overreturnseriesfor
theE-minifuturesinAppendix6.4.
16

<!-- page 18 -->
asthetruncationthresholdforidentifyingintradayandovernightjumpsasdefinedinEquation(5).
I do not merge the intraday and overnight observations because the two have different diurnal
patterns. Also, the separate estimation enables direct comparison with high-frequency finance
literature, which focuses on the intraday component of the return to identify jumps (A¨ıt-Sahalia
andJacod,2014).
I then use a threshold of 0.5% to filter out large jump observations for empirical analysis. The
mainconclusionsofthepaperremainrobusttodifferentthresholdvaluesforlargejumps.
3.3 Dow Jones Newswires
I use the Dow Jones Newswires to retrieve contemporaneous news released around the time of
systematic market jumps. The Dow Jones Newswires is a real-time, timely, and comprehensive
newsservicewidelyusedbyinstitutionalinvestorsviaplatformssuchasBloomberg.
Thisdatasetofferstwokeyadvantages. First,itprovidesprecisetimestampsindicatingexactly
when a news item reaches the market, enabling accurate alignment with high-frequency return
data. Second, it offers broad and reliable coverage of market-relevant news through reputable
mediaoutletssuchasTheWallStreetJournal,Barron’s,MarketWatch,amongothers.
ThesefeaturesmaketheDowJonesNewswiresparticularlywell-suitedforidentifyingmarket-
movingnarrativesinconjunctionwithhigh-frequencyfinancialdata.
In contrast to Aleti and Bollerslev (2025), who apply careful filtering and conduct topic
modeling using the anchor phrase methodology,7 I retain all news items released during the
identified market jump intervals and use LLM to retrieve relevant narratives. Their approach
filters the newswire to isolate systematic content, which requires substantial pre-processing. In
my approach, I take advantage of recent advances in LLMs and directly prompt the model to
processtherawnewstextandidentifytrulymarket-relevantitemswithoutpre-filtering.
To ensure that all relevant news fits within the LLM’s context window, I restrict attention to
7SeeHobergandManela(2025)foradetailedoverviewoftheanchorphrasemethod.
17

<!-- page 19 -->
jumps occurring in 15-minute intervals and exclude those during futures maintenance windows or
after-hours periods. Over 95% of the identified jumps occur within 15-minute windows,8 so this
restrictionmaintainscomprehensivecoverageofsystematicjumpevents.
3.4 Macroeconomic Information Release Schedule
Last but not least, I compile a list of pre-scheduled major macroeconomic news release dates
following Ai and Bansal (2018). Specifically, I consider four major macroeconomic data releases:
the unemployment / non-farm payroll, the CPI, the PPI, and the GDP. All four data are released
at 8:30 a.m. before the market opens. These four economic data are the top four announcements
rankedbytheBloomberginvestorattentionmeasure.
I download the release dates of unemployment, CPI, and PPI from the Bureau of Labor
Statistics website,9 and I download the release dates of GDP from the Federal Reserve Bank of
St. Louis website.10 This gives me, on average, 48 announcements per year since the data are
releasedatamonthlyfrequency.
4 Empirical Results
In this section, I present the main empirical results. Firstly, I provide a summary of evidence
on what news triggers market jumps in Subsection 4.1. Next, I present risk-premia estimates of
ex-ante compensation for bearing different risks in Subsection 4.2. Then I show investors can
improve their utility using LLM to understand the systematic risk compensation in real time and
build a portfolio to outperform the market in Subsection 4.3. Following this, I demonstrate the
incremental value from the LLM in Subsection 4.4. Lastly, I zoom in on the macroeconomic risk
premia and focus on the news item driving the jump, and distinguish the risk premia against that
8Some jumps fall in intervals with length larger than 15 minutes because these are times for brief trading halts,
futures daily clearing sessions, or weekend closures with no high-frequency price data. These account for a small
fractionoftotalidentifiedjumpsandtypicallyreflectmechanicalratherthannews-drivenpriceadjustments.
9https://www.bls.gov/bls/archived sched.htm
10https://alfred.stlouisfed.org/release/downloaddates?rid=53
18

<!-- page 20 -->
fromthepre-scheduledmacronewsreleaseinSubsection4.5.
4.1 What Triggers Market Jumps?
Figure 2 presents a visualization of all market jumps occurring in my sample. I divide them into
two categories: (1) jumps occurring in the intraday period; (2) jumps occurring in the overnight
period.
One prominent feature stands out from the figure: the vast majority of market jumps occur
overnight. I find that the intraday jumps account for only about 30% of the total observations.
The evidence highlights the importance of taking a holistic, ‘around-the-clock’ view to include
overnight observations to better understand systematic jump risk affecting the equity market.
Otherwise,theriskpremiaestimatesmightsufferfromomittedvariablebias.
Linking the news with the jumps, I run each jump and corresponding news through Prompt
1 to Prompt 3. With the overall categories listed in Table 1, I map each jump into one of the
categories. As a first sanity check, I examine whether the topic classification from the LLM is
consistentwiththethemeofeachtopic.
Figure3plotsthewordcloudsofthenewsitemsidentifiedasrelevantbytheLLMfortriggering
thejump. Ifindconsistentpatternswithineachtopiccategoryanddistinctworddistributionsacross
categories. The top words occurring within each cluster match the theme of the topic, suggesting
theLLMperformswellinallocatingeachjump-triggeringnewstorelevantcategories.
Next, Table 2 provides an overview of different types of news events’ contributions to driving
thestockmarketjump. Firstly,Ifindthatmorethan95%ofjumpeventscanbeexplicitlylinkedto
newsstories. TheresultisconsistentwithfindingsfromBakeretal.(2021). Theevidencesuggests
thatattheaggregatemarketlevel,thesystematicjumpsaremainlytriggeredbypublicinformation
ratherthanprivatetradingwithhiddeninformation.
In contrast, studies on firm-specific news find mixed evidence on the relationship between
news and jumps. Jeon et al. (2022) and Christensen et al. (2025) find news, especially earnings
19

<!-- page 21 -->
announcements, as important sources for jumps in individual stock returns. However, A¨ıt-Sahalia
etal.(2024)documentthattherearemanyfirm-specificjumpsthatcannotbetracedbacktonews.
Differentfromthisliterature,Ifocusonsystematicjumpsandaggregatemarketmovement.
Among the jumps that can be linked to news, I find that the unclassified category accounts for
lessthan10%ofthetotalobservations. ThismeanstheoverallcategoriesidentifiedbyLLMusing
Prompt2arecomprehensiveenoughtocovermostofthejumpobservations.
For the five groups of classified jumps, the ‘international market spillovers’ topic accounts for
most of the observations, representing 33% of total jumps. This is followed by the ‘U.S. macro
data surprises’ category, which takes up 1/5 of the total jump observations. Another prominent
categoryisthespilloverfromsystematicallyimportantfirms’earnings,accountingfor16%oftotal
jumps, highlighting the granular origins of aggregate volatility, as emphasized by Gabaix (2011).
The last two categories, policy and geopolitical tensions, each contribute around 7 to 12% of total
observations. However, the policy-triggered jumps are more volatile than other categories. In the
R2 space, it ranks third in variation accounted for, only below international spillover and macro
data surprises. Consistent with the findings from Baker et al. (2021), more than 75% of policy-
related jumps are positive, supporting the view of a ‘Fed put’ that selectively mitigates downside
riskafterlargestockmarketdeclines.
The prominent role played by international market spillover and macro data releases again
suggeststheimportanceofovernightobservationsforunderstandingU.S.marketjumprisks. This
is because international news usually happens when the U.S. market is closed, and the macro data
releasesusuallyhappenbeforetheU.S.marketopens.
To verify the accuracy of the classification provided by LLM, I manually inspect the narrative
retrieved and find that the reasons found by the model are highly plausible and accurate. They
satisfy the requirement that the news should have systematic implications for the overall market
andtherationalematchesthedirectionofthemarketmovement. Sincethereisafallbackcategory
of ”no plausible news causing the jump,” this significantly reduces the chance of hallucination
fromthemodelforcingitselftofindanewsitemtoexplainthejump.
20

<!-- page 22 -->
To provide another cross-validation on the accuracy of the jump topic classification, I apply
the ChronoBERT model (He et al., 2025a) and the LDA topic model (Bybee et al., 2024) to
independently classify each jump into the categories listed in Table 1. Table 3 reports the
percent agreement between different approaches. Overall, these results indicate that the baseline
classificationiscapturingbroadlysimilareconomicdriversofmarketjumps.
Lastly, I compare the identified jump that falls into the macroeconomic news category and
compare these jumps with the major pre-scheduled macroeconomic news release dates and time
introducedinSection3.4. Ifindabout68%oftheidentifiedmacroeconomic-news-triggeredjumps
fall within the time interval of macroeconomic news releases. The high agreement suggests the
modelisindeedcapturingthetruemacroeconomiceventsthatdrivemarketjumps.
In thenext section,I apply theFama-MacBeth regressionapproach toquantify the importance
ofthedifferenttypesofriskforex-anteriskpremia.
4.2 What Risks are Priced?
To quantify risk prices, I first estimate the real-time jump and continuous betas of the S&P 1500
panelofstocksusingEquations(8)and(9). Continuousbetasareupdatedmonthlyusinga1-month
rolling estimation window, and jump betas are updated annually using an expanding estimation
window.
Figure 4 plots the time series of percentile estimates for both continuous and topic-specific
jumpbetas. Themediancontinuousbetahoversaround1,exhibitingnotabletime-seriesvariation.
In contrast, the topic jump betas display more muted variation over time due to their lower update
frequencyandtheuseofexpandingwindowestimation.
Notably, the jump betas for macroeconomic, corporate, and international topics rise signif-
icantly following the 2008 financial crisis. This increase likely reflects the surge in systematic
jump events during the crisis and heightened comovement between individual stocks and the
corresponding jump risk factors. Toward the end of the sample period, the geopolitics jump beta
21

<!-- page 23 -->
alsorises,consistentwithelevatedgeopoliticaltensionsduringtheTrumpadministration.
Using the real-time beta estimates, I then form the jump-mimicking portfolios using Equation
(10) and calculate risk-premia estimates using Equation (11). Panel A of Table 4 presents the
estimates, standard errors, and Sharpe ratios of topic factor-mimicking portfolios for the around-
the-clock analysis. Firstly, the continuous risk premium is large in magnitude, accounting for
more than 49% of the total market risk premia. However, because of its high volatility, the factor-
mimickingportfoliohaslowSharperatios.
Among the topic-specific jump risks, the macroeconomic category commands the highest
premium, with an annualized return of 3.65% and a t-statistic of 2.77. Importantly, the
macro jump risk factor-mimicking portfolio achieves a Sharpe ratio of 0.78, outperforming the
contemporaneous market’s Sharpe ratio of 0.53, reflecting its high return and relatively low
volatilityaftercontrollingforothersystematicjumpriskexposuresandcontinuousriskexposures.
Other topic-specific jump risks with positive risk premia include the corporate bellwether
and international market spillover categories, with annualized returns of 2.77% and 1.91%,
respectively. Whiletheinternationaltopicaccountsforthelargestshareofcontemporaneousjump
events, it offers limited explanatory power for ex-ante risk compensation. The corporate topic
delivers a better risk-return tradeoff than the international category, but the estimated premium is
statistically insignificant, suggesting that investors may find it difficult to identify and act on this
riskfactorinrealtime.
Figure 5 displays the cumulative returns of the three jump risk factor-mimicking portfolios.
Both the corporate and international portfolios exhibit higher volatility than the macro portfolio.
Given their lower premia and greater volatility, the macroeconomic topic emerges as the only one
thatdeliversastatisticallyandeconomicallysignificantsourceofpricedjumprisk.
The prominence of macroeconomic risk premia is also consistent with the theory developed
in Appendix 6.2. The macroeconomic topic, compared to other topics, is more likely to
capture the stochastic variations in the investment opportunity set faced by investors because
the macroeconomy is closely related to the financial conditions of the market. Consequently,
22

<!-- page 24 -->
significant compensation for the factor and alphas relative to the factor benchmarks arise due to
theintertemporalhedgingmotiveoftherepresentativeinvestor.
I also conduct a Wald test with the null hypothesis that all the risk premia are equal in
magnitude. The test rejects the null at the 1% significance level, highlighting the heterogeneity
inriskcompensationacrossdifferentjumpriskcategories.11
An important question is whether priced jump risk arises from overnight or intraday returns.
Table 5 provides supporting evidence. Panel A examines portfolios that hold market exposure
exclusively during either the overnight or intraday window. The results show that nearly all
U.S. equity risk premia accrue overnight, underscoring the importance of overnight risk. Panel B
applies the real-time Fama-MacBeth regression framework to separately estimate risk premia for
continuous returns, overnight jumps, and intraday jumps. Again, the evidence points to overnight
jumpriskastheprimarysourceofcompensation.
For external validity, I also consider the GANs-based SDF constructed in Aleti and Bollerslev
(2025),followingthemethodologyofChenetal.(2024). TheFama-MacBethregressionconfirms
thatovernightjumpriskearnsthemostsignificantpremium.
To directly demonstrate the value of the around-the-clock analysis, I estimate jump risk
premia using only intraday observations. Panel B of Table 4 reports the estimates. The
results indicate that relying solely on intraday data leads to noisier and biased estimates. For
example, the macroeconomic topic, which is highly significant under the full around-the-clock
analysis, becomes insignificant in the intraday-only specification, likely because many major
macroeconomic announcements are released overnight. None of the jump topics is statistically
significantwhenusingonlyintradaydata.
Due to the increased estimation noise, a real-time strategy that invests in the most significant
topiceachmonthbasedonintraday-onlyestimatesyieldsaSharperatioofjust0.28. Incontrast,the
samestrategybasedonthearound-the-clockanalysisachievesaSharperatioof0.95,substantially
outperformingthemarketoverthesampleperiod.
11IprovidedetailsontheimplementationoftheWaldtestinAppendix6.1.
23

<!-- page 25 -->
I conduct extensive robustness checks on the LLM-based classification. In Section 4.4, I show
the results are robust to alternative classification methods (ChronoBERT, LDA) and examine the
value of reasoning capabilities by comparing thinking versus non-thinking versions of the same
model.
4.3 Real-time Jump Risk Management
Building on the risk premia estimates in Section 4.2, a natural question is whether investors can
identifytheheterogeneityinriskcompensationacrossdifferenttypesofsystematicriskinrealtime
andconstructfactor-mimickingportfoliosthatoutperformthemarket.
In this section, I evaluate the performance of a real-time optimal jump-topic factor-mimicking
portfolio. At the end of each year, I use Equation (11) to estimate the cross-sectional prices of
jump risk, substituting in the most up-to-date jump betas computed using all available data. I then
select the jump topic with the highest Sharpe ratio, i.e., the most significantly priced jump risk, as
thebasisforthefactor-mimickingportfoliointhesubsequentyear.
Figure6illustratestheperformanceofthisreal-timemaximumSharperatiojump-topicfactor-
mimicking portfolio. The macroeconomic topic consistently emerges as the dominant source of
priced jump risk from the early years of the sample and continues to exhibit strong performance
towardtheend. Theresultingportfoliodeliversanout-of-sampleSharperatioof0.95,substantially
exceedingthemarketSharperatioof0.53.
Toassesswhetherthesejump-topicfactor-mimickingportfolioscapturenewdimensionsofrisk
beyond traditional asset pricing factors, I regress their returns on standard risk factors commonly
used in the literature. Table 6 reports the results for both the macro factor-mimicking portfolio
and the real-time selected topic portfolio. In all specifications, the estimated alphas remain highly
significant, indicating that these portfolios are not simply repackaging exposures to known risk
factorsbutrathercapturedistinctsourcesofpricedjumprisk.
An important follow-up question concerns the economic value added by using large language
24

<!-- page 26 -->
models (LLMs) to classify jumps into distinct categories based on contemporaneous news. To
address this, I conduct a placebo analysis in which I randomly assign each jump to one of the six
categories, drawn from a uniform distribution. Using the same methodology, I construct real-time
factor-mimicking portfolios that invest in the jump category with the highest Sharpe ratio within
theestimationsample.
Figure 6 includes 20 such placebo strategies, shown as faint lines corresponding to random
seeds from 1 to 20. None of the placebo portfolios achieves a Sharpe ratio as high as the LLM-
based strategy. The average Sharpe ratio across placebo portfolios is 0.31, which is significantly
lower than that of the market. The highest Sharpe ratio among the placebo strategies is 0.71, over
25%lowerthantheLLM-basedoptimalportfolio.
Another question is whether the real-time jump risk factor-mimicking strategy is imple-
mentable in practice (Jensen et al., 2024). To answer this, I incorporate trading costs into my
analysis following DeMiguel et al. (2009). Specifically, I calculate net-of-trading-costs portfolio
performanceusingthefollowingequation:
Rnet =(1+R +R gross )(1−c·∆W )−(1+R ), (12)
p,t+1 f,t+1 p,t+1 t+1 f,t+1
where Rnet and R gross represent the net-of-trading-costs portfolio return and the gross portfolio
p,t+1 p,t+1
return. R is the risk-free rate in period t+1, c is the trading cost parameter, and ∆W is
f,t+1 t+1
definedas:
(cid:12)(cid:12) (cid:12)(cid:12)
(cid:12)(cid:12)
W
t
◦(1+1·R
f,t+1
+R
t+1
)
(cid:12)(cid:12)
∆W t+1 =(cid:12) (cid:12) (cid:12) (cid:12) W t+1 − 1+R +W′R (cid:12) (cid:12) (cid:12) (cid:12) , (13)
f,t+1 t t+1 1
where◦denoteselementwiseproduct,1representsthevectorofoneswithlengthequaltothetotal
number of assets, R is the vector of returns of all individual assets, and ||·|| denotes the L1
t+1 1
norm of a vector. So ∆W characterizes the distance between the target weight in period t+1 and
the current weight that naturally grows after the return in period t+1. To better understand the
turnoverfrequencyoftheportfolio,Ialsocalculatetheturnoverdefinedas:
Turnover=∆W /||W|| . (14)
t+1 t 1
25

<!-- page 27 -->
I scale the changes in weights by the L1 norm of the last period’s weight because the portfolio is
zero cost and consists of long and short sides. The dollar amount invested in long and short sides
doesnotnecessarilyequal1inallperiods.
Table 7 presents the performance of the real-time jump risk factor-mimicking portfolio after
trading costs. Following Frazzini et al. (2018), I consider trading costs specifications with c =
10bps, c = 20bps, and c = 50bps. The choice can also be justified by examining the portfolio’s
turnover,whichstandsat10%permonth. Thisturnovervaluefallsintothelowtomediumtrading
costscategoriesofanomaliesstudiedinNovy-MarxandVelikov(2016). Inallscenarios,Ifindthe
net-of-trading-cost portfolio performance remains strong, achieving Sharpe ratios of 0.93, 0.91,
and0.85,respectively.
Theportfoliohaslowturnoveringeneralbecausethejumpbetasarepersistentandre-estimated
once per year. The continuous betas would contribute to month-to-month portfolio changes, but
these estimates are also persistent over time. As a result, the final portfolio has modest turnover
eachmonth.
Takentogether,theseresultssuggestthatLLMsaddsubstantialeconomicvaluebyidentifying
jumpeventslinkedtosimilarunderlyingeconomicrisks. Becausetheserisksexhibitstablepricing
overtime,investorscanexploitreal-timeinformationtoconstructfactor-mimickingportfoliosthat
deliversuperiorout-of-sampleperformancerelativetothemarket.
4.4 Lookahead Bias in LLM and Incremental Value of Reasoning LLM
The previous sections present the risk premia estimates and the real-time jump factor-mimicking
portfolioperformanceusingaround-the-clockanalysisandlargelanguagemodels. Therearethree
remaining questions: (1) Whether the superb performance comes from the lookahead bias in pre-
trainedlanguagemodels(SarkarandVafa,2024)? (2)WhatistheincrementalvaluefromtheLLM
compared to a traditional word-count-based topic modeling approach, such as LDA (Bybee et al.,
2024)? (3)Whatisthevalueaddedfromenablingthelanguagemodeltothinklongerbeforegiving
26

<!-- page 28 -->
thefinalanswer(Weng,2025)?
Firstly, regarding lookahead bias, in my three-step prompting pipeline, the step that suffers
most from this concern is the final Prompt 3, which classifies each jump into different categories
based on the news retrieved. The reason is that the model can utilize the knowledge within its
cutoff range to determine that a certain type of news has significant economic implications for
futurestockmarketperformance.
To alleviate this concern, I redo this step using the ChronoBERT model developed in He
et al. (2025a). The first model in the series has a knowledge cutoff before the year 2000, so it
does not have the knowledge of future major economic events. Simultaneously, the model family
demonstratesstronglanguageunderstandingabilities,makingitusefulformyanalysis.
Specifically, at the beginning of each year, I fine-tune the model on the text-topic data in
previous years, and apply the fine-tuned model in the out-of-sample period to classify the news
and explanation texts into the six economic categories in Table 1. Appendix 6.3 provides details
on the fine-tuning process. I then use the ChronoBERT labeled jump categories to estimate jump
betas defined in Equation (8), estimate risk premia using Equation (11), and form real-time jump
riskfactor-mimickingportfolios.
PanelAofTable8presentstheresultsfromtheChronoBERTmodel. NotethatChronoBERTis
fine-tunedonlabelsgeneratedbythereasoningLLM.ComparingtheresultsagainstthoseinTable
4, I find close alignment in risk premia estimates. The macro topic again stands out as the only
significanttopicamongalljumptopics. Thejumpriskfactor-mimickingportfolioearnsannualized
returnsof3.1%withaSharperatioof0.68. Thesenumbersarecomparabletothebaselineresults.
The modest lookahead bias can also be seen from the high agreement in Table 3 (about 75%)
fortheout-of-sampletopicclassificationbetweenChronoBERTandthebaseline. Giventheability
of ChronoBERT to successfully classify a large number of retrieved narratives, it is unlikely the
classificationstepsufferssignificantlookaheadbias.
Moreover, the real-time jump risk factor-mimicking portfolio earns an annualized return of
27

<!-- page 29 -->
4.02% with a Sharpe ratio of 0.68, which remains significant and comparable to my baseline
results. Overall, the evidence suggests that the lookahead bias from applying the pretrained LLM
toclassifyjumptopicsismodestinthissetting.
Secondly, it remains a question whether the investment value and risk premia quantification
using the LLM is incremental to the traditional NLP approach with word count and LDA topic
modeling. To answer this question, I use the pretrained LDA model from Bybee et al. (2024) with
theWSJcorpus.
To classify the jumps into distinct topics using LDA, I first follow the same text preprocessing
procedureinBybeeetal.(2024)toconverttherawtextintoacountofunigramsandbigrams. Next,
given the word count, I can use estimated weights of P(word |topic) and the prior distribution of
topicsP(topic)toobtaintheposteriorprobabilityoftopicsP(topic|word). Finally,Iclassifyeach
jumpintooneLDAtopicbasedonthemaximumposteriorprobability.12
It is worth noting that the LDA topic classification is different from the six overall categories
identified by the LLM. To map the LDA topics into the same six categories, I use a prompt-based
approachandprovidetheLLMwithboththetopicnameandtopwordsintheLDAmodel,andlet
themodelclassifythemintothesixcategorieslistedinTable1.
To quantify the incremental value of LLM relative to the LDA approach, I calculate the risk
premia and form a real-time jump risk factor-mimicking portfolio. I report the results in Panel B
ofTable8. FromtheLDAanalysis,Ialsofindthemacrotopicremainssignificantandgeneratesa
Sharperatioof0.56. Inthisanalysis,therearesomediscrepanciescomparedtotheresultsinTable
4. TheCorporatetopicbecomessignificant,offeringaSharperatioof0.54. However,considering
the real-time jump risk factor-mimicking portfolio, I find that the portfolio only yields a Sharpe
ratioof0.28,underperformingthecontemporaneousmarketinmysampleperiod.
The decrease in investment performance suggests LDA introduces additional noise in jump
classification and may fail to classify the truly heterogeneous jumps into distinct categories. With
a closer examination of the agreement between LDA and the baseline in Table 3, I find the
12Appendix6.1providesdetailsontopicclassificationusingthepretrainedLDAmodel.
28

<!-- page 30 -->
agreement rate is 60%. The number is 75% between ChronoBERT and the baseline. Overall,
theincreasedlanguageunderstandinginLLMsandtheabilitytopayattentiontocontextallowthe
LLMapproachtobetterunderstandjumprisksandclassifythemintodistincteconomiccategories.
TheincreasedlanguageunderstandingtranslatesintotripletheSharperatiosinthereal-timejump
riskmanagementportfolios.
Thirdly, a key advance in modern LLMs is their reasoning capabilities. This ability allows the
language model to explore different possibilities and reflect on its own response to generate better
and more accurate answers, which is analogous to System II versus System I thinking proposed
in Kahneman (2011). Intuitively, this ability would be important for the first step for the model
to go through large amounts of news and determine the truly relevant ones that would trigger the
market-widejump.
However,itremainsanempiricalquestionhowlargetheincrementalvalueisfromallowingthe
modeltothink. AkeyfeatureoftheQwenmodelusedinthisstudyisthatitallowsforswitchingon
and off the thinking mode within the vLLM inference engine.13 This enables a direct comparison
ofthesamemodelarchitecturewithandwithoutreasoningcapabilities.
Irunthesamechain-of-thoughtPrompt1toPrompt3,usingreasoningversusnon-reasoning
versions of the Qwen model separately. There is a stark contrast in running time for the Prompt
1: the non-thinking model completes all requests in just 8 minutes, whereas the thinking model
takes over 2 hours using the same hardware. The evidence already suggests intrinsic difficulty in
evaluating the true cause of a market jump, with many potential news stories, even in a 15-minute
interval. In contrast, when running Prompt 3 through both models, both the reasoning and non-
reasoningmodelstakeasimilaramountofcomputetime. Theybothfinishthetaskwithinminutes.
The evidence suggests that classifying the jumps into existing categories would be a much easier
taskthandeterminingtheunderlyingreason.
With the additional test-time compute deployed to understand the cause of the market jump,
I find significant differences in the outcome from Prompt 1. Firstly, the non-reasoning model
13Appendix6.3providesdetailsonhostingandservingtheQwen3-235B-A22Bmodelinbothreasoningandnon-
reasoningmodes.
29

<!-- page 31 -->
can only attribute 69.7% of jumps to underlying news, a number that is much lower than the
reasoning model (97.2%). Since the model cannot trace back the reasons for many jumps, the
overall agreement in jump classification between the non-think model and other approaches is
significantlylower,withavaluearound55%(Table3).
Table 9 presents the risk premia estimates using the non-think model. I find the pattern of risk
premiaremainsconsistent,withmacroeconomicriskcommandingthelargestandmostsignificant
riskpremia.
However, for the non-thinking model, I find that there are, in general, smaller and less
significant risk premia estimated using the non-thinking model. The evidence is consistent
with measurement errors attenuating the coefficient estimates. I find the real-time jump risk
management portfolio from the non-reasoning model generates a Sharpe ratio of only 0.39, far
below the reasoning model (0.95). Overall, the evidence highlights the importance of reasoning
capabilitiesinLLMforcorrectlyidentifyingunderlyingcausesofthemarketsystematicjump.
4.5 Macroeconomic News Jump Risk Premia
The preceding analyses identify macroeconomic jump risk as the most significantly priced source
of systematic jump risk, both statistically and economically. Some natural follow-up questions
are: what specific macroeconomic indicators are responsible for these market-moving jumps?
Can pre-scheduled macroeconomic news releases explain the risk premia findings using LLM?
In this section, I zoom in on the macroeconomic risk premia and try to answer what drives the
compensationtotheriskfactor.
To shed light on the underlying drivers, I examine the detailed composition of macro-related
news that triggers U.S. market jumps. Table 10 presents a breakdown of macroeconomic jump
events into high-level categories and sub-categories based on LLM analysis of contemporaneous
newsarticles.
Three primary macro categories dominate: ‘Labor Market’, ‘Inflation’, and ‘Growth and Real
30

<!-- page 32 -->
Activity’. Among these, the labor market stands out as the most frequent driver, accounting for
50 of the 152 macro jumps. Within this group, the Non-farm Payroll (NFP) report, commonly
referred to as the Employment Situation release, alone explains 34 jumps. This empirical finding
confirms the NFP’s widely acknowledged importance as a timely, forward-looking indicator used
byinvestmentbanksandothermarketparticipantstoassessthemacroeconomicoutlook.
Intotal,152marketjumpeventswithinthemacroeconomiccategoryaresuccessfullyattributed
to specific indicators using LLM-guided classification. This evidence reinforces the notion
that systematic jump risk priced in the market stems from a well-defined set of high-frequency
economic data releases. These releases tend to occur in the pre-market period, further validating
the earlier finding that overnight jump risk is the primary driver of the equity risk premia in the
U.S.
Another question arises from the analysis: given that there are many pre-scheduled macroe-
conomic news releases (Table 10), will this finding be explained away by the premia associated
withpre-scheduledmacroeconomicannouncementsasdocumentedinAiandBansal(2018)when
uncertaintyresolves?
Toanswerthisquestion,Iobtainedascheduleformajormacroeconomicdatareleasesfromthe
websites of the BEA and BLS. To start, for these release dates, I consider holding a portfolio that
invests in the market from 4:00 p.m. one day before the announcement to 4:00 p.m. the day of
the announcement. Since the strategy is not always active, I follow Lucca and Moench (2015) to
consideranadjustedannualizedSharperatioas:
µ√
SR= N ,
a
σ
whereN istheaveragenumberofdaysthestrategyisactiveduringtheyear.
a
I find that such a strategy generates a Sharpe ratio of 0.33 from 2007 to 2020 when the
contemporaneous market Sharpe ratio is 0.53. So holding a portfolio at the pre-scheduled
macroeconomicreleasedatescannotgeneratethefindingdocumentedinSection4.2.
31

<!-- page 33 -->
Furthermore, I use the replicating portfolio approach introduced in Section 2 to build factor-
mimicking portfolios for market returns on the pre-scheduled macroeconomic news release dates.
Instead of having the jump βs associated with different news topics, I estimate βs associated with
thepre-scheduledmacroeconomicnewsrelease.
Specifically, I consider two specifications. In the first one, I have one continuous β and one β
associatedwithpre-scheduledmacroreleasedatesinEquation(10)(Pre-scheduledMacro). Inthe
secondone,IaddallfiveotherjumptopicbetasascontrolstotheFama-MacBethfactor-mimicking
portfolioregression(Pre-scheduledMacrowithControls).
Table 11 reports the risk premia of the pre-scheduled macro factors and their regression
against standard risk factors. I find that they fail to generate the performance of the macro factor
documented in Section 4.2. The regression against standard risk factors yields negligible alphas.
Whenaddingcontrols,thealphasevenfurtherdecreaseinmagnitude.
All the evidence highlights the unique role played by LLM in linking the jumps to the news,
andusingjustthepre-scheduleddateswouldnotuncoverthesameempiricalpattern.
5 Conclusion
In this paper, I present the first comprehensive, around-the-clock analysis of systematic jump risk
intheU.S.equitymarketbyintegratinghigh-frequencyfinancialdatawithcontemporaneousnews
narratives retrieved and interpreted using a state-of-the-art LLM. By decomposing systematic risk
intointerpretable,topic-specificjumpcomponents,Iprovidenewinsightsintothesources,pricing,
andmanagementofjumprisk.
The empirical evidence yields several key findings. First, this classification reveals significant
heterogeneity in risk premia: macroeconomic jump risk commands a sizeable and statistically
significant premium, outperforming the market in terms of Sharpe ratio, while other types of risk
carrylimitedcompensation.
32

<!-- page 34 -->
Second,Idemonstratethatthisinterpretableriskdecompositionhassubstantialeconomicvalue
for investors. A real-time trading strategy that dynamically allocates to the most significantly
priced jump-topic portfolio each year achieves an out-of-sample Sharpe ratio of 0.95, exceeding
that of the aggregate market. Importantly, placebo analyses confirm that this performance cannot
be replicated by randomly assigned jump categories or using a traditional NLP approach with
LDA topic modeling, underscoring the value added by LLM-based narrative understanding and
reasoning.
These results contribute to the literature on systematic risk, high-frequency econometrics, and
the growing field of LLM applications in finance. Methodologically, I extend the continuous-time
Fama-MacBeth regression framework to allow for an interpretable decomposition of risk based
on contemporaneous news content. Empirically, I provide a transparent and replicable approach
for mapping high-frequency news to market movements using open-source LLMs. Practically,
the findings offer new tools for constructing real-time, interpretable, and economically significant
investmentstrategies.
Future work could apply similar techniques to study interpretable factor risk premia other
than the market factor, explore firm-level jump exposures, or extend the analysis to international
settings. Furthermore,thetechniquescanbeadaptedtoassesssystematicriskinotherassetclasses
with around-the-clock continuous trading, such as currencies (Lustig et al., 2011), commodities
(Gorton et al., 2013), and cryptocurrencies (He et al., 2022). As LLMs continue to evolve in
theirreasoningandinterpretabilitycapabilities,theirintegrationwithhigh-frequencyfinancialdata
promisestounlockevendeeperunderstandingofhowmarketsprocessinformationandpricerisk.
33

<!-- page 35 -->
References
Ai, Hengjie, and Ravi Bansal, 2018, Risk preferences and the macroeconomic announcement
premium,Econometrica86,1383–1430.
A¨ıt-Sahalia, Yacine, and Jean Jacod, 2014, High-frequency financial econometrics, in High-
FrequencyFinancialEconometrics(PrincetonUniversityPress).
A¨ıt-Sahalia, Yacine, Ilze Kalnina, and Dacheng Xiu, 2020, High-frequency factor models and
regressions,JournalofEconometrics216,86–105.
A¨ıt-Sahalia, Yacine, Chen Xu Li, and Chenxu Li, 2024, So many jumps, so few news, Technical
report,NationalBureauofEconomicResearch.
A¨ıt-Sahalia, Yacine, Jean Jacod, and Dacheng Xiu, 2025, Continuous-time Fama-MacBeth
regressions,TheReviewofFinancialStudiesForthcoming.
Aleti,Saketh,andTimBollerslev,2025,Newsandassetpricing: Ahigh-frequencyanatomyofthe
SDF,TheReviewofFinancialStudies38,712–759.
Ang, Andrew, Jun Liu, and Krista Schwarz, 2020, Using stocks or portfolios in tests of factor
models,JournalofFinancialandQuantitativeAnalysis55,709–750.
Baker, Scott, Nicholas Bloom, Steven J Davis, and Marco C Sammon, 2021, What triggers stock
marketjumps?,NBERWorkingPaperNo.28687 .
Beckmann, Lars, Heiner Beckmeyer, Ilias Filippou, Stefan Menze, and Guofu Zhou, 2024,
Unusualfinancialcommunication: Chatgpt,earningscalls,andfinancialmarkets,OlinBusiness
SchoolCenterforFinance&AccountingResearchPaper .
Bogousslavsky, Vincent, 2021, The cross-section of intraday and overnight returns, Journal of
FinancialEconomics141,172–194.
Bollerslev, Tim, Sophia Zhengzi Li, and Viktor Todorov, 2016, Roughing up beta: Continuous
versusdiscontinuousbetasandthecrosssectionofexpectedstockreturns,JournalofFinancial
Economics120,464–490.
Bollerslev,Tim,AndrewJPatton,andRogierQuaedvlieg,2025,Granularbetasandriskpremium
functions,JournalofEconometrics106034.
Boudoukh, Jacob, Ronen Feldman, Shimon Kogan, and Matthew Richardson, 2019, Information,
trading, and volatility: Evidence from firm-specific news, The Review of Financial Studies 32,
992–1033.
34

<!-- page 36 -->
Boyarchenko, Nina, Lars C Larsen, and Paul Whelan, 2023, The overnight drift, The Review of
FinancialStudies36,3502–3547.
Bybee, J Leland, 2023, The ghost in the machine: Generating beliefs with large language models,
arXivpreprintarXiv:2305.02823349–389.
Bybee, Leland, Bryan Kelly, Asaf Manela, and Dacheng Xiu, 2024, Business news and business
cycles,TheJournalofFinance79,3105–3147.
Bybee,Leland,BryanKelly,andYinanSu,2023,Narrativeassetpricing: Interpretablesystematic
riskfactorsfromnewstext,TheReviewofFinancialStudies36,4759–4787.
Chen, Jian, Guohao Tang, Guofu Zhou, and Wu Zhu, 2025, Chatgpt and deepseek: Can they
predictthestockmarketandmacroeconomy?,arXivpreprintarXiv:2502.10008.
Chen, Luyang, Markus Pelger, and Jason Zhu, 2024, Deep learning in asset pricing, Management
Science70,714–750.
Chen,Yifei,BryanT.Kelly,andDachengXiu,2023,Expectedreturnsandlargelanguagemodels,
SSRNElectronicJournal .
Chib, Siddhartha, Yi Chun Lin, Kuntara Pukthuanthong, and Xiaming Zeng, 2023, Slope factors
outperform: evidencefromalargecomparativestudy,AvailableatSSRN3966807 .
Christensen, Kim, Allan Timmermann, and Bezirgen Veliyev, 2025, Warp speed price moves:
Jumpsafterearningsannouncements,JournalofFinancialEconomics167,104010.
Da, Rui, and Dacheng Xiu, 2021, When moving-average models meet high-frequency data:
uniforminferenceonvolatility,Econometrica89,2787–2825.
DeMiguel, Victor, Lorenzo Garlappi, and Raman Uppal, 2009, Optimal versus naive
diversification: How inefficient is the 1/n portfolio strategy?, The Review of Financial Studies
22,1915–1953.
Fama, Eugene F, and Kenneth R French, 1993, Common risk factors in the returns on stocks and
bonds,JournalofFinancialEconomics33,3–56.
Fama, Eugene F, and Kenneth R French, 2015, A five-factor asset pricing model, Journal of
FinancialEconomics116,1–22.
Fama, Eugene F, and Kenneth R French, 2018, Choosing factors, Journal of Financial Economics
128,234–252.
35

<!-- page 37 -->
Fama, Eugene F, and Kenneth R French, 2020, Comparing cross-section and time-series factor
models,TheReviewofFinancialStudies33,1891–1926.
Frazzini, Andrea, Ronen Israel, and Tobias J Moskowitz, 2018, Trading costs, volume 3229719
(SSRN).
French,KennethR,andRichardRoll,1986,Stockreturnvariances: Thearrivalofinformationand
thereactionoftraders,Journaloffinancialeconomics17,5–26.
Gabaix,Xavier,2011,Thegranularoriginsofaggregatefluctuations,Econometrica79,733–772.
Giglio,Stefano,BryanKelly,andDachengXiu,2022,Factormodels,machinelearning,andasset
pricing,AnnualReviewofFinancialEconomics14,337–368.
Glasserman, Paul, Kriste Krstovski, Paul Laliberte, and Harry Mamaysky, 2025, Does overnight
newsexplainovernightreturns?,arXivpreprintarXiv:2507.04481.
Gorton, Gary B, Fumio Hayashi, and K Geert Rouwenhorst, 2013, The fundamentals of
commodityfuturesreturns,ReviewofFinance17,35–105.
He, Songrun, Linying Lv, Asaf Manela, and Jimmy Wu, 2025a, Chronologically consistent large
languagemodels,arXivpreprintarXiv:2502.21206 .
He,Songrun,LinyingLv,AsafManela,andJimmyWu,2025b,Instructiontuningchronologically
consistentlanguagemodels.
He, Songrun, Asaf Manela, Omri Ross, and Victor von Wachter, 2022, Fundamentals of perpetual
futures,arXivpreprintarXiv:2212.06888.
Hendershott, Terrence, Dmitry Livdan, and Dominik Ro¨sch, 2020, Asset pricing: A tale of night
andday,JournalofFinancialEconomics138,635–662.
Hoberg,Gerard,andAsafManela,2025,Thenaturallanguageoffinance,FoundationsandTrends
inFinance.
Holden,CraigW,andStaceyJacobsen,2014,Liquiditymeasurementproblemsinfast,competitive
markets: Expensiveandcheapsolutions,TheJournalofFinance69,1747–1785.
Jensen, Theis Ingerslev, Bryan T Kelly, Semyon Malamud, and Lasse Heje Pedersen, 2024,
Machine learning and the implementable efficient frontier, Swiss Finance Institute Research
Paper .
36

<!-- page 38 -->
Jeon, Yoontae, Thomas H McCurdy, and Xiaofei Zhao, 2022, News as sources of jumps in stock
returns: Evidence from 21 million news articles for 9000 companies, Journal of Financial
Economics145,1–17.
Jha, Manish, Hongyi Liu, and Asaf Manela, 2025, Does finance benefit society? a language
embeddingapproach,ReviewofFinancialStudies.
Kahneman,Daniel,2011,Thinking,fastandslow(macmillan).
Lewellen,Jonathan,andStefanNagel,2006,TheconditionalCAPMdoesnotexplainasset-pricing
anomalies,JournalofFinancialEconomics82,289–314.
Li,Jia,ViktorTodorov,andGeorgeTauchen,2017,Jumpregressions,Econometrica85,173–195.
Lo, Andrew W, and A Craig MacKinlay, 1990, Data-snooping biases in tests of financial asset
pricingmodels,TheReviewofFinancialStudies3,431–467.
Lopez-Lira, Alejandro, and Yuehua Tang, 2023, Can ChatGPT forecast stock price movements?
returnpredictabilityandlargelanguagemodels,SSRNElectronicJournal .
Lucca, David O, and Emanuel Moench, 2015, The pre-fomc announcement drift, The Journal of
finance70,329–371.
Lustig,Hanno,NikolaiRoussanov,andAdrienVerdelhan,2011,Commonriskfactorsincurrency
markets,TheReviewofFinancialStudies24,3731–3777.
Lv, Linying, 2024, The value of information from sell-side analysts, arXiv preprint
arXiv:2411.13813.
Lv, Linying, 2025, Do sell-side analyst reports have investment value?, arXiv preprint
arXiv:2502.20489.
Manela, Asaf, and Alan Moreira, 2017, News implied volatility and disaster concerns, Journal of
FinancialEconomics123,137–162.
Merton, Robert C, 1973, An intertemporal capital asset pricing model, Econometrica: Journal of
theEconometricSociety867–887.
Merton, Robert C, 1980, On estimating the expected return on the market: An exploratory
investigation,JournalofFinancialEconomics8,323–361.
Nakamura, Emi, and Jo´n Steinsson, 2018a, High-frequency identification of monetary non-
neutrality: theinformationeffect,TheQuarterlyJournalofEconomics133,1283–1330.
37

<!-- page 39 -->
Nakamura, Emi, and Jo´n Steinsson, 2018b, Identification in macroeconomics, Journal of
EconomicPerspectives32,59–86.
Novy-Marx, Robert, and Mihail Velikov, 2016, A taxonomy of anomalies and their trading costs,
TheReviewofFinancialStudies29,104–147.
Romer, Christina D, and David H Romer, 1989, Does monetary policy matter? a new test in the
spiritoffriedmanandschwartz,NBERmacroeconomicsannual 4,121–170.
Romer, Christina D, and David H Romer, 2000, Federal reserve information and the behavior of
interestrates,Americaneconomicreview90,429–457.
Sarkar, Suproteem, and Keyon Vafa, 2024, Lookahead bias in pretrained language models, SSRN
ElectronicJournal .
Sarkar,SuproteemK,2024,Economicrepresentations.
Shanken, Jay, 1992, On the estimation of beta-pricing models, The Review of Financial Studies 5,
1–33.
Wald, Abraham, 1943, Tests of statistical hypotheses concerning several parameters when the
number of observations is large, Transactions of the American Mathematical society 54, 426–
482.
Wei,Jason,XuezhiWang,DaleSchuurmans,MaartenBosma,FeiXia,EdChi,QuocVLe,Denny
Zhou, et al., 2022, Chain-of-thought prompting elicits reasoning in large language models,
Advancesinneuralinformationprocessingsystems35,24824–24837.
Weng,Lilian,2025,Whywethink,lilianweng.github.io.
Wilson, Edwin B, 1927, Probable inference, the law of succession, and statistical inference,
JournaloftheAmericanStatisticalAssociation22,209–212.
Yang, An, Anfeng Li, Baosong Yang, Beichen Zhang, Binyuan Hui, Bo Zheng, Bowen Yu,
Chang Gao, Chengen Huang, Chenxu Lv, et al., 2025, Qwen3 technical report, arXiv preprint
arXiv:2505.09388.
38

<!-- page 40 -->
Figure2 IntradayandOvernightJumps
This figure displays the time series of intraday and overnight jump returns identified using Equation (5). Blue
dots indicate intraday jumps, while orange dots represent overnight jumps. Shaded gray areas denote NBER-dated
recessions. ThesampleperiodcoversSeptember1997toMay2020.
39

<!-- page 41 -->
Figure3 WordCloudsforDifferentSystematicRiskTopics
Thisfiguredisplayswordcloudsgeneratedfromnewsheadlinesassociatedwitheachcategoryofmarketjumpslisted
in Table 1. The word size reflects the frequency of each term within the headlines attributed to a given topic. The
samplespansfromSeptember1997toMay2020.
40

<!-- page 42 -->
Figure4 ContinuousandJumpBetasoverTime
Thisfiguredisplaysthetimeseriesofpercentileestimatesforcontinuousbetasandtopicjumpbetas. Thefirstpanel
presents the continuous beta estimates, while the following five panels show the jump beta estimates for the five
interpretable topics listed in Table 1. The sample covers the out-of-sample estimation period from January 2007 to
May2020. Thebluelinedenotesthecross-sectionalmedian,andthelightblueshadedareaindicatestheinterquartile
range(25thto75thpercentiles). Continuousbetasareupdatedmonthlyusingarollingwindow,whereasjumpbetas
areupdatedannuallyusinganexpandingwindow.
41

<!-- page 43 -->
Figure5 CumulativeReturnsofFactor-MimickingPortfolios
This figure plots the cumulative returns of portfolios designed to isolate jump risks associated with three types of
systematic events: (1) U.S. macroeconomic data surprises, (2) corporate earnings and forward guidance, and (3)
internationalmarketspillovers. Thesamplecoverstheout-of-sampleperiodfromJanuary2007toMay2020.
42

<!-- page 44 -->
Figure6 EconomicValueofJumpClassificationwithLLM
Thisfigureplotsthecumulativereturnsoftradingstrategiesthat,inrealtime,investinthejumpriskfactor-mimicking
portfoliowiththehighestSharperatio. Theredlinerepresentsthestrategyusingjumpcategoriesclassifiedbasedon
contemporaneousnewswireandLLManalysis. Thelighterlinesdepictplacebostrategieswherejumpcategoriesare
randomlyassignedfromauniformdistribution. Toensurecomparability,allportfoliosarevolatility-scaledtomatch
thestrategybasedonLLM-classifiedjumps. Thesamplespanstheout-of-sampleperiodfromJanuary2007toMay
2020.
43

<!-- page 45 -->
Table1 DefinitionsofTopicCategories
ThistableprovidesinformationontheoveralljumptopiccategoriesidentifiedusingthePrompt2. Thisclassification
informationisthenprovidedinthePrompt3toassigneachjumpintooneofthecategories.
TopicID TopicName TopicDefinition
1 U.S.PolicyActions(Monetary, Federal Reserve rate moves, emergency facilities, policy
Fiscal,&Political) statements,andmajorfiscalorpoliticalevents.
2 U.S.MacroDataSurprises Releases of macroeconomic information such as retail
sales, GDP, inflation, payrolls, jobless claims, etc., that
divergesharplyfromconsensus.
3 Geopolitical&SecurityEvents Developments in cross-border negotiations or ten-
sions. Terror attacks, war-risk headlines, or news that
eases/tightensmilitarytensions.
4 CorporateEarnings& Earnings/Warnings from bellwether firms or industries
Guidance thatdragorliftthewholemarket.
5 InternationalMarketSpillovers Significant moves or outlook changes in major foreign
equity markets, commodities, energy prices, or FX rates.
Overseas monetary/fiscal policy shifts, trade measures,
capital-flow controls, or other cross-border actions that
carryglobalriskimplications.
6 NoneoftheAbove Materialnewsthatdonotfittheabovedefinitions.
44

<!-- page 46 -->
Table2 SummaryStatisticsoftheJumpsbyCategories
This table reports summary statistics for jumps classified into seven categories. The six main categories—Policy,
Macro,Geopolitics,Corporate,International,andUnclassified—correspondtothosedefinedinTable1. Anadditional
category,‘Unattributable’,includesjumpsforwhichnocorrespondingnarrativeisidentifiedinthecontemporaneous
newswire.Thefinalcolumnreportsaggregatestatisticsacrossalljumps.Foreachcategory,thefollowingstatisticsare
reported: thenumberofjumps(N),theproportionoftotaljumps(%),theproportionofpositivejumps(PropPos),the
meanreturn(Mean),meanabsolutereturn(MeanAbs),standarddeviation(Std),interquartilerange(IQR),skewness
(Skew),andthevarianceexplained(R2),calculatedasthesumofsquaredreturnsinthatcategorydividedbythetotal
sumofsquaredreturnsacrossalljumps. ThesampleperiodspansfromSeptember1997toMay2020.
Policy Macro Geopol. Corp. Intl. Unclass. Unattrib. All
N 51 152 88 115 240 64 20 730
% 6.99 20.82 12.05 15.75 32.88 8.77 2.74 100.00
PropPos(%) 78.43 48.68 40.91 46.09 42.50 26.56 50.00 45.48
Mean(%) 0.63 -0.06 -0.25 -0.05 -0.15 -0.29 0.01 -0.08
MeanAbs(%) 1.07 0.79 0.86 0.78 0.80 0.80 0.91 0.82
Std(%) 1.12 0.85 0.95 0.86 0.85 0.83 0.99 0.91
IQR(%) 0.50 1.37 1.37 1.37 1.36 1.22 1.63 1.38
Skew -0.18 0.09 -0.29 0.21 0.20 0.51 -0.03 0.19
R2 13.68 18.00 13.92 13.94 29.30 8.06 3.09 100.00
45

<!-- page 47 -->
Table3 AgreementMatrixoftheJumpCategoriesamongDifferentApproaches
This table reports the agreement in jump classification among different approaches. In total, I report four different
approaches:(1)Qwen-Think:usingtheQwen3-235B-A22Bmodelwithreasoningenabledforbothnarrativeretrieval
andtopicclassification(baseline);(2)ChronoBERT:usingChronoBERTfortopicclassification;(3)LDA:usingLDA
fortopicclassification;(4)Qwen-Non-Think: usingtheQwen3-235B-A22Bmodelwithreasoningdisabledforboth
narrativeretrievalandtopicclassification.Eachnumberinthetableisthepercentagreementbetweentherowapproach
andthecolumnapproach. Thenumbersinparenthesesarethe95%confidenceintervalconstructedfollowingWilson
(1927). ThesampleperiodisfromSeptember1997toMay2020.
Qwen-Think ChronoBERT LDA Qwen-Non-Think
Qwen-Think 75.4 60.2 55.3
(71.9,78.6) (56.4,63.9) (51.5,59.2)
ChronoBERT 75.4 61.0 57.6
(71.9,78.6) (55.8,66.1) (52.3,62.7)
LDA 60.2 61.0 43.2
(56.4,63.9) (55.8,66.1) (39.5,47.1)
Qwen-Non-Think 55.3 57.6 43.2
(51.5,59.2) (52.3,62.7) (39.5,47.1)
46

<!-- page 48 -->
Table4 RiskPremiaEstimates
Thistablereportsannualizedriskpremiaestimates,standarderrors,andSharperatiosforsevenFama-MacBethfactor-
mimicking portfolios, based on the continuous-time Fama-MacBeth regression described in Equation (11). Risk
premia and standard errors are expressed in percentage points. The annualized Sharpe ratio is computed using the
correspondingfactor-mimickingportfolioreturns.Thefinalrowreportsresultsforthecontemporaneousmarketexcess
returnasabenchmark. Thesamplecoverstheout-of-sampleperiodfromJanuary2007toMay2020.
PanelA:Around-the-ClockAnalysis
AnnRP(%) StdErr(%) SR
Continuous 4.14 (5.29) 0.21
Policy 0.40 (1.79) 0.06
Macro 3.65 (1.32) 0.78
Geopolitics -0.92 (1.21) -0.21
Corporate 2.77 (1.59) 0.48
International 1.91 (2.04) 0.26
RealtimeTopic 5.72 (1.64) 0.95
PanelB:Intraday-OnlyAnalysis
AnnRP(%) StdErr(%) SR
Continuous 4.02 (5.20) 0.21
Policy 2.27 (1.30) 0.48
Macro 2.16 (1.49) 0.40
Geopolitics 2.05 (1.25) 0.45
Corporate -0.78 (1.08) -0.20
International -1.23 (0.81) -0.42
RealtimeTopic 2.69 (1.26) 0.58
Market 8.48 (4.35) 0.53
47

<!-- page 49 -->
Table5 OvernightandIntradayRiskPremia
This table presents the decomposition of annualized risk premia. Panel A reports the breakdown into overnight and
intradaycomponents,whereeachiscomputedbyholdingthefactorduringthecorrespondingtimewindow. PanelB
furtherdecomposestheriskpremiaintothreecomponents: thecontinuouspart,overnightjumps,andintradayjumps,
basedonthereal-timeFama-MacBethregressionspecifiedinEquation(11).Ireportresultsfortwosystematicfactors:
(1)thehigh-frequencymarketexcessreturn(Mkt-RF),and(2)thehigh-frequencyGANs-basedSDFconstructedby
AletiandBollerslev(2025),followingthemethodologyofChenetal.(2024). Foreachfactor,Ireporttheannualized
risk premia (Ann RP) and their corresponding standard errors (Std Err), both in percentage points. Asterisks *, **,
and *** denote statistical significance at the 10%, 5%, and 1% levels, respectively. The sample period spans from
September1997toMay2020.
PanelA:RiskPremiaDecomposition
Mkt-RF SDF
AnnRP(%) StdErr(%) AnnRP(%) StdErr(%)
Overnight 7.68*** (2.31) 6.63*** (2.04)
Intraday -0.25 (3.39) 9.48** (3.74)
PanelB:JumpRiskPremiaDecomposition
Mkt-RF SDF
AnnRP(%) StdErr(%) AnnRP(%) StdErr(%)
Continuous 2.11 (3.01) 10.37* (5.52)
Jump 7.96** (3.41) 9.31** (4.11)
Overnight
Jump 0.51 (2.64) 4.01 (3.59)
Intraday
48

<!-- page 50 -->
Table6 RegressionagainstRiskFactors
This table presents the results from regressions of topic-based factor-mimicking portfolios on standard risk factors.
Two test assets are evaluated: (i) a factor-mimicking portfolio constructed to offset exposure to the macroeconomic
topic risk, and (ii) a real-time portfolio that dynamically invests in the topic associated with the most significant t-
statisticfromtheFama-MacBethregressioneachmonth. Foreachspecification,Ireportthemonthlyabnormalreturn
(α),expressedinpercentagepoints,inthefirstrow.RegressionsincrementallycontrolfortheFamaandFrench(2015)
factors—marketexcessreturn(Mkt-RF),size(SMB),value(HML),profitability(RMW),investment(CMA),aswell
asmomentum(MOM).Newey-Weststandarderrorswith12lagsarereportedinparentheses. Asterisks*,**,and***
indicatestatisticalsignificanceatthe10%,5%,and1%levels,respectively. ThesamplespansJanuary2007toMay
2020.
MacroTopic Real-timeTopic
(1) (2) (3) (4) (5) (6)
Alpha(%) 0.30*** 0.31*** 0.28*** 0.48*** 0.41*** 0.29**
(0.10) (0.10) (0.09) (0.12) (0.11) (0.10)
Mkt-RF 0.01 0.02 0.11*** 0.11***
(0.04) (0.03) (0.04) (0.03)
SMB 0.15*** 0.11***
(0.02) (0.04)
HML -0.11*** -0.09**
(0.03) (0.04)
RMW -0.05 0.04
(0.07) (0.10)
CMA 0.17*** -0.10
(0.06) (0.11)
MOM 0.04* -0.01
(0.02) (0.05)
Months 161 161 161 161 161 161
49

<!-- page 51 -->
Table7 Real-TimeJumpRiskFactor-MimickingPortfoliowithTransactionCosts
This table reports the net of trading costs portfolio performance of the real-time topic-based jump risk factor-
mimicking portfolio. Following Frazzini et al. (2018), I consider three specifications with trading costs of 10 bps,
20bps,and50bpsperdollartraded. IreportthenetoftradingcostSharperatio(SR),annualizedreturn(AnnRP(%)),
volatility (SD(%)), and monthly portfolio turnover. The net trading cost portfolio performance is quantified using
Equation(12). Theout-of-sampleperiodspansJanuary2007toMay2020.
SR AnnRP(%) SD(%) Turnover
c=10bps 0.93 5.65 6.00 0.10
c=20bps 0.91 5.59 6.01 0.10
c=50bps 0.85 5.10 6.01 0.10
50

<!-- page 52 -->
Table8 LookaheadBiasinLLMandIncrementalValueofLLM
This table reports annualized risk premia estimates, standard errors, and Sharpe ratios similar to Table 4. Panel A
reportstheresultsforjumptopicclassificationbasedontheChronoBERTmodelproposedinHeetal.(2025a). Panel
B reports the results for jump topic classification based on the LDA model trained in Bybee et al. (2024). Risk
premia and standard errors are expressed in percentage points. The annualized Sharpe ratio is computed using the
correspondingfactor-mimickingportfolioreturns. Thesamplecoverstheout-of-sampleperiodfromJanuary2007to
May2020.
PanelA:RiskPremiaEstimatesusingChronoBERT
AnnRP(%) StdErr(%) SR
Continuous 4.19 (5.42) 0.21
Policy -0.31 (1.50) -0.06
Macro 3.10 (1.28) 0.68
Geopolitics -0.46 (0.86) -0.14
Corporate 1.56 (1.50) 0.29
International 2.00 (1.86) 0.30
Unclassified -1.07 (1.25) -0.23
RealtimeTopic 4.02 (1.62) 0.68
PanelB:RiskPremiaEstimatesusingLDA
AnnRP(%) StdErr(%) SR
Continuous 4.13 (5.44) 0.21
Policy -1.73 (1.70) -0.28
Macro 3.18 (1.58) 0.56
Geopolitics -0.91 (0.94) -0.27
Corporate 2.97 (1.54) 0.54
International 2.23 (1.66) 0.37
Unclassified -1.14 (1.49) -0.21
RealtimeTopic 1.58 (1.56) 0.28
51

<!-- page 53 -->
Table9 ValueofThinking
This table reports annualized risk premia estimates, standard errors, and Sharpe ratios similar to Table 4, using the
Qwen3-235B-A22Bmodelwithreasoningdisabled(Non-Thinkmode). Comparingtheresultsagainstthebaselinein
Table4,whichusesthesamemodelwithreasoningenabled,highlightsthevalueoftest-timecomputeandreasoning
capabilities. Risk premia and standard errors are expressed in percentage points. The annualized Sharpe ratio is
computed using the corresponding factor-mimicking portfolio returns. The sample covers the out-of-sample period
fromJanuary2007toMay2020.
RiskPremiaEstimatesusingQwen3-Non-Think
AnnRP(%) StdErr(%) SR
Continuous 4.15 (5.34) 0.21
Policy 0.97 (1.26) 0.21
Macro 2.02 (1.39) 0.40
Geopolitics -0.07 (0.91) -0.02
Corporate 1.61 (1.34) 0.33
International 1.67 (1.40) 0.33
Unclassified -1.45 (1.49) -0.27
RealtimeTopic 2.14 (1.50) 0.39
52

<!-- page 54 -->
Table10 CountsofMacroNewsCategoriesTriggeringU.S.MarketJumps
This table presents the category counts of the main macro indicator explaining the market jump within the
macroeconomictopic. ThemacroeconomictopicisidentifiedusingQwen3-235B-A22BwithPrompt1toPrompt3.
ThesamplespansfromSeptember1997toMay2020.
High-levelCategories IndicatorSub-category NumberofOccurrences
LaborMarket Non-farmPayroll/EmploymentSituation 34
WeeklyInitialJoblessClaims 13
ADPPrivatePayrolls 3
Subtotal 50
GrowthandRealActivities RetailSales 12
DurableGoodsOrders 9
GDP 8
IndustrialProduction/CapacityUtility 4
HousingStarts/BuildingPermits 3
ManufacturingSurveys 2
TradeBalance 1
Subtotal 39
Inflation ConsumerPriceIndex(CPI) 13
ProducerPriceIndex(PPI) 7
EmploymentCostIndex(ECI) 4
Import/GDPPriceDeflators 3
Subtotal 27
FinancialConditions CreditSpread 5
Subtotal 5
SectorSpecific SemiconductorSales 1
Subtotal 1
Total 152
53

<!-- page 55 -->
Table11 RiskPremiaofPre-ScheduledMacroeconomicFactor-MimickingFactors
This table presents the results from regressions of pre-scheduled macroeconomic factors on standard risk factors.
Two test assets are evaluated: (i) a factor-mimicking portfolio constructed to offset exposure to the pre-scheduled
macroeconomicnewsrisk,and(ii)thefactor-mimickingportfolioaddingallothernon-macronewstopicsascontrols.
For each specification, I report the monthly abnormal return (α), expressed in percentage points, in the first row.
Regressions incrementally control for the Fama and French (2015) factors—market excess return (Mkt-RF), size
(SMB),value(HML),profitability(RMW),investment(CMA),aswellasmomentum(MOM).Newey-Weststandard
errorswith12lagsarereportedinparentheses. Asterisks*, **, and***indicatestatisticalsignificanceatthe10%,
5%,and1%levels,respectively. ThesamplespansJanuary2007toMay2020.
Pre-scheduledMacro Pre-scheduledMacrowithControls
(1) (2) (3) (4) (5) (6)
Alpha(%) 0.41** 0.23 0.13 0.22 0.07 0.02
(0.17) (0.15) (0.15) (0.18) (0.17) (0.16)
Mkt-RF 0.25*** 0.30*** 0.20*** 0.19***
(0.03) (0.04) (0.03) (0.04)
SMB 0.04 0.24***
(0.07) (0.07)
HML -0.12** -0.16**
(0.06) (0.07)
RMW -0.04 -0.02
(0.09) (0.10)
CMA -0.10 -0.10
(0.11) (0.11)
MOM 0.05 0.01
(0.04) (0.04)
Months 161 161 161 161 161 161
54

<!-- page 56 -->
6 Appendix
6.1 Additional Results
This section presents the additional theoretical and empirical results for the paper. The first two
proofsshowthepure-playpropertyoftheFama-MacBethfactor-mimickingportfoliosanddiscuss
the cross-section regression estimates as the solution to the pure-play problem with minimum L2
portfolionorm. Next,IprovidedetailsontheWaldtestofwhetherallriskpremiaareequal. Then,
I discuss in detail the procedure I use for obtaining the topic classification using the pretrained
LDAmodelfromBybeeetal.(2024).
Proofofpure-playpropertyofFama-MacBethfactor-mimickingfactors:
Proof. Each Fama-MacBeth cross-section regression regresses the excess returns dR on an
t
interceptandlaggedβs. Writingthestackeddesignmatrixasβ =[1,βC,βJ].
t t t
TheportfolioweightingmatrixW satisfies:
t
W′ β =I .
t t K+2
Bydesign,the j-thcolumnofW satisfiesEquation(4). Therefore,theportfoliow′dR isthereturn
t j t
on a portfolio purely driven by exposure to the corresponding risk and is immunized against all
othersourcesofrisk.
Proof thatW defined in Equation (3) is the minimum L2 norm portfolio satisfying the pure-
t
playproperty:
Proof. Ateachdatet,runtheFama-MacBethcross-sectionthatregressesexcessreturnsdR onan
t
interceptandlaggedbetas. StacktheN assets’regressorsintheN×(K+2)designmatrix
β = (cid:2) 1,β C,β J(cid:3) ,
t t t
andassumeβ hasfullcolumnrank(nomulticollinearityacrosstheK+2columns).
t
Definetheportfolio-weightingmatrixW ∈RN×(K+2) suchthat
t
W′ β =I .
t t K+2
55

<!-- page 57 -->
Aconvenientchoiceisthe(transposeofthe)Moore–Penroseleftinverseofβ :
t
W′ = (β ′ β )−1β ′ ⇐⇒ W = β (β ′ β )−1.
t t t t t t t t
(cid:124)(cid:123)(cid:122)(cid:125)
(K+2)×N
Because (β′β )−1β′ is the Moore–Penrose left inverse, it is the unique solution to Xβ = I
t t t t K+2
with minimum Frobenius norm ∥X∥ , and columnwise it yields the minimum ℓ –norm portfolio
F 2
weightsthatachieveagivenexposure. Equivalently,foreach j∈{1,...,K+2},
w = arg min ∥w∥ s.t. β ′w=e ⇒ w =β (β ′ β )−1e ,
t,j 2 t j t,j t t t j
w∈RN
where e is the j-th canonical basis vector in RK+2. The constraint β′w =e says that w has
j t t,j j t,j
unitexposuretothe j-thcolumnofβ andzeroexposuretoallothercolumns. Hence,theportfolio
t
return w′ dR is pure-play: it is driven purely by the j-th risk and is immunized against all other
t,j t
risksinβ (includingtheintercept).
t
Therefore, withW =β (β′β )−1, each column w implements a pure-play factor-mimicking
t t t t t,j
portfolioand,amongallportfoliosachievingβ′w=e ,hastheminimumℓ normofweights.
t j 2
WaldHypothesisTestthatAllRiskPremiainEquation(2)areEqual.
I test whether the K jump-topic premia and the continuous risk premia are equal following
Wald(1943). LettheK+1-vectorofjumpriskfactor-mimickingportfolioreturnsbe
h ≡(β ′ β )−1β ′∆R ∈RK+1, t =1,...,T,
t t t t t
anddefinethe(unconditional)premiavectorΛ≡E[h ]withestimator
t
1 T
Λ(cid:98) = h¯ ≡ ∑h
t
∈RK+1.
T
t=1
The condition below states the null and restrictions. The hypothesis that all risk premia are equal
is
H : λ C =λ J,1 =···=λ J,K ⇐⇒ RΛ=0,
0
56

<!-- page 58 -->
whereR∈RK×(K+1) stacksadjacentdifferences,
 
1 −1 0 ··· 0
 0 1 −1 ··· 0 
 
R =   . . . . . . . . . ... . . .   .
 
0 ··· 0 1 −1
Fortheasymptoticvarianceofh¯,letS(cid:98)bethe(K+1)×(K+1)Newey-West(Bartlett)long-run
covarianceof{h },i.e.,
t
S(cid:98) = Γ
0
+ ∑ L w
ℓ
(cid:0) Γ
ℓ
+Γ′
ℓ
(cid:1) , Γ
ℓ
≡
T
1 ∑ T (h
t
−h¯)(h
t−ℓ
−h¯)′, w
ℓ
=1−
L+
ℓ
1
.
ℓ=1 t=ℓ+1
ThenVar(h¯)≈V(cid:98) ≡S(cid:98)/T.
With these setups, I lay out the Wald statistic and decision rule as follows. The Wald statistic for
H is:
0
(cid:16) (cid:17)−1
W = T(RΛ(cid:98))′ RV(cid:98)R′ (RΛ(cid:98)),
whichunderH satisfiesW →− d χ2. Forasignificancelevelα,rejectH if
0 K 0
W > χ2 .
K,1−α
ObtainingtopicprobabilityusingapretrainedLDAmodelbasedonword-countinformation:
Let K denote the number of topics andV the bigram vocabulary of the pretrained LDA model
(Bybee et al., 2024). Denote the pretrained probability of word count conditional on topic k by
φ =P(w|k)andthetopicpriorbyπ =P(k).
kw k
For a document represented by count vector c=(c ) , where c indicates the frequency of
w w∈V w
bi-gramwinthedocument,IcomputetheposteriorprobabilityoftopickviaBayes’ruleusingthe
multinomiallikelihood:
P(k|c) ∝ π ∏ φ cw
k kw
w∈V
This formulation assumes that word occurrences are generated independently from a multinomial
distribution conditional on the topic assignment. To avoid numerical underflow issues common
57

<!-- page 59 -->
withproductsofmanysmallprobabilities,Iimplementthiscomputationinlogspace:
logP(k|c) = logπ + ∑ c logφ +const.
k w kw
w∈V
Tokens that do not appear in the pretrained vocabulary V are excluded from the calculation,
effectivelytreatingthemasuninformativefortopicclassification.
My classification pipeline proceeds in three steps. First, I tokenize the retrieved articles and
model explanations into bi-grams using the pretrained vocabulary to obtain the count vector c.
This ensures consistency with the vocabulary used during LDA training. Second, I compute the
normalized posterior distribution pˆ = (pˆ ,...,pˆ ) over all K topics using the formula above,
1 K
where pˆ = P(k | c)/∑ K P(k′ | c). Third, I aggregate the fine-grained LDA topics into five
k k′=1
interpretable economic categories (plus an “unclassified” category for topics that do not fit the
primarycategories)usingamappingconstructedviaLLMannotationoftopickeywords. Finally,I
assigneachjumpeventtotheeconomiccategorywiththehighestaggregatedposteriorprobability:
Category=argmax ∑ pˆ
j∈{categories} k
k∈topics(j)
where topics(j) denotes the set of LDA topics mapped to category j. This approach leverages the
granularity of the pretrained topic model while producing economically interpretable classifica-
tions.
58

<!-- page 60 -->
6.2 Microfoundation for Empirical Analysis
In this section, I provide an ICAPM model following Merton (1973) to motivate the empirical
analysis framework laid out in Section 2.1. Specifically, I consider a infinite-period representative
investor economy with CRRA utilities, stochastic opportunities linked to jumps in the market. I
then present how this environment gives rise to the equilibrium risk premia for assets specified in
Equation(2).
Environment. Arepresentativeinvestorhastime-additiveCRRAutilityoverconsumption,
(cid:90) ∞ C 1−γ
max E e−δt t dt, γ >0, δ >0, (15)
0
{Ct,wt} 0 1−γ
and invests in N assets with (vector) excess return dR ∈RN and a risk-free rate r . LetW denote
t t t
wealthandw ∈RN portfolioweights(fractionsofwealthintheN riskyassets). Wealthevolvesas
t
(cid:104) (cid:105)
dW = W r dt+w′dR −C dt. (16)
t t t t t t
Systematic shocks, topics, and state dynamics. Let the vector of systematic shocks be dF =
t
(cid:0) dFC,dF J,1 ,...,dF J,K(cid:1)′ , where dFC is a continuous (diffusive) component and dF J,k are topic-
t t t t t
labeled jump components (macro, policy, international, etc.). The asset return process has a linear
exposure(beta)structure:
dR = B dF + dε , E [dε ]=0, Var (dε )=Σ . (17)
t t t t t t t t ε,t
Write B = [βC, β J,1 ,...,β J,K ] with βC ∈ RN and β J,k ∈ RN. The investment opportunity set
t t t t t t
dependsonaMarkovstateX ∈Rm thatishitbythesameshocks,
t
K
dX = a(X )dt + G (X )dFC + ∑G (X )dF J,k , (18)
t t C t t J,k t t
k=1
allowingexpectedreturns,volatilities,andtheshortratetodependonX .
t
Shockspecification. Fortransparency,Iassume
dFC = Σ 1/2 dZ , dF J,k = J (k) dN (k) −J¯(k) ν (k) dt, (19)
t F,t t t t t t t
(k)
where Z is a standard Brownian vector, Σ ≻ 0 is its conditional covariance, N is a Poisson
t F,t t
59

<!-- page 61 -->
processwithintensityν (k) ,J (k) isthejumpsize(vectorinRdim(dF)),andJ¯(k) :=E [J (k) ]isusedto
t t t t t
compensatethejumptozeromean. AllobjectsmaydependonX .
t
Investor’sHJB.LetV(W,X)bethevaluefunction. TheBellmanequationis
(cid:40)
C1−γ
0 = sup e−δt + V (cid:0) Wr+Ww′(E [dR ]/dt)−C (cid:1) + V′a(X)
1−γ W t t X
C,w
+ 1 V W2w′(Var (dR )/dt)w + 1 Tr (cid:2) V (Var (dX )/dt) (cid:3)
WW t t XX t t
2 2 (20)
+ V W(Cov (dR ,dX )/dt)w
WX t t t
(cid:41)
K (cid:104) (cid:105)
+ ∑ν (k)E V (cid:0) W +Ww′∆R(k),X+∆X(k)(cid:1) −V(W,X) ,
t
k=1
where∆R(k):=dR /dN (k) and∆X(k):=dX /dN (k) arethe(vector)jumpsinreturnsandstateupon
t t t t
atopic-k event.
First-order conditions. The consumption FOC is the usual e−δtC−γ =V . The portfolio FOC is
W
quadraticinw:
E [dR ] Cov (dR ,dX ) Var (dR )
0 =V W t t + V W t t t + V W2 t t w
W WX WW
dt dt dt
(21)
K (cid:104) (cid:105)
+ ∑ν (k)E ∆V(k)W∆R(k) ,
t
k=1
where∆V(k) :=V (cid:0) W +Ww′∆R(k),X+∆X(k)(cid:1) −V(W,X).
CRRA scaling and linearization. Under CRRA, V(W,X)=
W1−γ
Φ(X) with Φ(X)>0. Hence
1−γ
V =W−γΦ(X)andV =−γW−1V . AlsoV =W−γΦ (X)andV =W1−γΦ (X)/(1−
W WW W WX X XX XX
γ). Substitutingin(21)anddividingbyV W gives
W
E [dR ] Φ Cov (dR ,dX ) Var (dR )
t t X t t t t t
0 = + − γ w
dt Φ dt dt
(cid:124)(cid:123)(cid:122)(cid:125)
=:∇XlogΦ
 
(22)
K  ∆V(k) 
+ ∑ν (k)E  ∆R(k).
t V W 
k=1  W 
(cid:124) (cid:123)(cid:122) (cid:125)
jumpmarginalvalue
60

<!-- page 62 -->
For small jumps I linearize ∆V(k)/(V W) ≈ (1−γ)w′∆R(k)+ ΦX ∆X(k), which yields the affine
W Φ
FOC:
E t [dR t ] (cid:0) (cid:1)Cov t (dR t ,dX t )
γ(Var (dR )/dt)w = + ∇ logΦ
t t X
dt dt
(23)
K (cid:104) (cid:105)
+ ∑ν (k)E (cid:0) (1−γ)w′∆R(k)+(∇ logΦ)∆X(k)(cid:1) ∆R(k) .
t X
k=1
Projectiononsystematicshocks. Using(17)–(18)andtheorthogonalityofdε ,
t
E [dR ] E [dF]
t t t t
=B ,
t
dt dt
(cid:124) (cid:123)(cid:122) (cid:125)
=:Λt
Var (dR ) Var (dF)
t t =B t t B′+Σ ,
dt t dt t ε,t
Cov (dR ,dX ) (cid:16) (cid:17)
t t t
=B G , G ,...,G ,
t C J,1 J,K
dt
where Λ′ :=(λC,λ J,1 ,...,λ J,K ) stacks the drifts (prices) associated with dF.14 Solving (23) for
t t t t t
w and substituting back, the Euler equation holds for every portfolio. Therefore, for each asset i
theconditionalmeanmustbethelinearprojectiononthesystematicshocks:
K
E [dR ] = β C λ Cdt + ∑β J,k λ J,k dt, (24)
t i,t i,t t i,t t
k=1
withbetasdefinedasregressioncoefficients,
Cov (dR ,dFC)
E(cid:2)
dR dF
J,k(cid:3)
β C := t i,t t , β J,k := t i,t t , (25)
i,t Var t (dF t C) i,t E t (cid:2) (dF t J,k )2 (cid:3)
andtopicpricesofriskgivenby
λ C = γ Var (dFC)1/2 + (cid:0) ∇ logΦ (cid:1) G + (continuouspartofjumpcorrection),
t t t X C
(cid:104) (cid:105) (26)
λ J,k = ν (k)E (1−γ)w′B ∆F(k) + (∇ logΦ)∆X(k) ,
t t t t X
where ∆F(k) := dF/dN (k) . Equation (24) is exactly the expected-return relation used in our
t t
J,k
empirical work: each topic k carries a distinct price λ reflecting (i) risk compensation (via γ
t
and jump curvature) and (ii) the investment-opportunity channel through ∇ logΦ and how the
X
14BecausedFJ,k arecompensatedtozeromeanin(19),theirλ J,k originatefromthejumptermontheright-hand
t t
sideof(23).
61

<!-- page 63 -->
newstopicshockmovesX (thematricesG ,G and∆X(k)).
t C J,k
62

<!-- page 64 -->
6.3 Large Language Model Hosting and Fine-tuning
Inthissection,IfocusontheapproachIuseforhostingandfine-tuningthelargelanguagemodels.
InthefirstSubsection,IdiscussthemethodologyofhostingtheQwen3-235B-A22Bmodelinboth
itsreasoning(Think)andnon-reasoning(Non-Think)modes. InthesecondSubsection,Ifocuson
theapproachIusetofine-tunetheChronoBERTmodelfortextclassification.
HostingandServingQwen3-235B-A22B
This section describes the deployment and serving setup for the Qwen3-235B-A22B language
model(Yangetal.,2025),whichisusedthroughoutthisstudytoanalyzehigh-frequencyfinancial
newsandattributemarketjumps.
ModelOverview
Qwen3-235B-A22B is a 235-billion-parameter Mixture-of-Experts (MoE) reasoning large
language model (LLM), released by the Qwen team. Its architecture activates only 22 billion
parameters per query while maintaining strong logical reasoning, robust retrieval, and high-
capacity multitask learning capabilities. A crucial feature of this model is its ability to toggle
the thinking (reasoning) capability on and off, enabling direct comparison of reasoning versus
non-reasoningperformancewithinthesamemodelarchitecture.
ThinkingandReasoning
ThereasoningcapabilityofQwen3-235B-A22Ballowsthelanguagemodeltoexploredifferent
possibilities and reflect on its own response to generate better and more accurate answers,
analogous to System II versus System I thinking proposed in Kahneman (2011). Because the
objective values answer quality over brevity, the learned policy naturally allocates more tokens—
andthereforemoreFLOPs—toharderquestions,mirroringthecompute-adaptiveeffectsfirstnoted
by Wei et al. (2022). In this study, I exploit that capability by enabling more thinking tokens for
marketjumpreasonattribution. Withmorethinkingandreasoning,Qwen3-235B-A22Bcanweigh
multiplecandidatenarratives,evaluatetemporalprecedenceandsentimentconsistency,andoutput
themostplausibledriverofthemarketjump.
Model. For the reasoning Qwen3 model, I use Qwen/Qwen3-235B-A22B-Thinking-2507-FP8
downloaded from Hugging Face. The model is an FP8-quantized version of the original model.
Afterquantization,themodelfitsina4H10080GGPUhost.
For the non-reasoning Qwen3 model, I use Qwen/Qwen3-235B-A22B-Instruct-2507-FP8
63

<!-- page 65 -->
downloadedfromHuggingFace. Similartothereasoningversion,thismodelalsofitsina4H100
80GGPUhost.
Serving Details. The model is hosted using vLLM, an open-source, high-throughput inference
engine tailored for large transformer models. I run the following command for serving the
reasoningversionofQwen3-235B-A22B:
python -m vllm.entrypoints.openai.api_server \
--model /data/models/Qwen3-235B-A22B-Thinking-2507-FP8 \
--served-model-name qwen3-235b-a22b-think \
--tensor-parallel-size 4 \
--pipeline-parallel-size 1 \
--gpu-memory-utilization 0.95 \
--enable-chunked-prefill \
--trust-remote-code \
--port 8000 --host 0.0.0.0
For the non-reasoning version of Qwen3-235B-A22B, I use the following command to serve
themodel:
python -m vllm.entrypoints.openai.api_server \
--model /data/models/Qwen3-235B-A22B-Instruct-2507-FP8 \
--served-model-name qwen3-235b-a22b-instruct \
--tensor-parallel-size 4 \
--pipeline-parallel-size 1 \
--gpu-memory-utilization 0.95 \
--enable-chunked-prefill \
--trust-remote-code \
--port 8000 --host 0.0.0.0
For both cases, the option --tensor-parallel-size 4 enables model parallelism across 4
H100GPUs.
Fine-tuningChronoBERT
I fine-tune a year-by-year sequence classifier to map model-generated explanations and
retrieved news text to discrete economic jump topics. For a given calendar year y, the training
64

<!-- page 66 -->
set includes all observations with trading dates before December 31 of the year y−1. The out-of-
sample test set is January–December of year y. Labels are the pre-defined topic indices Table 1
identifiedusingareasoningLLM.
Model. I use manelalab/chrono-bert-v1-19991231 as the initialization checkpoint. A linear
classificationheadisattachedtothelasthiddenlayerofthemodel,withthenumberoflabelsequal
tothenumberofdistincttopicsinthetrainingsplit.
Training hyperparameters. For each year y, I use the following hyperparameters to fine-tune the
ChronoBERTmodel:
1. Splitthetrainingpoolintotrain/validation(80/20)stratifiedbythetopic.
2. Optimizecross-entropywithAdamW(lr=2×10−5,weightdecay=0.01).
3. Batchsize32.
4. Train up to 50 epochs with early stopping (patience =3) on weighted F1 of the validation set;
keepthebestcheckpoint.
5. Evaluateontheheld-outtestsetinyeary. Iconsideraccuracy,precision,recall,and(weighted)
F1ofthemodel.
The final out-of-sample classification from ChronoBERT is obtained by concatenating the
classificationsfromalltestsetsacrossallyears.
65

<!-- page 67 -->
6.4 Processing High-frequency Data
In this section, I discuss the approach of processing the high-frequency financial return data.
Subsection 6.4 presents the procedure for cleaning the raw individual stock high-frequency trade
and quote data. Subsection 6.4 shows how to link the TAQ data to the CRSP and presents the
evidencetoverifythelinkingquality. Lastly,Subsection6.4introducestheprocedureIusetoclean
the high-frequency futures return data and approach to construct continuously rollover futures
returnstime-series.
CleaningofRawTradeandQuoteData
MyintradaysamplecoversallNYSE,AMEX,andNASDAQcommonstocksfrom09/01/1997
through 05/31/2020.15 Because the millisecond data do not begin until late 2003, I use MTAQ for
09/01/1997–09/09/2003 and DTAQ thereafter. The identical cleaning filters are applied to each
feed. Toconstructa15-minutepanelofequityreturns,Iapplythefollowingsteps:
Step1: Trade&quotefilters.
Starting from the raw TAQ millisecond files, I follow the procedures of Holden and Jacobsen
(2014)andDaandXiu(2021)tofiltertherawtradeandquoterecords.
• Quote records – keep only the six “regular-market” condition codes (Qu Cond) A, B, H,
O, R, W; drop all quotes flagged as cancelled (Qu Cancel = B). For the timing range, I
keep 09:00–16:00 ET so that the opening National Best Bid and Offer (NBBO) is available
at09:30ET.
• Trade records – retain original, uncancelled prints (Tr Corr = 00) and the immediately
correctedversions(01);discardallothercorrectioncodes.
Step2: NBBOconstructionandtradematching.
IreconstructtheofficialNationalBestBidandOffer(NBBO)bycombiningTAQ’sNBBOM and
CQM snapshots, ordering by descending sequence number, and removing duplicate microsecond
stamps to leave exactly one quote per time-stamp. Quotes with spread > $5 or bid>ask are
likewise deleted. Each trade is then paired with the NBBO that was in force one nanosecond
earlier;anytradewhosesubsequentNBBOislockedorcrossedisdiscarded.
Step3: Extreme-valuefilters.
Matchedtradeswhosepricesfalloutsidetheday’sNBBOrangeareremoved.
15Daily TAQ (“DTAQ”)—time-stamped to the millisecond—first becomes available on WRDS on 09/10/2003,
whereastheearlierMonthlyTAQ(“MTAQ”)productprovidessecond-levelstampsbeginning01/01/1993.
66

<!-- page 68 -->
Step4: Samplingto15-minutefrequency.
Pricesaresampledonanequal-spaced15-minutegridfrom09:30to16:00ETusingthecleaned
trade data. The last trade observed at or before each grid point is carried forward (previous-tick
method).
The procedure yields an extensive panel of 15-minute stock prices from high-quality trade
prices aligned to the prevailing NBBO with minimal contamination from stale quotes, odd lots,
corrections,orextremeoutliers.
LinkingTAQtoCRSP
Thenextstepistolinkthishigh-frequencypaneltoCRSP,whichprovidestheovernightreturns
necessary to construct around-the-clock returns for all stocks. In this section, I describe in detail
the procedures used to merge the TAQ database with CRSP and outline the steps taken to verify
thequalityofthelinkage.
I first filter the CRSP stocks to consider only ordinary common shares listed on the three
primary U.S. exchanges (exchcd ∈ {1(NYSE),2(AMEX),3(NASDAQ)}, shrcd ∈ {10,11}).
Afterfiltering,ImergeeachsecuritytotheTAQusingtheCUSIPwithinthevaliddateranges.
Finally, to further clean the merged database, I compare the intraday trade prices against the
ASKHI and BIDLO from CRSP. Any intraday price that falls outside the interval [BIDLO,ASKHI] is
set to missing, as such violations almost surely reflect data errors rather than true trades. Missing
prices are then forward-filled from the most recent valid observation to preserve the regular 15-
minutegrid.
For daily open and close prices, I use the CRSP values in place of those from TAQ. I also use
the CRSP information to calculate the overnight returns for stocks that account for stock mergers
andsplits,aswellasreturnsfromdividendpayments.
Toverifythequalityofthelinkbetweenthetwodatabases,IfollowA¨ıt-Sahaliaetal.(2020)to
build high-frequency Fama-French factors and compare the return series with the daily frequency
factors downloaded from Kenneth French’s website at https://mba.tuck.dartmouth.edu/
pages/faculty/ken.french/data_library.html.
Specifically, I follow the open-source replication of Fama-French factor construction from
Freda Song at https://www.fredasongdrechsler.com/data-crunching/fama-french to
firstobtaintheFama-Frenchfactorportfolioconstituentsovertime.
After this, I use the constructed linking table to merge the portfolio constituents to high-
frequency return observations and construct the six Fama-French factors: Mkt-RF, SMB, HML,
RMW,CMA,andMOM,usingtwo-by-threesortingwithcutoffthresholdsandportfoliorebalanc-
67

<!-- page 69 -->
ing rules following exactly the same procedure as Fama and French (2015) and Fama and French
(2018).
Finally, I aggregate the constructed high-frequency factors to daily frequency and compare
them against the official version from Kenneth French. If the linking is successful for most stocks
used to construct the factors, the two versions should closely align with each other. Otherwise,
if there are large amounts of mismatch or unmatched stocks, there will exist large discrepancies
betweenthetwo.
Figure7presentsthecumulativereturnsofthehigh-frequencyFama-Frenchfactorsversusthe
dailycounterpart. Fromthefigure,Ifindaclosealignmentofthetwo,suggestingthatthematching
ofthetwodatasetsisofhighquality.
Furthermore, the paired return series also exhibit nearly perfect correlations. I find the
correlationcoefficientsbetweenthehigh-frequencyfactoranddailycounterpartforthesixfactors
(Mkt-RF,SMB,HML,RMW,CMA,andMOM)are: 0.9996,0.9942,0.9648,0.9783,0.9624,and
0.9593,respectively.
CleaningandRolloveroftheS&P500E-miniFutures
My analysis of overnight market jumps is based on high-frequency data from the S&P 500
E-minifutures,whichtradenearly24hoursadayandthusprovideanaturalproxyforthemarket’s
pricing of overnight risk. To construct a continuous time series of futures prices, I roll over the
futureswithdifferenttimetomaturities.
Rather than rolling on a fixed calendar date, the front contract is rolled on the first trading
day after the second-nearest contract becomes more liquid than the current front contract, where
liquidity is measured by daily trading volume (or by trade count when early-sample volume
is missing). Once the book is rolled forward, contracts never move “backwards”, preserving
chronologicalorderingoffront,second,andthirdpositions.
Because the second contract is typically priced above or below the expiring front contract, I
scalepositionsizeontherolldatetokeepnotionalexposureunchanged. Ifn frontcontractspriced
t
at f1 arereplacedbythesecondcontractpricedat f2,thenewpositionsizeis:
t t
f1
n =n t .
t+1 t
f2
t
This guarantees that the strategy is self-financing and the overnight roll return from t to t+1 is
f1
simply t+1 −1.
f2
t
The resulting high-frequency futures factor tracks the S&P 500 cash index extremely closely:
68

<!-- page 70 -->
the contemporaneous correlation in overlapping intraday windows is 0.9589. Such a high
correlationconfirmsthattherolledE-miniseriescapturesthesameaggregateriskastheunderlying
index—including overnight price discovery—and is therefore a reliable instrument for studying
market-widejumps.
Figure 8 compares the cumulative returns of the E-mini futures with those of the spot market.
The left panel displays total cumulative returns, while the right panel restricts to intraday periods
withoverlappinghigh-frequencyobservations. Inbothcases,thefuturescloselymirrorthereturns
of the aggregate equity market. Notably, the cumulative return over the overnight period is nearly
flat,underscoringtheroleofovernightriskinshapingequityriskpremia.
69

<!-- page 71 -->
Figure 7 Comparison of High-Frequency Fama-French Factors against Low-Frequency
Counterpart
Thisfigureplotsthecumulativereturnsofthehigh-frequencyFama-Frenchfactorsagainstthedailyfrequencyversion
fromKennethFrench’sdatalibrary. Thefactorsconsideredinclude: Mkt-RF,SMB,HML,RMW,CMA,andMOM.
Thehigh-frequencyfactorsareaggregatedtodailyfrequencyforcomparisonwiththelow-frequencycounterpart. The
sampleperiodisfrom09/01/1997to05/31/2020.
70

<!-- page 72 -->
Figure8 ComparisonofCumulativeReturnsofE-miniFuturesagainsttheSpot
ThisfigurecomparesthecumulativereturnsofS&PE-minifuturesandthespotmarket. Theleftpanelplotsthetotal
cumulative returns using all available observations. The right panel shows cumulative returns using only intraday
observations where both series have overlapping high-frequency data. The shaded gray areas indicate NBER-dated
recessions. ThesampleperiodspansfromSeptember1997toMay2020.
71
