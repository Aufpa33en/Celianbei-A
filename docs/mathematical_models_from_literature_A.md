# A题数学模型体系与严格推导

## 1. 建模边界与符号

本文把四个问题连接为一条可验证的模型链：问题1用策略类别解释已观测曲线，问题2用少量物理启发特征解释策略参数，问题3预测第151—200循环并谨慎外推80% SOH寿命，问题4在可信域内权衡充电时间和退化。该体系借鉴混合效应模型、早期特征正则化、高斯过程和多目标优化，但不照搬文献中本题没有的电压—容量曲线或完整EOL标签。

清洗后共有49块电池、9种策略、9350条循环记录；40块电池观测至第200循环，9块测试电池仅至第150循环。全部已观测SOH均不低于约0.9466，因此第151—200循环预测可以回测，80% SOH寿命只能作模型依赖的远期外推，不能称为已验证寿命。

记：

- $i=1,\ldots,n$ 表示电池，$p(i)$ 表示电池所属策略；
- $t$ 表示循环数，$x_t=t/200$ 为归一化循环数；
- $y_{it}=SOH_{it}$，并令退化量 $d_{it}=1-y_{it}$；
- 两阶段快充参数为 $\boldsymbol c=(C_1,q,C_2)$，其中 $q=Q_1/100$，充电区间为0—80% SOC；
- $B_k(x)$ 为给定节点的三次B样条基函数；
- 所有连续协变量进入回归前均按训练集均值和标准差标准化。

一个重要的数据约束是：`80PER_3_6C`策略缺失 $C_1$，故只能进入策略类别比较，不能进入连续参数效应估计。另有两个策略具有同样的 $(4.8,0.8,4.8)$，却分属旧/新结构且平均充电时间不同，说明“结构/批次”和策略参数存在混杂。

## 2. 模型一：策略—电池—循环三级函数型混合效应模型

### 2.1 模型目的

该模型回答问题1：不同策略的平均SOH轨迹是否不同，同一策略内电池为什么仍有明显差异，以及“9350行记录”为什么不能当作9350个独立样本。

### 2.2 模型形式

取 $K$ 个样条基函数，以某一参考策略为基准：

\[
y_{it}=\boldsymbol B(x_t)^\mathsf T\boldsymbol\beta
+\boldsymbol B(x_t)^\mathsf T\boldsymbol\delta_{p(i)}
+b_{0i}+b_{1i}x_t+\varepsilon_{it},
\tag{1}
\]

其中参考策略满足 $\boldsymbol\delta_1=\boldsymbol0$，随机效应

\[
\begin{pmatrix}b_{0i}\\b_{1i}\end{pmatrix}
\sim N\!\left(\begin{pmatrix}0\\0\end{pmatrix},\boldsymbol D\right).
\tag{2}
\]

为描述同一电池相邻循环的相关性，采用离散循环AR(1)残差：

\[
\operatorname{Cov}(\varepsilon_{it},\varepsilon_{is})
=\sigma^2\rho^{|t-s|},\qquad |\rho|<1,
\tag{3}
\]

不同电池间残差独立。式(1)中总体曲线为

\[
\mu_0(x)=\boldsymbol B(x)^\mathsf T\boldsymbol\beta,
\]

策略 $p$ 的平均曲线为

\[
\mu_p(x)=\boldsymbol B(x)^\mathsf T(\boldsymbol\beta+\boldsymbol\delta_p).
\tag{4}
\]

随机截距 $b_{0i}$ 表示初始SOH差异，随机斜率 $b_{1i}$ 表示个体退化速度差异。这样，同图中同策略曲线差异大不再被误认为画图错误，而被显式分解为电池个体差异。

### 2.3 估计推导

对电池 $i$，写成矩阵形式

\[
\boldsymbol y_i=\boldsymbol X_i\boldsymbol\theta
+\boldsymbol Z_i\boldsymbol b_i+\boldsymbol\varepsilon_i,
\]

积分消去随机效应后有

\[
\boldsymbol y_i\sim N(\boldsymbol X_i\boldsymbol\theta,
\boldsymbol V_i),\qquad
\boldsymbol V_i=\boldsymbol Z_i\boldsymbol D\boldsymbol Z_i^\mathsf T
+\boldsymbol R_i(\rho,\sigma^2).
\tag{5}
\]

给定方差参数 (\boldsymbol\psi=$\boldsymbol D,\rho,\sigma^2$)，广义最小二乘估计为

\[
\widehat{\boldsymbol\theta}(\boldsymbol\psi)=
\left(\sum_i\boldsymbol X_i^\mathsf T\boldsymbol V_i^{-1}\boldsymbol X_i\right)^{-1}
\left(\sum_i\boldsymbol X_i^\mathsf T\boldsymbol V_i^{-1}\boldsymbol y_i\right).
\tag{6}
\]

最终参数与区间用限制最大似然估计，以减小固定效应较多时方差分量的向下偏差；但比较不同固定效应的全局策略检验必须把零假设和备择模型都用普通最大似然重新拟合。样条自由度由按“整块电池”进行的交叉验证选择，而不是随机拆分循环行。

### 2.4 策略检验与效应量

总体假设为

\[
H_0:\boldsymbol\delta_2=\cdots=\boldsymbol\delta_9=\boldsymbol0,
\qquad H_1:\text{至少一个}\boldsymbol\delta_p\ne\boldsymbol0.
\tag{7}
\]

用似然比统计量

\[
\Lambda=2\{\ell(\widehat\Theta_1)-\ell(\widehat\Theta_0)\}
\tag{8}
\]

全局检验在零假设拟合模型下模拟随机效应和AR(1)残差，保持原电池数、策略分配和观测时点，每次重拟合两模型，以参数自助法给出 $p$ 值。曲线效应区间另用策略内整块电池聚类重采样获得；每组仅3—8块电池时区间会不稳定，需明确报告。策略 $p,r$ 的曲线差异用三个量报告：

\[
\Delta_{pr}(t)=\widehat\mu_p(t)-\widehat\mu_r(t),
\tag{9}
\]

\[
A_{pr}=\int_0^1\{\widehat\mu_p(x)-\widehat\mu_r(x)\}\,dx,
\tag{10}
\]

\[
R_p=-\int_0^1\widehat\mu'_p(x)\,dx
=\widehat\mu_p(0)-\widehat\mu_p(1).
\tag{11}
\]

其中 $A_{pr}$ 是整个观测窗内的平均曲线优势，$R_p$ 是200循环内的预计SOH损失。标量效应的区间由电池级自助法得到，并对有限个标量比较采用Holm校正；整条 $\Delta_{pr}(t)$ 曲线使用同时自助置信带，不对逐点区间机械使用Holm校正。

### 2.5 可辨识性与限制

该模型把策略作为类别，因此能使用全部9种策略，也不要求 $(C_1,Q_1,C_2)$ 独立变化；代价是只能说明“策略组合不同”，不能把差异因果归结到某一个参数。由于每策略仅3—8块电池，策略内电池数而不是循环行数决定策略效应的有效样本量。

## 3. 模型二：物理启发应力特征与约束退化模型

### 3.1 从两阶段恒流策略推导特征

SOC记为 $s\in[0,0.8]$。在 $C_1>0,C_2>0,0\le q\le0.8$，初始SOC为0、两段均恒流且忽略恒压尾段的假设下，两阶段C-rate函数为

\[
c(s)=\begin{cases}
C_1,&0\le s\le q,\\
C_2,&q<s\le0.8.
\end{cases}
\tag{12}
\]

因为C-rate满足 $ds/dt=c(s)/60$，故 $dt=60ds/c(s)$。理想快充时间为

\[
T_0(\boldsymbol c)=60\int_0^{0.8}\frac{ds}{c(s)}
=60\left(\frac q{C_1}+\frac{0.8-q}{C_2}\right).
\tag{13}
\]

若电流 $I\propto c$，焦耳热能代理量满足

\[
\int I^2dt\propto\int c(s)^2\frac{ds}{c(s)}
=\int c(s)ds,
\]

故定义总电流应力

\[
J(\boldsymbol c)=qC_1+(0.8-q)C_2.
\tag{14}
\]

为区分高SOC区间的同等电流，定义SOC加权应力

\[
H(\boldsymbol c)=\int_0^{0.8}s\,c(s)ds
=\frac12\left[C_1q^2+C_2(0.8^2-q^2)\right].
\tag{15}
\]

式(13)—(15)不是电化学定律的完整替代，而是在仅有策略汇总参数时可计算、量纲明确的代理特征。

### 3.2 设计可辨识性检验

去除缺失 $C_1$ 的策略后有8个完整策略标签，但因 $(4.8,0.8,4.8)$ 重复，只有7个不同参数坐标。未标准化时，带截距的 $(C_1,q,C_2)$ 设计矩阵秩为4、条件数约106.5；带截距的 $(T_0,J,H)$ 条件数约1760.2。标准化后的条件数分别约为1.98和19.89，且样本中

\[
\operatorname{corr}(T_0,J)=-0.984.
\]

因此不能在7个独立参数坐标上稳定估计大量主效应、二次项和交互项。主分析采用预先规定的两个应力量 $J,H$，其标准化设计矩阵条件数约3.79，并用岭收缩进一步稳定估计；$C_1,q,C_2$ 单独效应只作敏感性分析。具有相同数值参数的旧/新结构策略提示结构效应，故引入结构指示变量 $S_p$，但 $S_p$ 与数据集/批次不可分离，只能解释为“新结构标签、数据集及批次条件的联合关联”，不作纯结构因果解释。

### 3.3 约束退化模型

为保证平均SOH随循环下降，设

\[
y_{it}=a_i-r_i x_t-kx_t^2+\varepsilon_{it},
\qquad r_i>0,; k\ge0,
\tag{16}
\]

并令

\[
a_i=\alpha_0+\alpha_S S_{p(i)}+u_{0i},
\tag{17}
\]

\[
\log r_i=\beta_0+\beta_J\widetilde J_{p(i)}
+\beta_H\widetilde H_{p(i)}+\beta_S S_{p(i)}+u_{1i},
\tag{18}
\]

其中 $(u_{0i},u_{1i})^\mathsf T\sim N(\boldsymbol0,\boldsymbol D)$，$k=\exp(\kappa)$ 或在比较线性退化时令 $k=0$。残差沿用式(3)的电池内AR(1)协方差；稳健性分析改用电池级聚类稳健协方差。因为

\[
\frac{\partial E(y_{it}\mid i)}{\partial x}=-(r_i+2kx)<0,
\]

所以模型在观测和外推区间内保持单调退化，不会产生无物理意义的远期回升。

参数通过惩罚边际似然估计：

\[
\widehat\Theta=\arg\min_\Theta
\left\{-2\ell_{\mathrm{marg}}(\Theta)
+\lambda(\beta_J^2+\beta_H^2)\right\}.
\tag{19}
\]

$\lambda$ 用策略级留一交叉验证选取；若样本不足以稳定选择，则把 $J$ 与 $H$ 分别拟合成两个无惩罚的一特征模型，并用AICc和留一策略误差选择；惩罚模型不直接套用普通参数个数计算AICc。对 $\beta_J,\beta_H$ 的置信区间采用策略级参数自助法。显著性只表示在现有有限策略点内的关联，不等于独立随机实验下的因果效应。

### 3.4 80% SOH交点的解析推导

给定电池或策略的参数 $(a,r,k)$，令 $x_{80}$ 满足

\[
a-rx_{80}-kx_{80}^2=0.8.
\]

当 $k>0$ 时，取非负根：

\[
x_{80}=\frac{-r+\sqrt{r^2+4k(a-0.8)}}{2k},
\qquad L_{80}=200x_{80}.
\tag{20}
\]

当 $k=0$ 时，连续极限为

\[
L_{80}=200\frac{a-0.8}{r}.
\tag{21}
\]

当 $a=0.8$ 时交点为0；$a<0.8$ 表示阈值在观测起点前已越过，应记为左删失或起始即失效，在本数据背景下再检查是否由拟合失败导致。策略层面不能简单令随机效应为0并把结果称为平均寿命：需从 $(u_{0i},u_{1i})$ 联合分布抽样，对每次样本应用式(20)，报告寿命分布；其中 $E(r_i\mid p)=\exp(\eta_p+\sigma_{u_1}^2/2)$，而 $\exp(\eta_p)$ 只是中位退化速率。由于现有数据远未达到0.8，最终需同时报告线性模型 $k=0$、二次模型 $k>0$ 与不同外推上限下的 $L_{80}$；模型间差异是结构不确定性，不能被普通置信区间掩盖。

## 4. 模型三：退化均值约束的半参数高斯过程预测

### 4.1 模型目的

该模型是问题3的主预测候选，用前 $h\le150$ 个循环预测后续SOH。参数退化均值负责可解释的长期方向，高斯过程只学习平滑偏差和局部波动。

### 4.2 模型定义

对电池 $i$，令

\[
y_i(t)=m_i(t;\widehat a_i,\widehat r_i,\widehat k)+g_i(t)+\epsilon_i(t),
\tag{22}
\]

其中 $m_i$ 由式(16)给出，$g_i\sim GP(0,k_\phi)$，

\[
k_\phi(x,z)=\sigma_f^2
\left(1+\frac{\sqrt3|x-z|}{\ell}\right)
\exp\!\left(-\frac{\sqrt3|x-z|}{\ell}\right),
\tag{23}
\]

即在归一化循环数 $x=t/200$ 上使用Matérn-$3/2$核；$\epsilon_i(t)\sim N(0,\sigma_n^2)$。不加入线性核，因为它与式(18)的个体随机退化斜率重复，会造成长期趋势不可辨识。长度尺度限制为 $\ell\ge5/200$，防止模型把逐点噪声当成退化机制。

设训练循环集合为 $X=(1,\ldots,h)$，待预测集合为 $X_*=(h+1,\ldots,200)$，并定义去均值观测 $\boldsymbol r_X=\boldsymbol y_X-\boldsymbol m_X$。由联合高斯分布

\[
\begin{pmatrix}\boldsymbol r_X\\\boldsymbol g_*\end{pmatrix}
\sim N\!\left[
\boldsymbol0,
\begin{pmatrix}
\boldsymbol K_{XX}+\sigma_n^2\boldsymbol I&\boldsymbol K_{X*}\\
\boldsymbol K_{*X}&\boldsymbol K_{**}
\end{pmatrix}
\right],
\]

条件分布为

\[
E(\boldsymbol y_*\mid\boldsymbol y_X)=\boldsymbol m_*
+\boldsymbol K_{*X}(\boldsymbol K_{XX}+\sigma_n^2\boldsymbol I)^{-1}
(\boldsymbol y_X-\boldsymbol m_X),
\tag{24}
\]

\[
\operatorname{Cov}(\boldsymbol f_*\mid\boldsymbol y_X)
=\boldsymbol K_{**}-\boldsymbol K_{*X}
(\boldsymbol K_{XX}+\sigma_n^2\boldsymbol I)^{-1}\boldsymbol K_{X*}.
\tag{25}
\]

这里 $\boldsymbol f_*=\boldsymbol m_*+\boldsymbol g_*$ 是潜在平滑退化轨迹。未来实测SOH的预测协方差还需加上观测噪声：

\[
\operatorname{Cov}(\boldsymbol y_*\mid\boldsymbol y_X)
=\operatorname{Cov}(\boldsymbol f_*\mid\boldsymbol y_X)
+\sigma_n^2\boldsymbol I.
\tag{26}
\]

式(25)只包含给定超参数与均值参数后的条件不确定性。正式计算时以整块电池为单位自助重采样，每次重新拟合完整流程；目标电池的 $a_i,r_i$ 只能用其前 $h$ 个循环更新，不能使用第151—200循环。

### 4.3 层次信息共享

9块测试电池各来自一种策略。由于多个策略只有2块完整训练电池，首轮不估计策略专属核超参数，而在每个外层训练集的全部电池间共享 $\ell,\sigma_f,\sigma_n$；策略信息只进入式(16)—(18)的退化均值。策略专属核仅作为样本扩充后的敏感性模型。任何超参数都不能通过随机拆分循环点估计，以免泄漏未来状态。

### 4.4 预测验证矩阵

40块完整电池都模拟“只看到前 $h$ 个循环”，预测 $h+1$ 至200，取 $h\in\{50,100,120,150\}$。采用两类外层场景：

1. 已知策略预测：完整排除目标电池，只向模型提供该电池前 $h$ 个循环；其他同策略电池仍可训练；
2. 未见策略预测：整种策略从全局训练中删除，再向模型提供目标电池前 $h$ 个循环；仅连续参数完整的策略参与。

所有均值参数、核参数、标准化和超参数选择都必须在对应外层训练集内重做。

对预测集合 $\mathcal T_i$，报告

\[
RMSE_i=\sqrt{\frac1{|\mathcal T_i|}\sum_{t\in\mathcal T_i}
(\widehat y_{it}-y_{it})^2},
\tag{27}
\]

\[
MAE_i=\frac1{|\mathcal T_i|}\sum_{t\in\mathcal T_i}
|\widehat y_{it}-y_{it}|,
\tag{28}
\]

以及第200循环绝对误差、最大绝对误差和95%区间覆盖率。最终指标先在电池内汇总，再对电池取均值/中位数，不能让长序列电池获得更高权重。

### 4.5 80%寿命的概率外推

GP只负责已有早期观测电池的第151—200循环短期修正；200循环以后的主EOL外推采用模型二的单调参数均值。若把GP作为敏感性模型，则对每次后验或自助样本 $b$ 生成不含观测噪声的潜在轨迹 $f_i^{(b)}(t)$，定义首次通过时间

\[
L_{80}^{(b)}=\inf\{t:f_i^{(b)}(t)\le0.8\}.
\tag{29}
\]

若在预设最大外推循环 $T_{\max}$ 内不穿越，则记为右删失 $L_{80}^{(b)}>T_{\max}$。报告 $P(L_{80}\le T_{\max}\mid\mathcal D)$ 及已穿越样本的条件分位数；若超过一半样本删失，只能报告后验中位寿命大于 $T_{\max}$，不能给有限中位数。第151—200循环误差可称为验证误差，EOL只能称为外推不确定性。

## 5. 模型四：早期特征—未来轨迹的多任务Elastic Net基线

### 5.1 特征与响应

受早期寿命预测文献启发，但本题没有电压—容量曲线，因此只用现有循环变量。对每块训练电池和观察长度 $h$，从SOH、内阻、平均温度、充电时间分别提取首5循环均值、末5循环均值、稳健线性斜率、二次曲率、标准差和末值，并加入初始容量及可计算的 $T_0,J,H$。所有特征只能用第1至 $h$ 循环计算。

为保证预测在 $h$ 处连续，预测相对轨迹 $\Delta y_i(t)=y_i(t)-y_i(h)$，并在满足 $\Phi_m(h)=0$ 的预先固定三次B样条基上展开：

\[
\Delta y_i(t)=\sum_{m=1}^M a_{im}\Phi_m(t)+e_i(t).
\tag{30}
\]

由外层训练电池的未来真实轨迹估计系数矩阵 $\boldsymbol A=[a_{im}]$，早期特征矩阵记为 $\boldsymbol X$。在每个训练折内中心化两矩阵，使截距不受惩罚。采用行组稀疏的多任务Elastic Net：

\[
\widehat{\boldsymbol B}=
\arg\min_{\boldsymbol B}
\left\{
\frac1{2n}\|\boldsymbol A-\boldsymbol X\boldsymbol B\|_F^2
+\lambda\left[
\alpha\sum_j\|\boldsymbol B_{j\cdot}\|_2+
\frac{1-\alpha}{2}\|\boldsymbol B\|_F^2
\right]\right\}.
\tag{31}
\]

行组稀疏项使同一个早期特征在多个轨迹系数间共同进入或退出，岭项在强相关特征间稳定分配系数。预测轨迹为

\[
\widehat y_i(t)=y_i(h)+\sum_{m=1}^M
(\boldsymbol x_i^\mathsf T\widehat{\boldsymbol B})_m\Phi_m(t).
\tag{32}
\]

$M,\lambda,\alpha$ 必须在每个外层训练折内通过内层电池级验证选择，每个 $h$ 单独训练。若改用FPCA学习基函数，基函数也只能由外层训练电池学习；未见策略任务的内层划分同样按策略分组。不能先用全部40块完整电池选特征再回测。

### 5.2 定位

该模型是可复现的机器学习基线，适合检验温度、内阻等早期变量是否比只看SOH更有预测价值。其未来曲线形状受基函数限制，预测区间也不如高斯过程自然，因此不预设为最终主模型。策略参数可能直接编码策略身份，故必须分别报告“包含策略特征”和“不含策略特征”的结果，以识别特征泄漏或策略记忆效应。

## 6. 模型五：可信域内的充电时间—退化鲁棒多目标优化

### 6.1 充电时间代理模型

理想时间由式(13)给出，但数据中相同 $(4.8,0.8,4.8)$ 的两组平均时间不同，说明实际时间还受结构/批次及尾段充电影响。首轮对每个策略的电池平均充电时间做加权校准：

\[
\bar T_p=\gamma_0+\gamma_1T_0(\boldsymbol c_p)
+\gamma_S S_p+e_p,
\tag{33}
\]

权重取策略均值估计方差的倒数，参数和新策略预测区间用电池级自助法得到。若 $S_p$ 与数据批次重合，$\gamma_S$ 只表示联合关联。结构标签不是优化器可自由选择的因果决策变量，而是预先固定的情景；预测接口写为 $\widehat T(\boldsymbol c,S)$。式(13)的恒流、起始SOC和忽略恒压尾段假设不完全满足时，$T_0$ 只是校准解释变量，不是实际时间等式。

### 6.2 退化目标

选择一个可验证的规划周期 $N\le200$。连续新策略没有某块电池的前150循环，故只能调用模型二的总体退化代理，不能调用模型三的个体GP。令

\[
\eta(\boldsymbol c,S)=\beta_0+\beta_J\widetilde J(\boldsymbol c)
+\beta_H\widetilde H(\boldsymbol c)+\beta_SS,
\]

对式(18)的对数正态随机斜率积分，得到平均电池轨迹

\[
\mu_N(\boldsymbol c,S)=\alpha_0+\alpha_SS
-x_N\exp\!\left\{\eta(\boldsymbol c,S)+\frac{\sigma_{u_1}^2}{2}\right\}
-\exp(\kappa)x_N^2,
\]

从而

\[
D_N(\boldsymbol c,S)=1-\mu_N(\boldsymbol c,S).
\tag{34}
\]

若令 $u_{1i}=0$，得到的是中位个体而不是平均电池。对参数自助样本 $b$ 重新计算退化，并定义逐点风险调整分位数

\[
D_N^U(\boldsymbol c,S)=
Q_{1-\alpha}\!\left[D_N^{(b)}(\boldsymbol c,S)\mid\mathcal D\right].
\tag{35}
\]

式(35)若只抽参数，表示“平均电池退化均值”的不确定性；若还抽取个体随机效应，则表示“新电池退化”的预测分位数，二者必须分开报告。它是逐点风险调整目标，不宣称在整个连续搜索域同时具有 $1-\alpha$ 覆盖率。主优化使用可回测的 $D_{200}^U$，不直接使用未验证的 $L_{80}$；后者仅作敏感性指标。

### 6.3 可信可行域

固定结构情景 $S$，令该结构下的唯一完整参数点集合为 $\mathcal P_S$。新结构有6个不同坐标、仿射秩为3；旧结构只有2个不同坐标、仿射秩为1，因此两种结构绝不能混成同一凸包。分别在原始决策空间 $\boldsymbol c=(C_1,q,C_2)$ 和代理特征空间 $\boldsymbol z=(T_0,J,H)$ 标准化，定义保守几何插值域

\[
\mathcal C_{\mathrm{geom}}(S)=
\left\{\boldsymbol c:
\widetilde{\boldsymbol c}\in\operatorname{conv}
\{\widetilde{\boldsymbol c}_j:j\in\mathcal P_S\},
\quad d_c(\boldsymbol c)\le r_c,
\quad d_z(\boldsymbol c)\le r_z,
\quad C_1,C_2>0, 0\le q\le0.8
\right\}.
\tag{36}
\]

其中 $d_c,d_z$ 分别是到同结构最近实验点的标准化欧氏距离。凸包仅避免线性几何意义上的域外外推，不代表内部组合已经实验验证；邻域也只是局部性约束，不是安全保证。仅约7个留一策略折不足以可靠学习半径，故预先给出保守 $r_c,r_z$ 并做多组敏感性分析。旧结构的连续域只是一条线段；所有连续解均只称“候选实验点”。正式推荐首先来自9个已观测策略的离散Pareto前沿。

### 6.4 Pareto模型与解析性质

固定 $S$ 后，风险调整双目标问题为

\[
\min_{\boldsymbol c\in\mathcal C_{\mathrm{geom}}(S)}
\boldsymbol F^U(\boldsymbol c,S)=
\begin{pmatrix}
Q_{1-\alpha}[T^{(b)}(\boldsymbol c,S)\mid\mathcal D]\\
D_N^U(\boldsymbol c,S)
\end{pmatrix}.
\tag{37}
\]

策略 $a$ 支配策略 $b$，当且仅当两目标均不差且至少一个严格更优。论文同时给出名义均值前沿和式(37)的风险调整前沿，不能把不确定性惩罚造成的排序变化解释为真实性能变化。

为了从前沿中给出偏速度、均衡、偏寿命三种建议，令 $z_j^*$ 为理想点，$s_j>0$ 为固定尺度，采用不裁剪的正仿射标准化和增强切比雪夫问题

\[
\min_{\boldsymbol c\in\mathcal C_{\mathrm{geom}}(S)}
\max_j\left\{w_j\frac{F_j^U(\boldsymbol c,S)-z_j^*}{s_j}\right\}
+\rho\sum_jw_j\frac{F_j^U(\boldsymbol c,S)-z_j^*}{s_j},
\quad w_j>0,\ \rho>0.
\tag{38}
\]

若 $\mathcal C_{\mathrm{geom}}(S)$ 非空且紧、两个目标连续，则最优解存在。若最优解被另一可行解严格支配，最大项不增，而增强求和项因正权重至少严格下降一项，式(38)目标必然下降，与最优性矛盾。因此最优解是强Pareto有效解。

### 6.5 优化输出

最终不只给一个“最优参数”，而给：离散观测策略的正式Pareto前沿；同结构几何插值域内的探索性连续前沿；三种偏好下的代表解；相对基准策略的时间变化、第200循环SOH变化和预测区间；候选点在决策空间与代理特征空间到最近实验点的距离。只有当留一策略误差明显优于常数和最近邻基线、且不确定区间足够窄时才展示连续候选；这些候选必须经新实验验证，不能称为全局最优策略。

## 7. 五个模型之间的关系与首轮取舍

| 模型 | 主要任务 | 可直接验证的结论 | 不能越界声称的结论 | 首轮定位 |
|---|---|---|---|---|
| 函数型混合效应模型 | 问题1策略曲线比较 | 0—200循环策略差异、个体差异 | 单个参数的因果作用 | 主模型 |
| 应力特征约束退化模型 | 问题2参数关联、问题3外推均值 | 0—200循环拟合及留一策略误差 | 已验证的80%寿命 | 主模型/机理桥梁 |
| 半参数高斯过程 | 问题3轨迹与区间预测 | 第151—200循环预测误差和覆盖率 | 远期EOL真实精度 | 主预测候选 |
| 多任务Elastic Net | 问题3早期特征预测 | 与GP统一回测下的误差 | 复现文献电压曲线模型 | 基线模型 |
| 鲁棒Pareto优化 | 问题4策略推荐 | 观测策略与可信域内代理结果 | 全局最优或域外安全性 | 最终决策层 |

首轮实验不应同时把所有模型做得很复杂。推荐顺序为：先拟合模型一确定策略曲线差异；再比较模型二的线性/二次退化与单一/双应力特征；随后用统一截断回测比较模型二、模型三和模型四；只有代理模型通过验证后才运行模型五。

## 8. 必须执行的稳健性检查

1. 原始数据与三点修正后的清洗数据分别拟合，确认第12循环修正不会改变策略排序。
2. 对电池41分别使用原SOH、相对SOH和剔除该电池三种口径，检查基准异常的影响。
3. 比较独立残差、AR(1)残差及电池级聚类稳健标准误。
4. 比较线性退化、约束二次退化和GP均值模型，量化 $L_{80}$ 的结构不确定性。
5. 所有标准化、特征筛选、超参数选择均在交叉验证训练折内部完成。
6. 同时报告“已知策略下留一电池”和“整组留一策略”误差，区分同策略个体预测与新策略泛化。
7. 若连续策略代理在留一策略验证中明显劣于策略类别基线，则问题4只给离散策略推荐，不进行连续参数优化。

## 9. 当前结论

以上五个模型不是彼此竞争的五个孤立算法，而是从描述、解释、预测到决策的递进体系。模型一负责离散策略描述，模型二负责连续策略的总体退化代理，模型三负责已有电池获得早期数据后的个体预测，模型四作为预测基线，模型五只调用模型二与独立时间校准模型。当前数据最有把握支持的是0—200循环内的策略比较和151—200循环预测；连续参数效应因仅7个唯一参数坐标、强共线性和结构混杂而只能采用低维、收缩且分结构限制在几何插值域内的模型；80% SOH寿命必须以外推和敏感性分析的形式呈现。后续实验结果将决定高斯过程还是约束退化模型成为问题3主模型，也将决定问题4能否从离散策略比较扩展到探索性连续候选。
