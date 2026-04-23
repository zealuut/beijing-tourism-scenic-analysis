# 潭柘寺 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.6866
- issue_rate：0.1413
- negative_rate：0.1359
- dissatisfaction：0.1386
- performance：0.8614
- priority_index：0.0951
- quadrant：高重要性低表现 = 优先改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |    0.686567  |     0.141304 |         0.13587 |               0.138587  |      0.861413 |       0.0951493  | 高重要性低表现 = 优先改进   |
|                      2 | 交通与开放空间体验       |    0.0783582 |     0.047619 |         0       |               0.0238095 |      0.97619  |       0.00186567 | 低重要性高表现 = 低优先级观察 |
|                      3 | 现场服务与导览体验       |    0.0634328 |     0        |         0       |               0         |      1        |       0          | 低重要性高表现 = 低优先级观察 |