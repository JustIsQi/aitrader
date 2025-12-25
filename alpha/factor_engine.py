from multiprocessing import freeze_support

from dataset.template import AlphaDataset
import pandas as pd
import polars as pl
from load_bar_df import load_all_data_polars, load_bar_df

if __name__ == '__main__':
    freeze_support()
    from config import DATA_DIR
    df = pd.DataFrame()
    h5 = DATA_DIR.joinpath('all_stocks_by_symbols.h5')
    with pd.HDFStore(h5, mode='a', complib='blosc', complevel=9) as store:
        df = store.get('all')
        df['date'] = df.index


    # df = load_bar_df()
    dataset = AlphaDataset()
    dataset.add_feature('roc_20', 'roc(close,20)')
    #dataset.add_feature('ts_delay_2', 'ts_delay(close,2)')

    dataset.prepare_data(pl.from_pandas(df))

    print(dataset.raw_df.to_pandas())


