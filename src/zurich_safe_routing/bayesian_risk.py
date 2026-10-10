"""Fully Bayesian partial pooling of buffered accident counts, using collapsed Gibbs / Metropolis sampling."""
import numpy as np
from scipy.special import gammaln

def fit_hour(counts, exposure, groups, draws=1200, warmup=1200, seed=42):
    """Poisson(E*lambda); lambda~Gamma(2,2/mu_group).

    log(mu_group)~Normal(log(mu_city),1); log(mu_city)~Normal(0,5).
    Edge shape=2 and group log SD=1 are explicit fixed regularization priors.
    All group and city means have sampled posteriors; no plug-in hyperparameter fit.
    """
    counts=np.asarray(counts,float);exposure=np.asarray(exposure,float)
    names,index=np.unique(groups,return_inverse=True)
    global_rate=max(counts.sum()/exposure.sum(),1e-6)
    chains=[];acceptance=[]
    for chain in range(4):
        rng=np.random.default_rng(seed+chain)
        state=np.r_[np.log(global_rate),np.full(len(names),np.log(global_rate))]+rng.normal(0,.1,len(names)+1)
        step=np.full(len(state),.12);accept=np.zeros(len(state));samples=[]
        def group_logpost(logmeans, city):
            rate=2/np.exp(np.clip(logmeans[index],-35,35))
            likelihood=2*np.log(rate)-(counts+2)*np.log(rate+exposure)
            return np.bincount(index,weights=likelihood,minlength=len(names))-.5*(logmeans-city)**2
        value=group_logpost(state[1:],state[0])
        for iteration in range(warmup+draws):
            precision=len(names)+1/25
            state[0]=rng.normal(state[1:].sum()/precision,1/np.sqrt(precision))
            value=group_logpost(state[1:],state[0])
            proposal=state[1:]+rng.normal(size=len(names))*step[1:]
            proposed=group_logpost(proposal,state[0])
            ok=np.log(rng.random(len(names)))<proposed-value
            state[1:]=np.where(ok,proposal,state[1:])
            accept[1:]+=ok
            if iteration<warmup and (iteration+1)%100==0:
                step[1:]*=np.exp((accept[1:]/100-.44)*.7);accept[:]=0
            if iteration>=warmup:samples.append(state.copy())
        chains.append(samples);acceptance.append(float(accept[1:].mean()/draws))
    chains=np.asarray(chains)
    # Classical R-hat and conservative autocorrelation ESS, reported explicitly.
    n=draws;within=chains.var(axis=1,ddof=1).mean(axis=0)
    between=n*chains.mean(axis=1).var(axis=0,ddof=1)
    rhat=np.sqrt(((n-1)/n*within+between/n)/within)
    ess=[]
    for j in range(chains.shape[2]):
        series=chains[:,:,j];centered=series-series.mean(axis=1,keepdims=True)
        var=np.mean(centered**2)
        total=0
        for lag in range(1,min(n//2,500),2):
            pair=sum(np.mean(centered[:,:n-k]*centered[:,k:])/var for k in (lag,lag+1))
            if pair<=0:break
            total+=pair
        ess.append(4*n/(1+2*total))
    flat=chains.reshape(-1,chains.shape[-1]);rng=np.random.default_rng(seed+100)
    selected=flat[np.linspace(0,len(flat)-1,240,dtype=int)]
    rates=np.empty((len(selected),len(counts)))
    means=np.zeros(len(counts));second=np.zeros(len(counts))
    for s in flat:
        rate=2/np.exp(s[1:][index])+exposure
        means+=(counts+2)/rate
        second+=(counts+2)*(counts+3)/rate**2
    means/=len(flat);second/=len(flat)
    for i,s in enumerate(selected):rates[i]=rng.gamma(counts+2,1/(2/np.exp(s[1:][index])+exposure))
    return dict(mean=means,sd=np.sqrt(np.maximum(second-means**2,0)),low=np.quantile(rates,.025,axis=0),high=np.quantile(rates,.975,axis=0),prior_weight=np.mean([2/(2+exposure*np.exp(s[1:][index])) for s in selected],axis=0),diagnostics=dict(max_classical_rhat=float(rhat.max()),min_autocorrelation_ess=float(min(ess)),acceptance=acceptance,draws_per_chain=draws,chains=4),hyperparameters={str(name):float(np.exp(flat[:,j+1]).mean()) for j,name in enumerate(names)})
