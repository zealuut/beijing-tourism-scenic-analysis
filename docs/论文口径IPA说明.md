# 论文口径IPA说明

## 1. 为什么重做
- 本轮 IPA 不再沿用旧样本下的主观加权优先级公式。
- 新指标只依赖当前这批 20 个景区、6000 条评论的现有结果，避免跨样本继承旧权重造成解释不稳。

## 2. 基本思想
- IPA 仍保留经典的 `Importance - Performance Analysis` 框架。
- 但这里的 `Importance` 和 `Performance` 都直接由当前评论数据计算，不再引入上一轮实验的外部权重。

## 3. 指标定义
设景区为 `s`，一级主题为 `t`。

### 3.1 重要性 Importance
- `Importance_(s,t) = n_(s,t) / N_s`
- 其中 `n_(s,t)` 是景区 `s` 中属于主题 `t` 的评论数，`N_s` 是景区 `s` 中进入 LDA/IPA 阶段的可用评论总数。
- 含义：该主题在景区评论中被提及的比例，表示游客对该主题的关注度。

### 3.2 问题率 Issue Rate
- `IssueRate_(s,t) = m_(s,t) / n_(s,t)`
- 其中 `m_(s,t)` 是主题 `t` 下被 LLM 识别为存在问题标签的评论数。

### 3.3 负向情绪率 Negative Rate
- `NegativeRate_(s,t) = u_(s,t) / n_(s,t)`
- 其中 `u_(s,t)` 是主题 `t` 下被 SnowNLP 判为负向情绪的评论数。

### 3.4 不满意指数 Dissatisfaction Index
- `D_(s,t) = (IssueRate_(s,t) + NegativeRate_(s,t)) / 2`
- 这里采用等权平均，不再使用主观权重。
- 原因：显性问题标签反映“具体摩擦”，负向情绪反映“整体感受”，二者共同表征主题表现不佳的程度。

### 3.5 表现 Performance
- `Performance_(s,t) = 1 - D_(s,t)`
- 表现越高，说明该主题的整体体验越好。

### 3.6 优先级指数 Priority Index
- `PriorityIndex_(s,t) = Importance_(s,t) * D_(s,t)`
- 含义：一个主题既要“被大量提及”，又要“表现较差”，才会成为更高优先级的治理对象。

## 4. 整体IPA
- 整体层面按全部景区汇总后，用同样公式计算每个一级治理主题的 `Importance`、`Performance` 和 `PriorityIndex`。
- 满意主题 `整体满意与感知评价` 不进入治理 IPA。

## 5. 四象限划分
- 横轴：Importance
- 纵轴：Performance
- 以当前样本中所有治理主题的平均 `Importance` 和平均 `Performance` 作为象限分割线。

## 6. 解释优势
- 指标全部来自当前样本，避免跨样本继承旧权重。
- 每个指标都能直接落到评论计数和比例，论文中容易解释。
- `PriorityIndex = Importance × Dissatisfaction` 兼顾关注度与问题强度，直观适合景区治理排序。