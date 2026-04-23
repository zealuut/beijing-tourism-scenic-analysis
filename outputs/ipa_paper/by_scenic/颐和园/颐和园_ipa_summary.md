# 颐和园 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.2072
- issue_rate：0.2885
- negative_rate：0.4038
- dissatisfaction：0.3462
- performance：0.6538
- priority_index：0.0717
- quadrant：低重要性低表现 = 次级改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |     0.207171 |    0.288462  |       0.403846  |              0.346154   |      0.653846 |       0.0717131  | 低重要性低表现 = 次级改进   |
|                      2 | 现场服务与导览体验       |     0.422311 |    0.0566038 |       0.0471698 |              0.0518868  |      0.948113 |       0.0219124  | 高重要性高表现 = 继续保持   |
|                      3 | 交通与开放空间体验       |     0.227092 |    0.0175439 |       0         |              0.00877193 |      0.991228 |       0.00199203 | 低重要性高表现 = 低优先级观察 |