# 故宫博物院 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.1783
- issue_rate：0.2157
- negative_rate：0.4314
- dissatisfaction：0.3235
- performance：0.6765
- priority_index：0.0577
- quadrant：低重要性低表现 = 次级改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |     0.178322 |    0.215686  |       0.431373  |               0.323529  |      0.676471 |        0.0576923 | 低重要性低表现 = 次级改进   |
|                      2 | 现场服务与导览体验       |     0.727273 |    0.0288462 |       0.0432692 |               0.0360577 |      0.963942 |        0.0262238 | 高重要性高表现 = 继续保持   |
|                      3 | 交通与开放空间体验       |     0.013986 |    0         |       0         |               0         |      1        |        0         | 低重要性高表现 = 低优先级观察 |