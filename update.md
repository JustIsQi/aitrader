MySQL信息如下：10.100.0.28:3306;user/password: wind_admin/ELPWN2YJRXBCQKYd;database:winddb

中国A股-行情交易数据,,CRNCY_CODE,货币代码,VARCHAR2(10),,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,OBJECT_ID,对象ID,VARCHAR2(100),,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_ADJCLOSE,复权收盘价(元),"NUMBER(20,4)",收盘价*复权因子,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_ADJCLOSE_BACKWARD,前复权收盘价(元),"NUMBER(20,4)",,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_ADJFACTOR,复权因子,"NUMBER(20,6)",初始值为1；当日复权因子=前一交易日收盘价/当日昨收盘价*前一交易日复权因子。,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_ADJHIGH,复权最高价(元),"NUMBER(20,4)",最高价*复权因子,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_ADJLOW,复权最低价(元),"NUMBER(20,4)",最低价*复权因子,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_ADJOPEN,复权开盘价(元),"NUMBER(20,4)",开盘价*复权因子,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_ADJPRECLOSE,复权昨收盘价(元),"NUMBER(20,4)",昨收盘价*复权因子,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_AMOUNT,成交金额(千元),"NUMBER(20,4)",,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_AVGPRICE,均价(VWAP),"NUMBER(20,4)",成交金额/成交量,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_CHANGE,涨跌(元),"NUMBER(20,4)",S_DQ_CLOSE-S_DQ_PRECLOSE,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_CLOSE,收盘价(元),"NUMBER(20,4)",数据保留2位小数,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_HIGH,最高价(元),"NUMBER(20,4)",数据保留2位小数,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_LIMIT,涨停价(元),"NUMBER(20,4)",,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_LOW,最低价(元),"NUMBER(20,4)",数据保留2位小数,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_OPEN,开盘价(元),"NUMBER(20,4)",数据保留2位小数,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_PCTCHANGE,涨跌幅(%),"NUMBER(20,4)","ROUND((S_DQ_CLOSE - S_DQ_PRECLOSE) * 100 / S_DQ_PRECLOSE, 2)",中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_PRECLOSE,昨收盘价(元),"NUMBER(20,4)",数据保留2位小数,中国A股日行情,ASHAREEODPRICES
中国A股-行情交易数据,,S_DQ_STOPPING,跌停价(元),"NUMBER(20,4)",,中国A股日行情,ASHAREEODPRICES

## SQL如下
SELECT
TRADE_DT AS "trade_date", 
S_INFO_WINDCODE AS "stock_code", 
S_DQ_OPEN AS "real_open",
S_DQ_CLOSE AS "real_close",
S_DQ_LOW AS "real_low",
S_DQ_ADJOPEN AS "open",
S_DQ_ADJCLOSE AS "close",
S_DQ_ADJHIGH AS "high",
S_DQ_ADJLOW AS "low",
S_DQ_AVGPRICE AS "vwap",
S_DQ_VOLUME AS "volume"
FROM 
ASHAREEODPRICES 
WHERE 
S_INFO_WINDCODE IN ({codes}) AND TRADE_DT >= '{start_time}' AND TRADE_DT <= '{end_time}'