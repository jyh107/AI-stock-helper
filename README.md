# AI-Stock-Helper

一个股票AI助手，可以提供更加精确的技术分析以及形态分析，一个在dify和蚂蚁百宝箱（tbox）都有部署的ai智能体（chatflow）。

## 访问地址

* **百宝箱使用地址**：[https://www.tbox.cn/share/202507APJnJZ00475051?platform=WebService](https://www.tbox.cn/share/202507APJnJZ00475051?platform=WebService)
* **量化程序地址**：[https://quant.10jqka.com.cn/view/article/155964#profit-chart-normal](https://quant.10jqka.com.cn/view/article/155964#profit-chart-normal)
    * （注：量化版本为前几代未更新，有一些小错误，待优化）
    * 不知道啥原因，帖子被删了（25.7.17）<img width="978" height="152" alt="image" src="https://github.com/user-attachments/assets/1656491b-d701-4f49-bdcc-17e800c70a07" />



## 应用介绍

该股票AI助手，输入具体A股名称和查询区间，可获得这段时间该股的日K线数据。通过大模型研判，为用户提供该股的走势形态和技术面情况（如上升趋势、下降趋势、头肩底、箱体震荡、箱体突破、V型反转等），并提供买卖建议。对于分析股票，辅助判断未来走势有较大帮助。

应用内嵌了专业知识库，内容为实际案例与实战经验，例如：
* 箱体震荡的三个作用，以及主力意图是什么；
* 根据大小盘子判断主力是哪路资金（私募、公募，还是单一主力）；
* 何为高控盘走势；
* 主力集中拿货位置、主力仓位大小判断、主力是否出货、是否出货干净等等。
* 一些高胜率的盈利模式，如箱体突破、强势盘整等。

> **免责声明**：由于股票市场不确定性极强，请慎重考虑该应用给出的建议，盈亏自负。

## 智能体与技术实现

### 智能体示例

<img width="1214" height="964" alt="image" src="https://github.com/user-attachments/assets/86608cdf-f206-4310-a987-0c5103cb33b1" />
<img width="1109" height="1050" alt="image" src="https://github.com/user-attachments/assets/4229e2bc-875b-42ee-9104-b3b4ee84f16a" />
<img width="1096" height="1001" alt="image" src="https://github.com/user-attachments/assets/a64e83c3-cc18-4bb0-9ae9-3dae0d9710fb" />

### 应用创建关键点

1.  **Prompt Engineering**：文本大模型的prompt很重要，对于不同功能需要构建特定的prompt。
    <img width="440" height="437" alt="image" src="https://github.com/user-attachments/assets/d02581d2-8cd8-4331-957f-179dbc24aa7d" />

2.  **数据获取**: 通过`tushare`获取股票历史行情，为此需要自己创建一个插件，通过API访问。
    <img width="2236" height="348" alt="image" src="https://github.com/user-attachments/assets/27ec852d-1cfa-447b-87b8-26b1918d85f5" />

---

## 量化策略与结合

### 量化回测结果

* 量化程序在supermind使用python编写，需要配合supermind平台的环境和api文档。
* 量化程序为1.0版本，适合短期赚钱效应较好的时间段（盈利会更多）
* 基准收益采用中证300指数（399300.SZ）
<img width="2533" height="1162" alt="image" src="https://github.com/user-attachments/assets/4c229662-ee19-4051-8f8f-35a1da6df9db" />


### 后续计划
计划在百宝箱中接入同花顺supermind的量化程序策略每日返回的持仓结果。
* 由于两平台并不互通，且supermind对request请求有严格限制,回测中禁止使用request（专业量化平台通用的规则）。
* 于是我使用阿里云FC作为中转站，将supermind推送的数据存储在OSS中，并在百宝箱中设置插件工具，通过api访问FC获取结果。
* 但由于对阿里云服务并不是很熟悉，初期导致产生大量cu费用，且需一直运行但当前使用量极少，**现决定暂停此功能**，待后续有机会重启。
