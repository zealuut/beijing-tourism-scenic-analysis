# 居庸关长城 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.2174
- issue_rate：0.1000
- negative_rate：0.2500
- dissatisfaction：0.1750
- performance：0.8250
- priority_index：0.0380
- quadrant：高重要性低表现 = 优先改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |    0.217391  |          0.1 |       0.25      |               0.175     |      0.825    |       0.0380435  | 高重要性低表现 = 优先改进   |
|                      2 | 现场服务与导览体验       |    0.0507246 |          0   |       0.0714286 |               0.0357143 |      0.964286 |       0.00181159 | 低重要性高表现 = 低优先级观察 |
|                      3 | 交通与开放空间体验       |    0.0543478 |          0   |       0         |               0         |      1        |       0          | 低重要性高表现 = 低优先级观察 |