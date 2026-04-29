import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.api as sm
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.metrics import roc_curve, auc, confusion_matrix
import shap
import warnings
warnings.filterwarnings('ignore')

# ----------------- 0. 环境设置与数据加载 -----------------
# 设置中文字体，防止图表中的中文显示为方块
plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows用黑体
plt.rcParams['axes.unicode_minus'] = False    # 正常显示负号

file_path = r'E:\TongJiJianMo\data\sentiment_regression.xlsx'

# 加载数据
try:
    df = pd.read_excel(file_path)
    print("数据加载成功！")
except Exception as e:
    print(f"数据加载失败，请检查路径: {e}")

# 【数据清洗】因为截图中前两列名字都叫 'sentiment'，我们需要重命名以区分
# 假设第一列是得分(连续)，第二列是标签(分类)
col_names = list(df.columns)
col_names[0] = 'sentiment_score'
col_names[1] = 'sentiment_label'
df.columns = col_names

# 提取特征变量 X (即所有的 tag_ 开头的列)
X_cols =[col for col in df.columns if col.startswith('tag_')]
X = df[X_cols]

# 检查是否有全为0的列（零方差），这种列会导致回归模型矩阵奇异（Singular Matrix）
zero_var_cols = X.columns[X.var() == 0].tolist()
if zero_var_cols:
    print(f"警告：以下特征列方差为0（无变化），将在建模中剔除: {zero_var_cols}")
    X = X.drop(columns=zero_var_cols)

# 定义因变量 Y
y_linear = df['sentiment_score']

# 逻辑回归需要二分类因变量：将 'positive' 设为 1，'negative' 和 'neutral' 设为 0
y_logistic = df['sentiment_label'].apply(lambda x: 1 if x == 'positive' else 0)

# ----------------- 1. 多元线性回归模型 (OLS) -----------------
print("\n" + "="*50)
print("开始构建：多元线性回归模型 (分析情感得分驱动力)")
print("="*50)

# 使用 statsmodels 构建，因为它能提供极其详细的统计学检验报告(P值, t值, R方等)
X_sm = sm.add_constant(X) # 添加常数项(截距)
ols_model = sm.OLS(y_linear, X_sm).fit()

# 打印专业回归报告
print(ols_model.summary())

# 【可视化1】：线性回归系数条形图（剔除截距项）
plt.figure(figsize=(10, 6))
ols_coefs = ols_model.params.drop('const')
p_values = ols_model.pvalues.drop('const')
colors =['#2ca02c' if p < 0.05 else '#7f7f7f' for p in p_values] # 显著的用绿色，不显著用灰色

sns.barplot(x=ols_coefs.values, y=ols_coefs.index, palette=colors)
plt.title('多元线性回归: 各标签对情感得分的影响系数\n(绿色表示P<0.05，统计显著)', fontsize=14)
plt.xlabel('回归系数 (Coefficient)', fontsize=12)
plt.ylabel('服务标签', fontsize=12)
plt.axvline(0, color='black', linestyle='--')
plt.tight_layout()
plt.show()

# ----------------- 2. 逻辑回归模型 (Logit) -----------------
print("\n" + "="*50)
print("开始构建：逻辑回归模型 (分析好评率的驱动力)")
print("="*50)

# 使用 statsmodels 构建逻辑回归，获取统计报告
logit_model = sm.Logit(y_logistic, X_sm).fit(disp=0)
print(logit_model.summary())

# 计算 优势比 (Odds Ratios) - 业务中最常用的解释指标
# 优势比 = exp(回归系数)。如果某标签的OR=1.5，说明有这个标签时，好评的概率是没有时的1.5倍。
odds_ratios = np.exp(logit_model.params.drop('const'))

# 【可视化2】：逻辑回归优势比(Odds Ratio)条形图
plt.figure(figsize=(10, 6))
logit_p_values = logit_model.pvalues.drop('const')
colors_logit =['#1f77b4' if p < 0.05 else '#7f7f7f' for p in logit_p_values]

sns.barplot(x=odds_ratios.values, y=odds_ratios.index, palette=colors_logit)
plt.title('逻辑回归: 各标签对达成"好评(Positive)"的优势比(Odds Ratio)\n(蓝色表示P<0.05显著，OR>1表示正向促进)', fontsize=14)
plt.xlabel('优势比 (Odds Ratio)', fontsize=12)
plt.ylabel('服务标签', fontsize=12)
plt.axvline(1, color='red', linestyle='--') # OR=1 是基准线
plt.tight_layout()
plt.show()

# 【可视化3】：逻辑回归 ROC 曲线（评估模型整体区分能力）
y_pred_prob = logit_model.predict(X_sm)
fpr, tpr, thresholds = roc_curve(y_logistic, y_pred_prob)
roc_auc = auc(fpr, tpr)

plt.figure(figsize=(6, 6))
plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
plt.plot([0, 1],[0, 1], color='navy', lw=2, linestyle='--')
plt.xlim([0.0, 1.0])
plt.ylim([0.0, 1.05])
plt.xlabel('假阳性率 (False Positive Rate)')
plt.ylabel('真阳性率 (True Positive Rate)')
plt.title('逻辑回归模型 ROC 曲线')
plt.legend(loc="lower right")
plt.show()

# ----------------- 3. 核心贡献度分析 (SHAP 分析) -----------------
print("\n" + "="*50)
print("开始构建：SHAP 指标贡献度分析")
print("="*50)

# 为了兼容SHAP，我们这里使用 sklearn 的模型重新拟合一下(结果与statsmodels一致)
sk_linear = LinearRegression().fit(X, y_linear)

# 初始化 SHAP 线性解释器
explainer = shap.LinearExplainer(sk_linear, X)
shap_values = explainer.shap_values(X)

# 【可视化4】：SHAP 摘要图 (Summary Plot) - 蜂群图
# 展示了每个特征对每个样本的具体影响大小和方向
plt.figure(figsize=(10, 8))
plt.title("SHAP 贡献度分析：各标签对得分的微观影响分布", fontsize=14, pad=20)
shap.summary_plot(shap_values, X, show=False)
plt.tight_layout()
plt.show()

# 【可视化5】：SHAP 全局特征重要性柱状图
# 计算每个特征SHAP值的绝对值平均，这是衡量“核心驱动力”最科学的指标之一
plt.figure(figsize=(10, 6))
plt.title("全局核心驱动力排名 (基于平均绝对 SHAP 值)", fontsize=14, pad=20)
shap.summary_plot(shap_values, X, plot_type="bar", show=False, color='#ff7f0e')
plt.tight_layout()
plt.show()

print("\n分析流程执行完毕！")