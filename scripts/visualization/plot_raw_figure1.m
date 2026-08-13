%PLOT_RAW_FIGURE1 Create publication-ready raw-data diagnostic figures.
% No observation is deleted, replaced, interpolated, clipped, or resmoothed.
% Battery 1 is separated only in the visualization because its cycle-12
% measurement would compress the scale of all other SOH trajectories.

scriptPath = mfilename('fullpath');
projectRoot = string(fileparts(fileparts(fileparts(scriptPath))));
summaryPath = fullfile(projectRoot, "data", "raw", "battery_summary.csv");
cyclePath = fullfile(projectRoot, "data", "raw", "cycle_train.csv");
figureDir = fullfile(projectRoot, "figures", "raw_data");

assert(isfile(summaryPath), "Missing raw battery_summary.csv.");
assert(isfile(cyclePath), "Missing raw cycle_train.csv.");
if ~isfolder(figureDir)
    mkdir(figureDir);
end

summaryRaw = readtable(summaryPath, TextType="string", VariableNamingRule="preserve");
cycleRaw = readtable(cyclePath, TextType="string", VariableNamingRule="preserve");

[peakSOH, peakIndex] = max(cycleRaw.SOH);
anomalyBattery = cycleRaw.battery_id(peakIndex);
anomalyCycle = cycleRaw.cycle(peakIndex);
assert(anomalyBattery == 1 && anomalyCycle == 12, ...
    "The expected raw-data peak location has changed; review before plotting.");

plotAnomalyDiagnostic(cycleRaw, anomalyBattery, anomalyCycle, peakSOH, figureDir);
plotNormalCurvesByPolicy(summaryRaw, cycleRaw, anomalyBattery, figureDir);

fprintf('Publication-ready raw-data figures created without cleaning.\n');
fprintf('  Raw rows: summary=%d, cycle=%d\n', height(summaryRaw), height(cycleRaw));
fprintf('  Separated peak: battery=%d, cycle=%d, SOH=%.6f\n', ...
    anomalyBattery, anomalyCycle, peakSOH);
fprintf('  Output directory: %s\n', figureDir);

function plotAnomalyDiagnostic(cycleRaw, batteryId, peakCycle, peakSOH, outputDir)
one = cycleRaw(cycleRaw.battery_id == batteryId, :);
focus = one.cycle <= 30;
localReference = one.cycle >= peakCycle-2 & one.cycle <= peakCycle+2 & one.cycle ~= peakCycle;
capacityMedian = median(one.capacity(localReference));
capacityIncrease = 100*(one.capacity(one.cycle == peakCycle)/capacityMedian - 1);

fig = figure('Visible','off', 'Color','w', 'Position',[40 40 1780 1180]);
layout = tiledlayout(fig, 3, 2, 'TileSpacing','compact', 'Padding','compact');

ax = nexttile(layout, [1 2]); hold(ax,'on');
plot(ax, one.cycle(focus), one.SOH(focus), '-o', 'Color',[0.10 0.36 0.67], ...
    'MarkerSize',3.8, 'LineWidth',1.45, 'DisplayName','原始 SOH');
plot(ax, one.cycle(focus), one.SOH_smooth(focus), '-', 'Color',[0.91 0.42 0.15], ...
    'LineWidth',1.8, 'DisplayName','附件提供的 SOH\_smooth');
scatter(ax, peakCycle, peakSOH, 82, [0.78 0.08 0.12], 'filled', ...
    'MarkerEdgeColor','w', 'LineWidth',1.0, 'HandleVisibility','off');
xline(ax, peakCycle, '--', '第12循环异常', 'Color',[0.62 0.08 0.12], ...
    'LineWidth',1.2, 'HandleVisibility','off');
text(ax, peakCycle+0.7, peakSOH-0.025, sprintf('SOH = %.4f',peakSOH), ...
    'Color',[0.62 0.08 0.12], 'FontWeight','bold');
xlim(ax,[1 30]); ylim(ax,[0.98 1.46]);
ylabel(ax,'SOH');
title(ax,'(a) SOH尖峰及其对附件平滑序列的影响');
legend(ax,'Location','northeast','FontSize',9,'Interpreter','none');
styleAxes(ax);

ax = nexttile(layout); hold(ax,'on');
plotFocus(ax, one, focus, 'capacity', [0.10 0.36 0.67], peakCycle);
yline(ax, capacityMedian, ':', sprintf('邻近中位数 %.4f Ah',capacityMedian), ...
    'Color',[0.25 0.25 0.25], 'HandleVisibility','off');
text(ax, peakCycle+0.5, one.capacity(one.cycle==peakCycle)-0.04, ...
    sprintf('+%.1f%%',capacityIncrease), 'Color',[0.62 0.08 0.12], 'FontWeight','bold');
ylabel(ax,'容量 / Ah'); title(ax,'(b) 容量：尖峰的直接来源'); styleAxes(ax);

ax = nexttile(layout); hold(ax,'on');
plotFocus(ax, one, focus, 'IR', [0.34 0.62 0.30], peakCycle);
ylabel(ax,'内阻 IR'); title(ax,'(c) 内阻：同一循环达到全表最大值'); styleAxes(ax);

ax = nexttile(layout); hold(ax,'on');
plotFocus(ax, one, focus, 'Tavg', [0.56 0.30 0.64], peakCycle);
ylabel(ax,'平均温度'); xlabel(ax,'循环次数');
title(ax,'(d) 温度：同一循环同步下降'); styleAxes(ax);

ax = nexttile(layout); hold(ax,'on');
plotFocus(ax, one, focus, 'chargetime', [0.90 0.53 0.12], peakCycle);
ylabel(ax,'充电时间'); xlabel(ax,'循环次数');
title(ax,'(e) 充电时间：未出现同等级跳变'); styleAxes(ax);

title(layout, {'原始数据异常诊断：电池1第12循环'; ...
    '容量、SOH、内阻与温度同步异常；当前仅标记，不删除、不修正'}, ...
    'FontName','Microsoft YaHei', 'FontSize',16, 'FontWeight','bold');

savePublicationFigure(fig, outputDir, "fig01a_battery1_cycle12_anomaly");
end

function plotFocus(ax, one, focus, variableName, color, peakCycle)
values = one.(variableName);
plot(ax, one.cycle(focus), values(focus), '-o', 'Color',color, ...
    'MarkerFaceColor',color, 'MarkerSize',3.2, 'LineWidth',1.25);
peakValue = values(one.cycle == peakCycle);
scatter(ax, peakCycle, peakValue, 68, [0.78 0.08 0.12], 'filled', ...
    'MarkerEdgeColor','w', 'LineWidth',0.9);
xline(ax, peakCycle, '--', 'Color',[0.62 0.08 0.12], ...
    'LineWidth',1.0, 'HandleVisibility','off');
xlim(ax,[1 30]);
end

function plotNormalCurvesByPolicy(summaryRaw, cycleRaw, excludedBattery, outputDir)
summaryNormal = summaryRaw(summaryRaw.battery_id ~= excludedBattery, :);
policies = unique(summaryNormal.policy, 'stable');
assert(numel(policies) == 9, "Expected nine charging policies.");

fig = figure('Visible','off', 'Color','w', 'Position',[20 20 2100 1450]);
layout = tiledlayout(fig, 3, 3, 'TileSpacing','compact', 'Padding','compact');
palette = lines(8);

for p = 1:numel(policies)
    ax = nexttile(layout); hold(ax,'on');
    policy = policies(p);
    members = summaryNormal(summaryNormal.policy == policy, :);
    legendLabels = strings(height(members),1);
    lineHandles = gobjects(height(members),1);
    for j = 1:height(members)
        batteryId = members.battery_id(j);
        rows = cycleRaw.battery_id == batteryId;
        if logical(members.prediction_test(j))
            lineStyle = '--';
            width = 2.0;
            legendLabels(j) = sprintf('B%02d（测试）',batteryId);
        else
            lineStyle = '-';
            width = 1.25;
            legendLabels(j) = sprintf('B%02d',batteryId);
        end
        lineHandles(j) = plot(ax, cycleRaw.cycle(rows), cycleRaw.SOH(rows), ...
            'LineStyle',lineStyle, 'Color',palette(j,:), 'LineWidth',width);
    end
    xline(ax,150,':','Color',[0.35 0.35 0.35], ...
        'LineWidth',0.9,'HandleVisibility','off');
    xlim(ax,[0 205]); ylim(ax,[0.945 1.002]);
    xticks(ax,[0 50 100 150 200]);
    yticks(ax,[0.95 0.96 0.97 0.98 0.99 1.00]);
    if all(ismissing(members.C1))
        strategyLabel = sprintf('C_1缺失，Q_1=%.0f%%，C_2=%.1fC', ...
            members.Q1(1), members.C2(1));
    else
        strategyLabel = sprintf('C_1=%.1fC，Q_1=%.0f%%，C_2=%.1fC', ...
            members.C1(1), members.Q1(1), members.C2(1));
    end
    title(ax, sprintf('%s  (n=%d)', strategyLabel, height(members)), ...
        'Interpreter','tex','FontSize',10.5);
    legend(ax,lineHandles,legendLabels,'Location','southwest', ...
        'FontSize',7.2,'NumColumns',2,'Box','off');
    styleAxes(ax);
end

xlabel(layout,'循环次数 Cycle','FontName','Microsoft YaHei','FontSize',12);
ylabel(layout,'原始 SOH','FontName','Microsoft YaHei','FontSize',12);
title(layout, {'正常尺度下的原始SOH曲线：按充电策略分面'; ...
    '共48块电池；电池1仅因第12循环尖峰移至异常诊断图，未从原始数据删除；虚线为问题3测试电池'}, ...
    'FontName','Microsoft YaHei','FontSize',16,'FontWeight','bold');

savePublicationFigure(fig, outputDir, "fig01b_normal_soh_by_policy");
end

function styleAxes(ax)
grid(ax,'on'); box(ax,'on');
ax.GridAlpha = 0.14;
ax.MinorGridAlpha = 0.08;
ax.FontName = 'Microsoft YaHei';
ax.FontSize = 9.5;
ax.LineWidth = 0.8;
end

function savePublicationFigure(fig, outputDir, stem)
exportgraphics(fig, fullfile(outputDir, stem + ".png"), 'Resolution', 300);
savefig(fig, fullfile(outputDir, stem + ".fig"));
close(fig);
end
