### 效果很好


import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import tensorflow as tf
# ---【修改：为支持 Attention 机制，引入 Keras 的函数式 API】---
from keras.models import Model
from keras.layers import Input, LSTM, Dense, Dropout, Multiply, Activation, Flatten, RepeatVector, Permute, Lambda
import keras.backend as K
from keras.callbacks import EarlyStopping
import warnings
import joblib  # 用于保存Scaler
import scipy.stats as stats  # 用于绘制Q-Q图
from statsmodels.graphics.tsaplots import plot_acf  # 用于残差ACF
from statsmodels.stats.diagnostic import acorr_ljungbox  # 用于白噪声检验

# ==========================================
# 全局设置与随机种子固化
# ==========================================
warnings.filterwarnings("ignore")
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False

np.random.seed(42)
tf.random.set_seed(42)

# ==========================================
# 步骤 1: 数据加载与预处理 (加入多变量特征)
# ==========================================
print("--- 步骤 1: 数据加载与预处理 ---")
file_path = r'E:\TongJiJianMo\data\rate_LSTM.xlsx' 

try:
    df = pd.read_excel(file_path)
    df['time'] = pd.to_datetime(df['time'])
    df.set_index('time', inplace=True)
    df['rate'] = pd.to_numeric(df['rate'], errors='coerce').interpolate(method='linear')
    df = df.sort_index()
    print(f"数据加载成功！共计 {len(df)} 条记录。")
except Exception as e:
    print(f"数据读取出错: {e}。将生成模拟数据...")
    dates = pd.date_range(start='2023-04-01', periods=400, freq='D')
    df = pd.DataFrame({'time': dates, 'rate': np.sin(np.arange(400)*(2*np.pi/7)) + np.random.normal(0,0.2,400) + 1.5})
    df.set_index('time', inplace=True)

# # ---【新增：多变量特征提取（图一功能）】---
# # 从时间索引中提取出极其重要的“周内效应”和“周末效应”作为额外特征
# df['day_of_week'] = df.index.dayofweek
# df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
# # (如果后续你有AQI数据，可以直接在这里 pd.merge 进来)

# # 定义所有的特征列 (rate 必须在第一列, index 0)
# features = ['rate', 'day_of_week', 'is_weekend']
# data = df[features].values 
# target_data = df[['rate']].values # 专门保留单变量用于画图

# ---【新增：多变量特征提取（图一功能）】---
# 1. 提取时间特征
df['day_of_week'] = df.index.dayofweek
df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)

# 2. 【新增元认知模块 1：自我纠错机制 (Error-Correction Feature)】
# 我们使用 T-1 时刻的朴素预测偏差 (实际值 - 前一时刻值) 并将其延迟一步
# 这样在 T 时刻，模型能够接收到 T-1 时刻的“突发波动误差”，实现自我反思纠偏
df['naive_prediction'] = df['rate'].shift(1)             # 昨天的值作为朴素预测
df['history_error'] = df['rate'] - df['naive_prediction'] # 产生的误差偏差
df['history_error'] = df['history_error'].shift(1)       # 延迟一步，确保无未来数据穿越
df.fillna(method='bfill', inplace=True)                  # 填充头部的空值

# 定义所有的特征列 (rate 必须在第一列, index 0。现在特征变为 4 个！)
features =['rate', 'day_of_week', 'is_weekend', 'history_error']
data = df[features].values 
target_data = df[['rate']].values # 专门保留单变量用于画图

print(f"已加入特征: {features}")

# ==========================================
# 步骤 2: 数据归一化 (MinMaxScaler)
# ==========================================
print("\n--- 步骤 2: 数据归一化 ---")
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(data) # 现在是对 3 个变量同时归一化

joblib.dump(scaler, 'scaler.gz')
print("已保存多变量数据缩放器: scaler.gz")

# ==========================================
# 步骤 3: 构造时间序列滑动窗口 (多变量版)
# ==========================================
print("\n--- 步骤 3: 构造滑动窗口 ---")
look_back = 7 
num_features = scaled_data.shape[1] # 获取特征维度数 (当前为 3)

def create_dataset(dataset, look_back=1):
    X, Y = [],[]
    for i in range(len(dataset) - look_back):
        X.append(dataset[i:(i + look_back), :]) # 【修改：获取所有特征列】
        Y.append(dataset[i + look_back, 0])     # 【修改：预测目标仅为第0列 rate】
    return np.array(X), np.array(Y)

X, Y = create_dataset(scaled_data, look_back)
# 自动适配多变量维度 (Samples, TimeSteps, Features)
X = np.reshape(X, (X.shape[0], X.shape[1], num_features))

# ==========================================
# 步骤 4: 数据集顺序切分
# ==========================================
print("\n--- 步骤 4: 划分训练、验证、测试集 ---")
train_size = int(len(X) * 0.8)
val_size = int(len(X) * 0.1)
test_size = len(X) - train_size - val_size

X_train, Y_train = X[0:train_size], Y[0:train_size]
X_val, Y_val = X[train_size:train_size+val_size], Y[train_size:train_size+val_size]
X_test, Y_test = X[train_size+val_size:len(X)], Y[train_size+val_size:len(Y)]

print(f"训练集大小: {len(X_train)} | 验证集大小: {len(X_val)} | 测试集大小: {len(X_test)}")
print(f"模型输入形状 (X_train): {X_train.shape}")

# ==========================================
# 步骤 5: 构建并训练 LSTM + Attention 模型
# ==========================================
# print("\n--- 步骤 5: 构建并训练 LSTM+Attention 模型 ---")

# # ---【新增：构建带有注意力机制的网络（图二功能）】---
# # 1. 输入层
# inputs = Input(shape=(look_back, num_features))

# # 2. LSTM 层 (注意：return_sequences=True 是接入 Attention 的必要条件)
# lstm_out = LSTM(units=32, return_sequences=True)(inputs)

# # 3. Attention 注意力层
# # 计算时间步的权重
# attention_probs = Dense(1, activation='tanh')(lstm_out)
# attention_probs = Flatten()(attention_probs)
# attention_probs = Activation('softmax', name='attention_weights')(attention_probs)

# # 将权重维度变换对齐 LSTM 的输出 (32是LSTM的units)
# attention_probs_reshaped = RepeatVector(32)(attention_probs)
# attention_probs_reshaped = Permute([2, 1])(attention_probs_reshaped)

# # 权重与 LSTM 输出相乘，得到加权后的向量
# attention_mul = Multiply()([lstm_out, attention_probs_reshaped])

# # 将时间步求和融合成上下文向量
# context_vector = Lambda(lambda x: K.sum(x, axis=1))(attention_mul)

# # 4. Dropout 与全连接输出层
# x = Dropout(0.3)(context_vector)
# output = Dense(units=1)(x)

# # 5. 编译模型
# model = Model(inputs=inputs, outputs=output)
# model.compile(optimizer='adam', loss='mean_squared_error')

# # 打印模型结构（可以在控制台看到漂亮的 Attention 层结构）
# model.summary()

# # ==========================================
# # 步骤 5: 构建并训练 LSTM + Attention 模型
# # ==========================================
# print("\n--- 步骤 5: 构建并训练 LSTM+Attention 模型 ---")

# # 1. 输入层
# inputs = Input(shape=(look_back, num_features))

# # 2. LSTM 层 (return_sequences=True 是接入 Attention 的必要条件)
# lstm_out = LSTM(units=32, return_sequences=True)(inputs)

# # 3. Attention 注意力层
# # 计算时间步的权重
# attention_probs = Dense(1, activation='tanh')(lstm_out)
# attention_probs = Flatten()(attention_probs)
# attention_probs = Activation('softmax', name='attention_weights')(attention_probs)

# # 将权重维度变换对齐 LSTM 的输出 (32是LSTM的units)
# attention_probs_reshaped = RepeatVector(32)(attention_probs)
# attention_probs_reshaped = Permute([2, 1])(attention_probs_reshaped)

# # 权重与 LSTM 输出相乘
# attention_mul = Multiply()([lstm_out, attention_probs_reshaped])

# # ---【关键修复位置：显式指定 output_shape 或改用 tf.reduce_sum】---
# # 解决方法：添加 output_shape 参数
# context_vector = Lambda(lambda x: K.sum(x, axis=1), 
#                         output_shape=(32,), 
#                         name='Context_Vector')(attention_mul)

# # 4. Dropout 与全连接输出层
# x = Dropout(0.3)(context_vector)
# output = Dense(units=1)(x)

# # 5. 编译模型
# model = Model(inputs=inputs, outputs=output)
# model.compile(optimizer='adam', loss='mean_squared_error')

# model.summary()

# early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1)

# history = model.fit(
#     X_train, Y_train, 
#     epochs=100, 
#     batch_size=16, 
#     validation_data=(X_val, Y_val), 
#     callbacks=[early_stop], 
#     verbose=1
# )

# model.save('lstm_attention_traffic_model.h5')
# print("已保存含Attention的模型文件: lstm_attention_traffic_model.h5")

# ==========================================
# 步骤 5: 构建并训练 LSTM + Attention 模型
# ==========================================
print("\n--- 步骤 5: 构建并训练 LSTM+Attention 模型 ---")

# 1. 输入层
inputs = Input(shape=(look_back, num_features))

# 2. LSTM 层 (return_sequences=True 是接入 Attention 的必要条件)
lstm_out = LSTM(units=32, return_sequences=True)(inputs)

# 3. Attention 注意力层
# 计算时间步的权重
attention_probs = Dense(1, activation='tanh')(lstm_out)
attention_probs = Flatten()(attention_probs)
attention_probs = Activation('softmax', name='attention_weights')(attention_probs)

# 将权重维度变换对齐 LSTM 的输出
attention_probs_reshaped = RepeatVector(32)(attention_probs)
attention_probs_reshaped = Permute([2, 1])(attention_probs_reshaped)

# 权重与 LSTM 输出相乘
attention_mul = Multiply()([lstm_out, attention_probs_reshaped])

# ---【关键修复：使用 tf.reduce_sum 替代 K.sum 以彻底解决兼容性报错】---
# 直接调用 tf 的 reduce_sum，不再依赖 K 模块的接口
context_vector = Lambda(lambda x: tf.reduce_sum(x, axis=1), 
                        name='Context_Vector')(attention_mul)

# 4. Dropout 与全连接输出层
x = Dropout(0.3)(context_vector)
output = Dense(units=1)(x)

# 5. 编译模型
model = Model(inputs=inputs, outputs=output)
model.compile(optimizer='adam', loss='mean_squared_error')

model.summary()

early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1)

history = model.fit(
    X_train, Y_train, 
    epochs=100, 
    batch_size=16, 
    validation_data=(X_val, Y_val), 
    callbacks=[early_stop], 
    verbose=1
)

model.save('lstm_attention_traffic_model.h5')
print("已保存模型文件: lstm_attention_meta_traffic_model.h5")


# ==========================================
# 步骤 6: 模型评估与预测 (反归一化适配多变量)
# ==========================================
print("\n--- 步骤 6: 模型预测与反归一化 ---")
train_predict = model.predict(X_train)
test_predict = model.predict(X_test)

# ---【修改：因为 Scaler 包含了3个变量，反归一化时需要用 dummy 矩阵对齐】---
def invert_scale(scaler, pred_values, num_features, target_col=0):
    dummy = np.zeros((len(pred_values), num_features))
    dummy[:, target_col] = pred_values.flatten()
    return scaler.inverse_transform(dummy)[:, target_col].reshape(-1, 1)

train_predict = invert_scale(scaler, train_predict, num_features)
Y_train_inv = invert_scale(scaler, Y_train, num_features)
test_predict = invert_scale(scaler, test_predict, num_features)
Y_test_inv = invert_scale(scaler, Y_test, num_features)

rmse = np.sqrt(mean_squared_error(Y_test_inv, test_predict))
mae = mean_absolute_error(Y_test_inv, test_predict)
mape = np.mean(np.abs((Y_test_inv - test_predict) / Y_test_inv)) * 100

print(f"\n[测试集评估指标]")
print(f"均方根误差 (RMSE): {rmse:.4f}")
print(f"平均绝对误差 (MAE) : {mae:.4f}")
print(f"平均绝对百分比误差 (MAPE): {mape:.2f}%")

# ==========================================
# 步骤 7: 大赛级可视化输出
# ==========================================
print("\n--- 步骤 7: 可视化结果生成 ---")
fig, axes = plt.subplots(2, 1, figsize=(14, 10))

axes[0].plot(history.history['loss'], label='训练集 Loss', color='blue')
axes[0].plot(history.history['val_loss'], label='验证集 Loss (Val Loss)', color='orange')
axes[0].set_title('LSTM+Attention 模型训练过程中的 Loss 变化', fontsize=14)
axes[0].set_xlabel('迭代次数 (Epochs)', fontsize=12)
axes[0].set_ylabel('Mean Squared Error', fontsize=12)
axes[0].legend()
axes[0].grid(True, linestyle='--', alpha=0.6)

# 使用 target_data (单列原始拥堵指数) 来维持画图维度对齐
train_plot = np.empty_like(target_data)
train_plot[:, :] = np.nan
train_plot[look_back : look_back + len(train_predict), :] = train_predict

test_plot = np.empty_like(target_data)
test_plot[:, :] = np.nan
test_start_idx = look_back + len(train_predict) + val_size
test_plot[test_start_idx : len(target_data), :] = test_predict

axes[1].plot(df.index, target_data, label='真实拥堵指数 (Actual)', color='gray', alpha=0.7)
axes[1].plot(df.index, train_plot, label='训练集拟合值 (Train Predict)', color='green', alpha=0.8)
axes[1].plot(df.index, test_plot, label='测试集预测值 (Test Predict)', color='red', linewidth=2)

axes[1].set_title(f'LSTM+Attention (LookBack={look_back}) 多变量拥堵指数预测对比图', fontsize=14)
axes[1].set_xlabel('日期', fontsize=12)
axes[1].set_ylabel('拥堵指数', fontsize=12)
axes[1].legend()
axes[1].grid(True, linestyle='--', alpha=0.6)

plt.tight_layout()
plt.show()

# ==========================================
# 步骤 8: 残差分析与白噪声检验
# ==========================================
print("\n--- 步骤 8: 残差诊断与白噪声检验 ---")

residuals = Y_test_inv.flatten() - test_predict.flatten()

fig, axes = plt.subplots(2, 2, figsize=(15, 10))

axes[0, 0].plot(residuals, color='#2980b9')
axes[0, 0].axhline(y=0, color='r', linestyle='--')
axes[0, 0].set_title('测试集残差时序图')

axes[0, 1].hist(residuals, bins=30, color='#27ae60', edgecolor='white', density=True)
axes[0, 1].set_title('残差分布直方图')

stats.probplot(residuals, dist="norm", plot=axes[1, 0])
axes[1, 0].set_title('残差正态 Q-Q 图')

plot_acf(residuals, ax=axes[1, 1], lags=20, color='#f39c12')
axes[1, 1].set_title('残差自相关图 (ACF)')

plt.tight_layout()
plt.show()

lb_res = acorr_ljungbox(residuals, lags=[10], return_df=True)
p_val = lb_res['lb_pvalue'].values[0]

print(f"\n[Ljung-Box 检验结果]")
print(f"统计量阶数: 10 | P-value: {p_val:.4f}")
if p_val > 0.05:
    print("结论: P值 > 0.05，残差序列为白噪声，模型已充分提取信息。")
else:
    print("结论: P值 <= 0.05，残差仍存在自相关性，建议考虑增加特征或调参。")


# ==========================================
# ---【新增】步骤 9: Attention 权重可视化 (可解释性分析) ---
# ==========================================
print("\n--- 步骤 9: 提取 Attention 权重进行可解释性分析 ---")

# 1. 创建一个中间层模型，专门用于输出注意力权重
# 我们通过层的名称 'attention_weights' 来获取它
debug_model = Model(inputs=model.input, 
                    outputs=[model.output, model.get_layer('attention_weights').output])

# 2. 传入测试集数据获取权重
_, attn_weights = debug_model.predict(X_test)

# 3. 计算测试集上所有样本的平均注意力权重
avg_attn_weights = np.mean(attn_weights, axis=0)

# 4. 可视化注意力分布
plt.figure(figsize=(10, 6))
bars = plt.bar(range(1, look_back + 1), avg_attn_weights, color='#3498db', alpha=0.8, edgecolor='black')

# 在柱状图上标注数值
for bar in bars:
    yval = bar.get_height()
    plt.text(bar.get_x() + bar.get_width()/2, yval + 0.005, f'{yval:.3f}', ha='center', va='bottom', fontsize=10)

plt.title(f'模型对过去 {look_back} 天数据的注意力权重分布 (可解释性分析)', fontsize=14)
plt.xlabel('过去的天数 (T-n)', fontsize=12)
plt.ylabel('注意力权重 (Importance Score)', fontsize=12)
plt.xticks(range(1, look_back + 1), [f'T-{i}' for i in range(look_back, 0, -1)])
plt.grid(axis='y', linestyle='--', alpha=0.5)

# 添加解释性文字说明
description = "注：T-1 代表预测日的前一天。权重越高，代表该时刻数据对预测结果的影响越大。"
plt.annotate(description, xy=(0.5, -0.15), xycoords='axes fraction', ha='center', fontsize=10, color='gray')

plt.tight_layout()
plt.show()

# 5. 进阶：展示一个具体样本的注意力随时间的变化（热力图）
import seaborn as sns
plt.figure(figsize=(12, 4))
sns.heatmap(attn_weights[:50].T, cmap='YlGnBu', cbar_kws={'label': 'Attention Weight'})
plt.title('测试集前 50 个样本的时间步注意力热力图 (纵轴为回看时间步)', fontsize=14)
plt.xlabel('测试样本索引', fontsize=12)
plt.ylabel('回看步长 (1=最远, 7=最近)', fontsize=12)
plt.show()


# ==========================================
# 步骤 10: 【元认知模块 2】MC Dropout 认知不确定性评估
# ==========================================
print("\n--- 步骤 10: 提取元认知不确定性与置信区间 (MC Dropout) ---")

# 强制开启 training=True 以执行蒙特卡洛 Dropout 推理
@tf.function
def mc_predict_step(x):
    return model(x, training=True)

n_iter = 50  # 蒙特卡洛采样次数
mc_predictions =[]

# 将测试集转为 Tensor 加速计算
X_test_tensor = tf.convert_to_tensor(X_test, dtype=tf.float32)

print(f"正在进行 {n_iter} 次 MC Dropout 采样，量化认知不确定性...")
for i in range(n_iter):
    preds = mc_predict_step(X_test_tensor)
    # 调用你之前写好的反归一化函数，注意此处有4个特征
    preds_inv = invert_scale(scaler, preds.numpy(), num_features)
    mc_predictions.append(preds_inv.flatten())

mc_predictions = np.array(mc_predictions) # 形状: (50, test_size)

# 计算 50 次预测的均值和标准差
mc_mean = np.mean(mc_predictions, axis=0)
mc_std = np.std(mc_predictions, axis=0)

# 计算 95% 置信区间 (1.96个标准差)
upper_bound = mc_mean + 1.96 * mc_std
lower_bound = mc_mean - 1.96 * mc_std

# ---【元认知不确定性 可视化】---
plt.figure(figsize=(14, 6))
# 取最后 100 个点展示以便看清细节 (如果样本太长会挤在一起)
plot_len = min(100, len(Y_test_inv))
x_axis = df.index[-plot_len:]

plt.plot(x_axis, Y_test_inv.flatten()[-plot_len:], label='真实拥堵指数 (Ground Truth)', color='black', linewidth=1.5)
plt.plot(x_axis, mc_mean[-plot_len:], label='MC 预测均值 (MC Mean)', color='#c0392b', linestyle='--', linewidth=2)

# 绘制高级的置信区域边界 (阴影图)
plt.fill_between(x_axis, 
                 lower_bound[-plot_len:], 
                 upper_bound[-plot_len:], 
                 color='#e74c3c', alpha=0.25, label='95% 认知不确定性置信边界')

plt.title('元认知模块：带有认知不确定性评估的拥堵预测 (MC Dropout)', fontsize=15, fontweight='bold')
plt.xlabel('日期', fontsize=12)
plt.ylabel('拥堵指数', fontsize=12)
plt.legend(loc='upper right', fontsize=11)
plt.grid(True, linestyle='--', alpha=0.4)
plt.tight_layout()
plt.show()

# ==========================================
# 步骤 11: 误差纠错 (Error-Correction) 响应可视化
# ==========================================
print("\n--- 步骤 11: 误差纠错反馈特征的可视化 ---")

# 展示模型接收到的前一时刻误差与真实率之间的关系
# 取测试集对应的时间段
history_error_test = df['history_error'].iloc[-plot_len:].values

fig, ax1 = plt.subplots(figsize=(14, 5))

# 主轴：真实值
ax1.plot(x_axis, Y_test_inv.flatten()[-plot_len:], color='black', label='真实拥堵指数')
ax1.set_xlabel('日期', fontsize=12)
ax1.set_ylabel('真实拥堵指数', color='black', fontsize=12)
ax1.tick_params(axis='y', labelcolor='black')

# 副轴：历史误差补偿信号 (条形图)
ax2 = ax1.twinx()
# 正误差用红色，负误差用绿色
colors =['#e74c3c' if val > 0 else '#2ecc71' for val in history_error_test]
ax2.bar(x_axis, history_error_test, color=colors, alpha=0.4, width=0.6, label='T-1时刻纠错信号 (Error Shock)')
ax2.set_ylabel('纠错反馈信号幅度', color='gray', fontsize=12)
ax2.tick_params(axis='y', labelcolor='gray')

plt.title('元认知自我纠错机制：历史误差反馈动态追踪', fontsize=15, fontweight='bold')
# 合并图例
lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper left', fontsize=11)

plt.grid(False) # 关闭副轴网格防止杂乱
plt.tight_layout()
plt.show()

print("\n🎉 元认知模块分析完成！")
print(f"评估指标：测试集平均预测不确定性(标准差)为: {np.mean(mc_std):.4f}")