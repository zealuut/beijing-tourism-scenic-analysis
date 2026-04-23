# 首都博物馆 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.1365
- issue_rate：0.1351
- negative_rate：0.2162
- dissatisfaction：0.1757
- performance：0.8243
- priority_index：0.0240
- quadrant：低重要性低表现 = 次级改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |     0.136531 |    0.135135  |        0.216216 |              0.175676   |      0.824324 |       0.0239852  | 低重要性低表现 = 次级改进   |
|                      2 | 现场服务与导览体验       |     0.261993 |    0.0704225 |        0.084507 |              0.0774648  |      0.922535 |       0.0202952  | 低重要性高表现 = 低优先级观察 |
|                      3 | 交通与开放空间体验       |     0.464945 |    0         |        0.015873 |              0.00793651 |      0.992063 |       0.00369004 | 高重要性高表现 = 继续保持   |