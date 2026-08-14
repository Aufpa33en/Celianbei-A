# 2026-08-14 第三问全量验证与最终预测

## 变更范围

- 新增第三问正式全量验证模块、原子结果发布模块、正式运行入口和协议测试。
- 生成`result/q3/02_full_validation`与`result/q3/03_final_predictions`两个权威结果目录。
- 新增`reports/q3_full_validation_report.md`，补充第三问推导文档的正式结果与最终口径。

## 变更内容

1. 40块完整电池执行六模型、三个早期长度的外层LOBO；每折只用其余39块完成B/C/D调参。
2. 同时保存六固定候选比较和独立嵌套模型族选择器，避免把模型选择误差伪装成固定模型误差。
3. 用预先冻结的0.15/0.25/0.60综合指标选择`C_ridge`；模型族冻结后再用全部40块确定L=150部署超参数(K=1,\alpha=10)。
4. 对固定C模型的真正外层残差构造逐循环近似区间；9块测试电池只在冻结后读取1—150前缀并预测151—200。
5. 输出默认T80和不同窗口、幂指数、raw/projected设置下的EOL敏感性；EOL不参与选模。
6. 增加策略特征消融、5000次策略分层整块电池bootstrap、完整运行计时、组级唯一性、哈希和CSV回读检查。

## 结果摘要

- C综合分数0.001283，P1为0.001529；C−P1 bootstrap差值95%区间[-0.000382,-0.000043]。
- 固定C的L=150策略等权RMSE为0.000660；完整嵌套选模流程L=150为0.000709。
- 单看L=150时P1为0.000617，略优于C，因此C只能称为多早期长度综合最优。
- 最终9块电池SOH200 raw范围0.962027—0.995778。
- 默认T80情景694.1—2341.6；完整有限敏感性691.6—3653.0，电池11有6/18个设置超过5000。
- 总墙钟922秒；C消融583.91秒为主要瓶颈。

## 文件保护

- 原题、`data`、既有`scripts`、`src`、`tests`和`result/q3/01_smoke_test`共68个受保护文件在正式计算前后哈希一致。
- 没有修改或覆盖原始数据、前两问程序、第三问smoke程序或smoke结果。
- 新结果先在临时目录完成CSV回读、行数组、唯一键、模型冻结和哈希检查，再原子发布；权威目录拒绝覆盖。

## 审查与验证

- 运行前数学/EOL、泄漏攻击、运行与文件管理三位子代理均给出PASS。
- 运行后再次审计：数学结果PASS、40/9隔离与冻结链PASS、manifest和目录完整性PASS。
- `tests/test_q3_models.py`、`tests/test_q3_smoke_outputs.py`、`tests/test_q3_full_protocol.py`均通过。
- 02目录完整性15/15通过，03目录9/9通过，manifest SHA256和CSV行列复算无错误。

## 论文使用边界

- `C_ridge`是预先定义综合目标下的最优模型，不是L=150单点最优。
- 策略信息未显示稳定预测增益，早期动态轨迹是主要来源；策略系数不作因果解释。
- 区间是逐循环CV残差近似点区间，不是联合轨迹95%带或独立测试覆盖率。
- T80没有真实标签，只能报告默认情景、敏感性范围和状态，不能称为已验证寿命。

## 依据与工具

- Skill: `C:/Users/Aupassen/.codex/skills/math-modeling-stage-workflow/SKILL.md`
- Skill: `C:/Users/Aupassen/.codex/skills/project-logbook/SKILL.md`
- Source: `docs/q3_literature_and_model_derivation.md`
- Tool: 三位子代理运行前/后只读复核；Python正式全量程序；PowerShell测试与Git检查；`apply_patch`
