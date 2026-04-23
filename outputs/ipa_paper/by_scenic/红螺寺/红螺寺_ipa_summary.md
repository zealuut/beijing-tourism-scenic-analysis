# 红螺寺 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.4059
- issue_rate：0.0727
- negative_rate：0.0909
- dissatisfaction：0.0818
- performance：0.9182
- priority_index：0.0332
- quadrant：高重要性低表现 = 优先改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |    0.405904  |    0.0727273 |       0.0909091 |               0.0818182 |      0.918182 |       0.0332103  | 高重要性低表现 = 优先改进   |
|                      2 | 现场服务与导览体验       |    0.118081  |    0         |       0.09375   |               0.046875  |      0.953125 |       0.00553506 | 低重要性高表现 = 低优先级观察 |
|                      3 | 交通与开放空间体验       |    0.0664207 |    0.111111  |       0.0555556 |               0.0833333 |      0.916667 |       0.00553506 | 低重要性低表现 = 次级改进   |