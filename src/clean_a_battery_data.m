function [summaryClean, cycleClean, actions, quality] = clean_a_battery_data(summaryPath, cyclePath)
%CLEAN_A_BATTERY_DATA Apply the frozen Q1 cleaning rules.
% Raw values remain in *_raw columns. Cleaned values use *_clean names.
%
% 本函数是 Q1 数据清洗的唯一权威入口，对电池"摘要表"和"循环表"实施一整套冻结的清洗规则：
%   1) 局部异常检测：对每个电池的容量序列按局部稳健 z 分数判定离群点；
%   2) 线性插值修复：对判定为离群/非正的异常点，用相邻有效循环做线性插值补齐；
%   3) 审计留痕：所有被修复点的位置、原始值、修复值、方法、原因都写入 actions 表；
%   4) 质量统计：汇总清洗前后各项指标写入 quality 表。
% 返回四个变量：
%   summaryClean —— 每块电池一行，含基线容量/SOH 及初始 SOH 基线离群标记等汇总信息；
%   cycleClean   —— 每（电池,循环）一行，原始值保留在 *_raw 列，清洗后值放 *_clean 列；
%   actions      —— 审计表，记录每一处被修改的数据点；
%   quality      —— 关键数量指标（行数、修复点数、离群电池数等），便于论文附表引用。

arguments
    summaryPath (1,1) string   % 摘要表 CSV 路径（每个电池一行）
    cyclePath (1,1) string     % 循环表 CSV 路径（每个（电池,循环）一行）
end

% —— 数据读取与排序 ——
% 以字符串形式读入文本，并关闭列名规范化（保留原始列名，避免 MATLAB 自动改名破坏下游索引）。
summaryRaw = readtable(summaryPath, TextType="string", VariableNamingRule="preserve");
cycleRaw = readtable(cyclePath, TextType="string", VariableNamingRule="preserve");
% 排序：摘要表按电池编号排序；循环表按（电池,循环）双键排序，保证后续按序滑动窗口有效。
summaryRaw = sortrows(summaryRaw, "battery_id");
cycleRaw = sortrows(cycleRaw, ["battery_id","cycle"]);

% —— 数据完整性断言（清洗前提校验）——
% 行数与主键唯一性不满足即抛出错误，防止在数据不完整的情况下继续计算造成虚假结论。
assert(height(summaryRaw) == 49, "Expected 49 battery summary rows.");
assert(height(cycleRaw) == 9350, "Expected 9350 cycle rows.");
assert(numel(unique(summaryRaw.battery_id)) == height(summaryRaw), ...
    "Duplicate battery_id in summary data.");
% 用拼接字符串构造循环表主键，验证（电池,循环）对唯一。
cycleKey = string(cycleRaw.battery_id) + "_" + string(cycleRaw.cycle);
assert(numel(unique(cycleKey)) == height(cycleRaw), ...
    "Duplicate battery-cycle key in cycle data.");

% —— 摘要表初始化：新增清洗派生的汇总列 ——
summaryClean = summaryRaw;
% 记录 C1 是否缺失（缺失值在后续分析中单独处理，不参与插值）。
summaryClean.C1_missing = ismissing(summaryClean.C1);
% 预分配基线容量/SOH 列（初始化为 NaN），第 1~5 循环的稳健基线在下方循环中逐电池填充。
summaryClean.baseline_capacity_cycles_1_5 = nan(height(summaryClean),1);
summaryClean.baseline_soh_cycles_1_5 = nan(height(summaryClean),1);
% 初始 SOH 基线离群标记：先统一置 false，稳健 z 检验后再对超阈电池置 true。
summaryClean.flag_initial_soh_baseline_outlier = false(height(summaryClean),1);

% —— 循环表初始化：原始值全部归档到 *_raw 列 ——
% 新建 cycleClean，只保留原始观测值（容量、SOH、充电时间、内阻、温度等），
% 后续清洗结果写入 *_clean 列，确保原始数据可追溯、可复现。
cycleClean = table();
cycleClean.battery_id = cycleRaw.battery_id;
cycleClean.cycle = cycleRaw.cycle;
cycleClean.policy = cycleRaw.policy;
cycleClean.capacity_raw = cycleRaw.capacity;
cycleClean.SOH_raw = cycleRaw.SOH;
cycleClean.SOH_smooth_official_raw = cycleRaw.SOH_smooth;
cycleClean.chargetime_raw = cycleRaw.chargetime;
cycleClean.IR_raw = cycleRaw.IR;
cycleClean.Tavg_raw = cycleRaw.Tavg;

% —— 按电池编号把摘要信息关联到每个循环行 ——
% ismember 返回：knownBattery（是否匹配到摘要表）与 summaryIndex（对应摘要表的行号）。
[knownBattery, summaryIndex] = ismember(cycleRaw.battery_id, summaryClean.battery_id);
assert(all(knownBattery), "Cycle data contains an unknown battery_id.");
% 从摘要表按行号取回：是否测试集电池、C1/Q1 充电容量定义、初始容量，便于逐行归一化。
cycleClean.prediction_test = logical(summaryClean.prediction_test(summaryIndex));
cycleClean.C1 = summaryClean.C1(summaryIndex);
cycleClean.Q1 = summaryClean.Q1(summaryIndex);
cycleClean.C2 = summaryClean.C2(summaryIndex);
cycleClean.initial_capacity = summaryClean.initial_capacity(summaryIndex);

% —— SOH 公式一致性校验 ——
% SOH 定义为 capacity / initial_capacity，此处验证原始数据是否自洽；
% 若残差超过 1e-10 说明原始 SOH 与容量/初始容量不一致，直接报错而不是静默传播错误数据。
formulaResidual = cycleClean.SOH_raw - cycleClean.capacity_raw ./ cycleClean.initial_capacity;
assert(max(abs(formulaResidual)) < 1e-10, ...
    "Raw SOH is inconsistent with capacity / initial_capacity.");

% —— 局部异常检测列初始化 ——
cycleClean.flag_capacity_local_outlier = false(height(cycleClean),1);
% 稳健 z 分数与相对偏差两列用于记录每个点的离群判定依据（审计可查）。
cycleClean.capacity_local_robust_z = zeros(height(cycleClean),1);
cycleClean.capacity_local_relative_deviation = zeros(height(cycleClean),1);
% 内阻必须为正：IR <= 0 视为无效点，置标记以便后续修复。
cycleClean.flag_ir_nonpositive = cycleClean.IR_raw <= 0;
% 先令清洗值与原始值相同，只有被判定为离群/无效的点才会被后续插值覆盖。
cycleClean.capacity_clean = cycleClean.capacity_raw;
cycleClean.IR_clean = cycleClean.IR_raw;

% —— 逐电池局部稳健离群检测（滑窗）——
% 对每个电池，取当前点前后各 2 个（共至多 4 个）近邻组成局部邻域，
% 用"局部中位数 + 局部 MAD"的稳健尺度替代均值/标准差，避免离群点自身污染判定阈值。
batteryIds = unique(cycleClean.battery_id, "stable");
for b = 1:numel(batteryIds)
    rows = find(cycleClean.battery_id == batteryIds(b));
    capacity = cycleClean.capacity_raw(rows);
    n = numel(rows);
    for j = 1:n
        % 构造邻域位置：j 前后各 2 个循环，用 unique 去掉负向越界与重复。
        neighborPosition = unique([max(1,j-2):j-1, j+1:min(n,j+2)]);
        if numel(neighborPosition) < 2
            continue;   % 邻域不足 2 个点（多出现在序列两端），无法稳健估计，跳过该点
        end
        neighborCapacity = capacity(neighborPosition);
        localMedian = median(neighborCapacity, "omitmissing");          % 邻域中位数（稳健位置估计）
        localMad = median(abs(neighborCapacity-localMedian), "omitmissing"); % 邻域绝对中位差（稳健离散度）
        % 1.4826 为 MAD 到标准差的换算系数；取 max(…,1e-6) 防止除零。
        robustScale = max(1.4826*localMad, 1e-6);
        % 稳健 z 分数衡量当前点偏离邻域中位数几个稳健标准差。
        robustZ = abs(capacity(j)-localMedian)/robustScale;
        % 相对偏差衡量当前点与邻域中位数的相对差距（与规模无关）。
        relativeDeviation = abs(capacity(j)/localMedian-1);
        globalRow = rows(j);   % 该点在 cycleClean 中的全局行号
        % 记录判定依据（供审计/论文使用）。
        cycleClean.capacity_local_robust_z(globalRow) = robustZ;
        cycleClean.capacity_local_relative_deviation(globalRow) = relativeDeviation;
        % 判定规则：稳健 z > 8 且相对偏差 > 2% 同时成立才认定为离群，
        % 双条件设计可显著降低把正常波动误判为异常的风险。
        cycleClean.flag_capacity_local_outlier(globalRow) = ...
            robustZ > 8 && relativeDeviation > 0.02;
    end
end

% —— 修复容量离群点：相邻有效循环线性插值 ——
% 被标记的容量异常点用其所在电池前后相邻循环的"清洗后"容量做线性插值。
% 要求离群点不在序列边界（边界上无法双侧插值，故先断言，异常时应回溯数据而非强行修复）。
capacityFlagRows = find(cycleClean.flag_capacity_local_outlier);
for k = 1:numel(capacityFlagRows)
    row = capacityFlagRows(k);
    sameBattery = find(cycleClean.battery_id == cycleClean.battery_id(row));
    position = find(sameBattery == row, 1);   % 当前点在所属电池序列中的序号
    assert(position > 1 && position < numel(sameBattery), ...
        "Cannot interpolate a capacity anomaly at the series boundary.");
    previousRow = sameBattery(position-1);    % 前一循环的全局行号
    nextRow = sameBattery(position+1);        % 后一循环的全局行号
    % interp1 以循环号为自变量，对前后两点的容量做线性插值得到修复值。
    cycleClean.capacity_clean(row) = interp1( ...
        [cycleClean.cycle(previousRow), cycleClean.cycle(nextRow)], ...
        [cycleClean.capacity_clean(previousRow), cycleClean.capacity_clean(nextRow)], ...
        cycleClean.cycle(row), "linear");
end

% —— 修复非正内阻点：按有效点线性插值 ——
irFlagRows = find(cycleClean.flag_ir_nonpositive);
for k = 1:numel(irFlagRows)
    row = irFlagRows(k);
    sameBattery = find(cycleClean.battery_id == cycleClean.battery_id(row));
    position = find(sameBattery == row, 1);   % 当前点在所属电池序列中的序号
    % 只保留该电池内阻为正的循环作为插值节点，排除无效点本身。
    validRows = sameBattery(cycleClean.IR_raw(sameBattery) > 0);
    % 以循环号为自变量，在有效内阻点上线性插值出该循环的修复内阻。
    cycleClean.IR_clean(row) = interp1( ...
        cycleClean.cycle(validRows), cycleClean.IR_raw(validRows), ...
        cycleClean.cycle(row), "linear");
end

% —— 清洗后派生指标初始化 ——
% SOH_clean 由清洗后的容量重新计算，保证与容量修复保持一致（SOH=容量/初始容量）。
cycleClean.SOH_clean = cycleClean.capacity_clean ./ cycleClean.initial_capacity;
% SOH_relative_clean：相对首段基线（第 1~5 循环中位数）的 SOH，用于后续衰减分析。
cycleClean.SOH_relative_clean = nan(height(cycleClean),1);
% 预分配三种窗口长度的 rlowess 稳健局部加权回归趋势列（7/11/15），用于对比不同平滑强度。
cycleClean.SOH_trend_rlowess_7 = nan(height(cycleClean),1);
cycleClean.SOH_trend_rlowess_11 = nan(height(cycleClean),1);
cycleClean.SOH_trend_rlowess_15 = nan(height(cycleClean),1);

% —— 逐电池计算基线（第 1~5 循环）与 SOH 趋势 ——
for b = 1:numel(batteryIds)
    batteryId = batteryIds(b);
    rows = find(cycleClean.battery_id == batteryId);
    firstFive = rows(cycleClean.cycle(rows) <= 5);   % 该电池前 5 个循环的行号
    % 用中位数作为基线（稳健，抗前段个别离群点影响）。
    baselineCapacity = median(cycleClean.capacity_clean(firstFive), "omitmissing");
    baselineSoh = median(cycleClean.SOH_clean(firstFive), "omitmissing");
    % 把基线写回摘要表对应电池行。
    summaryRow = find(summaryClean.battery_id == batteryId, 1);
    summaryClean.baseline_capacity_cycles_1_5(summaryRow) = baselineCapacity;
    summaryClean.baseline_soh_cycles_1_5(summaryRow) = baselineSoh;
    % 相对 SOH = 当前容量 / 首段基线容量，逐行填充。
    cycleClean.SOH_relative_clean(rows) = cycleClean.capacity_clean(rows)/baselineCapacity;
    % rlowess：稳健局部加权回归平滑，窗口越大曲线越光滑（7 最灵敏、15 最平滑）。
    cycleClean.SOH_trend_rlowess_7(rows) = smoothdata(cycleClean.SOH_clean(rows), "rlowess", 7);
    cycleClean.SOH_trend_rlowess_11(rows) = smoothdata(cycleClean.SOH_clean(rows), "rlowess", 11);
    cycleClean.SOH_trend_rlowess_15(rows) = smoothdata(cycleClean.SOH_clean(rows), "rlowess", 15);
end

% —— 初始 SOH 基线的跨电池离群检测 ——
% 以所有电池基线 SOH 的中位数和 MAD 构造稳健尺度，检测个别电池初始状态异常。
baselineMedian = median(summaryClean.baseline_soh_cycles_1_5);
baselineMad = median(abs(summaryClean.baseline_soh_cycles_1_5-baselineMedian));
baselineScale = max(1.4826*baselineMad, 1e-6);   % MAD 换算为标准差尺度，并防止除零
% 稳健 z 分数：衡量每块电池基线 SOH 偏离总体中位数的程度。
summaryClean.initial_soh_baseline_robust_z = ...
    (summaryClean.baseline_soh_cycles_1_5-baselineMedian)/baselineScale;
% 与容量离群同样的阈值：|z|>8 视为初始 SOH 基线离群（极保守，避免误伤）。
summaryClean.flag_initial_soh_baseline_outlier = ...
    abs(summaryClean.initial_soh_baseline_robust_z) > 8;

% —— 汇总"是否经过修复"标记 ——
% 任一指标（容量局部离群或内阻非正）被修复即置 true，供下游按需剔除/标记样本。
cycleClean.flag_any_repair = cycleClean.flag_capacity_local_outlier | cycleClean.flag_ir_nonpositive;

% —— 审计留痕表：记录每一处数据修复 ——
% 将容量离群点与内阻非正点两类修复合并成一份审计表，
% 记录电池、循环、变量名、原始值、修复值、修复方法与原因，实现"每个改动都可回溯"。
actions = table();
actions.battery_id = [cycleClean.battery_id(capacityFlagRows); cycleClean.battery_id(irFlagRows)];
actions.cycle = [cycleClean.cycle(capacityFlagRows); cycleClean.cycle(irFlagRows)];
actions.variable = [repmat("capacity",numel(capacityFlagRows),1); repmat("IR",numel(irFlagRows),1)];
actions.raw_value = [cycleClean.capacity_raw(capacityFlagRows); cycleClean.IR_raw(irFlagRows)];
actions.clean_value = [cycleClean.capacity_clean(capacityFlagRows); cycleClean.IR_clean(irFlagRows)];
actions.method = [repmat("linear interpolation between adjacent valid cycles",numel(capacityFlagRows),1); ...
    repmat("linear interpolation after nonpositive value marked invalid",numel(irFlagRows),1)];
actions.reason = [repmat("local robust z > 8 and relative deviation > 2%",numel(capacityFlagRows),1); ...
    repmat("battery internal resistance must be positive",numel(irFlagRows),1)];

% —— 质量统计表：清洗前后的关键数量 ——
% metric 为指标名、value 为对应数值，逐项汇总：
% 行数、容量/内阻修复点数、初始 SOH 基线离群电池数、C1 缺失数、测试/训练电池数、
% 原始 SOH 公式最大残差、清洗后仍非正的内阻点数（应为 0）。
quality = table( ...
    ["summary_rows";"cycle_rows";"capacity_points_repaired";"ir_points_repaired"; ...
     "baseline_outlier_batteries";"C1_missing_batteries";"test_batteries"; ...
     "training_batteries";"max_raw_soh_formula_residual";"remaining_nonpositive_clean_ir"], ...
    [height(summaryClean);height(cycleClean);numel(capacityFlagRows);numel(irFlagRows); ...
     sum(summaryClean.flag_initial_soh_baseline_outlier);sum(summaryClean.C1_missing); ...
     sum(summaryClean.prediction_test==1);sum(summaryClean.prediction_test==0); ...
     max(abs(formulaResidual));sum(cycleClean.IR_clean<=0)], ...
    'VariableNames', {'metric','value'});
end
