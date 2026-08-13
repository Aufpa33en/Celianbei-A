function plot_a_cleaning_comparison(summaryClean, cycleClean, actions, outputDir)
%PLOT_A_CLEANING_COMPARISON Visual audit of every cleaning decision.

arguments
    summaryClean table
    cycleClean table
    actions table
    outputDir (1,1) string
end
if ~isfolder(outputDir), mkdir(outputDir); end

fig = figure('Visible','off','Color','w','Position',[30 30 1800 1200]);
layout = tiledlayout(fig,3,2,'TileSpacing','compact','Padding','compact');

rows = cycleClean.battery_id==1 & cycleClean.cycle>=7 & cycleClean.cycle<=17;
ax=nexttile(layout); hold(ax,'on');
plot(ax,cycleClean.cycle(rows),cycleClean.capacity_raw(rows),'-o','LineWidth',1.3,'DisplayName','原始容量');
plot(ax,cycleClean.cycle(rows),cycleClean.capacity_clean(rows),'-s','LineWidth',1.6,'DisplayName','清洗容量');
xline(ax,12,'--','第12循环','HandleVisibility','off');
ylabel(ax,'容量 / Ah'); title(ax,'(a) 电池1容量修复'); legend(ax,'Location','northwest'); styleAxes(ax);

ax=nexttile(layout); hold(ax,'on');
plot(ax,cycleClean.cycle(rows),cycleClean.SOH_raw(rows),'-o','LineWidth',1.3,'DisplayName','原始SOH');
plot(ax,cycleClean.cycle(rows),cycleClean.SOH_clean(rows),'-s','LineWidth',1.6,'DisplayName','清洗SOH');
plot(ax,cycleClean.cycle(rows),cycleClean.SOH_smooth_official_raw(rows),':','LineWidth',1.6,'DisplayName','附件SOH\_smooth');
plot(ax,cycleClean.cycle(rows),cycleClean.SOH_trend_rlowess_11(rows),'--','LineWidth',1.8,'DisplayName','清洗后11点rlowess');
xline(ax,12,'--','HandleVisibility','off');
ylabel(ax,'SOH'); title(ax,'(b) SOH重算与趋势重建'); legend(ax,'Location','northwest','Interpreter','none'); styleAxes(ax);

for panel=1:2
    batteryId=panel+1;
    rows=cycleClean.battery_id==batteryId & cycleClean.cycle>=7 & cycleClean.cycle<=17;
    ax=nexttile(layout); hold(ax,'on');
    plot(ax,cycleClean.cycle(rows),cycleClean.IR_raw(rows),'-o','LineWidth',1.3,'DisplayName','原始IR');
    plot(ax,cycleClean.cycle(rows),cycleClean.IR_clean(rows),'-s','LineWidth',1.6,'DisplayName','清洗IR');
    xline(ax,12,'--','第12循环','HandleVisibility','off');
    ylabel(ax,'内阻 IR'); title(ax,sprintf('(%c) 电池%d零内阻修复',char('b'+panel),batteryId));
    legend(ax,'Location','southeast'); styleAxes(ax);
end

rows=cycleClean.battery_id==41;
ax=nexttile(layout); hold(ax,'on');
plot(ax,cycleClean.cycle(rows),cycleClean.SOH_clean(rows),'-','LineWidth',1.7,'DisplayName','绝对SOH（保留）');
plot(ax,cycleClean.cycle(rows),cycleClean.SOH_relative_clean(rows),'--','LineWidth',1.7,'DisplayName','相对前5循环容量');
yline(ax,1,':','HandleVisibility','off'); xlabel(ax,'循环次数'); ylabel(ax,'SOH');
title(ax,'(e) 电池41：保留低基线并增加相对退化指标'); legend(ax,'Location','southwest'); styleAxes(ax);

ax=nexttile(layout);
actionVariables = ["capacity","IR"];
actionCounts = [sum(actions.variable=="capacity"),sum(actions.variable=="IR")];
bar(ax,categorical(actionVariables),actionCounts,'FaceColor',[0.25 0.52 0.73]);
ylabel(ax,'修复记录数'); xlabel(ax,'变量'); title(ax,'(f) 实际修改范围：共3个单元格');
ylim(ax,[0 3]); yticks(ax,0:3); styleAxes(ax);

title(layout,{'A题原始数据清洗前后对照'; ...
    '原始字段完整保留；仅修复1个容量值和2个零内阻值'}, ...
    'FontName','Microsoft YaHei','FontSize',16,'FontWeight','bold');

exportgraphics(fig,fullfile(outputDir,"fig02_cleaning_before_after.png"),'Resolution',300);
savefig(fig,fullfile(outputDir,"fig02_cleaning_before_after.fig"));
close(fig);
end

function styleAxes(ax)
grid(ax,'on'); box(ax,'on'); ax.GridAlpha=0.15;
ax.FontName='Microsoft YaHei'; ax.FontSize=10; ax.LineWidth=0.8;
end
