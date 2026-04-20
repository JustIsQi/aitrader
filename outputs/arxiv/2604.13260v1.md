# Which Voices Move Markets? Speaker Identity and the Cross-Section of Post-Earnings Returns

| 字段 | 内容 |
|------|------|
| ArXiv ID | 2604.13260v1 |
| 发布日期 | 2026-04-14 |
| 作者 | Karmanpartap Singh Sidhu, Junyi Fan, Maryam Pishgar |
| 分类 | q-fin.TR |
| PDF | https://arxiv.org/pdf/2604.13260v1 |

## 摘要

We utilize FinBERT, a domain-specific transformer model, to parse 6.5 million sentences from 16,428 S&P 500 quarterly earnings call transcripts (2015-2025) and demonstrate that post-earnings stock returns are not equally affected by all speakers in a conference call. Our section-weighted sentiment, with empirically derived speaker weights (Analyst 49%, CFO 30%, Executive 16%, Other 5%), achieves an out-of-sample Spearman IC of 0.142 versus 0.115 in-sample, generates monthly long-short alpha of 2.03% unexplained by the Fama-French five-factor model (t = 6.49), and remains significant after controlling for standardized unexpected earnings (SUE). FinBERT section-weighted sentiment entirely subsumes the Loughran-McDonald dictionary approach (FinBERT t = 5.90; LM t = 0.86 in the combined specification). Signal decay analysis and cumulative abnormal return charts confirm gradual price adjustment consistent with sluggish assimilation of soft information. All results undergo rigorous out-of-sample validation with an explicit temporal split, yielding improved rather than deteriorated predictive power.

---

## 正文

<!-- page 1 -->
Which Voices Move Markets? Speaker Identity and
the Cross-Section of Post-Earnings Returns
Karmanpartap Singh Sidhu, Junyi Fan, Maryam Pishgar
Viterbi School of Engineering, University of Southern California
kssidhu@usc.edu, junyifan@usc.edu, pishgar@usc.edu
Abstract—In this research, we have utilized FinBERT (a question from a Goldman Sachs analyst during the Q&A
domain-specifictransformermodel)parsing6.5millionsentences session. The CEO’s optimism may be strategically managed;
from 16,428 S&P 500 quarterly earnings call transcripts (2015–
the analyst’s skepticism reflects the real-time assessment of a
2025)andcategorizedtranscriptsentimentsbydifferentspeaker
sophisticated market participant with no incentive to manage
categoriesandprovedthatthestockreturnafteranearningscall
isnotequallyaffectedbyallthevoicesinanearningsconference tone.
call. The section-weighted sentiment empirically derived from This paper closes the gap between the richness of earn-
in-sample coefficients (IC) achieves an out-of-sample Spearman ings call data and the coarseness of existing measurement
IC of 0.142 versus 0.115 in-sample, generates monthly long–
approaches.WeapplyFinBERT,atransformer-basedlanguage
short alpha of 2.03% unexplained by the Fama–French five-
modelpre-trainedonfinancialtext[1],to6.5millionsentences
factormodel(t=6.49),andremainssignificantaftercontrolling
for standardized unexpected earnings (SUE) in Fama–MacBeth drawnfrom16,428quarterlyearningscalltranscriptsforS&P
cross-sectional regressions. We demonstrated that the FinBERT 500 firms over the period April 2015 to December 2025.
section-weighted sentiment entirely subsumes the Loughran– We classify each sentence by speaker role such as analyst,
McDonalddictionaryapproach(FinBERTt=5.90;LMt=0.86
chief financial officer, executive (CEO, COO, CTO), and
inthecombinedspecification),butthereverseisnottrue.Signal
other participants and propose a section-weighted aggregation
decayanalysisandcumulativeabnormalreturnchartsshowthat
prices gradually change, which is consistent with the sluggish schemeinwhichtheweightassignedtoeachspeakercategory
assimilation of soft information. All results are submitted to isderivedfromitsempiricalpredictivepowerforpost-earnings
rigorousout-of-samplevalidationwithanexplicittemporalsplit, returns on a training sample.
resultinginimprovedpredictivepowerratherthandeterioration.
Our analysis offers four key findings. First, the sentiment
aggregation method used has a first-order effect on the sig-
Index Terms—Earnings calls, sentiment analysis, FinBERT,
section weighting, Fama–French, information coefficient, NLP, nal’spredictivepotential.Thesection-weightedstrategy,which
textual analysis, asset pricing gives analyst sentiment the most weight (49%) based on
Information Coefficient (IC) estimate, yields a full-sample
I. INTRODUCTION Spearman rank IC of 0.119 versus one-day post-earnings
Corporate earnings conference calls are the single most returns, a 46% improvement over the simple mean tech-
information-dense recurring disclosure event in U.S. equity nique (IC = 0.081). Second, the section-weighted sentiment
markets. Unlike regulatory filings or press releases, which are signal produces economically significant anomalous returns:
carefully vetted documents, earnings calls feature real-time, monthly rebalanced long–short portfolios yield Fama–French
unscripted interactions between corporate management and five-factor alpha of 2.03% per month (t = 6.49), with alpha
sell-side analysts. In a typical call, the chief executive officer increasing monotonically across sentiment quintiles. Third,
and chief financial officer deliver prepared remarks summa- the mood signal captures information that differs from and
rizing the quarter’s results and strategic outlook, followed by complements the quantitative earnings surprise.
a question-and-answer session in which analysts investigate In Fama–MacBeth cross-sectional regressions with both
management on margins, guidance, competitive dynamics, section-weightedsentimentandstandardizedunexpectedearn-
and capital allocation. These conversations are rich in soft ings (SUE), both variables remain statistically significant, and
informationlikemanagerialconfidence,hedging,evasion,and double-sort analysis reveals large sentiment spreads across
analyst skepticism that is difficult to extract from quantitative all SUE terciles. Fourth, in a horse-race regression with
disclosures alone. both dictionary-based sentiment of FinBERT and Loughran–
Despite the centrality of earnings calls to the price discov- McDonald [2], FinBERT completely subsumes the dictionary
ery process, the textual analysis literature has predominantly approach: the FinBERT coefficient remains highly significant
treated each transcript as a monolithic document, computing (t=5.90), whereas the dictionary coefficient becomes statis-
aggregate sentiment scores that weight all speakers and sec- tically indistinguishable from zero (t=0.86).
tionsequally.Thisapproachdiscardsafundamentaldimension Perhaps our most remarkable discovery is on out-of-sample
of the data: the identity and informational role of the speaker. performance. Using an explicit temporal split training on data
A bullish statement by the CEO during scripted prepared until December 2022 and testing from January 2023 onward
remarks carries different informational content than a pointed with frozen section weights. The section-weighted sentiment
6202
rpA
41
]RT.nif-q[
1v06231.4062:viXra

<!-- page 2 -->
ICrisesfrom0.115in-sampleto0.142out-of-sample,andthe The recent development of transformer-based language
five-factor alpha rises from 1.56% per month in the training models has resulted in a new paradigm for financial text
period to 2.77% per month in the test period. This unusual analytics.Huangetal.[1]presentFinBERT,aBERT[6]model
pattern of out-of-sample improvement allays concerns about pre-trainedonalargecorpusoffinancialtextsuchascorporate
overfitting and indicates that the IC-derived section weights filings, earnings call transcripts, and analyst reports, which
accuratelycapturelong-termstructuralaspectsoftheearnings achieves 88.2% classification accuracy on financial sentiment
call information environment. tasks compared to 62.1% for the Loughran–McDonald dictio-
We contribute to the literature in three distinct ways. First, nary. Our work uses FinBERT as a measurement instrument
we look beyond the binary distinction between presentation ratherthanamethodologicaladdition;weareinterestedinthe
and Q&A segments to analyze individual speaker responsi- economic discoveries enabled by this more precise sentence-
bilities. We next suggest a principled, data-driven weighting levelmeasurement,aswellastheempiricalhorseracebetween
method that takes use of cross-speaker variation in predictive the two measurement paradigms.
capacity. Second, we present a thorough asset price anal-
B. Information Content of Earnings Calls
ysis including information coefficients, Fama–French factor
regressions,Fama–MacBethcross-sectionaltests,andearnings A parallel literature has focused on the information content
surprise controls that demonstrates the economic impact of of earnings conference calls. Bowen et al. [7]Matsumoto et
speaker-level sentiment decomposition. Third, we compare al. [8] provide the first systematic evidence that earnings call
context-aware deep learning sentiment to the standard dictio- language tone predicts abnormal returns and trading volume,
nary approach in a controlled horse race with identical data and that the question-and-answer segment of the call has
andreturnhorizons,providingclearevidencethattransformer- additional explanatory power for post-earnings-announcement
based models capture economically significant information drift. Their discovery that the Q&A part is more informa-
that lexicon-based methods do not. tive than prepared remarks is a significant forerunner to
The rest of the paper is organized as follows. Section II our speaker-level decomposition, even though they make no
explores the relevant literature and formulates our hypothe- distinction between individual speakers within either section.
ses. Section III discusses the data sources and sample cre-
C. Post-Earnings Announcement Drift and Earnings Surprise
ation. Section IV describes the technique, which includes
The post-earnings-announcement drift (PEAD), first de-
FinBERT sentiment scoring, the five aggregation methods,
scribedbyBallandBrown[9]andexpandeduponbyBernard
the IC-derived section weighting procedure, and the statistical
and Thomas [10], is one of the most robust oddities in
framework. Section V presents the key empirical findings.
empirical finance [11].
Section VI includes additional robustness tests. Section VII
concludes. D. Hypothesis Development
II. RELATEDLITERATUREANDHYPOTHESIS Hypothesis 1 (Speaker heterogeneity). Section-weighted
DEVELOPMENT FinBERT sentiment, with weights based on speaker-level
Information Coefficients, is more predictive of post-earnings
A. Textual Analysis in Finance
returns than equal-weighted or full-transcript sentiment. The
The use of textual data for financial prediction has de-
rationale is that various speakers hold fundamentally different
veloped dramatically since Tetlock’s (2007) [3], [4] seminal
informational perspectives. Analyst queries are spontaneous,
study proving that a gloomy tone in a Wall Street Journal
based on knowledgeable judgment, and difficult for manage-
column forecasts downward pressure on market prices and
ment to anticipate; planned management remarks are scripted
higher trading activity. That paper established a fundamental
and strategically constructed. To accurately anticipate returns,
principle: qualitative textual content provides information that
it is recommended to use a weighting technique that accounts
is more significant to the return than quantitative metrics.
for each speaker’s empirical predictive capacity, rather than
Loughran and McDonald [2] made a major methodological
relying solely on average.
contribution by demonstrating that the widely used Harvard-
Hypothesis 2 (Abnormal Returns). After adjusting for the
IV psychosocial dictionary consistently misclassifies financial
Fama and French [12] five-factor model, section-weighted
text words like “liability,” “tax,” and “capital” are labeled
FinBERT sentiment yields abnormal returns.
as negative while being neutral in financial contexts. Their
Hypothesis 3 (Orthogonality to SUE). The return pre-
finance-specific word lists, which included 347 positive and
dictability of section-weighted emotion is not absorbed by
2,345 negative phrases, were the standard instrument for
standardizedunexpectedearnings.Thishypothesisinvestigates
assessing tone in corporate disclosures and were utilized in
whether sentiment conveys soft information like managerial
hundreds of subsequent research. However, dictionary-based
confidence, strategic outlook, analyst skepticism that differs
techniques [5] are fundamentally context-blind: they identify
from hard earnings figures.
individual words in isolation, disregarding negation (“not
Hypothesis 4 (Deep Learning Subsumption). FinBERT
profitable”), hedging (“we hope to achieve”), or comparison
section-weighted sentiment replaces the Loughran–McDonald
framing (“down from strong performance last year”).
dictionary technique in a joint Fama–MacBeth regression.

<!-- page 3 -->
III. DATA portfolio-level time-series regressions use daily factor returns
A. Earnings Call Transcripts compounded to a monthly frequency. Alpha Vantage provides
quarterlyearningsdata,includingreportedandpredictedearn-
WeobtainedearningscalltranscriptsviatheAlphaVantage
ings per share, for the calculation of standardized unexpected
API, which provides verbatim records of quarterly earnings
earnings (SUE). The Loughran and McDonald [2] sentiment
conference calls for S&P 500 constituent companies. Each
dictionary was retrieved from the University of Notre Dame’s
transcript includes the speaker’s name and title, the full text
Accounting and Finance Software Repository.
of their remarks, and the date of the call. We supplement
For firm i in quarter t, the raw earnings surprise is defined
the transcripts with Yahoo Finance earnings call timestamps,
as:
which offer the exact time of each call and allow us to
Surprise =EPSactual−EPSestimate (1)
categorize them as BMO or AMC. This timing distinction is i,t i,t i,t
critical for building the appropriate return window for each Westandardizethesurprisebytheexpanding-windowstandard
event. deviation of historical earnings surprises for each firm:
Our sample covers quarterly earnings calls from April
Surprise
2015 to December 2025 for firms in the S&P 500 index. SUE = i,t (2)
i,t σ
We require each transcript to have a matched timestamp for i,t
correct return window assignment. After merging transcripts where σ is the expanding-window standard deviation com-
i,t
with timestamps and excluding calls with missing price data, puted over all prior earnings surprises for firm i, requiring
our final sample consists of 16,428 earnings call events a minimum of four prior observations for a stable variance
spanning 447 unique firms. On average, the sample includes estimate. SUE is winsorized at the 1st and 99th percentiles to
approximately 400 firms per quarter, representing the large- mitigate the influence of extreme outliers.
capitalization segment of the U.S. equity market. The sample
E. Summary Statistics
yields approximately 6.5 million scored sentences, with an
average of 394 sentences per call.
TABLEI
DESCRIPTIVESTATISTICS—PANELA:SAMPLEDESCRIPTION
B. Speaker Classification
One important aspect of our analysis is the breakdown Metric Value
of transcript sentiment by speaker role. We categorize each Sample period April 2015 – January 2025
sentence into one of four categories based on the speaker’s Total transcripts 16,537
name and title as recorded in the transcript: (i) Analyst,
Unique tickers 447
identified by titles or affiliations containing sell-side firm
Total sentences 6,513,208
names; (ii) Chief Financial Officer (CFO), identified by ti-
tles containing “CFO”, “Chief Financial Officer”, or “Trea- Mean sent./call 394
surer”; (iii) Executive, identified by titles containing “CEO”, Median sent./call 398
“Chief Executive”, “President”, “Chairman”, “COO”, “CTO”, Std. Dev. 116
or “Managing Director”; (iv) Other. Operator sentences are
Min / Max 36 / 2,172
removedfromallstudiesbecausetheyonlyincludeprocedural
ThesampleendswithearningscallsreportedthroughQ42024.Tickercount
language and no sentiment content. Table 1-2 shows sample
reflectsS&P500constituentswithavailabletranscripts;variationacrossyears
coverage and Table 3-4 shows coverage by category. isduetoindexreconstitutionanddataavailability.
C. Stock Returns
TABLEII
Yahoo Finance provides stock prices and daily returns. We
DESCRIPTIVESTATISTICS—ANNUALCOVERAGE
create event-window returns that take into account whether Year Calls Tickers
the earnings call takes place before or after market open. For
2015 1,098 387
AMC calls, the one-day return is calculated as the percentage
2016 1,250 388
changeinclosingpricefromdayt−1todayt+1,givingthe
market an entire trading session to react. For BMO calls, the 2017 1,310 366
one-day return is calculated from day t−1 to day t, as the 2018 1,477 403
market can respond during the same trading session. Five-day 2019 1,563 417
returnsarecreatedsimilarly,withthewindowextendedtoday
2020 1,574 427
t+5 (AMC) or day t+4 (BMO). This time convention is
2021 1,481 420
common practice in the earnings announcement literature.
2022 1,638 441
D. Fama–FrenchFactorsandStandardizedUnexpectedEarn-
2023 1,716 445
ings
2024 1,719 444
We get the Fama and French [12] five-factor data and
the risk-free rate from Kenneth French’s data library. The

<!-- page 4 -->
TABLEIII which captures the model’s certainty that the sentence carries
DESCRIPTIVESTATISTICS—PANELB:SUMMARYSTATISTICS non-neutral sentiment.
Variable N Mean Std Min P25 Med P75 Max
B. Aggregation Methods
Sentimentmeasures
Simplemean 16,109 0.263 0.085 −0.28 0.208 0.265 0.321 0.567 A single earnings call produces hundreds of sentence-level
(M1)
Conf-wtd(M2) 16,109 0.417 0.133 −0.48 0.336 0.433 0.514 0.757 sentiment assessments. Aggregating these into a call-level
Extremefrac 16,109 0.261 0.094 −0.30 0.199 0.261 0.324 0.613 signal necessitates a technique selection, and we demonstrate
(M3)
Sect-wtd(M4) 16,109 0.192 0.072 −0.33 0.145 0.194 0.241 0.684 that this decision has a first-order impact on predictive power.
Analyst(M5) 15,954 0.107 0.062 −0.26 0.067 0.108 0.147 0.477 Wecomparefiveaggregatingstrategies,rangingfromspeaker-
Returnvariables
agnostic to speaker-aware approaches.
1-dayret. 16,109 0.003 0.068 −0.84 −0.030 0.002 0.034 1.560
5-dayret. 16,109 0.006 0.097 −0.84 −0.036 0.004 0.045 6.786 LetS i ={s 1 ,s 2 ,...,s N }denotethesetofN non-operator
Controlvariables sentences in call i. For each sentence s, FinBERT produces
SUE 16,109 0.991 1.607 −3.41 0.038 0.730 1.795 5.566
a net sentiment score τ(s) ∈ [−1,1] and a confidence score
This table reports summary statistics for the main variables. The sample
consistsof16,109earningscall–returnobservationsforS&P500firmsfrom c(s)∈[0,1].
April2015toDecember2024.SentimentscoresarecomputedusingFinBERT Simple Mean (M1). The first method computes the arith-
at the sentence level and aggregated to the call level using five methods
metic average of net sentiment scores across all sentences:
described in Section IV. The 1-day post-earnings return is measured from
closeondayt−1tocloseondayt+1(AMCcalls)orcloseondayt(BMO 1 (cid:88)
calls).SUEiswinsorizedatthe1stand99thpercentiles. τˆmean = τ(s) (5)
i N
i
TABLEIV
s∈Si
PANELC:SPEAKERCLASSIFICATIONANDIC-DERIVEDWEIGHTS This is the approach taken implicitly by most previous inves-
tigations and serves as our baseline. It sees every sentence,
Speaker Sentences %Tot Mean Std ICWt
whetherspokenbytheCEO,ananalyst,orajuniorexecutive,
Analyst 1,313,021 20.2% 0.108 0.330 49.0%
as equally informative.
CFO 1,713,991 26.3% 0.268 0.574 30.0%
Executive 3,320,982 51.0% 0.325 0.471 16.2% Confidence-Weighted Mean (M2). The second method
Other 165,214 2.5% 0.171 0.415 4.7% weights each sentence by its FinBERT confidence score:
Total 6,513,208 100% 100% (cid:80)
c(s)·τ(s)
ICweightsarederivedfromthetrainingsample(pre-January2023).Foreach τˆcw = s∈Si (6)
speakercategoryg,wecomputetheSpearmanrankcorrelation(Information i (cid:80) c(s)
Coefficient) between category-average sentiment and 1-day post-earnings
s∈Si
returns. Weights are set proportional to the IC for categories with positive Statements that are confidently characterized as positive or
IC:wg =ICg/(cid:80) g′:ICg′>0 IC g′. negative receive more weight, but unclear or boilerplate state-
ments are given less weight. This is inspired by the finding
IV. METHODOLOGY
that a significant proportion of earnings call sentences contain
A. Sentence-Level Sentiment via FinBERT neutral procedural language, diluting the sentiment signal.
WeuseFinBERT[1],aBERT-basedtransformermodelpre- Extreme Fractions (M3). The third method measures
trained on a large corpus of financial text that includes cor- the proportion of strongly positive minus strongly negative
porate filings, earnings call transcripts, and analyst reports, to sentences:
assess the sentiment of each earnings call. Unlike dictionary- (cid:34) (cid:35)
1 (cid:88) (cid:88)
basedtechniques,whichidentifyindividualwordsinisolation, τˆext = ⊮{τ(s)>0.5}− ⊮{τ(s)<−0.5}
i N
FinBERT evaluates each phrase in its entirety, yielding three i s∈Si s∈Si
probability scores: P(positive), P(negative), and P(neutral) (7)
This captures the intensity of sentiment by focusing on the
that sum to one.
We use a sentence-level scoring approach for two reasons. tails of the sentence-level distribution rather than the central
First,FinBERT’smaximuminputlengthis512tokens,making tendency.
sentence-level processing a suitable unit of analysis. Second, Section-Weighted Mean (M4)—IC-Derived. The fourth
sentence-level scores provide the granularity required for method, which is our key methodological addition, gives
speaker-specific aggregation. The NLTK sentence tokenizer differential weights to sentences based on the speaker’s
splits each transcript paragraph into separate sentences. Sen- function, with the weights calculated using the em-
tences fewer than ten characters are eliminated because they pirical predictive power of each speaker category on
usually comprise greetings or procedural language with no the training sample. For each speaker category g ∈
sentiment content. For each sentence i, we compute a net G = {Analyst,CFO,Executive,Other}, we first compute the
sentiment score: within-category average sentiment for call i:
1 (cid:88)
S i =P(positive) i −P(negative) i (3) τ¯ i,g = |S | τ(s) (8)
i,g
which ranges from −1 to +1. We also define a confidence s∈Si,g
score as: whereS ⊆S isthesubsetofsentencesspokenbycategory
i,g i
c =1−P(neutral) (4) g. We then derive category weights from the training-period
i i

<!-- page 5 -->
Information Coefficients. For each category g, the Spearman p < 0.001) and earns nearly half the overall weight (48.8%),
rank IC between τ¯ and one-day post-earnings returns r although accounting for only 20.2% of total phrases. CFO
i,g i,1
is computed on the training sample (April 2015 to December sentiment carries 29.5% weight, executive sentiment 15.9%,
2022; 11,138 calls). Weights are proportional to the IC for andotherspeakers5.8%.Theseweightsarefrozenandapplied
categories with positive predictive power: to the out-of-sample time with no re-estimation required.

w g =
(cid:80)
g′:IC
IC
g′>
g
0 IC g′
if IC
g
>0
(9)
D.
F
L
o
o
r
u
t
g
h
h
e
ra
b
n
e
–
n
M
ch
c
m
D
a
o
r
n
k
a
c
ld
om
D
p
ic
a
t
r
i
i
o
s
n
o
a
n
r
,
y
se
S
n
c
t
o
im
rin
e
g
nt scores are cal-
0
otherwise culated using the Loughran and McDonald (2011) financial
sentimentvocabulary.Foreachsentence,wecountthenumber
wherethesumistakenoverallcategoriesg′ withpositiveIC,
of terms in the positive and negative word lists and calculate
ensuring that the weights sum to one. The section-weighted
a normalized tone measure.
sentiment score for call i is then:
(cid:80) w ·τ¯ E. Statistical Framework
τˆsw = g∈Gi g i,g (10)
i (cid:80) w 1) Information Coefficients: For each month m contain-
g∈Gi g
ing at least 20 earnings call observations, we compute the
whereG isthesetofcategoriespresentincalli.Thedenomi-
i Spearman rank correlation between the sentiment score and
natorrenormalizestheweightswhenacategoryisabsentfrom
the one-day post-earnings return. The time-series average IC
a particular transcript. Importantly, the weights are generated
and its statistical significance are assessed using Newey–West
just for the training period and applied without modification
[13] HAC standard errors with bandwidth L=min{3, ⌊0.75·
to the out-of-sample period (January 2023 onward), ensuring M1/3⌋}, where M is the number of monthly observations:
no look-ahead bias.
Analyst-Only Sentiment (M5). Motivated by the weight I¯C= 1 (cid:88) M IC
decomposition in Method 4—where analysts receive 49% of M m
total weight despite contributing only 20% of sentences—we m=1 (12)
I¯C
consider a parsimonious specification that uses only analyst t =
NW (cid:113)
sentiment: Vˆar (I¯C)
NW
1 (cid:88)
τˆanalyst = τ(s) (11) 2) Fama–MacBeth Cross-Sectional Regressions: We esti-
i |S |
i,analyst s∈Si,analyst mate monthly cross-sectional regressions following Fama and
MacBeth [14]:
This removes all management remarks, leaving only sell-side
analystinquiriesandfollow-ups.Therationaleisthatanalysts,
r =γ +γ τˆ +ε (13)
i,t+1 0,m 1,m i,t i,m
as informed market participants with no incentive to manage
tone,providealessfilteredassessmentofthefirm’sprospects. r i,t+1 =γ 0,m +γ 1,m τˆ i,t +γ 2,m SUE∗ i,t +ε i,m (14)
C. IC-Derived Section Weights whereallindependentvariablesarecross-sectionallystandard-
ized within each month to facilitate comparison of coefficient
TABLEV magnitudes. The time-series averages of slope coefficients are
IC-DERIVEDSECTIONWEIGHTDERIVATION reported with Newey–West t-statistics.
Speaker TrainIC p-value N ICwt. Eqwt. Hardwt. 3) Fama–French Five-Factor Time-Series Regressions: For
Analyst 0.128*** 3.03e–42 11,179 48.8% 25.0% 40.0% the portfolio-level analysis, we sort stocks each month into
CFO 0.078*** 5.44e–16 10,835 29.5% 25.0% 25.0% quintiles by sentiment and compute equal-weighted portfolio
Executive 0.042*** 1.13e–05 10,963 15.9% 25.0% 25.0%
returns. The long–short portfolio buys Q5 (most positive
Other 0.015 3.35e–01 4,029 5.8% 25.0% 10.0%
sentiment) and sells Q1 (most negative). We regress monthly
Sum 0.263 100% 100% 100%
Thistablereportsthederivationofsectionweightsfromin-sampleInformation portfolio excess returns on the five Fama–French factors:
Coefficients. The training sample includes all 11,179 earnings call observa-
tionspriortoJanuary1,2023.Foreachspeakercategoryg,wecomputethe R −Rf =α +β MktRF +β SMB +β HML
Spearmanrankcorrelationbetweencategory-averageFinBERTnetsentiment p,t t p 1 t 2 t 3 t (15)
+β RMW +β CMA +ε
and 1-day post-earnings returns. N varies across categories because not all 4 t 5 t p,t
callscontaineveryspeakertype.AllfourcategoriesexhibitpositiveIC,though
The intercept α represents the average monthly abnormal
Otherisnotstatisticallysignificant(p=0.335).Analystsentimentcarriesthe p
highest marginal predictive content (IC = 0.128, p < 0.001) and receives return unexplained by the five factors.
nearlyhalfthetotalweight(48.8%),despitecomprisingonly20.2%oftotal 4) Double-Sort Analysis: To test orthogonality between
sentences.Theseweightsarefrozenandappliedwithoutmodificationtothe
sentiment and earnings surprise, we independently sort firms
out-of-sample period (January 2023 onward). Hardcoded weights reflect an
ad hoc prior used in preliminary analysis. *** p < 0.01; ** p < 0.05; * into SUE terciles and, within each tercile, into sentiment
p<0.10. quintiles. For each SUE tercile q ∈ {Low,Mid,High}, we
Table5showstheweightderivation.Inthetrainingsample, compute the long–short return spread:
the IC for all four categories is positive. Analyst attitude
∆r =r¯(Q5|q)−r¯(Q1|q) (16)
has the highest marginal predictive content (IC = 0.128, q

<!-- page 6 -->
Significant spreads across all three SUE terciles confirm that TABLEVII
sentiment captures return-relevant information orthogonal to OUT-OF-SAMPLEVALIDATION
earnings surprises.
Method TrainIC N TestIC N Decay
5) Out-of-Sample Design: We employ an explicit temporal
Simplemean(M1) 0.0806 11,297 0.0966 5,131 −19.9%
split for out-of-sample validation. The training period spans Conf-wtd(M2) 0.1005 11,297 0.1075 5,131 −6.9%
April 2015 to December 2022 (11,138 call observations), and Extreme(M3) 0.0736 11,297 0.0914 5,131 −24.2%
the test period spans January 2023 onward (4,971 observa- Sect-wtd(M4) 0.1141 11,297 0.1442 5,131 −26.4%
tions).SectionweightsforMethodM4arederivedexclusively Analyst(M5) 0.1273 11,297 0.1707 5,131 −34.1%
from training-period ICs and applied without modification to Thistablereportstheout-of-samplevalidationofeachsentimentaggregation
method. Train IC is computed on the in-sample period (April 2015 –
the test period. This design ensures no look-ahead bias and
December 2022; N = 11,297). Test IC is computed on the out-of-sample
provides a clean assessment of whether the sentiment signal’s period(January2023–December2024;N =5,131),usingweightsfrozen
predictive power generalizes to new data. fromthetrainingperiod.Decayisdefinedas(TrainIC−TestIC)/|TrainIC|;
negativevaluesindicatethesignalstrengthensoutofsample.Section-weighted
V. EMPIRICALRESULTS sentimentusesIC-derivedweightsfromthetrainingsample(Table5):Analyst
48.8%,CFO29.5%,Executive15.9%,Other5.8%.
A. Information Coefficient Comparison
TABLEVI
INFORMATIONCOEFFICIENTCOMPARISONACROSSAGGREGATION
METHODS
Method IC(1d) tNW p-value IC(5d)
Simplemean(M1) 0.0813 5.49*** 4.10e–08 0.0673
Conf-wtd(M2) 0.0986 6.36*** 2.04e–10 0.0804
Extremefrac(M3) 0.0749 5.36*** 8.43e–08 0.0620
Section-wtd(M4) 0.1188 9.11*** 8.05e–20 0.0988
Analyst-only(M5) 0.1405 11.71*** 1.16e–31 0.1171
SpearmanrankICbetweeneachaggregationmethodandpost-earningsreturns
for S&P 500 firms. Full sample N = 16,428. tNW: Newey–West t-
statisticfrommonthlyICs;lag=min{3,⌊0.75·T1/3⌋}.IC-derivedweights
(Table 5): Analyst 48.8%, CFO 29.5%, Executive 15.9%, Other 5.8%. ***
p<0.01;**p<0.05;*p<0.10. Fig. 1. Monthly Information Coefficients Over Time. Blue bars: in-sample
(2015–2022);redbars:out-of-sample(2023+).Blackline:six-monthrolling
Table 6 shows the Spearman rank Information Coefficients
average. In-sample mean IC = 0.099; OOS mean IC = 0.115. The signal is
for each sentiment aggregation method versus one-day post- positivein85%ofmonthsandstrengthensout-of-sample.
earnings returns. The findings clearly confirm Hypothesis 1:
TABLEVIII
selecting an aggregate method has a first-order effect on
QUINTILEPORTFOLIORETURNS—PANELA:FULLSAMPLE
predictive power. The section-weighted approach (M4) yields (N =16,428)
a full-sample IC of 0.119 (t = 9.11), demonstrating a 46%
improvement over the basic mean baseline (IC = 0.081, Method Q1 Q2 Q3 Q4 Q5 Q5-Q1 t Mon
Simple(M1) −0.67 0.24 0.34 0.38 0.93 1.60*** 9.89 Yes
t = 5.49) and a 21% improvement over the confidence-
Sect-wtd(M4) −0.96 −0.18 0.46 0.60 1.30 2.26*** 13.33 Yes
weighted approach (IC = 0.099, t = 6.36). The analyst-only Analyst(M5) −1.22 −0.10 0.19 0.77 1.63 2.85*** 16.35 Yes
specification (M5) has the highest IC of 0.141 (t = 11.71),
TABLEIX
which is consistent with the discovery that analyst sentiment
QUINTILEPORTFOLIORETURNS—PANELB:OUT-OF-SAMPLE
receives the most section weight. (N =5,131)
B. Out-of-Sample Validation Method Q1 Q2 Q3 Q4 Q5 Q5-Q1 t Mon
Simple(M1) −1.34 −0.04 0.06 0.47 0.79 2.13*** 6.28 Yes
Several explanations could explain this finding. First, the
Sect-wtd(M4) −1.77 −0.38 0.31 0.40 1.38 3.14*** 9.07 Yes
trainingperiodencompassesthevolatile2020–2021era,when
Analyst(M5) −2.02 −0.77 −0.00 0.98 1.74 3.76*** 10.58 Yes
unprecedented fiscal and monetary actions dominated price
C. Quintile Portfolio Analysis
dynamics,reducingtheimpactoffirm-specificsentiment.Sec-
ond,theincreasingprominenceofalgorithmicandquantitative Table8-10showstheaverageone-daypost-earningsreturns
trading in post-2023 markets may have accelerated the rate at for quintile portfolios organized by section-weighted emo-
which sentiment is reflected in prices, paradoxically creating tion. Returns are precisely monotonic across quintiles, with
more opportunities for a properly calibrated sentiment metric. Q1 (most negative sentiment) earning an average return of
Third, and most significantly, the IC-derived section weights −0.96%andQ5(mostpositive)earning+1.30%.TheQ5–Q1
properly identify analyst tone as a long-term informative long–short spread is 2.26% daily (t=13.33). This monotonic
signal, a structural aspect of the earnings call information pattern is economically significant. A quintile-sorted spread
environmentthatisunlikelytobeduetoin-sampleoverfitting. of more than 2% in a single trading day and it supports
Hypothesis 2.

<!-- page 7 -->
TABLEX of0.00679(t=7.16).Table11-12showswhenSUEisadded
PANELC:DETAILEDQUINTILEBREAKDOWN—SECTION-WEIGHTED asajointregressor,thesentimentcoefficientdropsto0.00505,
(M4),FULLSAMPLE
although it remains highly significant (t = 5.57). The SUE
Mean Meanret. Stdret. coefficient keeps its predictive effectiveness after correcting
Quintile N t-stat
sent. (%) (%) forsentiment,droppingveryslightlyfrom0.01425(univariate)
Q1(mostneg) 3,286 0.0907 −0.962 6.716 −8.21 to 0.01342 (joint). These findings suggest that sentiment and
Q2 3,285 0.1557 −0.183 6.351 −1.65
SUEcaptureprimarilyorthogonalinformation,whichsupports
Q3 3,286 0.1941 0.458 6.916 3.79
Hypothesis 3.
Q4 3,285 0.2310 0.603 6.853 5.04
Q5(mostpos) 3,286 0.2906 1.301 7.042 10.59 TABLEXIII
Q5−Q1 2.263*** 13.33 DOUBLE-SORT:SENTIMENTQUINTILESWITHINSUETERCILES
This table reports average 1-day post-earnings returns (%) for quintile port-
folios sorted by sentiment. Q1 contains the most negative sentiment calls; SUETercile N Q1(%) Q5(%) Q5-Q1 t
Q5 contains the most positive. Q5–Q1 is the long–short spread. Panel A LowSUE 5,370 −2.767 −0.539 2.227*** 7.27
reports full-sample results. Panel B reports out-of-sample results (January MidSUE 5,369 −0.291 1.323 1.613*** 5.67
2023onward),usingsectionweightsfrozenfromthetrainingperiod.PanelC
HighSUE 5,370 1.178 2.323 1.145*** 4.06
provides a detailed breakdown for M4, including the mean sentiment score,
returnstandarddeviation,andindividualquintilet-statistics.Monoindicates Thistablereportsanon-parametrictestofwhethersentimentpredictsreturns
monotonicity. The t-statistic for Q5–Q1 is from a two-sample t-test. *** independentlyofearningssurprise.Observationsarefirstsortedintoterciles
p<0.01. by SUE, then within each SUE tercile, stocks are sorted into quintiles by
section-weightedsentiment(M4).Thesentimentspreadisstatisticallysignif-
In the out-of-sample time, the spread increases to 3.14% icantatthe1%levelinallthreeSUEterciles.ThespreadislargestforLow
SUEfirms(2.23%),suggestingthatsentimentisparticularlyinformativewhen
(t = 9.07), demonstrating that the signal extends beyond the
earningsdisappoint—positivetoneduringabadquartersignalsmanagement
training data. Panel C’s detailed quintile breakdown reveals confidencethatthemarketunderweights.
that both sides of the deal contribute: Q1 gets significantly
Table 13 shows non-parametric confirmation using double-
negative returns (t = −8.21), while Q5 earns significantly
sort analysis. Within each SUE tercile, the Q5–Q1 sentiment
positive returns.
spread is positive and statistically significant at the 1% level:
D. Controlling for Earnings Surprise 2.23%forlow-SUEenterprises,1.61%formid-SUEfirms,and
1.15% for high-SUE firms. The highest spread occurs among
TABLEXI firmswithnegativeearningssurprises,implyingthatsentiment
CONTROLLINGFOREARNINGSSURPRISE:PANELA—INFORMATION
is especially useful when earnings disappoint. A positive tone
COEFFICIENTS
duringadifficultquarterconveysmanagementconfidencethat
Signal IC(1d) tNW p-value N the market is initially underweighted.
SUE 0.2458 17.58*** 3.29e–69 16,109
Sect-wtd(M4) 0.1184 8.95*** 3.55e–19 16,109
Analyst(M5) 0.1409 11.94*** 7.07e–33 15,954
TABLEXII
CONTROLLINGFOREARNINGSSURPRISE:PANELB—FAMA–MACBETH
REGRESSIONS
Variable Model1 Model2 Model3 Model4
Sect-wtd(M4) 0.00679*** — 0.00505*** —
(7.16) (5.57)
Analyst(M5) — — — 0.00809***
(6.94)
SUE — 0.01425*** 0.01342*** 0.01346***
(14.17) (13.43) (13.17)
Months 110 110 110 110
This table examines whether sentiment predicts post-earnings returns af-
ter controlling for SUE. Panel A reports Spearman ICs. Panel B reports
Fama–MacBeth cross-sectional regression coefficients (standardized cross-
sectionally), with Newey–West t-statistics in parentheses. Model 3 is the Fig. 2. Return Surface: Section-Weighted Sentiment × SUE. Mean 1-day
keyspecification:section-weightedsentimentremainshighlysignificant(t= post-earnings returns across 16,109 calls sorted into sentiment quintiles and
5.57) after jointly controlling for SUE. The SUE coefficient declines only SUEterciles.Surfacespans−2.63%(Q1,LowSUE)to+2.23%(Q5,High
modestlyfrom0.01425to0.01342,confirmingthatsentimentandSUEcapture SUE).Bothdimensionscontributeindependently(p<0.01).
largelyorthogonalinformation.***p<0.01.
E. Fama–French Five-Factor Alpha
A natural fear is that earnings call attitude only serves as
a proxy for the hard earnings surprise: managers sound opti- Table 14 shows the findings of time-series regressions of
misticwhentheyexceedexpectationsanddepressedwhenthey sentiment-sorted portfolio returns on the Fama and French
fall short. Table 11 handles this issue directly using Fama– [12] five factors. The long–short portfolio based on section-
MacBeth cross-sectional regressions. In the univariate model, weighted sentiment generates a monthly alpha of 2.03%
section-weighted sentiment has a Fama–MacBeth coefficient (t=6.49), which translates to an annualized alpha of 24.3%.

<!-- page 8 -->
TABLEXIV Table 16 investigates alpha stability across subperiods. The
FF5ALPHA—PANELA:LONG–SHORTPORTFOLIOFACTORLOADINGS section-weighted long–short portfolio provides significant al-
pha both before and after COVID (2.23%/month, t = 11.70
Factor M4 Coeff tNW M5 Coeff tNW
and 2.87%/month, t = 10.35). The only time with low
α(monthly) 2.026%*** 6.49 2.542%*** 8.69
alpha is 2020–2021, when enormous macroeconomic actions
α(annualized) 24.31% 30.51%
dominated individual stock price movements. In the out-of-
Mkt–RF 0.1223* 1.74 0.1013 1.56
sample test period (2023 onward), alpha is 2.77% per month
SMB −0.1816* −1.79 −0.0925 −0.86
(t=8.56), which exceeds the training-period alpha of 1.56%,
HML 0.2002* 1.86 −0.0012 −0.01
consistent with the IC evidence of out-of-sample progress.
RMW −0.1077 −0.72 −0.1411 −1.21
CMA −0.1953 −1.60 0.0858 0.59 F. FinBERT versus Loughran–McDonald: Horse Race
R2 0.079 0.034
TABLEXVII
N (months) 100 99
FINBERTVS.LM:PANELA—FULL-SAMPLEIC
The R2 of 0.079 confirms the signal is largely orthogonal to known risk
factors.Newey–Weststandarderrorswith⌊0.75·T1/3⌋lags.***p<0.01; LM
Method FBIC FBt LMt FB/LM
**p<0.05;*p<0.10. IC
The five-factor regression has an R2 of only 0.079, indicating Simplemean 0.0813 10.46*** 0.0691 8.88*** 1.2×
thatknownriskvariablesexplainlittleofthelong–shortreturn Conf-wtd 0.0986 12.70*** 0.0930 11.98*** 1.1×
variation.Factorloadingsaretinyandlargelyinconsequential, Extreme 0.0749 9.63*** 0.0716 9.20*** 1.0×
indicating that the emotion signal is not a proxy for any of Section-wtd 0.1188 15.33*** 0.0745 9.58*** 1.6×
the usual risk factors. Analyst-only 0.1405 18.10*** 0.0619 7.91*** 2.3×
Full-sampleSpearmanICsagainst1-daypost-earningsreturns(N =16,428).
TABLEXV
FinBERT dominates LM across all methods; the advantage is largest for
FF5ALPHA—PANELB:ALPHABYQUINTILE,SECTION-WEIGHTED
section-weighted(1.6×)andanalyst-only(2.3×)aggregations.***p<0.01.
(M4)
Quintile α(mo.) α(ann.) tNW p-value TABLEXVIII
FINBERTVS.LM:PANELB—OUT-OF-SAMPLEIC
Q1(mostneg) −0.939%*** −11.27% −3.34 8.41e–04
Q2 0.040% 0.48% 0.21 8.31e–01 FB LM LM
Method FB Test
Q3 0.106% 1.27% 0.49 6.25e–01 Train Train Test
Q4 0.479%*** 5.74% 3.36 7.94e–04 Simple mean 0.0806 0.0966 0.0625 0.0876
Q5(mostpos) 1.086%*** 13.04% 7.76 8.75e–15 Conf-wtd 0.1005 0.1075 0.0963 0.0944
Q5−Q1 2.026%*** 24.31% 6.49 8.36e–11
Extreme 0.0736 0.0914 0.0765 0.0763
Table 15 decomposes alpha into distinct quintiles. The Section-wtd 0.1141 0.1442 0.0586 0.1077
pattern is strikingly monotonic: Q1 gets a monthly alpha of Analyst-only 0.1273 0.1707 0.0452 0.0936
−0.94% (t = −3.34), Q2 through Q3 earn near-zero alpha,
FinBERT’s OOS advantage widens for section-weighted and analyst-only
and Q5 earns +1.09% (t = 7.76). The fact that both the methods.Train:N =11,297;Test:N =5,131.
long and short sides contribute to the spread contradicts risk-
based theories and supports the view that the mood signal TABLEXIX
FINBERTVS.LM:PANELC—QUINTILELONG–SHORTSPREADS
captures mispricing caused by the sluggish integration of soft
information. FinBERT
Method LMQ5-Q1
Q5-Q1
TABLEXVI
SUB-PERIODANDOUT-OF-SAMPLEFF5ALPHA Simplemean 1.604% 1.251%
Conf-wtd 1.844% 1.678%
Period α(mo.) α(ann.) tNW p-value Mo.
Extreme 1.469% 1.060%
Sub-periodanalysis
Section-wtd 2.263% 1.355%
Pre-COVID
2.227%*** 26.73% 11.70 1.33e–31 39
(15–19) Analyst-only 2.847% 1.029%
COVID(20–21) −0.505% −6.06% −0.68 4.99e–01 21
Table 17 shows a head-to-head comparison of FinBERT
Post-COVID(22+) 2.865%*** 34.38% 10.35 4.29e–25 40
and Loughran–McDonald (LM) prediction power for all five
Out-of-samplevalidation
aggregations. FinBERT outperforms LM across all methods,
Train(pre-23) 1.560%*** 18.72% 4.48 7.55e–06 71
Test(2023+) 2.770%*** 33.23% 8.56 1.16e–17 29 with the greatest advantage for section-weighted (IC: 0.119
This table reports the FF5 alpha of the section-weighted (M4) long–short vs.0.075,a1.6×ratio)andanalyst-only(IC:0.141vs.0.062,
portfolioacrosssub-periodsandout-of-sampleusingweightsfrozenfromthe a 2.3× ratio) aggregations. FinBERT’s contextual awareness
training period. Alpha is significant at the 1% level in all periods except
is most effective when applied to the language of sophisti-
2020–2021. The test-period alpha (2.77%/month, t = 8.56) exceeds the
training-period alpha (1.56%/month), consistent with out-of-sample signal cated market players (analysts) who use hedging, conditional
strengthening.Newey–Weststandarderrorswith⌊0.75·T1/3⌋lags.
wording, and implicit comparison. Tables 18 and 19 confirm

<!-- page 9 -->
thatFinBERT’sadvantagewidensout-of-sampleandtranslates B. Cumulative Abnormal Returns
into larger quintile spreads. The advantage is weakest for
We create cumulative abnormal return (CAR) charts by
confidence-weighted aggregate (1.1×).
categorizing companies into sentiment quintiles during each
earnings call and tracking abnormal returns (compared to
TABLEXX
FAMA–MACBETHHORSERACE:DOESFINBERTSUBSUMELM? the S&P 500) for 30 trading days after the call. The CAR
chart shows the classic fan-shaped divergence between Q1
Model 1 Model 2 Model 3
Variable and Q5. Over 30 days, the most positive sentiment quintile
(FB) (LM) (Joint)
collects around +1.5% in anomalous returns, while the most
PanelA:Section-WeightedSentiment
negativequintileaccumulatesapproximately−1.5%,resulting
FinBERTsect-wtd 0.00692*** — 0.00660***
in a total variance of around 3.0%. The divergence begins
(7.14) (5.90)
abruptlyonday0(theannouncementday)andsteadilywidens
LMsect-wtd — 0.00306*** 0.00073
over the next two weeks, consistent with delayed information
(4.09) (0.86)
assimilation and the PEAD literature.
PanelB:Analyst-OnlySentiment
FinBERTanalyst 0.00956*** — 0.00986*** C. Industry Controls
(8.18) (7.65) To ensure that our findings are not influenced by industry-
LManalyst — 0.00262*** −0.00109 level sentiment clustering for example, if technology busi-
(3.57) (−1.37) nesses consistently have more positive earnings calls and
Months 112 112 112 greater returns. We incorporate GICS sector fixed effects into
ThistablereportsFama–MacBethcross-sectionalregressionstestingwhether the Fama–MacBeth regressions. The section-weighted senti-
FinBERT sentiment subsumes the LM dictionary. Newey–West t-statistics mentcoefficientremainssignificantfollowingthisadjustment,
in parentheses. Models 3 and 6 are the key subsumption tests. FinBERT
remains highly significant (t = 5.90 and t = 7.65) while LM becomes indicating that the signal acts within industries rather than
insignificant (t = 0.86 and t = −1.37), demonstrating that FinBERT across them.
completelysubsumestheLMdictionary.TheFinBERTcoefficientisvirtually
unchangedbetweenunivariateandjointspecifications(0.00692→0.00660 D. Machine Learning Validation: XGBoost with SHAP
in Panel A; 0.00956 → 0.00986 in Panel B), confirming LM adds no
incrementalinformation.***p<0.01. As an alternative validation of the IC-derived section
weights, we train an XGBoost gradient-boosted tree model
Table 20 shows the definitive subsumption test. In the
[15] to predict one-day post-earnings returns using the four
Fama–MacBethhorseracewithsection-weightedaggregation,
speaker-categorysentimentscoresasinputfeatures.Themodel
FinBERT alone gives a coefficient of 0.00692 (t = 7.14),
is trained on the same pre-2023 sample and evaluated out-of-
while LM alone produces 0.00306 (t = 4.09). When both
sample with frozen parameters. We then apply SHAP [16]
are considered together, FinBERT maintains its significance
(SHapley Additive exPlanations) to decompose the model’s
(0.00660, t=5.90), whereas LM becomes statistically indis-
predictionsintofeature-levelcontributionsontheheld-outtest
tinguishable from zero (0.00073, t = 0.86). The results are
set.
even more dramatic for analyst-only aggregation: in the joint
specification, FinBERT’s coefficient actually grows somewhat TABLEXXI
(0.00986, t = 7.65), whereas LM’s becomes negative and XGBOOST–SHAPFEATUREIMPORTANCEANDICVALIDATION
negligible (−0.00109, t = −1.37). This comprehensive sub-
Mean
Speaker Feature SHAP % IC Wt %
sumptionresultshowsthatFinBERTcatchesallthedictionary |SHAP|
does, plus significant more information gleaned from compre- Analyst 0.00489 59.6% 48.8%
hendingthelinguisticcontextinwhichfinancialtermsappear. CFO / Finance 0.00239 29.1% 29.5%
This finding supports Hypothesis 4.
Top Executive 0.00070 8.5% 15.9%
VI. ADDITIONALTESTSANDROBUSTNESS Other Mgmt 0.00023 2.8% 5.8%
A. Return Horizon Decay ModelInformationCoefficients
In-sample IC 0.1723 (std=0.0613)
We look at how the Information Coefficient of the section-
Out-of-sample IC 0.1711 (std=0.0686)
weightedsentimentsignaldecaysoverreturnhorizonsranging
ThistablereportsSHAPfeatureimportancefromanXGBoostmodeltrained
from1to21tradingdays.TheICismaximumfortheone-day
onthefourspeaker-categoryFinBERTsentimentscorestopredict1-daypost-
horizon (0.119) and decreases almost exponentially, reaching earningsreturns.Themodelistrainedonthepre-2023sampleandevaluated
0.099 after 5 days, 0.065 after 10 days, and 0.032 after 21 out-of-sample.Mean|SHAP|istheaverageabsoluteSHAPvalueacrosstest-
setobservations.SHAP%iseachfeature’sshareoftotalimportance.ICWt
days. The signal has a half-life of about 6–7 trading days,
%reproducestheSpearmanIC-derivedweightsfromTable5forcomparison.
whichsupportsthetheorythatearningscallemotioncomprises TheSHAPrankingconfirmstheIC-derivedhierarchy.Thenear-zeroin-sample
short-lived information that is gradually integrated into prices to out-of-sample IC decay (0.172 → 0.171) confirms the stability of the
speakerimportancestructure.
throughoutthefirstonetotwoweeksafterthecall.Thisdecay
pattern is significant for practitioners since the signal is most The SHAP-derived importance ranking closely mirrors the
beneficial when executed shortly after the call and fades over IC-derivedweighthierarchy:analystsentimentdominateswith
a monthly period. 59.6% of total SHAP importance (compared to 48.8% IC

<!-- page 10 -->
weight), followed by CFO sentiment at 29.1% (vs. 29.5% IC whichassigns49%weighttoanalystsentiment,30%toCFOs,
weight).TheXGBoostmodelachievesanin-sampleSpearman 16% to executives, and 5% to other speakers, substantially
IC of 0.172 (std = 0.061) and an out-of-sample IC of 0.171 outperforms na¨ıve equal-weighted aggregation. The section-
(std = 0.069), representing a meaningful improvement over weighted sentiment signal achieves an out-of-sample Infor-
the linear section-weighted approach (OOS IC = 0.144). mation Coefficient of 0.142, generates monthly Fama–French
Crucially, the near-zero decay between in-sample and out-of- five-factoralphaof2.03%forthelong–shortportfolio,andre-
sample IC (0.172 vs. 0.171) further confirms that the speaker- mainssignificantaftercontrollingforstandardizedunexpected
level sentiment hierarchy is a stable, structural feature of the earnings.
earnings call information environment rather than a statistical Our most important methodological finding is the com-
artifact.Theconvergencebetweenthemodel-freeICweighting plete subsumption of the Loughran–McDonald dictionary by
approach and the nonlinear machine learning model provides FinBERT in a controlled horse-race regression. When both
strong corroborating evidence that analyst sentiment is the measures are included in the same Fama–MacBeth speci-
dominant return-predictive component of earnings calls, and fication, FinBERT retains full statistical significance while
that the relative ranking of speaker categories is robust to the the dictionary-based measure becomes indistinguishable from
choice of estimation methodology. zero.Thisresulthasbroadimplicationsforthetextualanalysis
literature: it suggests that context-aware deep-learning models
E. ExampleSentences:FinBERTversusLoughran–McDonald
capture everything that bag-of-words methods capture, plus
Table 22 illustrates the divergence between FinBERT and substantial additional information arising from an understand-
LM classification. Panel A shows cases where FinBERT ingofnegation,hedging,andcomparativeframinginfinancial
detects clear sentiment but LM finds no dictionary words language.
for example, “15% YoY growth” scores +0.95 in FinBERT Several implications follow from our findings. For prac-
but 0.00 in LM because “growth” is absent from the LM titioners, our results identify a specific, implementable al-
lexicon. Panel B highlights disagreements: LM flags “strong” pha source: buying stocks with positive earnings call senti-
as positive in “down 24% from strong performance,” while ment and selling those with negative sentiment, with weights
FinBERT correctly reads the sentence as negative. Panel C tiltedtowardanalystcommentary.Foracademics,oursection-
confirms both methods agree on unambiguous cases. weightedICframeworkprovidesaprincipledmethodologyfor
constructing sentiment signals from any multi-speaker corpo-
TABLEXXII
EXAMPLESENTENCES:FINBERTVS.LMDIVERGENCE rate communication. For regulators and market microstructure
researchers,thefindingthatmarketsareslowtoincorporatethe
Sentence(abridged) FB LM Category
nuancedinformationembeddedinearningscallconversations,
PanelA:FinBERTdetects,LMseesnothing
particularly the divergence between analyst and management
“This15%YoYgrowthforJAKAFA
tone, contributes to the growing understanding of how soft
net product sales reflects higher pa- +0.95 0.00 FB+/LM∅
tientdemandacrossallindications.” information is priced in equity markets.
“Revenues were $545M, down 5% Our analysis is subject to certain limitations. The sample
vs. prior year, while adjusted rev- −0.97 0.00 FB−/LM∅
is restricted to S&P 500 firms, which represent the large-
enuesfell4%.”
capitalization segment of the market; it remains an open
PanelB:FinBERTandLMdisagree
question whether section-weighted sentiment is equally in-
“Excluding negative FX, revenue
grew 4%... while EPS increased +0.95 −0.04 FB+/LM− formative for small-cap firms where information asymmetry
14%.” may be more acute. We also note that implementation of the
“FICC revenues $2B, down 24% −0.97 +0.04 FB−/LM+ long–short strategy would face transaction costs and capacity
fromstrongperformancelastyear.”
constraints that we do not model. Finally, while our out-of-
PanelC:Bothagree(validation)
sampleresultsareencouraging,thetestperiod(2023–2025)is
“Strongglobalgrowthimprovedend-
userdemandacrossallregions.” +0.95 +0.18 Both+ relativelyshort,andlonger-termstabilityofthesignalwarrants
“Total revenue down 4%, including continued monitoring.
3% organic decline and 1 ppt unfa- −0.97 −0.12 Both−
vorableFX.” REFERENCES
FinBERTscores:[−1,+1].LM:(Npos−Nneg)/N words.PanelA:FinBERT
[1] Huang, A. H., Wang, H., and Yang, Y. (2023). “FinBERT: A Large
detectssentimentwhereLMfindsnodictionarywords.PanelB:disagreements
LanguageModelforExtractingInformationfromFinancialText.”Con-
fromcontext-blindwordmatching.PanelC:agreementonunambiguouscases.
temporaryAccountingResearch,40(2),806–841.
[2] Loughran, T. and McDonald, B. (2011). “When Is a Liability Not a
VII. CONCLUSION Liability? Textual Analysis, Dictionaries, and 10-Ks.” The Journal of
Finance,66(1),35–65.
This paper demonstrates that the identity of the speaker in
[3] Tetlock,P.C.(2007).“GivingContenttoInvestorSentiment:TheRole
an earnings conference call matters as much as what they say of Media in the Stock Market.” The Journal of Finance, 62(3), 1139–
for predicting post-announcement stock returns. By applying 1168.
[4] Tetlock, P. C., Saar-Tsechansky, M., and Macskassy, S. (2008). “More
FinBERTto6.5millionsentencesfromS&P500earningscall
ThanWords:QuantifyingLanguagetoMeasureFirms’Fundamentals.”
transcripts and decomposing sentiment by speaker role, we TheJournalofFinance,63(3),1437–1467.
show that an empirically derived section-weighting scheme,

<!-- page 11 -->
[5] Jegadeesh,N.andWu,D.(2013).“WordPower:ANewApproachfor
ContentAnalysis.”JournalofFinancialEconomics,110(3),712–729.
[6] Devlin, J., Chang, M.-W., Lee, K., and Toutanova, K. (2019). “BERT:
Pre-training of Deep Bidirectional Transformers for Language Under-
standing.”ProceedingsofNAACL-HLT,4171–4186.
[7] Bowen, R. M., Davis, A. K., and Matsumoto, D. A. (2002). “Do
ConferenceCallsAffectAnalysts’Forecasts?”TheAccountingReview,
77(2),285–316.
[8] Matsumoto, D., Pronk, M., and Roelofsen, E. (2011). “What Makes
Conference Calls Useful? The Information Content of Managers’ Pre-
sentationsandAnalysts’DiscussionSessions.”TheAccountingReview,
86(4),1383–1414.
[9] Ball,R.andBrown,P.(1968).“AnEmpiricalEvaluationofAccounting
IncomeNumbers.”JournalofAccountingResearch,6(2),159–178.
[10] Bernard,V.L.andThomas,J.K.(1989).“Post-Earnings-Announcement
Drift:DelayedPriceResponseorRiskPremium?”JournalofAccounting
Research,27,1–36.
[11] Jiang,F.,Lee,J.,Martin,X.,andZhou,G.(2019).“ManagerSentiment
andStockReturns.”JournalofFinancialEconomics,132(1),126–149.
[12] Fama, E. F. and French, K. R. (2015). “A Five-Factor Asset Pricing
Model.”JournalofFinancialEconomics,116(1),1–22.
[13] Newey, W. K. and West, K. D. (1987). “A Simple, Positive Semi-
Definite,HeteroskedasticityandAutocorrelationConsistentCovariance
Matrix.”Econometrica,55(3),703–708.
[14] Fama,E.F.andMacBeth,J.D.(1973).“Risk,Return,andEquilibrium:
EmpiricalTests.”JournalofPoliticalEconomy,81(3),607–636.
[15] Chen,T.andGuestrin,C.(2016).“XGBoost:AScalableTreeBoosting
System.”Proceedingsofthe22ndACMSIGKDD,785–794.
[16] Lundberg, S. M. and Lee, S.-I. (2017). “A Unified Approach to Inter-
pretingModelPredictions.”AdvancesinNeuralInformationProcessing
Systems,30,4766–4777.
