# 明十三陵 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.6525
- issue_rate：0.2426
- negative_rate：0.3905
- dissatisfaction：0.3166
- performance：0.6834
- priority_index：0.2066
- quadrant：高重要性低表现 = 优先改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |    0.65251   |     0.242604 |        0.390533 |                0.316568 |      0.683432 |        0.206564  | 高重要性低表现 = 优先改进   |
|                      2 | 现场服务与导览体验       |    0.127413  |     0.151515 |        0.151515 |                0.151515 |      0.848485 |        0.019305  | 低重要性高表现 = 低优先级观察 |
|                      3 | 交通与开放空间体验       |    0.0617761 |     0.125    |        0.3125   |                0.21875  |      0.78125  |        0.0135135 | 低重要性高表现 = 低优先级观察 |