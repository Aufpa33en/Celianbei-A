%TEST_Q1_CLEANING Verify the frozen Q1 cleaning output.

scriptPath = mfilename('fullpath');
projectRoot = string(fileparts(fileparts(scriptPath)));
rawSummary = readtable(fullfile(projectRoot,"data","raw","battery_summary.csv"),VariableNamingRule="preserve");
rawCycle = readtable(fullfile(projectRoot,"data","raw","cycle_train.csv"),VariableNamingRule="preserve");
cleanSummary = readtable(fullfile(projectRoot,"data","processed","q1_cleaned","battery_summary_clean.csv"),VariableNamingRule="preserve");
cleanCycle = readtable(fullfile(projectRoot,"data","processed","q1_cleaned","cycle_train_clean.csv"),VariableNamingRule="preserve");
actions = readtable(fullfile(projectRoot,"outputs","summary","q1_cleaning","cleaning_actions.csv"),TextType="string",VariableNamingRule="preserve");

assert(height(cleanSummary)==49 && height(cleanCycle)==9350,"Output row counts changed.");
assert(isequal(rawCycle.capacity,cleanCycle.capacity_raw),"Raw capacity was not preserved.");
assert(max(abs(rawCycle.SOH-cleanCycle.SOH_raw))<1e-14, ...
    "Raw SOH changed beyond CSV floating-point serialization tolerance.");
assert(isequal(rawCycle.IR,cleanCycle.IR_raw),"Raw IR was not preserved.");
assert(sum(cleanCycle.flag_capacity_local_outlier)==1,"Expected one capacity anomaly.");
assert(sum(cleanCycle.flag_ir_nonpositive)==2,"Expected two nonpositive IR values.");
assert(height(actions)==3,"Expected exactly three repaired cells.");

row12=find(cleanCycle.battery_id==1 & cleanCycle.cycle==12);
row11=find(cleanCycle.battery_id==1 & cleanCycle.cycle==11);
row13=find(cleanCycle.battery_id==1 & cleanCycle.cycle==13);
expectedCapacity=(cleanCycle.capacity_raw(row11)+cleanCycle.capacity_raw(row13))/2;
assert(abs(cleanCycle.capacity_clean(row12)-expectedCapacity)<1e-12,"Capacity interpolation mismatch.");
assert(max(abs(cleanCycle.SOH_clean-cleanCycle.capacity_clean./cleanCycle.initial_capacity))<1e-12, ...
    "Clean SOH formula mismatch.");
assert(all(cleanCycle.IR_clean>0),"Clean IR must be positive.");
assert(sum(cleanSummary.C1_missing)==3,"C1 missing values must remain explicit.");
assert(any(cleanSummary.battery_id==41),"Battery 41 must be retained.");
assert(sum(cleanSummary.flag_initial_soh_baseline_outlier)==1, ...
    "Expected one initial baseline outlier battery.");
for batteryId = cleanSummary.battery_id'
    rows = cleanCycle.battery_id==batteryId & cleanCycle.cycle<=5;
    summaryRow = cleanSummary.battery_id==batteryId;
    expectedBaseline = median(cleanCycle.SOH_clean(rows));
    assert(abs(cleanSummary.baseline_soh_cycles_1_5(summaryRow)-expectedBaseline)<1e-12, ...
        "Stored SOH baseline must be the first-five-cycle median.");
end
assert(max(abs(cleanCycle.SOH_relative_clean - ...
    cleanCycle.SOH_clean ./ cleanSummary.baseline_soh_cycles_1_5( ...
    arrayfun(@(id)find(cleanSummary.battery_id==id,1),cleanCycle.battery_id)))) < 1e-12, ...
    "Relative SOH must use the stored first-five-cycle median baseline.");
assert(all(~ismissing(cleanCycle.SOH_trend_rlowess_11)),"Clean trend contains missing values.");
assert(sum(cleanSummary.prediction_test)==sum(rawSummary.prediction_test),"Test flags changed.");

fprintf('All Q1 cleaning tests passed.\n');
