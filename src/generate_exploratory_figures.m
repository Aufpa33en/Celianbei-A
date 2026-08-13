function generate_exploratory_figures(summaryData, cycleData, batteryFeatures, strategySummary, cfg)
%GENERATE_EXPLORATORY_FIGURES Create MATLAB figures for initial inspection.

arguments
    summaryData table
    cycleData table
    batteryFeatures table
    strategySummary table
    cfg (1,1) struct
end

rng(cfg.randomSeed, "twister");
if ~isfolder(cfg.figureDir)
    mkdir(cfg.figureDir);
end

baseColors = lines(max(9, height(strategySummary)));

% Figure 1: all battery SOH trajectories, train/test distinguished.
fig = newFigure();
hold on;
for i = 1:height(summaryData)
    rows = cycleData.battery_id == summaryData.battery_id(i);
    if summaryData.prediction_test(i)
        plot(cycleData.cycle(rows), cycleData.SOH_smooth(rows), '-', ...
            'Color', [0.88 0.28 0.28], 'LineWidth', 1.25);
    else
        plot(cycleData.cycle(rows), cycleData.SOH_smooth(rows), '-', ...
            'Color', [0.68 0.78 0.90], 'LineWidth', 0.85);
    end
end
yline(0.8, '--k', '80% SOH threshold', 'LineWidth', 1.2);
xline(cfg.earlyCycleLimit, ':', 'Test observation boundary', 'LineWidth', 1.2);
grid on; box on;
xlabel('Cycle'); ylabel('Smoothed SOH');
title('All battery SOH trajectories');
subtitle('Blue: 40 training batteries; red: 9 prediction-test batteries');
saveFigure(fig, cfg.figureDir, "fig01_all_battery_soh", cfg.figureResolution);

% Figure 2: strategy-level mean SOH trajectories.
fig = newFigure();
hold on;
policies = strategySummary.policy;
for p = 1:numel(policies)
    rows = cycleData.policy == policies(p);
    cycles = unique(cycleData.cycle(rows));
    meanSoh = nan(size(cycles));
    for j = 1:numel(cycles)
        meanSoh(j) = mean(cycleData.SOH_smooth(rows & cycleData.cycle == cycles(j)), "omitmissing");
    end
    plot(cycles, meanSoh, 'LineWidth', 2.0, 'Color', baseColors(p,:));
end
grid on; box on;
xlabel('Cycle'); ylabel('Mean smoothed SOH');
title('Mean SOH trajectory by charging policy');
legend(compose('%s (n=%d)', policies, strategySummary.n_batteries), ...
    'Interpreter', 'none', 'Location', 'eastoutside', 'FontSize', 8);
saveFigure(fig, cfg.figureDir, "fig02_policy_mean_soh", cfg.figureResolution);

% Figure 3: charge-time versus early degradation trade-off.
fig = newFigure();
hold on;
train = ~batteryFeatures.prediction_test;
test = batteryFeatures.prediction_test;
scatter(batteryFeatures.mean_chargetime_observed(train), ...
    -1e4*batteryFeatures.early_soh_slope(train), 58, ...
    batteryFeatures.mean_temperature_observed(train), 'filled', ...
    'MarkerEdgeColor', [0.15 0.15 0.15]);
scatter(batteryFeatures.mean_chargetime_observed(test), ...
    -1e4*batteryFeatures.early_soh_slope(test), 92, ...
    batteryFeatures.mean_temperature_observed(test), 'd', ...
    'filled', 'MarkerEdgeColor', [0.75 0.05 0.05], 'LineWidth', 1.2);
grid on; box on;
xlabel('Mean charge time'); ylabel('Early SOH decline rate (-slope x 10^4/cycle)');
title('Charging-time and early-degradation trade-off');
subtitle('Color indicates mean temperature; diamonds are prediction-test batteries');
cb = colorbar; cb.Label.String = 'Mean temperature';
saveFigure(fig, cfg.figureDir, "fig03_charge_time_vs_degradation", cfg.figureResolution);

% Figure 4: sampled policy parameter space colored by early degradation.
fig = newFigure();
scatter3(summaryData.C1, summaryData.Q1, summaryData.C2, 82, ...
    -1e4*batteryFeatures.early_soh_slope, 'filled', ...
    'MarkerEdgeColor', [0.12 0.12 0.12]);
grid on; box on; view(40, 25);
xlabel('C_1'); ylabel('Q_1 (%)'); zlabel('C_2');
title('Observed two-stage charging-policy space');
subtitle('Color indicates early SOH decline rate');
cb = colorbar; cb.Label.String = '-SOH slope x 10^4/cycle';
saveFigure(fig, cfg.figureDir, "fig04_policy_parameter_space", cfg.figureResolution);

% Figure 5: three representative batteries across SOH, resistance, temperature.
[~, order] = sort(batteryFeatures.early_soh_slope, "descend");
representative = order([1, round(numel(order)/2), numel(order)]);
labels = ["slow decline", "median decline", "fast decline"];
fig = newFigure();
tiledlayout(3,1, 'TileSpacing','compact', 'Padding','compact');
quantities = ["SOH_smooth", "IR", "Tavg"];
ylabels = ["Smoothed SOH", "Internal resistance", "Mean temperature"];
for q = 1:3
    nexttile; hold on;
    for j = 1:3
        batteryId = batteryFeatures.battery_id(representative(j));
        rows = cycleData.battery_id == batteryId;
        yValues = cycleData.(quantities(q));
        plot(cycleData.cycle(rows), yValues(rows), ...
            'LineWidth', 1.8, 'Color', baseColors(j,:));
    end
    grid on; box on; ylabel(ylabels(q));
    if q == 1
        title('Representative battery health indicators');
        legend(compose('Battery %d: %s', batteryFeatures.battery_id(representative), labels), ...
            'Location','best', 'Interpreter','none');
    end
end
xlabel('Cycle');
saveFigure(fig, cfg.figureDir, "fig05_representative_health_indicators", cfg.figureResolution);
end

function fig = newFigure()
fig = figure('Visible','off', 'Color','w', 'Position',[80 80 1500 880]);
set(fig, 'DefaultAxesFontName', 'Microsoft YaHei', ...
    'DefaultTextFontName', 'Microsoft YaHei', ...
    'DefaultAxesFontSize', 11);
end

function saveFigure(fig, outputDir, stem, resolution)
pngPath = fullfile(outputDir, stem + ".png");
figPath = fullfile(outputDir, stem + ".fig");
exportgraphics(fig, pngPath, 'Resolution', resolution);
savefig(fig, figPath);
close(fig);
end
