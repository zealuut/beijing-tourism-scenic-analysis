# llm_issue_tag_fewshot_v1

## 使用说明

- 只判断 `issue_tags`
- 没有明确治理问题时，返回空数组 `[]`
- 可以多标签，但不要过度打标

## No-Issue 示例

### Example 1
- review_text：景色很美，拍照很好看，路线也比较顺，整体值得来。
- issue_tags：[]
- why：整体是正向体验，没有明确治理问题。

### Example 2
- review_text：建议早点到，上午人少一些，天气好的时候风景特别漂亮。
- issue_tags：[]
- why：这是游玩建议，不是治理问题抱怨。

## 标签示例

### staff_service
- review_text：现场工作人员态度很差，问路爱答不理，客服也一直不回复。
- issue_tags：["staff_service"]
- why：核心问题是服务态度和响应意愿差。

### service_process
- review_text：集合安排特别乱，安检和检票流程反复折返，浪费了很多时间。
- issue_tags：["service_process"]
- why：核心问题是流程组织和现场衔接混乱。

### guide_explanation
- review_text：讲解员讲得特别乱，声音也听不清，很多内容都没有解释明白。
- issue_tags：["guide_explanation"]
- why：核心问题是讲解质量差。

### queue_wait
- review_text：缆车排队排了快两个小时，队伍特别长，体验被拖得很差。
- issue_tags：["queue_wait"]
- why：核心问题是等待时间过长。

### reservation_entry
- review_text：预约说明不清楚，到了入口才发现还要实名核验，二维码也进不去。
- issue_tags：["reservation_entry"]
- why：核心问题是预约入园与核验规则。

### ticket_price
- review_text：门票和联票都偏贵，里面很多项目还要二次收费，性价比很低。
- issue_tags：["ticket_price"]
- why：核心问题是价格与性价比。

### traffic_access
- review_text：地铁出来还要走很远，打车也不好打，停车场几乎找不到位置。
- issue_tags：["traffic_access"]
- why：核心问题是交通到达和停车换乘不便。

### facility_hygiene
- review_text：厕所太少而且很脏，休息区也不够，环境卫生整体一般。
- issue_tags：["facility_hygiene"]
- why：核心问题是配套设施和环境卫生。

### crowding
- review_text：景区里人太多了，走路都被挤着走，热门点位几乎站不住。
- issue_tags：["crowding"]
- why：核心问题是景区内部拥挤和人流压力。

### commercialization
- review_text：一路都在推销拍照和纪念品，旅拍和卖货严重干扰正常参观。
- issue_tags：["commercialization"]
- why：核心问题是商业化和消费干扰。

### platform_transaction
- review_text：在携程上买的票到了现场不能核销，退款也一直处理不了。
- issue_tags：["platform_transaction"]
- why：核心问题是第三方平台订单与履约问题。

## 多标签示例

### Example 1
- review_text：携程上买的票二维码打不开，最后只能重新排队现场买票。
- issue_tags：["platform_transaction", "queue_wait"]
- why：既有平台二维码失效，也有因此产生的排队等待。

### Example 2
- review_text：入口规则太混乱，工作人员态度也很差，问了半天都没人说明白。
- issue_tags：["reservation_entry", "staff_service"]
- why：同时涉及入园规则问题和服务态度问题。
