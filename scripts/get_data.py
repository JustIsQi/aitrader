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
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import threading


# ==================== 代理配置 ====================
# 代理池配置 - 支持多个代理自动切换
# 注意：如果代理不可用，会自动跳过代理直连
PROXY_POOL = [
    {"http": "http://g896.kdltps.com:15818", "https": "http://g896.kdltps.com:15818"},
    # 添加更多代理以实现轮换
    # {"http": "http://proxy2.example.com:8080", "https": "http://proxy2.example.com:8080"},
    # {"http": "http://proxy3.example.com:8080", "https": "http://proxy3.example.com:8080"},
]

# 是否启用代理（设为False可以禁用代理）
ENABLE_PROXY = True  # 必须使用代理，避免IP被封禁

# 最大重试次数（当代理IP被封锁时重复请求）
MAX_RETRY_TIMES = 10  # 每个数据最多重试10次

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

# 根据配置决定是否启用代理
if ENABLE_PROXY:
    # 设置代理到环境变量（akshare会使用）
    current_proxy = proxy_manager.get_next_proxy()
    os.environ['HTTP_PROXY'] = current_proxy['http']
    os.environ['HTTPS_PROXY'] = current_proxy['https']
    proxy_info = proxy_manager.get_proxy_info()
    print(f"使用代理 {proxy_info['index']+1}/{proxy_info['total']}: {current_proxy['http']}")
else:
    print("代理已禁用，将直连网络")

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==================== 数据获取函数 ====================
def format_date_for_akshare(date_str):
    """将日期字符串转换为akshare需要的YYYYMMDD格式

    Args:
        date_str: 日期字符串，支持多种格式

    Returns:
        str: YYYYMMDD格式的日期字符串
    """
    if not date_str:
        return None

    import pandas as pd
    # 尝试解析日期
    date_obj = pd.to_datetime(date_str, errors='coerce')
    if pd.isna(date_obj):
        return None

    return date_obj.strftime('%Y%m%d')
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

            # 判断是否是代理相关错误（包括数据为空的情况，可能是IP被封）
            is_proxy_error = any(keyword in error_msg for keyword in [
                'ProxyError', 'Tunnel connection failed', 'Proxy Setup Failed',
                'Cannot connect to proxy', 'ConnectionRefusedError',
                '517', '502', '503', '504',
                '数据为空', '可能是代理问题'  # 新增：检测我们自定义的空数据错误
            ])

            if is_proxy_error:
                proxy_manager.mark_failure()
                # 切换到新代理
                new_proxy = proxy_manager.get_next_proxy()
                os.environ['HTTP_PROXY'] = new_proxy['http']
                os.environ['HTTPS_PROXY'] = new_proxy['https']
                proxy_info = proxy_manager.get_proxy_info()
                print(f"    [代理切换] 第 {attempt+1} 次失败（检测到:{error_msg[:30]}...），切换到代理 {proxy_info['index']+1}/{proxy_info['total']}")
            else:
                print(f"    [请求失败] 第 {attempt+1} 次: {e}")

            if attempt < max_retries - 1:
                sleep_time = wait_seconds * (attempt + 1)  # 递增延迟
                print(f"    等待 {sleep_time} 秒后重试...")
                time.sleep(sleep_time)
            else:
                raise


def fetch_stock_history(symbol, start_date=None, end_date=None, adjust="hfq"):
    """获取股票历史数据

    Args:
        symbol: 股票代码
        start_date: 开始日期 (YYYYMMDD 格式)
        end_date: 结束日期 (YYYYMMDD 格式)
        adjust: 复权类型 ('qfq'前复权, 'hfq'后复权, ''不复权)
    """
    result = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust=adjust,
                              start_date=start_date, end_date=end_date)
    return result


def fetch_etf_history(symbol, start_date=None, end_date=None, adjust="hfq"):
    """获取ETF历史数据

    Args:
        symbol: ETF代码
        start_date: 开始日期 (YYYYMMDD 格式)
        end_date: 结束日期 (YYYYMMDD 格式)
        adjust: 复权类型 ('qfq'前复权, 'hfq'后复权, ''不复权)
    """
    result = ak.fund_etf_hist_em(symbol=symbol, period="daily", adjust=adjust,
                                start_date=start_date, end_date=end_date)
    return result

def fetch_stock_history_with_proxy(symbol, func=fetch_stock_history, start_date=None, end_date=None):
    """使用代理获取股票/ETF历史数据，失败时自动重试

    Args:
        symbol: 股票或ETF代码
        func: 获取函数，默认为 fetch_stock_history，可传入 fetch_etf_history
        start_date: 开始日期 (YYYYMMDD 格式)
        end_date: 结束日期 (YYYYMMDD 格式)

    Note:
        - 全量下载（start_date=None）时，如果返回空数据会重试最多 MAX_RETRY_TIMES 次
        - 增量下载（start_date有值）时，返回空数据是正常的（表示没有新数据），不会重试
        - 每次重试之间会等待 2 秒
    """
    func_name = func.__name__.replace('fetch_', '').replace('_', ' ').title()
    print(f'  [代理] 正在获取 {symbol} ({func_name})...')

    # 判断是否为增量下载
    is_incremental = start_date is not None

    # 直接重试，不切换代理
    for attempt in range(MAX_RETRY_TIMES):
        try:
            result = func(symbol, start_date=start_date, end_date=end_date)

            # 检查结果是否为空
            if result is None or result.empty or result.shape[1] == 0:
                # 增量下载返回空数据是正常的，直接返回
                if is_incremental:
                    return result

                # 全量下载返回空数据，需要重试
                raise ValueError(f"获取 {symbol} 的数据为空（第 {attempt+1}/{MAX_RETRY_TIMES} 次尝试）")

            # 成功获取数据
            if attempt > 0:
                print(f'    ✓ 第 {attempt+1} 次尝试成功')
            return result

        except Exception as e:
            error_msg = str(e)

            # 最后一次尝试失败
            if attempt == MAX_RETRY_TIMES - 1:
                print(f'  [{symbol}] 获取失败: 已重试 {MAX_RETRY_TIMES} 次，最后错误: {error_msg[:50]}...')
                raise

            # 显示重试信息
            print(f'    ⚠ 第 {attempt+1}/{MAX_RETRY_TIMES} 次失败: {error_msg[:50]}...，2秒后重试...')

            # 等待后重试
            time.sleep(2)


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
