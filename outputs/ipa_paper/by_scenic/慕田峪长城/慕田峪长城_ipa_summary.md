# 慕田峪长城 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.4021
- issue_rate：0.2478
- negative_rate：0.3894
- dissatisfaction：0.3186
- performance：0.6814
- priority_index：0.1281
- quadrant：高重要性低表现 = 优先改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |    0.402135  |    0.247788  |        0.389381 |               0.318584  |      0.681416 |       0.128114   | 高重要性低表现 = 优先改进   |
|                      2 | 现场服务与导览体验       |    0.106762  |    0.0333333 |        0.1      |               0.0666667 |      0.933333 |       0.00711744 | 低重要性高表现 = 低优先级观察 |
|                      3 | 交通与开放空间体验       |    0.0355872 |    0         |        0.1      |               0.05      |      0.95     |       0.00177936 | 低重要性高表现 = 低优先级观察 |