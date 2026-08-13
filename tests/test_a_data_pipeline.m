%TEST_A_DATA_PIPELINE Dataset-specific integrity tests for the initial A pipeline.

scriptPath = mfilename('fullpath');
projectRoot = string(fileparts(fileparts(scriptPath)));
summaryPath = fullfile(projectRoot, "data", "processed", "battery_summary_clean.csv");
cyclePath = fullfile(projectRoot, "data", "processed", "cycle_train_clean.csv");

assert(isfile(summaryPath), "Missing cleaned battery summary.");
assert(isfile(cyclePath), "Missing cleaned cycle data.");

summaryData = readtable(summaryPath, TextType="string", VariableNamingRule="preserve");
cycleData = readtable(cyclePath, TextType="string", VariableNamingRule="preserve");

assert(height(summaryData) == 49, "Expected 49 batteries.");
assert(height(cycleData) == 9350, "Expected 9350 cycle records.");
assert(numel(unique(summaryData.battery_id)) == 49, "battery_id must be unique in summary.");
cycleKey = string(cycleData.battery_id) + "_" + string(cycleData.cycle);
assert(numel(unique(cycleKey)) == height(cycleData), "Duplicate battery-cycle keys found.");
assert(sum(logical(summaryData.prediction_test)) == 9, "Expected 9 prediction-test batteries.");
assert(~any(ismissing(cycleData.battery_id) | ismissing(cycleData.cycle)), ...
    "Core cycle keys must not be missing.");
assert(max(abs(cycleData.SOH_residual)) < 1e-6, ...
    "Provided SOH is inconsistent with capacity / initial_capacity.");

testIds = summaryData.battery_id(logical(summaryData.prediction_test));
trainIds = summaryData.battery_id(~logical(summaryData.prediction_test));
for i = 1:numel(testIds)
    assert(max(cycleData.cycle(cycleData.battery_id == testIds(i))) == 150, ...
        "Every prediction-test battery should end at cycle 150.");
end
for i = 1:numel(trainIds)
    assert(max(cycleData.cycle(cycleData.battery_id == trainIds(i))) == 200, ...
        "Every training battery should end at cycle 200.");
end

fprintf('All A-problem pipeline tests passed.\n');

