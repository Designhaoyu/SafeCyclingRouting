# Step 3 对接指南

这份文档给 Step 3 可视化同学使用。它说明 Step 3 应该如何调用 Step 2 路由算法，以及应该读取哪些输出文件。

## 1. 核心思路

Step 3 的需求是：

```text
用户在 GUI 中选择一个起点
目的地固定为 ETH Zentrum 和 ETH Hoenggerberg
系统展示不同策略下的推荐路线、距离、时间和风险指标
```

Step 2 不会提前生成“苏黎世所有起点到两个校区”的巨大路线数据库。正确流程是：

```text
Step 3 获取用户起点经纬度
        ↓
Step 3 调用 Step 2 脚本
        ↓
Step 2 在完整 Zurich cycling graph 中找到最近路网节点
        ↓
Step 2 计算到两个固定校区的路线
        ↓
Step 3 读取 Step 2 新生成的 GeoJSON 和 CSV
```

## 2. Step 3 需要的文件

Step 3 最主要需要这两个输出文件：

```text
results/step2_current_routes.geojson
results/step2_route_summary.csv
```

可选文件：

```text
results/step2_route_summary.md
results/step2_current_route_plot.png
```

其中：

- `step2_current_routes.geojson` 用来在地图上画路线。
- `step2_route_summary.csv` 用来展示路线指标，比如距离、时间、平均风险。
- `step2_route_summary.md` 是给人看的报告式摘要。
- `step2_current_route_plot.png` 是静态检查图，不是正式 GUI 必需文件。

## 3. Step 3 不应该直接读取什么

Step 3 一般不需要直接读取：

```text
data/processed/zurich_hourly_edge_safety_score.csv
data/raw/zurich_bike_graph.graphml
```

这两个文件是 Step 2 的内部输入：

- `zurich_hourly_edge_safety_score.csv` 是 Step 1 给 Step 2 的真实 hourly safety score。
- `zurich_bike_graph.graphml` 是 Step 2 使用的完整 Zurich 自行车路网。

Step 3 只需要把用户起点传给 Step 2，然后读取 Step 2 生成的结果文件。

## 4. 安装环境

在项目根目录运行：

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS 或 Linux 使用：

```bash
source .venv/bin/activate
```

## 5. Step 3 调用 Step 2 的命令

如果用户在地图上选择了一个起点，例如：

```text
latitude  = 47.37139
longitude = 8.51680
```

Step 3 可以调用：

```bash
python scripts/run_step2_pipeline.py --safety-file data/processed/zurich_hourly_edge_safety_score.csv --time-period 8 --origin-lat 47.37139 --origin-lon 8.51680 --origin-name "User selected start" --destination both_campuses
```

含义：

- `--safety-file`: 使用真实 Step 1 hourly safety 数据。
- `--time-period 8`: 使用早上 8 点的风险分数。真实数据里的 `h08` 会被自动识别。
- `--origin-lat`: 用户选择起点的纬度。
- `--origin-lon`: 用户选择起点的经度。
- `--origin-name`: 用户起点的显示名称，可以自由设置。
- `--destination both_campuses`: 同时计算到 ETH Zentrum 和 ETH Hoenggerberg 的路线。

如果 Step 3 想使用 17 点的风险数据：

```bash
python scripts/run_step2_pipeline.py --safety-file data/processed/zurich_hourly_edge_safety_score.csv --time-period 17 --origin-lat 47.37139 --origin-lon 8.51680 --origin-name "User selected start" --destination both_campuses
```

## 6. time_period 说明

真实数据中的 `time_period` 是：

```text
h00, h01, h02, ..., h23
```

但调用命令时可以写得更简单：

```text
--time-period 8
```

Step 2 会把以下写法都识别为同一个小时：

```text
8
08
h08
hour_08
08:00
```

## 7. GeoJSON 文件结构

`results/step2_current_routes.geojson` 是一个 GeoJSON `FeatureCollection`。

如果使用：

```text
--destination both_campuses
```

通常会得到：

```text
4 种路线策略 × 2 个校区 = 8 条完整路线
```

但是 GeoJSON 里不是“每条完整路线一个 feature”。现在每一个 feature 表示一小段路网 Link，也就是一条完整路线会被拆成几十个 `LineString`。这样 Step 3 可以按每一小段自己的风险值上色。

每一个 Link feature 的重要字段包括：

```text
geometry
properties.route_id
properties.route_type
properties.origin_name
properties.destination_name
properties.segment_index
properties.u
properties.v
properties.key
properties.edge_id
properties.risk_score
properties.safety_score
properties.length_m
properties.travel_time_s
properties.highway
properties.route_total_distance_km
properties.route_estimated_travel_time_min
properties.route_mean_risk_score
```

其中：

- `geometry` 是这一小段 Link 的坐标，坐标顺序是 `[longitude, latitude]`。
- `route_id` 可以把属于同一条完整路线的 Links 分组。
- `segment_index` 表示该 Link 在完整路线中的顺序。
- `route_type` 是路线策略，比如 `shortest_distance`、`fastest_time`、`safest_route`、`balanced_route`。
- `destination_name` 表示这条路线去哪个校区。
- `risk_score` 是这一小段 Link 自己的风险值，是 Step 3 做颜色映射最重要的字段。
- `length_m` 和 `travel_time_s` 是这一小段 Link 的物理属性。
- `route_mean_risk_score` 是整条完整路线的平均风险。

## 8. CSV 文件结构

`results/step2_route_summary.csv` 是路线指标表。Step 3 可以用它做卡片、表格或柱状图。

重要列包括：

```text
route_type
origin_name
destination_name
number_of_edges
estimated_travel_time_min
total_risk_exposure
mean_risk_score
total_distance_km
alpha
beta
```

推荐 Step 3 至少展示：

```text
route_type
destination_name
total_distance_km
estimated_travel_time_min
mean_risk_score
```

## 9. 路线策略说明

Step 2 默认输出 4 种路线策略：

```text
shortest_distance
fastest_time
safest_route
balanced_route
```

含义：

- `shortest_distance`: 距离最短。
- `fastest_time`: 估计时间最短。
- `safest_route`: 风险暴露最低。
- `balanced_route`: 时间和风险暴露同等重要，即 `alpha = 0.5`, `beta = 0.5`。

## 10. Step 3 的推荐流程

建议 Step 3 GUI 按这个流程做：

```text
1. 用户在地图上选择起点。
2. GUI 得到该点的 latitude 和 longitude。
3. GUI 调用 scripts/run_step2_pipeline.py。
4. 等脚本运行结束。
5. GUI 读取 results/step2_current_routes.geojson 画路线。
6. GUI 读取 results/step2_route_summary.csv 展示指标。
7. 如果用户换起点或换小时，重复步骤 3 到 6。
```

## 11. 注意事项

- 每次运行 Step 2 都会覆盖 `results/step2_current_routes.geojson` 和 `results/step2_route_summary.csv`。
- 如果 Step 3 需要保存多个用户查询结果，需要在 Step 3 端复制或重命名输出文件。
- 默认使用 `--time-period 8`。如果用户在 GUI 中选择了其他小时，Step 3 需要传入对应的 `--time-period`。
- 如果命令行显示少量 graph edges 没有匹配 safety file，通常可以接受；如果缺失数量很大，说明 Step 1 的 safety file 和 Step 2 的 OSM graph 可能不是同一份图。
