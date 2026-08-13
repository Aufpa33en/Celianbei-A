%PLOT_RAW_FIGURE1 Plot Figure 1 directly from the official raw CSV files.
% This script performs no cleaning, deduplication, interpolation, smoothing,
% clipping, or feature construction. SOH values are plotted as supplied.

scriptPath = mfilename('fullpath');
projectRoot = string(fileparts(fileparts(scriptPath)));
summaryPath = fullfile(projectRoot, "data", "raw", "battery_summary.csv");
cyclePath = fullfile(projectRoot, "data", "raw", "cycle_train.csv");
figureDir = fullfile(projectRoot, "figures");

assert(isfile(summaryPath), "Missing raw battery_summary.csv.");
assert(isfile(cyclePath), "Missing raw cycle_train.csv.");
if ~isfolder(figureDir)
    mkdir(figureDir);
end

summaryRaw = readtable(summaryPath, TextType="string", VariableNamingRule="preserve");
cycleRaw = readtable(cyclePath, TextType="string", VariableNamingRule="preserve");

fig = figure('Visible','off', 'Color','w', 'Position',[80 40 1500 1120]);
layout = tiledlayout(fig, 2, 1, 'TileSpacing','compact', 'Padding','compact');
trainColor = [0.66 0.76 0.88];
testColor = [0.88 0.25 0.22];
axesList = gobjects(2,1);

for panel = 1:2
    ax = nexttile(layout);
    axesList(panel) = ax;
    hold(ax, 'on');
    for i = 1:height(summaryRaw)
        batteryId = summaryRaw.battery_id(i);
        rows = cycleRaw.battery_id == batteryId;
        if logical(summaryRaw.prediction_test(i))
            plot(ax, cycleRaw.cycle(rows), cycleRaw.SOH(rows), '-', ...
                'Color', testColor, 'LineWidth', 1.10, 'HandleVisibility','off');
        else
            plot(ax, cycleRaw.cycle(rows), cycleRaw.SOH(rows), '-', ...
                'Color', trainColor, 'LineWidth', 0.75, 'HandleVisibility','off');
        end
    end
    plot(ax, nan, nan, '-', 'Color', trainColor, 'LineWidth', 2.2, ...
        'DisplayName', '训练电池（40块，观测至200循环）');
    plot(ax, nan, nan, '-', 'Color', testColor, 'LineWidth', 2.2, ...
        'DisplayName', '预测测试电池（9块，观测至150循环）');
    if panel == 2
        boundaryLabel = '测试数据观测终点';
    else
        boundaryLabel = '';
    end
    xline(ax, 150, ':', boundaryLabel, 'LineWidth', 1.2, ...
        'LabelVerticalAlignment', 'bottom', 'HandleVisibility','off');
    grid(ax, 'on');
    box(ax, 'on');
    xlim(ax, [0 205]);
    ylabel(ax, '原始 SOH');
    set(ax, 'FontName','Microsoft YaHei', 'FontSize',10.5, 'LineWidth',0.8);
end

rawMin = min(cycleRaw.SOH);
rawMax = max(cycleRaw.SOH);
ylim(axesList(1), [floor(rawMin*100)/100-0.01, ceil(rawMax*100)/100+0.01]);
title(axesList(1), sprintf('完整范围（原始最小值 %.4f，最大值 %.4f）', rawMin, rawMax));
ylim(axesList(2), [0.94 1.10]);
title(axesList(2), '主体区间放大（0.94-1.10）');
xlabel(axesList(2), '循环次数 Cycle');
legend(axesList(2), 'Location','southwest', 'FontSize',9.5);
title(layout, {'图1  49块电池的原始 SOH 循环曲线'; ...
    '直接读取 cycle_train.csv 的 SOH 字段，未进行任何清洗或二次平滑'}, ...
    'FontName','Microsoft YaHei', 'FontSize',15, 'FontWeight','bold', ...
    'Interpreter','none');

pngPath = fullfile(figureDir, "fig01_raw_soh_curves.png");
figPath = fullfile(figureDir, "fig01_raw_soh_curves.fig");
exportgraphics(fig, pngPath, 'Resolution', 180);
savefig(fig, figPath);
close(fig);

fprintf('Raw Figure 1 created without data cleaning.\n');
fprintf('  Rows read: summary=%d, cycle=%d\n', height(summaryRaw), height(cycleRaw));
fprintf('  PNG: %s\n', pngPath);
fprintf('  FIG: %s\n', figPath);
