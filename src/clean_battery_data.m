function [summaryClean, cycleClean, batteryFeatures, strategySummary, qualitySummary] = clean_battery_data(cfg)
%CLEAN_BATTERY_DATA Validate, clean, enrich, and summarize the A-problem data.
% Exact duplicate rows are removed. Original measurements are retained;
% suspicious values are flagged instead of silently discarded or clipped.

arguments
    cfg (1,1) struct
end

summaryRaw = readtable(cfg.summaryInput, TextType="string", VariableNamingRule="preserve");
cycleRaw = readtable(cfg.cycleInput, TextType="string", VariableNamingRule="preserve");

summaryRequired = ["battery_id","global_id","dataset_id","local_id","policy", ...
    "C1","Q1","C2","initial_capacity","mean_chargetime","mean_IR","mean_Tavg","prediction_test"];
cycleRequired = ["battery_id","cycle","capacity","SOH","SOH_smooth", ...
    "chargetime","IR","Tavg","policy"];
assert(all(ismember(summaryRequired, string(summaryRaw.Properties.VariableNames))), ...
    "battery_summary.csv is missing required variables.");
assert(all(ismember(cycleRequired, string(cycleRaw.Properties.VariableNames))), ...
    "cycle_train.csv is missing required variables.");

summaryRowsRaw = height(summaryRaw);
cycleRowsRaw = height(cycleRaw);
summaryExactDuplicates = summaryRowsRaw - height(unique(summaryRaw, "rows", "stable"));
cycleExactDuplicates = cycleRowsRaw - height(unique(cycleRaw, "rows", "stable"));

summaryClean = unique(summaryRaw, "rows", "stable");
cycleClean = unique(cycleRaw, "rows", "stable");
summaryClean.policy = strtrim(summaryClean.policy);
cycleClean.policy = strtrim(cycleClean.policy);

assert(~any(ismissing(summaryClean.battery_id)), "battery_summary contains missing battery_id.");
assert(~any(ismissing(cycleClean.battery_id) | ismissing(cycleClean.cycle)), ...
    "cycle_train contains missing battery_id or cycle.");
assert(numel(unique(summaryClean.battery_id)) == height(summaryClean), ...
    "battery_summary contains duplicate battery_id values.");

cycleKey = string(cycleClean.battery_id) + "_" + string(cycleClean.cycle);
assert(numel(unique(cycleKey)) == height(cycleClean), ...
    "cycle_train contains duplicate battery_id-cycle keys.");
assert(all(ismember(cycleClean.battery_id, summaryClean.battery_id)), ...
    "cycle_train contains battery IDs absent from battery_summary.");

summaryClean = sortrows(summaryClean, "battery_id");
cycleClean = sortrows(cycleClean, ["battery_id","cycle"]);

summaryPolicy = containers.Map(cellstr(string(summaryClean.battery_id)), cellstr(summaryClean.policy));
canonicalPolicy = strings(height(cycleClean), 1);
for row = 1:height(cycleClean)
    canonicalPolicy(row) = string(summaryPolicy(char(string(cycleClean.battery_id(row)))));
end
policyMismatch = ~ismissing(cycleClean.policy) & cycleClean.policy ~= canonicalPolicy;
missingPolicy = ismissing(cycleClean.policy) | strlength(cycleClean.policy) == 0;
cycleClean.policy(missingPolicy) = canonicalPolicy(missingPolicy);

[isKnownBattery, summaryIndex] = ismember(cycleClean.battery_id, summaryClean.battery_id);
assert(all(isKnownBattery), "Failed to map cycle rows to battery summary.");
cycleClean.prediction_test = logical(summaryClean.prediction_test(summaryIndex));
cycleClean.C1 = summaryClean.C1(summaryIndex);
cycleClean.Q1 = summaryClean.Q1(summaryIndex);
cycleClean.C2 = summaryClean.C2(summaryIndex);
cycleClean.initial_capacity = summaryClean.initial_capacity(summaryIndex);
cycleClean.SOH_recomputed = cycleClean.capacity ./ cycleClean.initial_capacity;
cycleClean.SOH_residual = cycleClean.SOH - cycleClean.SOH_recomputed;
cycleClean.flag_nonpositive_measurement = cycleClean.capacity <= 0 | cycleClean.chargetime <= 0 | ...
    cycleClean.IR <= 0 | cycleClean.Tavg <= 0;
cycleClean.flag_soh_outside_expected = cycleClean.SOH_smooth < cfg.sohLowerFlag | ...
    cycleClean.SOH_smooth > cfg.sohUpperFlag;

summaryClean.prediction_test = logical(summaryClean.prediction_test);
summaryClean.flag_invalid_strategy = summaryClean.C1 <= 0 | summaryClean.C2 <= 0 | ...
    summaryClean.Q1 <= 0 | summaryClean.Q1 > 80;

batteryIds = summaryClean.battery_id;
nBatteries = height(summaryClean);
batteryFeatures = table('Size', [nBatteries 16], ...
    'VariableTypes', [repmat("double",1,13), "string", "logical", "double"], ...
    'VariableNames', ["battery_id","n_cycles","min_cycle","max_cycle", ...
    "initial_soh_smooth","final_soh_smooth","delta_soh_smooth", ...
    "early_soh_slope","early_ir_slope","mean_chargetime_observed", ...
    "mean_ir_observed","mean_temperature_observed","soh_residual_rmse", ...
    "policy","prediction_test","final_observed_cycle"]);

for i = 1:nBatteries
    batteryId = batteryIds(i);
    rows = cycleClean.battery_id == batteryId;
    one = cycleClean(rows,:);
    early = one.cycle <= cfg.earlyCycleLimit;
    batteryFeatures.battery_id(i) = batteryId;
    batteryFeatures.n_cycles(i) = height(one);
    batteryFeatures.min_cycle(i) = min(one.cycle);
    batteryFeatures.max_cycle(i) = max(one.cycle);
    batteryFeatures.initial_soh_smooth(i) = one.SOH_smooth(1);
    batteryFeatures.final_soh_smooth(i) = one.SOH_smooth(end);
    batteryFeatures.delta_soh_smooth(i) = one.SOH_smooth(end) - one.SOH_smooth(1);
    pSoh = polyfit(one.cycle(early), one.SOH_smooth(early), 1);
    pIr = polyfit(one.cycle(early), one.IR(early), 1);
    batteryFeatures.early_soh_slope(i) = pSoh(1);
    batteryFeatures.early_ir_slope(i) = pIr(1);
    batteryFeatures.mean_chargetime_observed(i) = mean(one.chargetime, "omitmissing");
    batteryFeatures.mean_ir_observed(i) = mean(one.IR, "omitmissing");
    batteryFeatures.mean_temperature_observed(i) = mean(one.Tavg, "omitmissing");
    batteryFeatures.soh_residual_rmse(i) = sqrt(mean(one.SOH_residual.^2, "omitmissing"));
    batteryFeatures.policy(i) = summaryClean.policy(i);
    batteryFeatures.prediction_test(i) = summaryClean.prediction_test(i);
    batteryFeatures.final_observed_cycle(i) = one.cycle(end);
end

policies = unique(summaryClean.policy, "stable");
nPolicies = numel(policies);
strategySummary = table('Size', [nPolicies 9], ...
    'VariableTypes', ["string", repmat("double",1,8)], ...
    'VariableNames', ["policy","n_batteries","C1","Q1","C2", ...
    "mean_early_soh_slope","std_early_soh_slope","mean_final_observed_soh","mean_chargetime"]);
for i = 1:nPolicies
    rowsSummary = summaryClean.policy == policies(i);
    rowsFeature = batteryFeatures.policy == policies(i);
    strategySummary.policy(i) = policies(i);
    strategySummary.n_batteries(i) = sum(rowsSummary);
    strategySummary.C1(i) = mean(summaryClean.C1(rowsSummary));
    strategySummary.Q1(i) = mean(summaryClean.Q1(rowsSummary));
    strategySummary.C2(i) = mean(summaryClean.C2(rowsSummary));
    strategySummary.mean_early_soh_slope(i) = mean(batteryFeatures.early_soh_slope(rowsFeature));
    strategySummary.std_early_soh_slope(i) = std(batteryFeatures.early_soh_slope(rowsFeature));
    strategySummary.mean_final_observed_soh(i) = mean(batteryFeatures.final_soh_smooth(rowsFeature));
    strategySummary.mean_chargetime(i) = mean(summaryClean.mean_chargetime(rowsSummary));
end
strategySummary = sortrows(strategySummary, "mean_early_soh_slope", "descend");

summaryMissing = sum(ismissing(summaryClean), "all");
cycleMissing = sum(ismissing(cycleClean(:, cycleRequired)), "all");
qualitySummary = table( ...
    ["summary_rows_raw";"summary_rows_clean";"cycle_rows_raw";"cycle_rows_clean"; ...
     "summary_exact_duplicates_removed";"cycle_exact_duplicates_removed"; ...
     "summary_missing_cells";"cycle_missing_cells_core";"policy_mismatch_rows"; ...
     "nonpositive_measurement_rows";"soh_flagged_rows";"train_batteries"; ...
     "test_batteries";"unique_policies";"max_abs_soh_residual"], ...
    [summaryRowsRaw;height(summaryClean);cycleRowsRaw;height(cycleClean); ...
     summaryExactDuplicates;cycleExactDuplicates;summaryMissing;cycleMissing;sum(policyMismatch); ...
     sum(cycleClean.flag_nonpositive_measurement);sum(cycleClean.flag_soh_outside_expected); ...
     sum(~summaryClean.prediction_test);sum(summaryClean.prediction_test);nPolicies; ...
     max(abs(cycleClean.SOH_residual))], ...
    'VariableNames', {"metric","value"});
end

