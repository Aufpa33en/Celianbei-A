%RUN_A_DATA_CLEANING Execute the frozen Q1 cleaning rules.

scriptPath = mfilename('fullpath');
projectRoot = string(fileparts(fileparts(fileparts(scriptPath))));
addpath(fullfile(projectRoot,"src"));

summaryPath = fullfile(projectRoot,"data","raw","battery_summary.csv");
cyclePath = fullfile(projectRoot,"data","raw","cycle_train.csv");
processedDir = fullfile(projectRoot,"data","processed","q1_cleaned");
summaryDir = fullfile(projectRoot,"outputs","summary","q1_cleaning");
figureDir = fullfile(projectRoot,"figures","cleaning");
if ~isfolder(processedDir), mkdir(processedDir); end
if ~isfolder(summaryDir), mkdir(summaryDir); end
if ~isfolder(figureDir), mkdir(figureDir); end

[summaryClean,cycleClean,actions,quality] = clean_a_battery_data(summaryPath,cyclePath);
writetable(summaryClean,fullfile(processedDir,"battery_summary_clean.csv"));
writetable(cycleClean,fullfile(processedDir,"cycle_train_clean.csv"));
writetable(actions,fullfile(summaryDir,"cleaning_actions.csv"));
writetable(quality,fullfile(summaryDir,"cleaning_quality_summary.csv"));
plot_a_cleaning_comparison(summaryClean,cycleClean,actions,figureDir);

fprintf('Q1 cleaning completed.\n');
fprintf('  Clean data: %s\n',processedDir);
fprintf('  Audit summaries: %s\n',summaryDir);
fprintf('  Comparison figure: %s\n',figureDir);
disp(quality);

