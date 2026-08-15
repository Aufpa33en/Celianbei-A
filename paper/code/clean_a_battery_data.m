function [summaryClean, cycleClean, actions, quality] = clean_a_battery_data(summaryPath, cyclePath)
%CLEAN_A_BATTERY_DATA Apply the frozen Q1 cleaning rules.
% Raw values remain in *_raw columns. Cleaned values use *_clean names.

arguments
    summaryPath (1,1) string
    cyclePath (1,1) string
end

summaryRaw = readtable(summaryPath, TextType="string", VariableNamingRule="preserve");
cycleRaw = readtable(cyclePath, TextType="string", VariableNamingRule="preserve");
summaryRaw = sortrows(summaryRaw, "battery_id");
cycleRaw = sortrows(cycleRaw, ["battery_id","cycle"]);

assert(height(summaryRaw) == 49, "Expected 49 battery summary rows.");
assert(height(cycleRaw) == 9350, "Expected 9350 cycle rows.");
assert(numel(unique(summaryRaw.battery_id)) == height(summaryRaw), ...
    "Duplicate battery_id in summary data.");
cycleKey = string(cycleRaw.battery_id) + "_" + string(cycleRaw.cycle);
assert(numel(unique(cycleKey)) == height(cycleRaw), ...
    "Duplicate battery-cycle key in cycle data.");

summaryClean = summaryRaw;
summaryClean.C1_missing = ismissing(summaryClean.C1);
summaryClean.baseline_capacity_cycles_1_5 = nan(height(summaryClean),1);
summaryClean.baseline_soh_cycles_1_5 = nan(height(summaryClean),1);
summaryClean.flag_initial_soh_baseline_outlier = false(height(summaryClean),1);

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

[knownBattery, summaryIndex] = ismember(cycleRaw.battery_id, summaryClean.battery_id);
assert(all(knownBattery), "Cycle data contains an unknown battery_id.");
cycleClean.prediction_test = logical(summaryClean.prediction_test(summaryIndex));
cycleClean.C1 = summaryClean.C1(summaryIndex);
cycleClean.Q1 = summaryClean.Q1(summaryIndex);
cycleClean.C2 = summaryClean.C2(summaryIndex);
cycleClean.initial_capacity = summaryClean.initial_capacity(summaryIndex);

formulaResidual = cycleClean.SOH_raw - cycleClean.capacity_raw ./ cycleClean.initial_capacity;
assert(max(abs(formulaResidual)) < 1e-10, ...
    "Raw SOH is inconsistent with capacity / initial_capacity.");

cycleClean.flag_capacity_local_outlier = false(height(cycleClean),1);
cycleClean.capacity_local_robust_z = zeros(height(cycleClean),1);
cycleClean.capacity_local_relative_deviation = zeros(height(cycleClean),1);
cycleClean.flag_ir_nonpositive = cycleClean.IR_raw <= 0;
cycleClean.capacity_clean = cycleClean.capacity_raw;
cycleClean.IR_clean = cycleClean.IR_raw;

batteryIds = unique(cycleClean.battery_id, "stable");
for b = 1:numel(batteryIds)
    rows = find(cycleClean.battery_id == batteryIds(b));
    capacity = cycleClean.capacity_raw(rows);
    n = numel(rows);
    for j = 1:n
        neighborPosition = unique([max(1,j-2):j-1, j+1:min(n,j+2)]);
        if numel(neighborPosition) < 2
            continue;
        end
        neighborCapacity = capacity(neighborPosition);
        localMedian = median(neighborCapacity, "omitmissing");
        localMad = median(abs(neighborCapacity-localMedian), "omitmissing");
        robustScale = max(1.4826*localMad, 1e-6);
        robustZ = abs(capacity(j)-localMedian)/robustScale;
        relativeDeviation = abs(capacity(j)/localMedian-1);
        globalRow = rows(j);
        cycleClean.capacity_local_robust_z(globalRow) = robustZ;
        cycleClean.capacity_local_relative_deviation(globalRow) = relativeDeviation;
        cycleClean.flag_capacity_local_outlier(globalRow) = ...
            robustZ > 8 && relativeDeviation > 0.02;
    end
end

capacityFlagRows = find(cycleClean.flag_capacity_local_outlier);
for k = 1:numel(capacityFlagRows)
    row = capacityFlagRows(k);
    sameBattery = find(cycleClean.battery_id == cycleClean.battery_id(row));
    position = find(sameBattery == row, 1);
    assert(position > 1 && position < numel(sameBattery), ...
        "Cannot interpolate a capacity anomaly at the series boundary.");
    previousRow = sameBattery(position-1);
    nextRow = sameBattery(position+1);
    cycleClean.capacity_clean(row) = interp1( ...
        [cycleClean.cycle(previousRow), cycleClean.cycle(nextRow)], ...
        [cycleClean.capacity_clean(previousRow), cycleClean.capacity_clean(nextRow)], ...
        cycleClean.cycle(row), "linear");
end

irFlagRows = find(cycleClean.flag_ir_nonpositive);
for k = 1:numel(irFlagRows)
    row = irFlagRows(k);
    sameBattery = find(cycleClean.battery_id == cycleClean.battery_id(row));
    position = find(sameBattery == row, 1);
    validRows = sameBattery(cycleClean.IR_raw(sameBattery) > 0);
    cycleClean.IR_clean(row) = interp1( ...
        cycleClean.cycle(validRows), cycleClean.IR_raw(validRows), ...
        cycleClean.cycle(row), "linear");
end

cycleClean.SOH_clean = cycleClean.capacity_clean ./ cycleClean.initial_capacity;
cycleClean.SOH_relative_clean = nan(height(cycleClean),1);
cycleClean.SOH_trend_rlowess_7 = nan(height(cycleClean),1);
cycleClean.SOH_trend_rlowess_11 = nan(height(cycleClean),1);
cycleClean.SOH_trend_rlowess_15 = nan(height(cycleClean),1);

for b = 1:numel(batteryIds)
    batteryId = batteryIds(b);
    rows = find(cycleClean.battery_id == batteryId);
    firstFive = rows(cycleClean.cycle(rows) <= 5);
    baselineCapacity = median(cycleClean.capacity_clean(firstFive), "omitmissing");
    baselineSoh = median(cycleClean.SOH_clean(firstFive), "omitmissing");
    summaryRow = find(summaryClean.battery_id == batteryId, 1);
    summaryClean.baseline_capacity_cycles_1_5(summaryRow) = baselineCapacity;
    summaryClean.baseline_soh_cycles_1_5(summaryRow) = baselineSoh;
    cycleClean.SOH_relative_clean(rows) = cycleClean.capacity_clean(rows)/baselineCapacity;
    cycleClean.SOH_trend_rlowess_7(rows) = smoothdata(cycleClean.SOH_clean(rows), "rlowess", 7);
    cycleClean.SOH_trend_rlowess_11(rows) = smoothdata(cycleClean.SOH_clean(rows), "rlowess", 11);
    cycleClean.SOH_trend_rlowess_15(rows) = smoothdata(cycleClean.SOH_clean(rows), "rlowess", 15);
end

baselineMedian = median(summaryClean.baseline_soh_cycles_1_5);
baselineMad = median(abs(summaryClean.baseline_soh_cycles_1_5-baselineMedian));
baselineScale = max(1.4826*baselineMad, 1e-6);
summaryClean.initial_soh_baseline_robust_z = ...
    (summaryClean.baseline_soh_cycles_1_5-baselineMedian)/baselineScale;
summaryClean.flag_initial_soh_baseline_outlier = ...
    abs(summaryClean.initial_soh_baseline_robust_z) > 8;

cycleClean.flag_any_repair = cycleClean.flag_capacity_local_outlier | cycleClean.flag_ir_nonpositive;

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
