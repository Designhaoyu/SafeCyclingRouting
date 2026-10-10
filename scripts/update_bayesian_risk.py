"""Rebuild hourly risk scores with hierarchical Bayesian partial pooling."""
from pathlib import Path
import sys,json,shutil
import numpy as np,pandas as pd,geopandas as gpd,osmnx as ox
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from zurich_safe_routing.bayesian_risk import fit_hour
from zurich_safe_routing.config import DEFAULT_CONFIG

def main():
    out=ROOT/'results/bayesian_risk';out.mkdir(parents=True,exist_ok=True)
    target=DEFAULT_CONFIG.real_safety_path
    backup=out/'zurich_hourly_edge_safety_score_before_bayes.csv'
    if not backup.exists():shutil.copy2(target,backup)
    graph=ox.load_graphml(DEFAULT_CONFIG.graph_cache_path)
    edges=ox.graph_to_gdfs(graph,nodes=False).to_crs(2056).reset_index()
    # Consolidate reverse directions with identical physical geometry and road class.
    def tags(x):return str(x[0]) if isinstance(x,list) else str(x)
    edges['road_class']=edges.highway.map(tags)
    def physical(row):
        coords=tuple(tuple(p) for p in row.geometry.coords)
        return (min(coords,coords[::-1]),row.road_class)
    keys=[physical(r) for r in edges.itertuples()]
    mapping={};ids=[]
    for key in keys:
        if key not in mapping:mapping[key]=len(mapping)
        ids.append(mapping[key])
    edges['physical_id']=ids
    physical_edges=edges.drop_duplicates('physical_id').sort_values('physical_id').copy()
    length=physical_edges.geometry.length.to_numpy()/1000
    # Same 50m neighborhood as the old model; length is a spatial proxy, not traffic exposure.
    buffers=gpd.GeoDataFrame(physical_edges[['physical_id']].copy(),geometry=physical_edges.geometry.buffer(50),crs=2056)
    raw=pd.read_csv(ROOT/'data/raw/roadtrafficaccidentlocations.csv')
    raw=raw[raw.AccidentInvolvingBicycle.astype(str).str.lower().eq('true') & pd.to_numeric(raw.MunicipalityCode,errors='coerce').eq(261)].copy()
    for col in ['AccidentHour','AccidentYear','AccidentLocation_CHLV95_E','AccidentLocation_CHLV95_N']:raw[col]=pd.to_numeric(raw[col],errors='coerce')
    raw=raw.dropna(subset=['AccidentHour','AccidentYear','AccidentLocation_CHLV95_E','AccidentLocation_CHLV95_N'])
    raw=raw[raw.AccidentHour.between(0,23)&raw.AccidentHour.eq(raw.AccidentHour.astype(int))].drop_duplicates('AccidentUID')
    points=gpd.GeoDataFrame(raw,geometry=gpd.points_from_xy(raw.AccidentLocation_CHLV95_E,raw.AccidentLocation_CHLV95_N),crs=2056)
    matched=gpd.sjoin(points[['AccidentUID','AccidentHour','geometry']],buffers,how='inner',predicate='within').drop_duplicates(['AccidentUID','physical_id'])
    counts=matched.groupby(['physical_id','AccidentHour']).size().unstack(fill_value=0).reindex(index=range(len(physical_edges)),columns=range(24),fill_value=0).fillna(0)
    years=int(raw.AccidentYear.max()-raw.AccidentYear.min()+1)
    exposure=np.maximum(length,.01)*years
    groups=physical_edges.road_class.to_numpy()
    penalties={'cycleway':0,'path':.05,'track':.05,'pedestrian':.05,'living_street':.1,'residential':.15,'service':.2,'unclassified':.25,'tertiary':.3,'tertiary_link':.35,'secondary':.45,'secondary_link':.5,'primary':.65,'primary_link':.7,'trunk':.9,'trunk_link':.9,'motorway':1,'motorway_link':1}
    penalty=edges.road_class.map(lambda x:penalties.get(x,.3)).to_numpy()
    diagnostics=[];tables=[];posterior=[]
    for hour in range(24):
        result=fit_hour(counts[hour].to_numpy(),exposure,groups,seed=20261010+hour*10)
        diagnostics.append(dict(hour=hour,**result['diagnostics'],group_posterior_means=result['hyperparameters']))
        mean=result['mean'][ids];spread=mean.max()-mean.min()
        normalized=(mean-mean.min())/spread if spread>0 else np.zeros(len(mean))
        risk=pd.Series(3*normalized+penalty).rank(method='average',pct=True).to_numpy()
        table=edges[['u','v','key']].copy();table['edge_id']=table.u.astype(str)+'_'+table.v.astype(str)+'_'+table.key.astype(str)
        table['time_period']=f'h{hour:02d}';table['risk_score']=risk;table['safety_score']=1-risk;table['highway']=edges.road_class
        table['risk_source']='hierarchical_bayesian_gamma_poisson_50m_2011_2025'
        tables.append(table)
        posterior.append(pd.DataFrame(dict(physical_id=range(len(physical_edges)),hour=hour,count=counts[hour].to_numpy(),length_km=length,posterior_rate_mean=result['mean'],posterior_rate_sd=result['sd'],posterior_rate_q025=result['low'],posterior_rate_q975=result['high'],prior_weight=result['prior_weight'],road_class=groups)))
        print('Hour',hour,'diagnostics',result['diagnostics'],flush=True)
    new=pd.concat(tables,ignore_index=True)
    assert len(new)==len(edges)*24 and not new.duplicated(['edge_id','time_period']).any() and new.risk_score.between(0,1).all()
    staged=out/'zurich_hourly_edge_safety_score_bayesian.csv';new.to_csv(staged,index=False)
    pd.concat(posterior,ignore_index=True).to_csv(out/'posterior_edge_hour_rates.csv',index=False)
    (out/'diagnostics.json').write_text(json.dumps(dict(years=years,accidents=len(raw),physical_segments=len(physical_edges),directed_edges=len(edges),hours=diagnostics),indent=2),encoding='utf-8')
    old=pd.read_csv(backup);comparison=new.merge(old[['edge_id','time_period','risk_score']],on=['edge_id','time_period'],suffixes=('_new','_old'))
    comparison['score_change']=comparison.risk_score_new-comparison.risk_score_old
    comparison.groupby('time_period').agg(n=('score_change','size'),mean_absolute_change=('score_change',lambda x:x.abs().mean()),mean_change=('score_change','mean')).to_csv(out/'score_comparison.csv')
    # Gate activation on convergence; keep candidate available if diagnostics fail.
    passed=all(d['max_classical_rhat']<1.05 and d['min_autocorrelation_ess']>=100 for d in diagnostics)
    if passed:shutil.copy2(staged,target)
    print('ACTIVATED:',passed,'candidate rows:',len(new),flush=True)
if __name__=='__main__':main()
