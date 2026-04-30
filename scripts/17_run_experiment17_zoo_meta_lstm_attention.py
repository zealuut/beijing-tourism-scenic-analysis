import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error
import tensorflow as tf
from keras.models import Model
from keras.layers import Input, LSTM, Dense, Dropout, Multiply, Activation, Flatten, RepeatVector, Permute, Lambda
import keras.backend as K
from keras.callbacks import EarlyStopping
import warnings
import scipy.stats as stats
from statsmodels.graphics.tsaplots import plot_acf
from statsmodels.stats.diagnostic import acorr_ljungbox

# ==========================================
# 全局设置与随机种子固化
# ==========================================
warnings.filterwarnings("ignore")
plt.rcParams['font.sans-serif'] = ['SimHei']  # 正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False    # 正常显示负号

np.random.seed(42)
tf.random.set_seed(42)

ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    ROOT
    / "data"
    / "time_series"
    / "beijing_zoo"
    / "beijing_zoo_multivariate_meta_lstm_input.xlsx"
)
OUTPUT_DIR = ROOT / "outputs" / "zoo_meta_lstm_attention"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# 步骤 1: 数据加载、对齐与预处理 (大赛级缺失值处理)
# ==========================================
print("--- 步骤 1: 多源异构数据加载与对齐 ---")

try:
    df_merged = pd.read_excel(INPUT_PATH).copy()
    df_merged["date"] = pd.to_datetime(df_merged["date"])
    df_merged = df_merged.sort_values("date").set_index("date")
    for column in ["zoo_index", "ticket_index", "AQI"]:
        df_merged[column] = pd.to_numeric(df_merged[column], errors="coerce")

    df_merged.interpolate(method="time", inplace=True)
    df_merged.fillna(method="bfill", inplace=True)
    df_merged.fillna(method="ffill", inplace=True)

    if "day_of_week" not in df_merged.columns:
        df_merged["day_of_week"] = df_merged.index.dayofweek
    if "is_weekend" not in df_merged.columns:
        df_merged["is_weekend"] = df_merged["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
    if "history_error" not in df_merged.columns:
        df_merged["naive_prediction"] = df_merged["zoo_index"].shift(1)
        df_merged["history_error"] = (df_merged["zoo_index"] - df_merged["naive_prediction"]).shift(1)
        df_merged.drop(columns=["naive_prediction"], inplace=True)
        df_merged["history_error"].fillna(0, inplace=True)

    output_path = OUTPUT_DIR / "experiment17_prepared_panel.xlsx"
    df_merged.reset_index().to_excel(output_path, index=False)
    print(f"数据清洗与融合完成！已生成文件: {output_path}")
    print(df_merged.head())
except Exception as e:
    print(f"数据处理出错: {e}")
    exit()

# 定义模型特征 (必须保证 zoo_index 在第0列，因为它是被预测的 target)
features =['zoo_index', 'ticket_index', 'AQI', 'day_of_week', 'is_weekend', 'history_error']
data = df_merged[features].values
target_data = df_merged[['zoo_index']].values
num_features = len(features)

# ==========================================
# 步骤 2: 数据归一化与滑动窗口构造
# ==========================================
print("\n--- 步骤 2: 数据归一化与滑动窗口 ---")
scaler = MinMaxScaler(feature_range=(0, 1))
scaled_data = scaler.fit_transform(data)

look_back = 14  # 历史回看天数

def create_dataset(dataset, look_back=1):
    X, Y = [],[]
    for i in range(len(dataset) - look_back):
        X.append(dataset[i:(i + look_back), :]) # 提取所有 6 个特征
        Y.append(dataset[i + look_back, 0])     # 预测目标仅为 zoo_index
    return np.array(X), np.array(Y)

X, Y = create_dataset(scaled_data, look_back)

# 数据集切分 (80% 训练, 10% 验证, 10% 测试)
train_size = int(len(X) * 0.8)
val_size = int(len(X) * 0.1)
test_size = len(X) - train_size - val_size

X_train, Y_train = X[0:train_size], Y[0:train_size]
X_val, Y_val = X[train_size:train_size+val_size], Y[train_size:train_size+val_size]
X_test, Y_test = X[train_size+val_size:], Y[train_size+val_size:]

print(f"特征数: {num_features} | X_train 形状: {X_train.shape}")

# ==========================================
# 步骤 3: 构建并训练 元认知 LSTM+Attention 模型
# ==========================================
print("\n--- 步骤 3: 训练 Meta-Cognitive LSTM-Attention ---")

inputs = Input(shape=(look_back, num_features))
lstm_out = LSTM(units=64, return_sequences=True)(inputs)

# Attention 层
attention_probs = Dense(1, activation='tanh')(lstm_out)
attention_probs = Flatten()(attention_probs)
attention_probs = Activation('softmax', name='attention_weights')(attention_probs)

attention_probs_reshaped = RepeatVector(64)(attention_probs)
attention_probs_reshaped = Permute([2, 1])(attention_probs_reshaped)
attention_mul = Multiply()([lstm_out, attention_probs_reshaped])

context_vector = Lambda(lambda x: tf.reduce_sum(x, axis=1), name='Context_Vector')(attention_mul)

# Dropout 层 (将在推理时用于提取元认知不确定性)
x = Dropout(0.3)(context_vector)
output = Dense(units=1)(x)

model = Model(inputs=inputs, outputs=output)
model.compile(optimizer='adam', loss='mean_squared_error')

early_stop = EarlyStopping(monitor='val_loss', patience=15, restore_best_weights=True, verbose=1)

history = model.fit(
    X_train, Y_train, 
    epochs=300, 
    batch_size=32, 
    validation_data=(X_val, Y_val), 
    callbacks=[early_stop], 
    verbose=1
)

model_path = OUTPUT_DIR / "experiment17_zoo_lstm_attention_model.h5"
model.save(model_path)
print(f"已保存模型文件: {model_path}")

# ==========================================
# 步骤 4: 基础模型预测与反归一化评估
# ==========================================
print("\n--- 步骤 4: 基础评估 ---")

train_predict = model.predict(X_train)
test_predict = model.predict(X_test)

# 多变量反归一化辅助函数
def invert_scale(scaler, pred_values, num_feats, target_col=0):
    dummy = np.zeros((len(pred_values), num_feats))
    dummy[:, target_col] = pred_values.flatten()
    return scaler.inverse_transform(dummy)[:, target_col].reshape(-1, 1)

train_predict = invert_scale(scaler, train_predict, num_features)
test_predict = invert_scale(scaler, test_predict, num_features)
Y_test_inv = invert_scale(scaler, Y_test, num_features)

rmse = np.sqrt(mean_squared_error(Y_test_inv, test_predict))
mae = mean_absolute_error(Y_test_inv, test_predict)
mape = np.mean(np.abs((Y_test_inv - test_predict) / Y_test_inv)) * 100

print(f"[测试集评估] RMSE: {rmse:.2f} | MAE: {mae:.2f} | MAPE: {mape:.2f}%")

# ==========================================
# 步骤 5: 大赛级高级可视化输出
# ==========================================
print("\n--- 步骤 5: 可视化与统计学检验生成 ---")

# (1) Loss与整体拟合情况图
fig, axes = plt.subplots(2, 1, figsize=(14, 10))
axes[0].plot(history.history['loss'], label='训练集 Loss')
axes[0].plot(history.history['val_loss'], label='验证集 Loss')
axes[0].set_title('多源异构模型训练 Loss 收敛曲线')
axes[0].legend()
axes[0].grid(True, linestyle='--', alpha=0.6)

# test_plot = np.empty_like(target_data)
# test_plot[:, :] = np.nan
test_plot = np.empty_like(target_data, dtype=np.float64)
test_plot[:, :] = np.nan
test_plot[look_back + len(train_predict) + val_size : len(target_data), :] = test_predict

axes[1].plot(df_merged.index, target_data, label='真实总客流指数 (Zoo Index)', color='gray', alpha=0.5)
axes[1].plot(df_merged.index, test_plot, label='测试集预测值', color='red', linewidth=1.5)
axes[1].set_title('北京动物园综合客流压力时序预测 (多变量驱动)')
axes[1].legend()
axes[1].grid(True, linestyle='--', alpha=0.6)
plt.tight_layout()
plt.show()

# (2) 白噪声检验与残差分析图
residuals = Y_test_inv.flatten() - test_predict.flatten()
fig, axes = plt.subplots(2, 2, figsize=(14, 9))
axes[0, 0].plot(residuals, color='#2980b9')
axes[0, 0].axhline(y=0, color='r', linestyle='--')
axes[0, 0].set_title('残差序列震荡图')
axes[0, 1].hist(residuals, bins=30, color='#27ae60', edgecolor='white', density=True)
axes[0, 1].set_title('残差正态分布直方图')
stats.probplot(residuals, dist="norm", plot=axes[1, 0])
axes[1, 0].set_title('残差 Q-Q 图')
plot_acf(residuals, ax=axes[1, 1], lags=20, color='#f39c12')
axes[1, 1].set_title('残差 ACF 自相关检验')
plt.tight_layout()
plt.show()

lb_res = acorr_ljungbox(residuals, lags=[10], return_df=True)
p_val = lb_res['lb_pvalue'].values[0]
print(f"[残差白噪声检验] Ljung-Box P-value: {p_val:.4f} " + ("(通过, 充分提取)" if p_val > 0.05 else "(未通过)"))

# (3) Attention 时间维度可解释性权重图
debug_model = Model(inputs=model.input, outputs=model.get_layer('attention_weights').output)
# _, attn_weights = debug_model.predict(X_test)
attn_weights = debug_model.predict(X_test)
avg_attn_weights = np.mean(attn_weights, axis=0)

plt.figure(figsize=(10, 5))
bars = plt.bar(range(1, look_back + 1), avg_attn_weights, color='#3498db', edgecolor='black')
for bar in bars:
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.002, 
             f'{bar.get_height():.3f}', ha='center', va='bottom', fontsize=10)
plt.title(f'Attention模块：回看窗口时间依赖权重分布 (T-n)', fontsize=14)
plt.xticks(range(1, look_back + 1),[f'T-{i}' for i in range(look_back, 0, -1)])
plt.grid(axis='y', linestyle='--', alpha=0.5)
plt.show()

# (4) 【元认知模块一】: MC Dropout 认知不确定性边界图
@tf.function
def mc_predict_step(x):
    return model(x, training=True) # 开启 Dropout

mc_predictions =[]
X_test_tensor = tf.convert_to_tensor(X_test, dtype=tf.float32)
for i in range(50):
    preds = mc_predict_step(X_test_tensor)
    preds_inv = invert_scale(scaler, preds.numpy(), num_features)
    mc_predictions.append(preds_inv.flatten())

mc_predictions = np.array(mc_predictions)
mc_mean = np.mean(mc_predictions, axis=0)
mc_std = np.std(mc_predictions, axis=0)
upper_bound = mc_mean + 1.96 * mc_std
lower_bound = mc_mean - 1.96 * mc_std

plot_len = min(120, len(Y_test_inv))
x_axis = df_merged.index[-plot_len:]

plt.figure(figsize=(14, 6))
plt.plot(x_axis, Y_test_inv.flatten()[-plot_len:], label='真实客流量 (Ground Truth)', color='black', linewidth=1.5)
plt.plot(x_axis, mc_mean[-plot_len:], label='网络预测均值 (MC Mean)', color='#c0392b', linestyle='--')
plt.fill_between(x_axis, lower_bound[-plot_len:], upper_bound[-plot_len:], 
                 color='#e74c3c', alpha=0.25, label='95% 认知不确定性边界 (Epistemic Uncertainty)')
plt.title('元认知机制 I：带有认知不确定性的北京动物园综合压力预测', fontsize=15, fontweight='bold')
plt.legend(loc='upper left')
plt.grid(True, linestyle='--', alpha=0.4)
plt.tight_layout()
plt.show()

# (5) 【元认知模块二】: 误差反馈动态响应图 (双轴)
history_error_test = df_merged['history_error'].iloc[-plot_len:].values

fig, ax1 = plt.subplots(figsize=(14, 5))
ax1.plot(x_axis, Y_test_inv.flatten()[-plot_len:], color='black', label='真实客流压力')
ax1.set_ylabel('真实客流量指数', color='black', fontsize=12)

ax2 = ax1.twinx()
colors =['#e74c3c' if val > 0 else '#2ecc71' for val in history_error_test]
ax2.bar(x_axis, history_error_test, color=colors, alpha=0.5, width=0.6, label='T-1时刻纠错信号 (Error Shock)')
ax2.set_ylabel('前置偏差反馈幅度', color='gray', fontsize=12)

plt.title('元认知机制 II：自回归误差反思与纠错动态追踪', fontsize=15, fontweight='bold')
lines_1, labels_1 = ax1.get_legend_handles_labels()
lines_2, labels_2 = ax2.get_legend_handles_labels()
ax1.legend(lines_1 + lines_2, labels_1 + labels_2, loc='upper right', fontsize=11)
plt.tight_layout()
plt.show()

print("\n🎉 全部建模与可视化流程已顺利跑通！")
