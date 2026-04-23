# 天坛公园 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.4380
- issue_rate：0.2583
- negative_rate：0.4500
- dissatisfaction：0.3542
- performance：0.6458
- priority_index：0.1551
- quadrant：高重要性低表现 = 优先改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |     0.437956 |    0.258333  |        0.45     |               0.354167  |      0.645833 |       0.155109   | 高重要性低表现 = 优先改进   |
|                      2 | 交通与开放空间体验       |     0.142336 |    0.0769231 |        0.025641 |               0.0512821 |      0.948718 |       0.00729927 | 低重要性高表现 = 低优先级观察 |
|                      3 | 现场服务与导览体验       |     0.145985 |    0.025     |        0        |               0.0125    |      0.9875   |       0.00182482 | 低重要性高表现 = 低优先级观察 |