# IPA Paper Outputs

## 1. 本目录是什么

本目录保存的是**论文正式口径**的 IPA 结果。  
这一版不再沿用旧样本下的人工加权优先级公式，而是只依赖当前 20 个景区、当前这批评论样本的现有结果重新计算。

对应脚本：

- `旅游景点分析/scripts/07_run_experiment7_paper_ipa.py`

上游输入：

- `旅游景点分析/data/sentiment/experiment5_snownlp_scored.csv`
- `旅游景点分析/data/lda/experiment3_lda_topic_assignments.csv`

## 2. 进入IPA的对象

IPA 的分析对象是 **LDA 一级治理主题**，不是 11 个二级问题标签。

当前进入治理 IPA 的主题有：

- `票务预约与入园体验`
- `现场服务与导览体验`
- `交通与开放空间体验`

主题 `整体满意与感知评价` 被视为满意主题，**不进入治理 IPA 排序**。

需要特别说明：

- `LDA 一级主题` 和 `LLM 11 个二级问题标签` 不是同一层级。
- 一级主题用于做 IPA 与聚类，回答“游客主要在谈哪类治理主题”。
- 二级标签用于解释主题内部的具体摩擦点，回答“游客到底在抱怨什么”。
- 两者是“一级主题 -> 二级标签”的关系，不是一一对应关系。

当前样本的主题-标签实证对应表已导出到：

- `experiment7_theme_issue_tag_mapping.csv`

对应的文字说明见：

- `旅游景点分析/docs/LDA一级主题与11个二级标签对应说明.md`

## 3. 这版IPA为什么可解释

这版指标设计遵循一个原则：

- `Importance` 反映游客对主题的关注度
- `Performance` 反映主题的实际体验表现
- `PriorityIndex` 同时考虑“提得多不多”和“体验差不差”

所有指标都直接来自当前样本中的评论计数与比例，因此适合写进论文方法部分。

## 4. 核心指标定义

设景区为 `s`，一级主题为 `t`。

### 4.1 样本基数

- `N_s`：景区 `s` 中进入 LDA / IPA 阶段的可用评论总数
- `n_(s,t)`：景区 `s` 中被分配到主题 `t` 的评论数
- `m_(s,t)`：主题 `t` 下被判定为存在问题标签的评论数
- `u_(s,t)`：主题 `t` 下被判定为负向情绪的评论数

注意：

- `N_s` 不是原始抓取评论总数
- `N_s` 也不是固定的 300
- 它是经过 LDA 前清洗和过滤后，真正进入 IPA 计算的评论数

## 5. 景区层IPA公式

### 5.1 Importance

`Importance_(s,t) = n_(s,t) / N_s`

含义：

- 该主题在该景区评论中的出现比例
- 比例越高，说明游客对该主题关注度越高

### 5.2 Issue Rate

`IssueRate_(s,t) = m_(s,t) / n_(s,t)`

含义：

- 在该主题评论里，被 LLM 标为“有治理问题”的比例

### 5.3 Negative Rate

`NegativeRate_(s,t) = u_(s,t) / n_(s,t)`

含义：

- 在该主题评论里，被 SnowNLP 判为负向情绪的比例

### 5.4 Dissatisfaction Index

`Dissatisfaction_(s,t) = (IssueRate_(s,t) + NegativeRate_(s,t)) / 2`

含义：

- 该主题的“不满意程度”
- 这里采用**等权平均**

这样设定的理由是：

- `IssueRate` 反映显性治理摩擦
- `NegativeRate` 反映整体体验情绪
- 两者都重要，但本轮不再主观指定不同权重

### 5.5 Performance

`Performance_(s,t) = 1 - Dissatisfaction_(s,t)`

含义：

- 表现越高，说明该主题整体体验越好
- 表现越低，说明该主题更值得治理关注

### 5.6 Priority Index

`PriorityIndex_(s,t) = Importance_(s,t) * Dissatisfaction_(s,t)`

含义：

- 一个主题既要“被大量提及”，又要“体验表现差”，才会获得更高优先级

## 6. 整体IPA公式

整体层面沿用同样逻辑，只是把所有景区汇总后再计算主题指标。

设：

- `N`：全部景区进入 LDA / IPA 阶段的可用评论总数
- `n_t`：全部景区中属于主题 `t` 的评论总数
- `m_t`：全部景区中主题 `t` 下有问题标签的评论总数
- `u_t`：全部景区中主题 `t` 下负向情绪评论总数

则：

- `Importance_t = n_t / N`
- `IssueRate_t = m_t / n_t`
- `NegativeRate_t = u_t / n_t`
- `Dissatisfaction_t = (IssueRate_t + NegativeRate_t) / 2`
- `Performance_t = 1 - Dissatisfaction_t`
- `PriorityIndex_t = Importance_t * Dissatisfaction_t`

## 7. IPA四象限设置

本轮 IPA 采用经典的 `Importance - Performance Analysis` 图。

### 横轴

- `Importance`

### 纵轴

- `Performance`

### 象限分割线

不是手动指定常数，而是使用当前样本中治理主题的平均值：

- 整体 IPA：用整体三个治理主题的平均 `Importance` 和平均 `Performance`
- 单景区 IPA：用该景区内部三个治理主题的平均 `Importance` 和平均 `Performance`

### 四象限解释

- 高重要性低表现 = 优先改进
- 高重要性高表现 = 继续保持
- 低重要性低表现 = 次级改进
- 低重要性高表现 = 低优先级观察

## 8. 当前参数与口径设置

本轮 IPA 的关键设置如下：

- 只使用当前样本，不继承旧实验权重
- 满意主题不进入治理 IPA
- `IssueRate` 与 `NegativeRate` 等权
- `PriorityIndex = Importance × Dissatisfaction`
- 单景区与整体都使用各自样本均值作为象限分割线

## 9. 主要输出文件

### 根目录

- `experiment7_theme_panel.csv`
  主题层基础面板。每一行是“景区-一级主题”组合，记录评论数、问题数、负向数、重要性、表现、优先级等。

### `overall/`

- `experiment7_ipa_overall_matrix.csv`
  整体一级治理主题 IPA 结果表。
- `experiment7_ipa_overall.png`
  整体 IPA 图。
- `experiment7_ipa_overall_report.md`
  整体 IPA 的文字化解释。

### `by_scenic/`

每个景区一个文件夹，包含：

- `*_ipa_table.csv`
  该景区的主题排序表。
- `*_ipa.png`
  该景区的 IPA 图。
- `*_ipa_summary.md`
  该景区首要治理主题及解释。

## 10. 论文中如何解释

建议在论文中这样表达：

- `Importance` 表示游客对该主题的关注程度
- `Performance` 表示该主题的整体体验表现
- `PriorityIndex` 用于识别“高关注且高不满意”的治理重点
- 整体 IPA 回答“当前样本中哪类主题最该优先治理”
- 景区 IPA 回答“某个景区具体应优先改哪类主题”

## 11. 注意事项

- 这版 IPA 建立在当前 LDA 一级主题结构之上，因此会受主题稳定性影响
- 当前样本中 `票务预约与入园体验` 较强，因此很多景区会把它识别为首要治理主题
- 如果后续你们重跑 LDA 主题结构，IPA 也需要同步重算
