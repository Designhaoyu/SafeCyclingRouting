"""Evaluate all risk-covered intersection origins to both ETH campuses at 08:00."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from zurich_safe_routing.config import DEFAULT_CONFIG,Location
from zurich_safe_routing.graph_builder import build_or_load_graph,nearest_node
from zurich_safe_routing.safety_data import load_safety_scores,attach_safety_scores_to_graph
from zurich_safe_routing.routing import prepare_edge_weights,default_route_strategies,compute_route

def main():
    out=ROOT/'results/benchmark_all_campus_od';out.mkdir(parents=True,exist_ok=True)
    g=build_or_load_graph(allow_synthetic_fallback=False)
    scores=load_safety_scores(DEFAULT_CONFIG.real_safety_path,time_period='8')
    assert scores.risk_score.between(0,1).all() and not scores.edge_id.duplicated().any()
    covered=set()
    for r in scores.itertuples():
        u,v,k=int(r.u),int(r.v),int(r.key)
        if g.has_edge(u,v,k):covered.update((u,v))
    intersections={n for n,d in g.nodes(data=True) if int(d.get('street_count',0))>=3}
    origins=intersections&covered
    attach_safety_scores_to_graph(g,scores);prepare_edge_weights(g)
    strategies=default_route_strategies(g)
    rows=[];od_rows=[];excluded=[];validation=[];campus_counts={}
    for campus in DEFAULT_CONFIG.campus_destination_keys:
        destination=DEFAULT_CONFIG.example_locations[campus]
        target=nearest_node(g,destination)
        reachable=nx.ancestors(g,target)
        selected=sorted(origins&reachable)
        campus_counts[campus]=len(selected)
        for u in sorted(origins-{target}-reachable):excluded.append(dict(campus=campus,origin_node=u,reason='no_directed_path'))
        for u in selected:
            d=g.nodes[u];t=g.nodes[target]
            od_rows.append(dict(pair_id=f'{campus}_{u}',campus=campus,origin_node=u,destination_node=target,origin_lat=d['y'],origin_lon=d['x'],destination_lat=t['y'],destination_lon=t['x']))
        for strategy in strategies:
            distances,paths=nx.single_source_dijkstra(g.reverse(copy=False),target,weight=strategy.weight_attribute)
            # Concrete parallel edge selection matches choose_route_edges in the existing algorithm.
            edge_metrics={}
            for u,v,k,d in g.edges(keys=True,data=True):
                weight=float(d[strategy.weight_attribute])
                if (u,v) not in edge_metrics or weight<edge_metrics[u,v][0]:
                    edge_metrics[u,v]=(weight,float(d['length']),float(d['travel_time_s'])/60,float(d['risk_cost']))
            check_nodes=set(selected[::max(1,len(selected)//10)][:10])
            for u in selected:
                path=list(reversed(paths[u]))
                totals=np.zeros(4)
                for a,b in zip(path[:-1],path[1:]):totals+=edge_metrics[a,b][:4]
                cost,length,minutes,risk=totals
                assert length>0 and np.isclose(cost,distances[u])
                rows.append(dict(pair_id=f'{campus}_{u}',campus=campus,origin_node=u,destination_node=target,hour=8,route_type=strategy.name,distance_km=length/1000,time_min=minutes,risk_exposure=risk,mean_risk_score=risk/length,number_of_edges=len(path)-1,objective_cost=cost))
                if u in check_nodes:
                    d=g.nodes[u];direct=compute_route(g,Location(str(u),d['y'],d['x']),destination,u,target,strategy)
                    assert np.isclose(direct.combined_cost,cost), 'Reverse and forward objective differ'
                    validation.append(dict(campus=campus,origin_node=u,route_type=strategy.name,reverse_cost=cost,forward_cost=direct.combined_cost,same_path=path==direct.path_nodes))
            print(f'{campus}: {strategy.name}, {len(selected)} routes completed',flush=True)
    routes=pd.DataFrame(rows);ods=pd.DataFrame(od_rows)
    assert len(routes)==len(ods)*4 and not routes.duplicated(['pair_id','route_type']).any()
    for strategy,metric in [('fastest_time','time_min'),('shortest_distance','distance_km'),('safest_route','risk_exposure')]:
        optimum=routes[routes.route_type.eq(strategy)].set_index('pair_id')[metric]
        assert (routes[metric].to_numpy()>=routes.pair_id.map(optimum).to_numpy()-1e-7).all()
    comparisons=[]
    for baseline in ['fastest_time','shortest_distance']:
        base=routes[routes.route_type.eq(baseline)].set_index('pair_id')
        c=routes.copy();c['baseline']=baseline
        risk0=c.pair_id.map(base.risk_exposure);time0=c.pair_id.map(base.time_min);distance0=c.pair_id.map(base.distance_km)
        c['risk_reduction_pct']=100*(1-c.risk_exposure/risk0.replace(0,np.nan))
        c['time_penalty_pct']=100*(c.time_min/time0-1)
        c['distance_penalty_pct']=100*(c.distance_km/distance0-1)
        c['extra_time_min']=c.time_min-time0
        c['risk_reduction_absolute']=risk0-c.risk_exposure
        comparisons.append(c)
    comparisons=pd.concat(comparisons,ignore_index=True)
    summary=[]
    for scope,c in [('all_campuses',comparisons)]+[(k,comparisons[comparisons.campus.eq(k)]) for k in campus_counts]:
        for (baseline,strategy),s in c.groupby(['baseline','route_type']):
            entry=dict(scope=scope,baseline=baseline,route_type=strategy,n_pairs=len(s),zero_baseline_risk_pairs=int(s.risk_reduction_pct.isna().sum()))
            for metric in ['risk_reduction_pct','time_penalty_pct','distance_penalty_pct','extra_time_min']:
                entry.update({metric+'_mean':s[metric].mean(),metric+'_median':s[metric].median(),metric+'_p10':s[metric].quantile(.1),metric+'_p90':s[metric].quantile(.9)})
            entry['pairs_with_risk_reduction']=int((s.risk_reduction_absolute>1e-7).sum())
            entry['risk_improved_pct']=100*entry['pairs_with_risk_reduction']/len(s)
            entry['risk_improved_with_time_penalty_le_10pct_pct']=100*((s.risk_reduction_absolute>1e-7)&(s.time_penalty_pct<=10+1e-7)).mean()
            summary.append(entry)
    summary=pd.DataFrame(summary)
    ods.to_csv(out/'od_pairs.csv',index=False);routes.to_csv(out/'route_metrics.csv',index=False)
    comparisons.to_csv(out/'paired_tradeoffs.csv',index=False);summary.to_csv(out/'summary.csv',index=False)
    pd.DataFrame(excluded).to_csv(out/'excluded_origins.csv',index=False)
    pd.DataFrame(validation).to_csv(out/'forward_reverse_validation.csv',index=False)
    metadata=dict(risk_model="hierarchical_bayesian_gamma_poisson_50m_2011_2025",balanced_alpha_time=0.8,balanced_beta_risk=0.2,hour=8,graph_nodes=len(g),graph_edges=g.number_of_edges(),intersection_nodes=len(intersections),covered_intersection_nodes=len(origins),campus_od_counts=campus_counts,total_od_pairs=len(ods),routes=len(routes),missing_risk_edges=g.graph['safety_scores_missing_edges'],sampling='All risk-covered street_count >= 3 origins with a directed path to each campus; exclude destination itself',aggregation='Equal weight for every OD, no observed travel demand weighting',algorithm='Reverse single-source Dijkstra per destination and strategy; original forward edge weights; ties may select a different equally optimal path',forward_crosschecks=len(validation))
    for label,path in [('graph',DEFAULT_CONFIG.graph_cache_path),('scores',DEFAULT_CONFIG.real_safety_path)]:metadata[label+'_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    for ax,campus in zip(axes,campus_counts):
        s=comparisons[comparisons.campus.eq(campus)&comparisons.baseline.eq('fastest_time')&comparisons.route_type.eq('balanced_route')]
        image=ax.hexbin(s.time_penalty_pct,s.risk_reduction_pct,gridsize=45,mincnt=1,bins='log',cmap='viridis')
        ax.set(title=campus+' (balanced vs fastest)',xlabel='Estimated time increase (%)',ylabel='Model risk exposure reduction (%)')
        fig.colorbar(image,ax=ax,label='OD count (log scale)')
    fig.tight_layout();fig.savefig(out/'tradeoff.png',dpi=180);plt.close(fig)
    lines=['# All intersection-to-campus OD benchmark','',f'08:00; {len(ods):,} directed OD pairs; {len(routes):,} routes. Four unchanged routing objectives; balanced alpha=0.8, beta=0.2.','', '| Scope | Strategy | Mean risk reduction | Mean time penalty | Mean distance penalty | Mean extra minutes | Risk improved |','|---|---|---:|---:|---:|---:|---:|']
    for _,s in summary[summary.baseline.eq('fastest_time')].iterrows():lines.append(f'| {s.scope} | {s.route_type} | {s.risk_reduction_pct_mean:.2f}% | {s.time_penalty_pct_mean:.2f}% | {s.distance_penalty_pct_mean:.2f}% | {s.extra_time_min_mean:.2f} | {s.risk_improved_pct:.2f}% |')
    lines+=['','## Method and limitations','','- Origins are all current cached OSM nodes with street_count >= 3 and at least one incident edge present in the hourly safety table. Each campus destination is snapped to the existing graph. No additional municipal boundary clipping or physical-junction consolidation was performed.', f'- Reachable OD counts: {campus_counts}. The destination itself is excluded; unreachable origins are listed in excluded_origins.csv.', '- This is an exhaustive enumeration of the defined model population at 08:00, not observed OD flows. Every OD receives equal weight; no traffic demand data are used. Shared origins and overlapping routes mean OD results are correlated.', '- Risk exposure = sum(edge risk score * length in metres). Travel time follows existing road-class speeds. Results are model-based, not observed crash-probability reductions.', '- Paired percentages use each OD baseline denominator, then arithmetic means across OD pairs. Medians and 10th/90th percentiles are included. Zero baseline risk, if any, yields undefined percentage reduction and is counted separately.', '- No sample bootstrap confidence intervals are reported for this complete finite OD population. Risk-model uncertainty and effects of time of day remain outside this evaluation.', f'- {metadata["missing_risk_edges"]} graph edges without matched scores use the existing default risk score of 0.5; paths can traverse these edges.', f'- Reverse routing was checked against {len(validation)} original forward searches: objective costs agree. All {len(routes):,} route results were checked for the respective shortest/fastest/safest metric ordering. Equal-cost ties may produce alternate equally optimal paths.', '', 'Run: `D:/software/Anaconda/python.exe scripts/benchmark_all_campus_od.py`','']
    (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    print(summary[summary.baseline.eq('fastest_time')][['scope','route_type','n_pairs','risk_reduction_pct_mean','time_penalty_pct_mean','distance_penalty_pct_mean','extra_time_min_mean','risk_improved_pct']].to_string(index=False),flush=True)
    print(json.dumps(metadata,indent=2),flush=True)
if __name__=='__main__':main()
