function cfg = a_data_pipeline_config(projectRoot)
%A_DATA_PIPELINE_CONFIG Paths and fixed parameters for the A-problem pipeline.

arguments
    projectRoot (1,1) string
end

cfg = struct();
cfg.projectRoot = projectRoot;
cfg.summaryInput = fullfile(projectRoot, "data", "raw", "battery_summary.csv");
cfg.cycleInput = fullfile(projectRoot, "data", "raw", "cycle_train.csv");
cfg.processedDir = fullfile(projectRoot, "data", "processed");
cfg.summaryOutput = fullfile(cfg.processedDir, "battery_summary_clean.csv");
cfg.cycleOutput = fullfile(cfg.processedDir, "cycle_train_clean.csv");
cfg.outputSummaryDir = fullfile(projectRoot, "outputs", "summary");
cfg.figureDir = fullfile(projectRoot, "figures");
cfg.earlyCycleLimit = 150;
cfg.expectedTrainCycles = 200;
cfg.expectedTestCycles = 150;
cfg.sohLowerFlag = 0.75;
cfg.sohUpperFlag = 1.15;
cfg.figureResolution = 180;
cfg.randomSeed = 20260813;
end

