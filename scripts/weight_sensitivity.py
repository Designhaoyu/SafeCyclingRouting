"""Sensitivity of existing normalized time-risk weighting on all campus ODs."""
from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd,networkx as nx
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from zurich_safe_routing.graph_builder import build_or_load_graph
from zurich_safe_routing.config import DEFAULT_CONFIG
from zurich_safe_routing.safety_data import load_safety_scores,attach_safety_scores_to_graph
from zurich_safe_routing.routing import prepare_edge_weights,add_balanced_weight

def main():
 out=ROOT/'results/weight_sensitivity';out.mkdir(parents=True,exist_ok=True)
 ods=pd.read_csv(ROOT/'results/benchmark_all_campus_od/od_pairs.csv')
 previous=pd.read_csv(ROOT/'results/benchmark_all_campus_od/route_metrics.csv')
 meta=json.loads((ROOT/'results/benchmark_all_campus_od/metadata.json').read_text())
 digest=hashlib.sha256(DEFAULT_CONFIG.real_safety_path.read_bytes()).hexdigest()
 assert digest==meta['scores_sha256'],'Run full benchmark again after changing risk scores'
 g=build_or_load_graph(allow_synthetic_fallback=False)
 attach_safety_scores_to_graph(g,load_safety_scores(DEFAULT_CONFIG.real_safety_path,time_period='8'));prepare_edge_weights(g)
 rows=[]
 for alpha in np.linspace(0,1,11):
  alpha=round(float(alpha),1);weight=add_balanced_weight(g,alpha=alpha,beta=1-alpha,base_weight='time')
  metrics={}
  for u,v,k,d in g.edges(keys=True,data=True):
   item=(float(d[weight]),float(d['travel_time_s'])/60,float(d['length'])/1000,float(d['risk_cost']))
   if (u,v) not in metrics or item[0]<metrics[u,v][0]:metrics[u,v]=item
  for campus,subset in ods.groupby('campus'):
   target=int(subset.destination_node.iloc[0]);costs,paths=nx.single_source_dijkstra(g.reverse(copy=False),target,weight=weight)
   for od in subset.itertuples():
    path=paths[od.origin_node];values=np.zeros(4)
    for a,b in zip(path[:-1],path[1:]):values+=metrics[b,a]
    assert np.isclose(values[0],costs[od.origin_node])
    rows.append(dict(pair_id=od.pair_id,campus=campus,alpha_time=alpha,beta_risk=round(1-alpha,1),time_min=values[1],distance_km=values[2],risk_exposure=values[3]))
  print('Completed alpha=',alpha,flush=True)
 routes=pd.DataFrame(rows)
 base=previous[previous.route_type.eq('fastest_time')].set_index('pair_id')
 for name in ['time_min','distance_km','risk_exposure']:routes['baseline_'+name]=routes.pair_id.map(base[name])
 routes['risk_reduction_pct']=100*(1-routes.risk_exposure/routes.baseline_risk_exposure)
 routes['time_penalty_pct']=100*(routes.time_min/routes.baseline_time_min-1)
 routes['distance_penalty_pct']=100*(routes.distance_km/routes.baseline_distance_km-1)
 routes['extra_time_min']=routes.time_min-routes.baseline_time_min
 assert len(routes)==len(ods)*11
 summary=[]
 for scope,df in [('all_campuses',routes)]+[(k,routes[routes.campus.eq(k)]) for k in ods.campus.unique()]:
  for alpha,s in df.groupby('alpha_time'):
   row=dict(scope=scope,alpha_time=alpha,beta_risk=round(1-alpha,1),n_pairs=len(s))
   for metric in ['risk_reduction_pct','time_penalty_pct','distance_penalty_pct','extra_time_min']:
    row[metric+'_mean']=s[metric].mean();row[metric+'_median']=s[metric].median()
   row['risk_improved_pct']=100*(s.risk_reduction_pct>1e-7).mean()
   row['risk_improved_with_time_le_15_distance_le_10_pct']=100*((s.risk_reduction_pct>1e-7)&(s.time_penalty_pct<=15+1e-7)&(s.distance_penalty_pct<=10+1e-7)).mean()
   summary.append(row)
 summary=pd.DataFrame(summary);total=summary[summary.scope.eq('all_campuses')].copy()
 # Report a transparent example decision rule, not a user-approved optimum.
 feasible=total[(total.time_penalty_pct_mean<=15+1e-7)&(total.distance_penalty_pct_mean<=10+1e-7)]
 choice=feasible.sort_values('risk_reduction_pct_mean',ascending=False).iloc[0]
 # Confirm key weights against previously computed objectives on every OD.
 checks=[]
 for alpha,strategy in [(0,'safest_route'),(.8,'balanced_route'),(1,'fastest_time')]:
  prior=previous[previous.route_type.eq(strategy)].set_index('pair_id')
  subset=routes[routes.alpha_time.eq(alpha)]
  # Endpoint min-max normalization subtracts an edge-count-dependent constant;
  # alpha=0/1 may differ from raw safest/fastest objectives; report rather than assume equality.
  delta=subset.time_min-subset.pair_id.map(prior.time_min)
  riskdelta=subset.risk_exposure-subset.pair_id.map(prior.risk_exposure)
  checks.append(dict(alpha=alpha,reference=strategy,max_abs_time_difference=float(delta.abs().max()),max_abs_risk_difference=float(riskdelta.abs().max())))
  if alpha==.8:assert np.allclose(delta,0) and np.allclose(riskdelta,0)
 routes.to_csv(out/'od_weight_tradeoffs.csv',index=False);summary.to_csv(out/'summary.csv',index=False)
 summary[summary.alpha_time.eq(.8)].to_csv(out/'selected_weight_summary.csv',index=False)
 fig,axes=plt.subplots(1,2,figsize=(11,4.5))
 for campus in ['all_campuses']+list(ods.campus.unique()):
  s=summary[summary.scope.eq(campus)]
  axes[0].plot(s.alpha_time,s.risk_reduction_pct_mean,'o-',label=campus)
  axes[1].plot(s.alpha_time,s.time_penalty_pct_mean,'o-',label=campus)
 axes[0].set(xlabel='Time weight alpha',ylabel='Mean model risk exposure reduction (%)')
 axes[1].set(xlabel='Time weight alpha',ylabel='Mean estimated travel time increase (%)')
 for ax in axes:ax.grid(alpha=.2);ax.legend(fontsize=8)
 fig.tight_layout();fig.savefig(out/'weight_sensitivity.png',dpi=180);plt.close(fig)
 fig,ax=plt.subplots(figsize=(7,5))
 ax.plot(total.time_penalty_pct_mean,total.risk_reduction_pct_mean,'o-')
 for r in total.itertuples():ax.annotate(f'alpha={r.alpha_time:g}',(r.time_penalty_pct_mean,r.risk_reduction_pct_mean),xytext=(4,4),textcoords='offset points',fontsize=8)
 ax.set(xlabel='Mean estimated time increase vs raw fastest (%)',ylabel='Mean model risk reduction vs raw fastest (%)',title='Time-risk trade-off, all campus ODs, 08:00');ax.grid(alpha=.2)
 fig.tight_layout();fig.savefig(out/'tradeoff_curve.png',dpi=180);plt.close(fig)
 lines=['# Weight sensitivity with Bayesian risk','',f'08:00, {len(ods):,} equal-weight campus OD pairs, 11 weights, {len(routes):,} routes. Existing balanced objective: alpha * time_norm + (1-alpha) * risk_cost_norm. Distance is an evaluation metric, not an optimization objective. Baseline is the raw fastest-time route.','', '| Time alpha | Risk beta | Mean risk reduction | Mean time increase | Mean distance increase | Mean extra min |','|---:|---:|---:|---:|---:|---:|']
 for r in total.itertuples():lines.append(f'| {r.alpha_time:.1f} | {r.beta_risk:.1f} | {r.risk_reduction_pct_mean:.2f}% | {r.time_penalty_pct_mean:.2f}% | {r.distance_penalty_pct_mean:.2f}% | {r.extra_time_min_mean:.2f} |')
 lines+=['',f'Example constraint-based selection: among tested weights with mean time increase <=15% and mean distance increase <=10%, alpha={choice.alpha_time:.1f}, beta={choice.beta_risk:.1f} yields the greatest mean risk reduction ({choice.risk_reduction_pct_mean:.2f}%). These thresholds are illustrative, not approved requirements; mean limits do not guarantee limits for every OD.', '', 'The user-selected default weight is time=0.8, risk=0.2; the full sweep is retained for comparison. No unique overall optimum is claimed. Values are model exposure reductions, not measured accident reductions. This is a discrete 0.1 grid at one hour; finer weights and other hours can change the preferred setting.', '', 'Endpoint caution: min-max normalization subtracts a constant per traversed edge. Therefore alpha=0 and alpha=1 do not necessarily reproduce raw safest and raw fastest routes; endpoint checks are in metadata.json. This analysis preserves the existing implementation.', '']
 (out/'report.md').write_text('\n'.join(lines),encoding='utf-8')
 (out/'metadata.json').write_text(json.dumps(dict(selected_final_weight={'alpha_time':0.8,'beta_risk':0.2},hour=8,od_pairs=len(ods),routes=len(routes),scores_sha256=digest,endpoint_checks=checks,example_constraint_choice=choice.to_dict()),indent=2),encoding='utf-8')
 print(total[['alpha_time','risk_reduction_pct_mean','time_penalty_pct_mean','distance_penalty_pct_mean','extra_time_min_mean']].to_string(index=False),flush=True)
 print('EXAMPLE CHOICE',choice.to_dict(),flush=True);print('CHECKS',checks,flush=True)
if __name__=='__main__':main()
