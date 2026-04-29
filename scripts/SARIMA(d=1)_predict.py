import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.statespace.sarimax import SARIMAX


import matplotlib.pyplot as plt
from matplotlib.font_manager import FontManager

def set_chinese_font():
    fm = FontManager()
    # 常见的中文支持字体列表
    zh_fonts = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS', 'WenQuanYi Micro Hei']
    for font in zh_fonts:
        if font in [f.name for f in fm.ttflist]:
            plt.rcParams['font.sans-serif'] = [font]
            plt.rcParams['axes.unicode_minus'] = False # 解决负号显示问题
            print(f"已成功设置字体为: {font}")
            return
    print("未找到内置中文字体，请检查系统字体库。")

set_chinese_font()


# ==========================================
# 1. 数据加载与清洗（训练集 + 验证集）
# ==========================================
# 训练集（原来的数据）
df_train = pd.read_excel(r'E:\TongJiJianMo\data\rate.xlsx')
df_train['rate'] = pd.to_numeric(df_train['rate'], errors='coerce')
df_train['time'] = pd.to_datetime(df_train['time'])
df_train.set_index('time', inplace=True)
df_train = df_train.sort_index().interpolate().fillna(method='bfill')

# 验证集（你要对比的后面几天的真实数据）
df_test = pd.read_excel(r'E:\TongJiJianMo\data\rate2.xlsx')
df_test['rate'] = pd.to_numeric(df_test['rate'], errors='coerce') # 处理 '--' 为 NaN
df_test['time'] = pd.to_datetime(df_test['time'])
df_test.set_index('time', inplace=True)

# 注意：rate2.xlsx 的最后一天 (07-03) 是 '--'，我们只对比有真实值的数据部分
df_test_real = df_test.dropna() 

# ==========================================
# 2. 重新训练模型（使用你确定的参数）
# ==========================================
# 根据你之前运行出的最优结果：SARIMA(1, 1, 2)x(1, 1, 1, 7)
model = SARIMAX(df_train['rate'], 
                order=(1, 1, 2), 
                seasonal_order=(1, 1, 1, 7),
                enforce_stationarity=False,
                enforce_invertibility=False)
results = model.fit(disp=False)

# ==========================================
# 3. 执行预测
# ==========================================
# 预测步数：从训练集结束点开始，一直预测到 rate2.xlsx 的结束点
# 我们直接预测出整个验证集对应的时间段
forecast_steps = len(df_test)
forecast_res = results.get_forecast(steps=forecast_steps)
forecast_df = forecast_res.summary_frame()

# 将预测值的时间索引对齐
forecast_df.index = df_test.index

# ==========================================
# 4. 可视化对比图
# ==========================================
plt.figure(figsize=(14, 6))

# 画出真实值（rate2.xlsx 中已有的）
plt.plot(df_test_real.index, df_test_real['rate'], 
         label='原始真实值', color='#2c3e50', marker='o', linewidth=2)

# 画出模型预测值
plt.plot(forecast_df.index, forecast_df['mean'], 
         label='SARIMA 预测值', color='#e74c3c', linestyle='--', marker='s', linewidth=2)

# 画出置信区间（阴影部分，体现预测的不确定性）
plt.fill_between(forecast_df.index, forecast_df['mean_ci_lower'], forecast_df['mean_ci_upper'], 
                 color='r', alpha=0.1, label='95% 置信区间')

plt.title('北京交通拥堵指数：模型预测 vs 实际观测', fontsize=15)
plt.xlabel('日期', fontsize=12)
plt.ylabel('拥堵指数', fontsize=12)
plt.legend()
plt.grid(True, linestyle=':', alpha=0.6)

# 打印出具体的预测数值，方便你填表
print("--- 预测结果一览 ---")
compare_df = pd.DataFrame({
    '真实值': df_test['rate'],
    '预测值': forecast_df['mean']
})
print(compare_df)

plt.show()