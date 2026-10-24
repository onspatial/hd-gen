#!/usr/bin/env python3
"""Analyze paired simulation scores from one JSON file.

Usage:
    python analyze_transferability.py transferability_results.json --out results

Higher scores are assumed better. Correlations are invariant to jointly
reversing this convention, but winners, top-3, and regret are not.
"""
import argparse, csv, json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr, pearsonr, rankdata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def num_id(s):
    try: return int(s.rsplit('_', 1)[1])
    except (ValueError, IndexError): return s


def compute(path, out):
    out.mkdir(parents=True, exist_ok=True)
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    assert set(raw) == {'atl', 'bjng'}, f'Expected atl and bjng; got {list(raw)}'
    sim_ids = sorted(raw['bjng'], key=num_id)
    if set(sim_ids) != set(raw['atl']):
        raise ValueError('Simulation IDs differ by map')
    metric_ids = sorted(raw['bjng'][sim_ids[0]], key=num_id)
    for loc in ['bjng','atl']:
        for sid in sim_ids:
            if set(raw[loc][sid]) != set(metric_ids):
                raise ValueError(f'Metric IDs differ for {loc} {sid}')
    B = np.asarray([[raw['bjng'][sid][metric]['score'] for metric in metric_ids]
                  for sid in sim_ids], dtype=float)
    A = np.asarray([[raw['atl'][sid][metric]['score'] for metric in metric_ids]
                  for sid in sim_ids], dtype=float)
    if not (np.isfinite(A).all() and np.isfinite(B).all()):
        raise ValueError('NaN or infinite scores detected')

    n_sims, n_metrics = B.shape
    mean_B, mean_A = B.mean(axis=1), A.mean(axis=1)
    median_B, median_A = np.median(B, axis=1), np.median(A, axis=1)
    rank_B = rankdata(-mean_B, method='min').astype(int)
    rank_A = rankdata(-mean_A, method='min').astype(int)
    winner_B, winner_A = np.argmax(B, axis=0), np.argmax(A, axis=0)

    def correlations_per_metric(B, A):
        br = rankdata(B, axis=0, method='average')
        ar = rankdata(A, axis=0, method='average')
        br -= br.mean(axis=0, keepdims=True)
        ar -= ar.mean(axis=0, keepdims=True)
        denominator = np.sqrt(np.sum(br**2, axis=0) * np.sum(ar**2, axis=0))
        return np.divide(np.sum(br*ar, axis=0), denominator,
                         where=denominator>0,
                         out=np.full(B.shape[1], np.nan))

    metric_rho = correlations_per_metric(B, A)
    rho_excl = correlations_per_metric(B[1:], A[1:])
    global_spearman = spearmanr(mean_B, mean_A)
    global_pearson = pearsonr(mean_B, mean_A)
    winning_sim_idx = int(np.argmax(mean_B))
    atl_regret = A.max(axis=0) - A[winning_sim_idx]
    atl_span = A.max(axis=0) - A.min(axis=0)
    normalized_regret = np.divide(atl_regret, atl_span,
                                  where=atl_span>0,
                                  out=np.zeros_like(atl_regret))
    top3_B = np.argsort(-mean_B)[:3]
    top3_A = np.argsort(-mean_A)[:3]

    summary = {
        'assumption': 'Higher score is better; direct map score scales may differ',
        'simulation_count_per_map': n_sims,
        'metric_count_per_simulation': n_metrics,
        'score_count_per_map': int(n_sims*n_metrics),
        'raw_mean_beijing': float(B.mean()),
        'raw_mean_atlanta': float(A.mean()),
        'raw_score_range_beijing': [float(B.min()),float(B.max())],
        'raw_score_range_atlanta': [float(A.min()),float(A.max())],
        'spearman_over_10_simulation_means': float(global_spearman.statistic),
        'spearman_p_value': float(global_spearman.pvalue),
        'pearson_over_10_simulation_means': float(global_pearson.statistic),
        'beijing_best_overall_id': sim_ids[winning_sim_idx],
        'atlanta_best_overall_id': sim_ids[int(np.argmax(mean_A))],
        'top_3_ids_beijing': [sim_ids[k] for k in top3_B],
        'top_3_ids_atlanta': [sim_ids[k] for k in top3_A],
        'same_metric_winner_fraction': float(np.mean(winner_B==winner_A)),
        'beijing_overall_winner_best_atlanta_fraction': float(np.mean(winner_A==winning_sim_idx)),
        'median_metric_spearman': float(np.nanmedian(metric_rho)),
        'mean_metric_spearman': float(np.nanmean(metric_rho)),
        'metric_fraction_spearman_at_least_0_8': float(np.nanmean(metric_rho >= 0.8)),
        'undefined_metric_spearman_count': int(np.isnan(metric_rho).sum()),
        'mean_metric_spearman_without_id_0': float(np.nanmean(rho_excl)),
        'best_winner_agreement_without_id_0_fraction': float(np.mean(np.argmax(B[1:],axis=0)==np.argmax(A[1:],axis=0))),
        'normalized_regret_of_beijing_overall_winner_in_atlanta': float(normalized_regret.mean()),
        'median_normalized_regret': float(np.median(normalized_regret)),
    }
    with open(out/'summary.json','w',encoding='utf-8') as f:
        json.dump(summary,f,indent=2)

    with open(out/'simulation_summary.csv','w',newline='',encoding='utf-8') as f:
        w=csv.writer(f)
        w.writerow(['simulation','beijing_mean','atlanta_mean','beijing_median','atlanta_median',
                    'beijing_rank','atlanta_rank','atlanta_minus_beijing_mean',
                    'fraction_metric_score_higher_on_atlanta',
                    'fraction_best_per_metric_beijing','fraction_best_per_metric_atlanta'])
        for i, sid in enumerate(sim_ids):
            w.writerow([sid,*[float(x) for x in [mean_B[i],mean_A[i],median_B[i],median_A[i]]],
                        int(rank_B[i]),int(rank_A[i]),float(mean_A[i]-mean_B[i]),
                        float(np.mean(A[i]>B[i])),float(np.mean(winner_B==i)),
                        float(np.mean(winner_A==i))])

    with open(out/'metric_summary.csv','w',newline='',encoding='utf-8') as f:
        w=csv.writer(f)
        w.writerow(['metric_id','beijing_mean_score','atlanta_mean_score','beijing_winner',
                    'atlanta_winner','winner_agrees','ranking_spearman','normalized_transfer_regret'])
        for j, mid in enumerate(metric_ids):
            w.writerow([mid,float(B[:,j].mean()),float(A[:,j].mean()),
                        sim_ids[winner_B[j]],sim_ids[winner_A[j]],int(winner_B[j]==winner_A[j]),
                        float(metric_rho[j]) if np.isfinite(metric_rho[j]) else '',
                        float(normalized_regret[j])])

    # Figure 1: ranking slope chart, using within-city ranks to avoid scale assumptions.
    fig,ax=plt.subplots(figsize=(8.4,6.4),dpi=170)
    fig.patch.set_facecolor('white')
    lefts={i:str(i) for i in range(n_sims)}
    for i in sorted(range(n_sims),key=lambda j:j!=winning_sim_idx):
        important=i in top3_B
        color='#007f83' if i==winning_sim_idx else ('#4769a7' if important else '#a2abb6')
        lw=3.0 if i==winning_sim_idx else (2.1 if important else 1.15)
        alpha=1 if important else .67
        ax.plot([0,1],[rank_B[i],rank_A[i]],color=color,lw=lw,alpha=alpha,marker='o',ms=6 if important else 4,zorder=3 if important else 1)
        ax.text(-.055,rank_B[i],f'{sim_ids[i]}',fontsize=9,ha='right',va='center',color='#005f64' if i==winning_sim_idx else '#273142',fontweight='bold' if important else 'normal')
        ax.text(1.05,rank_A[i],f'{sim_ids[i]}',fontsize=9,ha='left',va='center',color='#005f64' if i==winning_sim_idx else '#273142',fontweight='bold' if important else 'normal')
    ax.set_xlim(-.45,1.45);ax.set_ylim(n_sims+.4,.55)
    ax.set_xticks([0,1],['Beijing','Atlanta'],fontweight='bold',fontsize=12)
    ax.set_yticks(range(1,n_sims+1));ax.set_ylabel('Rank (1 = highest mean score)',fontsize=10)
    ax.grid(axis='y',ls=':',alpha=.2);ax.spines[['top','right','bottom']].set_visible(False)
    ax.set_title('Simulation ranking transfers across maps',loc='left',fontsize=15,fontweight='bold',pad=18)
    fig.subplots_adjust(left=.2,right=.82,top=.85,bottom=.13)
    fig.savefig(out/'ranking_transfer.png',bbox_inches='tight');fig.savefig(out/'ranking_transfer.svg',bbox_inches='tight');plt.close(fig)

    # Figure 2: relationship of raw means; correlation, not equality, is the target.
    fig,ax=plt.subplots(figsize=(7.1,5.65),dpi=170)
    ax.scatter(mean_B,mean_A,s=62,color='#35659d',zorder=4,edgecolor='white',linewidth=.8)
    ax.scatter([mean_B[winning_sim_idx]],[mean_A[winning_sim_idx]],s=130,color='#007f83',zorder=5,edgecolor='white',linewidth=1.1)
    for i,sid in enumerate(sim_ids):
        ax.annotate(sid,(mean_B[i],mean_A[i]),xytext=(6,4 if i%2 else -12),textcoords='offset points',fontsize=9,color='#263b51')
    xline=np.linspace(min(mean_B)-2,max(mean_B)+2,100)
    coef=np.polyfit(mean_B,mean_A,1)
    ax.plot(xline,np.polyval(coef,xline),'--',color='#879aaa',lw=1.4,alpha=.9)
    ax.grid(alpha=.18,ls=':');ax.spines[['top','right']].set_visible(False)
    ax.set_xlabel('Beijing mean raw score (higher = better)')
    ax.set_ylabel('Atlanta mean raw score (higher = better)')
    ax.set_title('Mean-score relationship across 10 matched simulations',loc='left',fontsize=13,fontweight='bold',pad=17)
    ax.text(.04,.96,f'Pearson r = {global_pearson.statistic:.3f}  |  Spearman ρ = {global_spearman.statistic:.3f}',transform=ax.transAxes,va='top',fontsize=10,color='#354a5f',bbox=dict(facecolor='white',edgecolor='none',alpha=.85))
    fig.tight_layout();fig.savefig(out/'score_relationship.png',bbox_inches='tight');fig.savefig(out/'score_relationship.svg',bbox_inches='tight');plt.close(fig)

    # Figure 3: independent metric configurations' ranking correlations.
    fig,ax=plt.subplots(figsize=(7.1,5.2),dpi=170)
    finite_rho=metric_rho[np.isfinite(metric_rho)]
    ax.hist(finite_rho,bins=np.linspace(-1,1,61),color='#4769a7',edgecolor='white',linewidth=.35)
    ax.axvline(float(np.median(finite_rho)),color='#007f83',lw=2.5,label=f'Median = {np.median(finite_rho):.3f}')
    ax.axvline(.8,color='#bd7d32',lw=1.4,ls='--',label='Strong agreement threshold: 0.8')
    ax.set_xlim(-1,1);ax.set_xlabel('Spearman rank correlation per metric across 10 simulations');ax.set_ylabel('Number of metrics')
    ax.set_title('Metric-level ranking consistency',loc='left',fontsize=14,fontweight='bold',pad=17)
    ax.text(.05,.94,f'{100*np.mean(finite_rho>=.8):.1f}% of defined metric correlations ≥ 0.8',transform=ax.transAxes,fontsize=10,va='top',color='#2c3c51')
    ax.legend(fontsize=8,loc='upper left',bbox_to_anchor=(.05,.85),frameon=False)
    ax.spines[['top','right']].set_visible(False);ax.grid(axis='y',ls=':',alpha=.18)
    fig.tight_layout();fig.savefig(out/'metric_rank_consistency.png',bbox_inches='tight');fig.savefig(out/'metric_rank_consistency.svg',bbox_inches='tight');plt.close(fig)

    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('json',type=Path,help='single combined JSON with atl, bjng')
    parser.add_argument('--out',type=Path,default=Path('transferability_analysis'))
    args=parser.parse_args();compute(args.json,args.out)