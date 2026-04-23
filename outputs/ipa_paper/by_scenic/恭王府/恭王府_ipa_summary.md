# 恭王府 IPA

## 1. 计算口径
- Importance：该主题评论数 / 该景区进入LDA/IPA阶段的可用评论总数
- Performance：1 - [(主题问题率 + 主题负向情绪率) / 2]
- PriorityIndex：Importance × Dissatisfaction

## 2. 当前景区首要治理主题
- 主题：票务预约与入园体验
- importance：0.2463
- issue_rate：0.2273
- negative_rate：0.2727
- dissatisfaction：0.2500
- performance：0.7500
- priority_index：0.0616
- quadrant：低重要性低表现 = 次级改进

## 3. 主题排序表
|   scenic_priority_rank | theme_name_cn   |   importance |   issue_rate |   negative_rate |   dissatisfaction_index |   performance |   priority_index | quadrant         |
|-----------------------:|:----------------|-------------:|-------------:|----------------:|------------------------:|--------------:|-----------------:|:-----------------|
|                      1 | 票务预约与入园体验       |    0.246269  |    0.227273  |       0.272727  |               0.25      |      0.75     |       0.0615672  | 低重要性低表现 = 次级改进   |
|                      2 | 现场服务与导览体验       |    0.458955  |    0.0406504 |       0.0487805 |               0.0447154 |      0.955285 |       0.0205224  | 高重要性高表现 = 继续保持   |
|                      3 | 交通与开放空间体验       |    0.0858209 |    0.0869565 |       0         |               0.0434783 |      0.956522 |       0.00373134 | 低重要性高表现 = 低优先级观察 |