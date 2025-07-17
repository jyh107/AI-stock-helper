# 涨停板跟踪量化策略
import numpy as np
import datetime
import pandas as pd
from tabulate import tabulate
from mindgo_api import *

def init(context):
    # 设置基准收益：中证300指数
    set_benchmark('399300.SZ')
    
    log.info('涨停板跟踪策略开始运行')
    
    # 设置股票每笔交易的手续费为万分之二五
    set_commission(PerShare(type='stock', cost=0.0025))
    # 设置股票交易滑点0.1%
    set_slippage(PriceSlippage(0.001))
    
    # 初始化候选股票列表
    #context.limit_up_candidates = []
    
    # 使用同花顺AI筛选首板涨停股票
    get_iwencai("今日首板涨停；主板非st股；流通市值大于25亿小于800亿", "limit_up_candidates", "online")
    
    run_daily(func=test_day, time_rule='every_bar', reference_security='000856.SZ')
    #run_daily(func=execute_buy_strategy, time_rule='every_bar', reference_security='000856.SZ')
    run_daily(func=monitor_sell_conditions, time_rule='every_bar', reference_security='000856.SZ')
    #run_daily(func=get_current_price, time_rule='every_bar', reference_security='000856.SZ')
    
    
    # 策略参数
    context.max_positions = 2  # 最大持仓数量
    context.profit_threshold = 0.14  # 止盈阈值%
    context.max_hold_days = 3  # 最大持有天数
    
    # 记录股票买入信息
    context.stock_buy_info = {}  # {股票代码: {'buy_date': date, 'limit_up_high': price, 'days_without_new_high': 0}}
    
def before_trading(context):

    log.info('======== 开盘前的准备 ========')

    # 打印前一交易日持仓情况
    positions = context.portfolio.positions
    if positions:
        log.info(f'前一交易日持仓数量: {len(positions)}')
        for stock, position in positions.items():
            if position.available_amount > 0:
                log.info(f'持仓股票: {stock}, 数量: {position.available_amount}')
    
    # 清理过期的买入信息记录
    stocks_to_remove = []
    current_date = get_datetime().date()
    
    for stock, buy_info in context.stock_buy_info.items():
        if stock not in positions:
            stocks_to_remove.append(stock)
        elif 'buy_date' in buy_info:
            # 计算持有天数
            buy_date = buy_info['buy_date']
            hold_days = (current_date - buy_date).days
            if hold_days > 10:  # 超过10天的记录清理掉
                stocks_to_remove.append(stock)
    
    for stock in stocks_to_remove:
        if stock in context.stock_buy_info:
            del context.stock_buy_info[stock]


def test_day(context, bar_dict):
    """主要交易逻辑处理函数"""
        
    time = get_datetime()
    
    # 14:55尾盘买入
    if get_datetime().strftime("%H:%M") == "14:55":
        execute_buy_strategy(context, bar_dict)
        log.info('执行买入策略时间点')
        
        
    
    # 实时监控卖出条件
    monitor_sell_conditions(context, bar_dict)


def execute_buy_strategy(context, bar_dict):
    """执行买入策略"""
    log.info('======== 开始执行买入策略 ========')
    
    # 获取当前持仓
    current_positions = list(context.portfolio.positions.keys())
    available_positions = context.max_positions - len(current_positions)
    
    log.info(f'当前持仓数量: {len(current_positions)}, 可用仓位: {available_positions}')
    
    if available_positions <= 0:
        log.info('已满仓，无法继续买入')
        return
    
    # 筛选符合条件的股票
    qualified_stocks = filter_qualified_stocks(context)
    
    log.info(f'筛选出符合条件的股票数量: {len(qualified_stocks)}')
    
    if len(qualified_stocks) == 0:
        log.info('没有符合条件的股票可买入')
        return
    
    # 按可用仓位数量买入
    buy_count = min(len(qualified_stocks), available_positions)
    available_cash = context.portfolio.stock_account.available_cash
    
    log.info(f'可用资金: {available_cash:.2f}, 计划买入数量: {buy_count}')
    
    for i in range(buy_count):
        stock = qualified_stocks[i]
        
        # 检查是否涨停，涨停则无法买入
        if is_limit_up(stock):
            log.info(f'股票 {stock} 已涨停，无法买入')
            continue
        
        # 计算买入金额
        position_value = available_cash / (buy_count - i)
        
        if position_value < 1000:  # 最小买入金额检查
            log.info(f'资金不足，跳过买入 {stock}')
            continue
        
        try:
            order_value(stock, position_value)
            
            # 记录买入信息
            limit_up_high = float(get_limit_up_high_price(stock))
            current_price = float(get_current_price(stock))
            
            context.stock_buy_info[stock] = {
                'buy_date': get_datetime().date(),
                'limit_up_high': limit_up_high,
                'days_without_new_high': 0,
               
            }
            
            log.info(f'买入股票: {stock}, 金额: {position_value:.2f}, 首板涨停最高价: {limit_up_high:.2f}, 当前价: {current_price:.2f}')
            available_cash -= position_value
            
        except Exception as e:
            log.error(f'买入股票 {stock} 失败: {str(e)}')


def filter_qualified_stocks(context):
    """筛选符合买入条件的股票"""
    qualified_stocks = []
    
    if not hasattr(context, 'limit_up_candidates') or not context.limit_up_candidates:
        log.info('没有候选股票列表')
        return qualified_stocks
    
    log.info(f'开始筛选候选股票，总数: {len(context.limit_up_candidates)}')
    
    for stock in context.limit_up_candidates:
        try:
            # 获取昨日数据
            hist_data = history(stock, ['high', 'low', 'close', 'open'], 2, '1d')
            #log.info(hist_data)
            if len(hist_data) < 2:
                log.info(f'股票 {stock} 历史数据不足')
                continue
            today_low = float(get_low_price(stock))
            today_open = float(get_open_price(stock))
            today_high = float(get_high_price(stock))
            yesterday_close = float(hist_data['close'].iloc[-1])  # 昨日收盘价(涨停价)
           
            current_time = get_datetime()
            current_price = float(get_current_price(stock))  # 当前价
        
        
            log.info(f'股票 {stock} - 开盘价: {today_open}, : 最低价{today_low}')
        
            # 这里可以继续后续的逻辑处理
            # 例如：计算涨跌幅
            
            # 条件1: 最低价不能低于昨日涨停价
            if today_low < yesterday_close * 0.999:  # 允许0.1%的误差
                log.info(f'股票 {stock} 不符合条件1: 今日现价 {today_low:.2f} < 昨日收盘价 {yesterday_close:.2f}')
                continue
            
            if today_high >= yesterday_close * 1.091 :
                log.info(f'股票最高价为涨停价不好')
                continue
            
            body_ratio = 0.0
            if today_high - today_low > 0.0 :
                body_ratio = float(abs(current_price - today_open) / (today_high - today_low))
            
            if body_ratio > 0.3 : #实体部分占整根k线长度
                log.info(f'股票 {stock} 不符合条件3:实体部分太大')
                continue
            
            # 条件2: 当前形成阳线(收盘价>开盘价)
            if current_price > yesterday_close*1.05  :
                log.info(f'股票 {stock} 不符合条件2: 涨幅过高，现价 {current_price:.2f} > 昨日收盘 {yesterday_close:.2f}')
                continue
            
            # 条件3: 排除已持有的股票
            if stock in context.portfolio.positions:
                log.info(f'股票 {stock} 已持有，跳过')
                continue
            
            qualified_stocks.append(stock)
            log.info(f'股票 {stock} 符合买入条件')
            
        except Exception as e:
            log.error(f'筛选股票 {stock} 时出错: {str(e)}')
            continue
    
    return qualified_stocks


def monitor_sell_conditions(context, bar_dict):
    """监控卖出条件"""
    positions_to_sell = []
    
    for stock, position in context.portfolio.positions.items():
        if position.available_amount <= 0:
            continue
        
        try:
            current_price = float(get_current_price(stock))
            buy_info = context.stock_buy_info.get(stock, {})
            # 检查必要的买入信息是否存在
            if not buy_info:
                log.info(f'股票 {stock} 没有买入信息，跳过卖出检查')
                continue            
            sell_reason = check_sell_conditions(stock, current_price, position, buy_info, context)
            
            if sell_reason:
                positions_to_sell.append((stock, sell_reason))
                
        except Exception as e:
            log.error(f'监控股票 {stock} 卖出条件时出错: {str(e)}')
    
    # 执行卖出
    for stock, reason in positions_to_sell:
        execute_sell(stock, reason, context)


def check_sell_conditions(stock, current_price, position, buy_info, context):
    """检查卖出条件"""
    if 'buy_date' not in buy_info:
        log.info(f'股票 {stock} 缺少买入日期信息')
        return None
    buy_date = buy_info['buy_date']
    current_date = get_datetime().date()
    trade_days = get_trade_days(buy_date.strftime('%Y%m%d'), current_date.strftime('%Y%m%d'))
    hold_days = len(trade_days) - 1  # 减去买入当天
    
    # 条件1: 跌破首板涨停最高价(止损)
    if hold_days == 1  and current_price < buy_info['limit_up_high']*0.96:
        
        return f'第一天跌破首板涨停最高价的6%止损: {current_price:.2f} < {buy_info["limit_up_high"]*0.96:.2f}'
        
    elif hold_days > 1 and current_price < buy_info['limit_up_high']*0.99 :
        return f'跌破首板涨停最高价止损: {current_price:.2f} < {buy_info["limit_up_high"]*0.99:.2f}'
        
    #条件5 动态止盈7个点
    current_price = float(get_current_price(stock))
    open_price = float(get_open_price(stock))
    min_price = float(get_low_price(stock))
    if (current_price - min_price)/min_price >= 0.07 :
        profit_rate = (current_price / position.cost_basis - 1)
        return f'动态止盈卖出：收益率 {profit_rate:.2%}'
        
  
 
    # 条件2: 收益超过%止盈
    if position.cost_basis > 0:
        profit_rate = (current_price / position.cost_basis - 1)
        if profit_rate >= context.profit_threshold:
            return f'止盈卖出: 收益率 {profit_rate:.2%}'
           
    
     # 条件4: 持仓超过max_hold_days天    
    if hold_days >= context.max_hold_days:
        return f'持仓超过两天'
    
    # 条件3: 到达前高压力位
    resistance_level = calculate_resistance_level(stock)
    if resistance_level and current_price >= resistance_level:
        return f'到达压力位卖出: {current_price:.2f} >= {resistance_level:.2f}'
    

    
    return None


def calculate_resistance_level(stock):
    """计算压力位 - 基于成交量加权的前高"""
    try:
        # 获取过去60天的数据
        hist_data = history(stock, ['high', 'low', 'close', 'volume'], 60, '1d')
        if len(hist_data) < 30:
            return None
        
        # 寻找近期高点
        highs = hist_data['high'].values
        volumes = hist_data['volume'].values
        
        # 找到局部高点（比前后5天都高的点）
        local_highs = []
        for i in range(5, len(highs) - 5):
            if all(highs[i] >= highs[j] for j in range(i-5, i+6) if j != i):
                # 计算该高点附近的成交量密集度
                volume_weight = np.mean(volumes[i-2:i+3])
                local_highs.append((highs[i], volume_weight))
        
        if not local_highs:
            return None
        
        # 按成交量权重排序，取最重要的压力位
        local_highs.sort(key=lambda x: x[1], reverse=True)
        
        # 返回成交量最大的前高作为压力位
        current_price = get_current_price(stock)
        for high_price, _ in local_highs:
            if high_price > current_price * 1.02:  # 压力位应该在当前价格之上
                return high_price
        
        return None
        
    except Exception as e:
        log.error(f'计算股票 {stock} 压力位时出错: {str(e)}')
        return None



def execute_sell(stock, reason, context):
    """执行卖出操作"""
    try:
        position = context.portfolio.positions[stock]
        order_target(stock, 0)
        
        # 清除买入信息
        if stock in context.stock_buy_info:
            del context.stock_buy_info[stock]
        
        log.info(f'卖出股票: {stock}, 原因: {reason}')
        
    except Exception as e:
        log.error(f'卖出股票 {stock} 失败: {str(e)}')


def get_current_price(stock):
    """获取当前价格"""
    try:
        # 先尝试获取分钟级数据
        minute_data = history(stock, ['close'], 1, '1m')
        if len(minute_data) > 0:
            return minute_data.values[0]
    except:
        pass
    
    
    return None

def get_open_price(stock):
    """获取最低价格"""
    try:
        current_date = get_datetime().strftime('%Y-%m-%d')
        df = get_price(stock, current_date, current_date, '1d', ['open'])
        if df is None or df.empty:
            log.warning(f'股票 {stock} 最低价数据为空')
            return None
        
         #从DataFrame中提取数值
        # 方法1: 获取最新的open值
        open_value = df['open'].iloc[0]
       # log.info(f'{stock}价格为{low_value}')
        return open_value
        # minute_data = history(stock, ['low'], 1, '1m')
       #  if len(minute_data) > 0:
        #     return minute_data.values[0]
    except:
        pass
    
    
    return None

def get_low_price(stock):
    """获取最低价格"""
    try:
        current_date = get_datetime().strftime('%Y-%m-%d')
        df = get_price(stock, current_date, current_date, '1d', ['low'])
        if df is None or df.empty:
            log.warning(f'股票 {stock} 最低价数据为空')
            return None
        
         #从DataFrame中提取数值
        # 方法1: 获取最新的low值
        low_value = df['low'].iloc[0]
       # log.info(f'{stock}价格为{low_value}')
        return low_value
        # minute_data = history(stock, ['low'], 1, '1m')
       #  if len(minute_data) > 0:
        #     return minute_data.values[0]
    except:
        pass
    
    
    return None
    
def get_high_price(stock):
    """获取最gao价格"""
    try:
        current_date = get_datetime().strftime('%Y-%m-%d')
        df = get_price(stock, current_date, current_date, '1d', ['high'])
        if df is None or df.empty:
            log.warning(f'股票 {stock} 最低价数据为空')
            return None
        
         #从DataFrame中提取数值
        # 方法1: 获取最新的low值
        high_value = df['high'].iloc[0]
       # log.info(f'{stock}价格为{low_value}')
        return high_value
        # minute_data = history(stock, ['low'], 1, '1m')
       #  if len(minute_data) > 0:
        #     return minute_data.values[0]
    except:
        pass
    
    
    return None
        
def get_limit_up_high_price(stock):
    """获取首板涨停那天的最高价"""
      # 获取昨日行情数据
    try:
        # 获取昨日的最高价数据
        y_data = history(stock, ['close', 'high_limit'], 1, '1d', True, 'pre').iloc[0]
        return y_data['high_limit']  # 昨天的最高价
        
    except Exception as e:
        log.error(f'获取股票 {stock} 涨停最高价失败: {str(e)}')
        return None


def is_limit_up(stock):
    """判断股票是否涨停"""
    try:
        current_price = get_current_price(stock)
        yesterday_close = history(stock, ['close'], 2, '1d').values[-2]
        
        # 计算涨停价（10%涨幅，四舍五入到分）
        limit_up_price = round(yesterday_close * 1.1, 2)
        
        # 判断是否接近涨停价（误差0.01元内）
        return abs(current_price - limit_up_price) <= 0.01
        
    except:
        return False


def after_trading_end(context):
    """收盘后处理"""
    log.info('======== 交易日结束 ========')
    
    # 更新持仓信息
    for stock in context.stock_buy_info:
        if stock in context.portfolio.positions:
            current_price = get_current_price(stock)
            buy_info = context.stock_buy_info[stock]
            
          
    
    # 打印当前持仓情况
    positions = context.portfolio.positions
    if positions:
        log.info(f'当前持仓数量: {len(positions)}')
        for stock, position in positions.items():
            if position.available_amount > 0:
                current_price = get_current_price(stock)
                profit_rate = (current_price / position.cost_basis - 1) if position.cost_basis > 0 else 0
                log.info(f'持仓: {stock}, 成本: {position.cost_basis:.2f}, 现价: {current_price:.2f}, 收益: {profit_rate:.2%}')
    else:
        log.info('当前空仓')



    
