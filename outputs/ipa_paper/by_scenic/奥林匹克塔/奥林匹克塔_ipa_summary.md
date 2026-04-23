# 奥林匹克塔 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.1397
- issue_rate：0.4737
- negative_rate：0.5526
- dissatisfaction：0.5132
- performance：0.4868
- priority_index：0.0717
- quadrant：低重要性低表现 = 次级改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |    0.139706  |    0.473684  |       0.552632  |               0.513158  |      0.486842 |       0.0716912  | 低重要性低表现 = 次级改进   |
|                      2 | 交通与开放空间体验       |    0.330882  |    0.0444444 |       0.0444444 |               0.0444444 |      0.955556 |       0.0147059  | 高重要性高表现 = 继续保持   |
|                      3 | 现场服务与导览体验       |    0.0367647 |    0.1       |       0.2       |               0.15      |      0.85     |       0.00551471 | 低重要性高表现 = 低优先级观察 |