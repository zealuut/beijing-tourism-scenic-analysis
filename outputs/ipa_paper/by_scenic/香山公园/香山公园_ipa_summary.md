# 香山公园 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.3063
- issue_rate：0.2353
- negative_rate：0.2500
- dissatisfaction：0.2426
- performance：0.7574
- priority_index：0.0743
- quadrant：高重要性低表现 = 优先改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |     0.306306 |     0.235294 |            0.25 |                0.242647 |      0.757353 |        0.0743243 | 高重要性低表现 = 优先改进   |
|                      2 | 现场服务与导览体验       |     0.018018 |     0.25     |            0.25 |                0.25     |      0.75     |        0.0045045 | 低重要性低表现 = 次级改进   |
|                      3 | 交通与开放空间体验       |     0.103604 |     0        |            0    |                0        |      1        |        0         | 低重要性高表现 = 低优先级观察 |