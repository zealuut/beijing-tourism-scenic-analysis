# 动态案例输出

## 1. 目的
- 将 `multi_data_for_MetaLSTM.xlsx` 转成适合论文叙事的北京动物园动态案例数据。
- 主模型强调可解释性和显著性；attention 仅保留为辅助热力图。

## 2. 核心文件
- `experiment12_dynamic_regression_coefficients.csv`：主模型系数、稳健标准误与显著性
- `experiment12_dynamic_regression_coefficients.svg`：主模型系数图
- `experiment12_dynamic_regression_panel_with_fit.csv`：带拟合值与残差的日度面板
- `experiment12_attention_like_heatmap.svg`：attention 风格时滞热力图
- `experiment12_attention_like_heatmap_data.csv`：热力图底表
- `experiment12_feature_selection_rationale.csv`：为什么选这些变量、不选哪些列
- `experiment12_calendar_group_summary.csv`：按周末/节假日/学校假期/高压日的描述性汇总
- `experiment12_dynamic_case_report.md`：案例方法与解释报告