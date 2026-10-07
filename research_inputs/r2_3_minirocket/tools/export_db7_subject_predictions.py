#!/usr/bin/env python3
"""Real DB7 S21 prediction export using canonical raw MiniROCKET."""
import os, sys, json, hashlib, gc, time, pathlib
import numpy as np
from scipy.io import loadmat
from sklearn.linear_model import RidgeClassifierCV
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import config
from optimized_pipeline import load_subject_window_cache
from p01a_run_main_loso_benchmark import get_feature_extractor, N_RIDGE, split_by_repetition, stratified_subsample
from domain_adaptation import BatchedStandardScaler

DB='db7'; TARGET=21; SEED=42; WINDOW_MS=200; OVERLAP=.5; FS=2000
KERNELS=10000; MAX_TRAIN=50000; PER_SUBJECT=5000
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW_ROOT=pathlib.Path(os.environ.get('NINAPRO_DB7','data/ninapro/db7/subject21'))
OUT=ROOT/'outputs/predictions_db7_s21'; OUT.mkdir(parents=True,exist_ok=True)

def sha(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1<<20),b''): h.update(b)
 return h.hexdigest()

def raw_metadata(mat_path):
 d=loadmat(mat_path)
 emg=np.asarray(d['emg'],dtype=np.float32)
 if emg.ndim==2 and emg.shape[0] < emg.shape[1]: emg=emg.T
 stim=np.asarray(d.get('restimulus',d.get('stimulus'))).squeeze().astype(np.int32)
 rep=np.asarray(d['repetition']).squeeze().astype(np.int32)
 win=int(FS*WINDOW_MS/1000); step=int(win*(1-OVERLAP))
 rows=[]; start=0; cur_s=int(stim[0]); cur_r=int(rep[0])
 for i in range(1,len(stim)+1):
  boundary=i==len(stim) or int(stim[i])!=cur_s or int(rep[i])!=cur_r
  if not boundary: continue
  end=i
  if cur_s>0 and end-start>=100:
   n=(end-start-win)//step+1
   for j in range(max(0,n)):
    s=start+j*step; rows.append((str(mat_path),s,s+win,cur_s,cur_r))
  if i<len(stim): start=i; cur_s=int(stim[i]); cur_r=int(rep[i])
 return rows

def find_mats():
 paths=sorted(RAW_ROOT.rglob('*.mat'))
 if not paths: raise FileNotFoundError(f'No MAT under {RAW_ROOT}')
 return paths

def ridge_fit(X,y):
 scaler=BatchedStandardScaler(batch_size=5000); Xs=scaler.fit_transform(X)
 rng=np.random.RandomState(SEED); idx=rng.choice(len(y),min(N_RIDGE,len(y)),replace=False)
 sub=Xs[idx].copy(); ys=y[idx].copy(); del Xs; gc.collect()
 clf=None
 for kw in (dict(alphas=np.logspace(-3,6,15),gcv_mode='svd',store_cv_results=False),dict(alphas=np.logspace(-3,6,15))):
  try: clf=RidgeClassifierCV(**kw); clf.fit(sub,ys); break
  except TypeError: continue
 if clf is None: raise RuntimeError('RidgeClassifierCV construction failed')
 return scaler,clf,float(clf.alpha_)

def main():
 subjects=load_subject_window_cache(DB,WINDOW_MS,OVERLAP,False)
 by={int(s['subject_id']):s for s in subjects}; target=by[TARGET]
 mask_test,_,_=split_by_repetition(target['y'],target['rep_id'],held_out_fraction=.5,seed=SEED,min_reps_per_class_each_side=1)
 Xtest=target['X'][mask_test].astype(np.float32); ytest=target['y'][mask_test].astype(np.int32)
 xs=[]; ys=[]; total=0; train_ids=[]
 for sid in sorted(by):
  if sid==TARGET: continue
  x=by[sid]['X'].astype(np.float32); y=by[sid]['y'].astype(np.int32)
  if len(y)>PER_SUBJECT: x,y=stratified_subsample(x,y,PER_SUBJECT,SEED)
  xs.append(x); ys.append(y); total+=len(y); train_ids.append(sid)
  if total>=MAX_TRAIN: break
 X=np.vstack(xs); y=np.concatenate(ys)
 if len(y)>MAX_TRAIN: X,y=stratified_subsample(X,y,MAX_TRAIN,SEED)
 print('fit',X.shape,Xtest.shape,flush=True)
 rocket=get_feature_extractor('canonical',num_kernels=KERNELS,random_state=SEED,n_jobs=1)
 t=time.time(); F=rocket.fit_transform(X); Ft=rocket.transform(Xtest); print('features',F.shape,Ft.shape,time.time()-t,flush=True)
 scaler,clf,alpha=ridge_fit(F,y); del F,X,xs,ys; gc.collect(); Ft=scaler.transform(Ft)
 pred=clf.predict(Ft); score=clf.decision_function(Ft)
 if score.ndim==1: score=np.column_stack([-score,score])
 decision=np.max(score,axis=1).astype(float)
 mats=find_mats(); offsets=[]
 for mat in mats: offsets.extend(raw_metadata(mat))
 cand=[r for r in offsets if r[3]>0 and 1<=r[3]<=40]
 all_y=np.array([r[3]-1 for r in cand],dtype=np.int32); all_r=np.array([r[4] for r in cand],dtype=np.int32)
 if len(all_y)!=len(target['y']) or not np.array_equal(all_y,target['y']) or not np.array_equal(all_r,target['rep_id']):
  raise RuntimeError(f'raw/cache alignment failed: raw={len(all_y)} cache={len(target["y"])} labels_equal={np.array_equal(all_y,target["y"])} reps_equal={np.array_equal(all_r,target["rep_id"])}')
 src=[cand[i] for i in np.flatnonzero(mask_test)]
 model_id=f'{DB}_raw_canonical_seed{SEED}_loso_testS{TARGET:02d}'
 meta={'dataset':DB,'test_subject':TARGET,'training_subjects':train_ids,'feature_extractor':'canonical','kernel_count':KERNELS,'window_ms':WINDOW_MS,'overlap':OVERLAP,'seed':SEED,'classifier':'RidgeClassifierCV','best_alpha':alpha,'protocol_version':'R2.3-OVERRIDE-v1','raw_source_files':[str(m) for m in mats],'raw_source_sha256':{str(m):sha(m) for m in mats},'decision_score_only':True}
 (OUT/'model_metadata.json').write_text(json.dumps(meta,indent=2))
 rows=[]
 for i,(src_file,s,e,_,_) in enumerate(src):
  rows.append({'dataset':DB,'subject_id':TARGET,'source_file':src_file,'window_index':i,'sample_start':int(s),'sample_end':int(e),'timestamp_start_s':s/FS,'timestamp_end_s':e/FS,'timestamp_s':(s+e)/(2*FS),'true_label':int(ytest[i]),'predicted_label':int(pred[i]),'decision_score':float(decision[i]),'model_id':model_id,'model_version':'canonical-minirocket-ridge-v1','protocol_version':'R2.3-OVERRIDE-v1','seed':SEED})
 out=OUT/'S21_predictions.jsonl'; out.write_text('\n'.join(json.dumps(r) for r in rows)+'\n')
 metrics={'dataset':DB,'subject_id':TARGET,'n_test_windows':len(rows),'accuracy':float(np.mean(ytest==pred)),'decision_score_semantics':'RidgeClassifier decision_function max class score; not probability','source_mats':[str(m) for m in mats],'source_mat_sha256':{str(m):sha(m) for m in mats},'model_metadata_sha256':sha(OUT/'model_metadata.json'),'prediction_sha256':sha(out),'train_subjects':train_ids,'status':'PASS'}
 (OUT/'metrics.json').write_text(json.dumps(metrics,indent=2)); print(json.dumps(metrics,indent=2))
if __name__=='__main__': main()
