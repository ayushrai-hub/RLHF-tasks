#!/usr/bin/env bash
# Module B of the w7 toolchain.
# phase_b: read claim rows on stdin, group them by id, choose the surviving claim
# for each id from the rules in rules_contract.md, drop removed ids, and print one
# resolved row per id.
phase_b() {
  awk -F'\t' '
  {
    surf=$1; id=$2; ep=$3; role=$4; region=$5; act=$6;
    ids[id]=1;
    cand[id]=cand[id] (cand[id]==""?"":";") surf ":" ep ":" role ":" region;
    if (act=="retire") { retire[id]=1 }
    else if (act=="alias") { aliasq[id]=1; atarget[id]=role; aep[id]=ep }
    else if (surf=="r3") { r3s[id]=1; r3e[id]=ep; r3r[id]=role; r3g[id]=region }
    else if (surf=="r2") { r2s[id]=1; r2e[id]=ep; r2r[id]=role; r2g[id]=region }
    else if (surf=="r1") { if (!(id in r1e) || ep+0 > r1e[id]+0) { r1e[id]=ep; r1r[id]=role; r1g[id]=region } }
  }
  END {
    # Resolve every non-retired, non-alias host by authority.
    for (id in ids) {
      if (id in retire || id in aliasq) continue;
      if (id in r3s)      { res_d[id]="override";          res_s[id]="r3"; res_e[id]=r3e[id]; res_r[id]=r3r[id]; res_g[id]=r3g[id]; done[id]=1 }
      else if (id in r2s) { res_d[id]="verified_baseline";  res_s[id]="r2"; res_e[id]=r2e[id]; res_r[id]=r2r[id]; res_g[id]=r2g[id]; done[id]=1 }
      else if (id in r1e) { res_d[id]="freshest_probe";     res_s[id]="r1"; res_e[id]=r1e[id]; res_r[id]=r1r[id]; res_g[id]=r1g[id]; done[id]=1 }
    }
    # Ordered output.
    m=0; for (id in ids) { order[m++]=id }
    for (i=0;i<m;i++) for (j=i+1;j<m;j++) if (order[j] < order[i]) { t2=order[i]; order[i]=order[j]; order[j]=t2 }
    for (i=0;i<m;i++) {
      id=order[i];
      if (id in retire) {
        printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n", id, "retired", "-", "-", "-", "-", cand[id];
      } else if (id in done) {
        printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n", id, res_d[id], res_s[id], res_e[id], res_r[id], res_g[id], cand[id];
      }
    }
  }'
}
