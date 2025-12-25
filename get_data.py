# %
# akshare 获取A股股票数据
# %
from socket import timeout
import akshare as ak
import time
import os
import urllib3
import pandas as pd
import random
from tqdm import tqdm
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading


# ==================== 代理配置 ====================
# 代理池配置 - 支持多个代理自动切换
PROXY_POOL = [
    {"http": "http://g896.kdltps.com:15818", "https": "http://g896.kdltps.com:15818"},
    # 添加更多代理以实现轮换
    # {"http": "http://proxy2.example.com:8080", "https": "http://proxy2.example.com:8080"},
    # {"http": "http://proxy3.example.com:8080", "https": "http://proxy3.example.com:8080"},
]

class ProxyManager:
    """代理管理器 - 支持自动切换和健康检查"""

    def __init__(self, proxy_pool):
        self.proxy_pool = proxy_pool
        self.current_index = 0
        self.failed_counts = {i: 0 for i in range(len(proxy_pool))}
        self.lock = threading.Lock()
        self.max_failures = 5  # 连续失败5次后跳过该代理
        self.test_url = "http://www.baidu.com"  # 代理测试URL
        self.timeout = 10  # 代理测试超时时间

    def get_next_proxy(self):
        """获取下一个可用代理"""
        with self.lock:
            # 尝试找到一个未超过失败阈值的代理
            for _ in range(len(self.proxy_pool)):
                proxy = self.proxy_pool[self.current_index]

                # 如果该代理失败次数过多，跳过它
                if self.failed_counts[self.current_index] < self.max_failures:
                    return proxy

                # 重置失败计数并尝试下一个
                self.failed_counts[self.current_index] = 0
                self.current_index = (self.current_index + 1) % len(self.proxy_pool)

            # 如果所有代理都失败了，重置计数并返回当前代理
            self.failed_counts = {i: 0 for i in range(len(self.proxy_pool))}
            return self.proxy_pool[self.current_index]

    def mark_failure(self, proxy=None):
        """标记代理失败"""
        with self.lock:
            if proxy is None:
                idx = self.current_index
            else:
                idx = self.proxy_pool.index(proxy)
            self.failed_counts[idx] += 1
            print(f"    [代理警告] 代理 {idx+1}/{len(self.proxy_pool)} 失败计数: {self.failed_counts[idx]}")

            # 如果失败次数过多，切换到下一个代理
            if self.failed_counts[idx] >= self.max_failures:
                print(f"    [代理切换] 代理 {idx+1} 连续失败 {self.max_failures} 次，切换代理...")
                self.current_index = (self.current_index + 1) % len(self.proxy_pool)

    def mark_success(self, proxy=None):
        """标记代理成功（重置失败计数）"""
        with self.lock:
            if proxy is None:
                idx = self.current_index
            else:
                idx = self.proxy_pool.index(proxy)
            self.failed_counts[idx] = 0

    def test_proxy(self, proxy):
        """测试代理是否可用"""
        try:
            test_proxies = {
                'http': proxy['http'],
                'https': proxy.get('https', proxy['http'])
            }
            response = requests.get(
                self.test_url,
                proxies=test_proxies,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            if response.status_code == 200:
                return True
        except Exception as e:
            print(f"    [代理测试失败] {e}")
        return False

    def get_proxy_info(self):
        """获取当前代理信息"""
        proxy = self.proxy_pool[self.current_index]
        return {
            'proxy': proxy,
            'index': self.current_index,
            'total': len(self.proxy_pool),
            'failures': self.failed_counts[self.current_index]
        }


# 创建全局代理管理器
proxy_manager = ProxyManager(PROXY_POOL)

# 设置代理到环境变量（akshare会使用）
current_proxy = proxy_manager.get_next_proxy()
os.environ['HTTP_PROXY'] = current_proxy['http']
os.environ['HTTPS_PROXY'] = current_proxy['https']
proxy_info = proxy_manager.get_proxy_info()
print(f"使用代理 {proxy_info['index']+1}/{proxy_info['total']}: {current_proxy['http']}")

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==================== 数据获取函数 ====================
def fetch_with_retry(func, *args, max_retries=5, wait_seconds=3, **kwargs):
    """
    带有代理切换功能的通用重试函数
    当请求失败时，会自动切换代理并重试
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e)

            # 判断是否是代理相关错误
            is_proxy_error = any(keyword in error_msg for keyword in [
                'ProxyError', 'Tunnel connection failed', 'Proxy Setup Failed',
                'Cannot connect to proxy', 'ConnectionRefusedError',
                '517', '502', '503', '504'
            ])

            if is_proxy_error:
                proxy_manager.mark_failure()
                # 切换到新代理
                new_proxy = proxy_manager.get_next_proxy()
                os.environ['HTTP_PROXY'] = new_proxy['http']
                os.environ['HTTPS_PROXY'] = new_proxy['https']
                proxy_info = proxy_manager.get_proxy_info()
                print(f"    [代理切换] 第 {attempt+1} 次失败，切换到代理 {proxy_info['index']+1}/{proxy_info['total']}")
            else:
                print(f"    [请求失败] 第 {attempt+1} 次: {e}")

            if attempt < max_retries - 1:
                sleep_time = wait_seconds * (attempt + 1)  # 递增延迟
                print(f"    等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                raise


@retry(
    stop=stop_after_attempt(3),  # 每个代理最多重试3次
    wait=wait_fixed(2),
    reraise=True
)
def fetch_stock_history(symbol):
    """获取股票历史数据，配合代理切换使用"""
    try:
        return ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="hfq")
    except Exception as e:
        # 让外层的 fetch_with_retry 来处理代理切换
        raise

def fetch_etf_history(symbol):
    try:
        return ak.fund_etf_hist_em(symbol=symbol, period="daily",  adjust="hfq")
    except Exception as e:
        raise

def fetch_stock_history_with_proxy(symbol, func=fetch_stock_history):
    """使用代理管理器获取股票/ETF历史数据

    Args:
        symbol: 股票或ETF代码
        func: 获取函数，默认为 fetch_stock_history，可传入 fetch_etf_history
    """
    proxy_info = proxy_manager.get_proxy_info()
    func_name = func.__name__.replace('fetch_', '').replace('_', ' ').title()
    print(f'  [代理 {proxy_info["index"]+1}/{proxy_info["total"]}] 正在获取 {symbol} ({func_name})...')

    try:
        result = fetch_with_retry(func, symbol, max_retries=5, wait_seconds=2)
        proxy_manager.mark_success()
        return result
    except Exception as e:
        print(f'  [{symbol}] 获取失败: {e}')
        raise


def is_etf(symbol):
    """判断是否为ETF代码

    ETF代码特征:
    - 上海5开头: 51xxxx, 56xxxx
    - 深圳15开头: 159xxx
    """
    # 移除市场后缀
    code = symbol.split('.')[0]

    # 上海ETF: 51xxxx 或 56xxxx
    if code.startswith('51') or code.startswith('56'):
        return True

    # 深圳ETF: 159xxx
    if code.startswith('159'):
        return True

    return False


def download_symbol_data(symbol):
    """下载单个股票/ETF数据并保存到文件

    Args:
        symbol: 股票代码，格式如 '600000.SH' 或 '159915.SZ'

    Returns:
        bool: 下载是否成功
    """
    csv_path = f'./data/akshare_data/{symbol}_history.csv'

    # 检查是否已存在
    if os.path.exists(csv_path):
        return True

    try:
        # 判断是ETF还是股票
        if is_etf(symbol):
            # 去掉市场后缀获取数据
            code = symbol.split('.')[0]
            df = fetch_stock_history_with_proxy(code, func=fetch_etf_history)
        else:
            # 股票去掉市场后缀
            code = symbol.split('.')[0]
            df = fetch_stock_history_with_proxy(code, func=fetch_stock_history)

        if df is None or df.empty:
            print(f'  [{symbol}] 获取到的数据为空')
            return False

        # 保存数据
        os.makedirs('./data/akshare_data', exist_ok=True)
        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f'  [{symbol}] 数据已保存: {df.shape}')
        return True

    except Exception as e:
        print(f'  [{symbol}] 下载失败: {e}')
        return False


def fetch_stock_list():
    """获取股票列表，支持代理自动切换"""
    print("正在获取A股股票列表...")

    interfaces = [
        ("东方财富", lambda: ak.stock_zh_a_spot_em()),
        ("新浪", lambda: ak.stock_zh_a_spot()),
    ]

    for name, func in interfaces:
        try:
            print(f"尝试使用 {name} 接口...")
            df = fetch_with_retry(func, max_retries=5, wait_seconds=3)
            print(f"✓ {name} 接口成功，获取到 {len(df)} 只股票")
            return df
        except Exception as e:
            print(f"✗ {name} 接口失败: {e}")
            continue

    raise Exception("所有接口均失败")


# ==================== 主程序 ====================
def main():
    # 确保数据目录存在
    os.makedirs('./data/akshare_data', exist_ok=True)

    # 获取股票代码列表
    if not os.path.exists('./data/akshare_data/stock_code.csv'):
        try:
            stock_zh_a_spot_em_df = fetch_stock_list()
            stock_codes = stock_zh_a_spot_em_df['代码'].tolist()
            print(f'股票总数: {len(stock_codes)}')
            stock_zh_a_spot_em_df.to_csv('./data/akshare_data/stock_code.csv', index=False, encoding='utf-8-sig')
            print('股票列表已保存')
            time.sleep(3)
        except Exception as e:
            print(f'获取股票列表失败: {e}')
            print('请检查:')
            print('  1. 代理是否可用')
            print('  2. 网络连接是否正常')
            print('  3. 是否需要添加更多代理到 PROXY_POOL')
            return
    else:
        print('读取已保存的股票列表...')
        stock_codes = pd.read_csv('./data/akshare_data/stock_code.csv', dtype={'代码': str})['代码'].to_list()
        print(f'股票总数: {len(stock_codes)}')

    # 统计
    success_count = 0
    failed_count = 0
    skip_count = 0

    # 遍历股票获取历史数据
    print('\n开始下载历史数据...\n')
    for code in tqdm(stock_codes, desc="下载进度"):
        # 跳过北交所股票
        if code.startswith('bj'):
            skip_count += 1
            continue

        # 检查是否已下载
        if os.path.exists(f'./data/akshare_data/{code}_history.csv'):
            skip_count += 1
            continue

        # 去掉市场前缀
        symbol = code[2:] if code.startswith(('sh', 'sz')) else code

        try:
            stock_zh_a_hist_df = fetch_stock_history_with_proxy(symbol)
            print(f'    [{code}] 数据形状: {stock_zh_a_hist_df.shape}')
            stock_zh_a_hist_df.to_csv(f'./data/akshare_data/{code}_history.csv', index=False, encoding='utf-8-sig')
            success_count += 1

            # 随机延迟，避免请求过快
            time.sleep(random.uniform(0.3, 0.8))

        except Exception as e:
            print(f'    [{code}] 最终失败: {e}')
            failed_count += 1
            time.sleep(1)

    # 输出统计信息
    print('\n' + '='*50)
    print('下载完成！')
    print(f'  成功: {success_count}')
    print(f'  失败: {failed_count}')
    print(f'  跳过: {skip_count}')

    # 代理使用统计
    print('\n代理使用统计:')
    for i, proxy in enumerate(PROXY_POOL):
        failures = proxy_manager.failed_counts[i]
        status = "✓ 正常" if failures < proxy_manager.max_failures else "✗ 失败过多"
        print(f"  代理 {i+1}: {proxy['http']} - 失败次数: {failures} {status}")
    print('='*50)


if __name__ == '__main__':
    main()
