import akshare as ak

def fetch_etf(symbol):
    df = ak.fund_etf_hist_em(symbol=symbol, period="daily", start_date="20000101", adjust="hfq")
    cols = {'最高':'high','最低':'low','收盘':'close','开盘':'open','成交量':'volume','日期':'date'}
    #print(df)

    df.rename(columns=cols,inplace=True)
    df['date'] = df['date'].apply(lambda x: x.replace('-', ''))
    return df[list(cols.values())]


symbols = ['513100' #纳指100
           ,'513500',#标普500
           '510300',#沪深300，
           '159915', #创业板
           '518880',#黄金
           '512890',# 红利低波
           '159985', #豆粕
           '511880',# 银华日利-货币ETF
           '511260', # 十年国债
           '511220', #城投债
           '510180', #上证180
          ]

symbols = ['159915']

for s in symbols:
    print(f'获取{s}并保存到csv')
    df = fetch_etf(s) # 获取纳指ETF
    #df.to_csv(f'{s}.csv',index=False)
    if s[0] == '5': s += '.SH'
    if s[0] == '1': s += '.SZ'
    df.to_csv(f'../data/quotes/{s}.csv',index=False)