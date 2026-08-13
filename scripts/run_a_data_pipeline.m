%RUN_A_DATA_PIPELINE Clean A-problem data and generate exploratory figures.

scriptPath = mfilename('fullpath');
projectRoot = string(fileparts(fileparts(scriptPath)));
addpath(fullfile(projectRoot, "configs"));
addpath(fullfile(projectRoot, "src"));

cfg = a_data_pipeline_config(projectRoot);
requiredDirs = [cfg.processedDir, cfg.outputSummaryDir, cfg.figureDir];
for i = 1:numel(requiredDirs)
    if ~isfolder(requiredDirs(i))
        mkdir(requiredDirs(i));
    end
end

[summaryClean, cycleClean, batteryFeatures, strategySummary, qualitySummary] = ...
    clean_battery_data(cfg);

writetable(summaryClean, cfg.summaryOutput);
writetable(cycleClean, cfg.cycleOutput);
writetable(batteryFeatures, fullfile(cfg.outputSummaryDir, "battery_level_features.csv"));
writetable(strategySummary, fullfile(cfg.outputSummaryDir, "strategy_summary.csv"));
writetable(qualitySummary, fullfile(cfg.outputSummaryDir, "data_quality_summary.csv"));

generate_exploratory_figures(summaryClean, cycleClean, batteryFeatures, strategySummary, cfg);

fprintf('A-problem data pipeline completed.\n');
fprintf('  Clean summary rows: %d\n', height(summaryClean));
fprintf('  Clean cycle rows: %d\n', height(cycleClean));
fprintf('  Batteries: %d; policies: %d\n', height(summaryClean), height(strategySummary));
fprintf('  Processed data: %s\n', cfg.processedDir);
fprintf('  Figures: %s\n', cfg.figureDir);

