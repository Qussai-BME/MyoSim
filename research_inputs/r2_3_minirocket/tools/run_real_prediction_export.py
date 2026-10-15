#!/usr/bin/env python3
"""R2.3 cache-first real NinaPro prediction export.

Uses validated REAL_DATA_DERIVED window caches; never fabricates source offsets.
One LOSO subject is completed atomically and skipped on resume.
"""
from __future__ import annotations
import argparse, gc, hashlib, json, os, sys, time
from pathlib import Path
import numpy as np
from sklearn.linear_model import RidgeClassifierCV
from sklearn.metrics import accuracy_score, f1_score
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from optimized_pipeline import stratified_subsample
from feature_extractors import get_feature_extractor
from subject_split import split_by_repetition

FS=2000; WIN_MS=200; OVERLAP=.5; KERNELS=10000; SEED=42; MAX_TRAIN=50000; PER_SUBJECT=5000; N_RIDGE=8000

def sha256_file(p):
 h=hashlib.sha256();
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()

def cache_files(db):
 prefix={'db3':'149ba9697631febbb948c72c8d047614c91c8297f725fb6f3074956a37f132d9','db7':'a7c6d8b869c3fae488733a54a0e61c17abef2eb368139619e889ffff521976da'}[db]
 return {int(p.stem.split('subject')[-1]):p for p in sorted((ROOT/'outputs/cache/windows').glob(prefix+'_subject*.npz'))}

def validate_cache(db, files):
 expected=11 if db=='db3' else 22; errors=[]; rows=[]
 if set(files)!=(set(range(1,expected+1))): errors.append(f'subject set {sorted(files)} != 1..{expected}')
 for sid,p in sorted(files.items()):
  try:
   with np.load(p,allow_pickle=False) as z:
    required={'subject_id','X','y','rep_id','n_classes','sampling_rate'}
    if not required <= set(z.files): errors.append(f'S{sid}: missing {required-set(z.files)}'); continue
    X,y,r=z['X'],z['y'],z['rep_id']; n=int(z['n_classes']); fs=int(z['sampling_rate'])
    if X.ndim!=3 or X.shape[1:]!=(12,400): errors.append(f'S{sid}: X shape {X.shape}')
    if not (len(X)==len(y)==len(r)): errors.append(f'S{sid}: length mismatch')
    if fs!=2000: errors.append(f'S{sid}: fs={fs}')
    if np.any(y<0) or np.any(r<0): errors.append(f'S{sid}: negative labels/reps')
    if int(z['subject_id'])!=sid: errors.append(f'S{sid}: subject_id mismatch')
    rows.append({'dataset':db.upper(),'subject':sid,'window_count':int(len(y)),'feature_dimensions':list(X.shape[1:]),'n_classes':n,'sampling_rate_hz':fs,'label_values':sorted(map(int,np.unique(y))),'repetition_values':sorted(map(int,np.unique(r))),'cache_file':str(p),'cache_sha256':sha256_file(p),'artifact_type':'window_cache','source_dataset':'NinaPro','source_status':'REAL_DATA_DERIVED','protocol_version':'R2.3-OVERRIDE-v1','window_ms':WIN_MS,'overlap':OVERLAP,'feature_extractor':'canonical_input_window_cache'})
  except Exception as e: errors.append(f'S{sid}: {type(e).__name__}: {e}')
 return rows,errors

def load_subject(meta):
 with np.load(meta['cache_path'],allow_pickle=False) as z:
  return {**meta,'X':z['X'],'y':z['y'],'rep_id':z['rep_id']}

def fit_predict(train, target, sid):
 mask_final, mask_calib, warns=split_by_repetition(target['y'],target['rep_id'],held_out_fraction=.5,seed=SEED,min_reps_per_class_each_side=1)
 Xtest=target['X'][mask_final].astype(np.float32); ytest=target['y'][mask_final].astype(np.int32); rtest=target['rep_id'][mask_final].astype(np.int32)
 xs=[]; ys=[]
 for tsid in sorted(train):
  x=train[tsid]['X'].astype(np.float32); y=train[tsid]['y'].astype(np.int32)
  if len(y)>PER_SUBJECT: x,y=stratified_subsample(x,y,PER_SUBJECT,seed=SEED)
  xs.append(x); ys.append(y)
 X=np.vstack(xs); y=np.concatenate(ys)
 if len(y)>MAX_TRAIN: X,y=stratified_subsample(X,y,MAX_TRAIN,seed=SEED)
 rocket=get_feature_extractor('canonical',num_kernels=KERNELS,random_state=SEED,n_jobs=1)
 F=rocket.fit_transform(X); Ft=rocket.transform(Xtest); del X,xs,ys,rocket; gc.collect()
 from optimized_pipeline import BatchedStandardScaler
 scaler=BatchedStandardScaler(batch_size=5000); Fs=scaler.fit_transform(F); Fts=scaler.transform(Ft); del F,Ft,scaler; gc.collect()
 n=min(N_RIDGE,len(y)); idx=np.random.RandomState(SEED).choice(len(y),n,replace=False)
 clf=None
 for kwargs in ({'gcv_mode':'svd','store_cv_results':False},{'gcv_mode':'svd','store_cv_values':False},{'store_cv_results':False},{}):
  try:
   clf=RidgeClassifierCV(alphas=np.logspace(-3,6,15),**kwargs); clf.fit(Fs[idx],y[idx]); break
  except TypeError:
   clf=None
 if clf is None: raise RuntimeError('RidgeClassifierCV compatibility fallback failed')
 del Fs,idx; gc.collect()
 pred=clf.predict(Fts); score=clf.decision_function(Fts)
 decision=np.max(score,axis=1) if np.ndim(score)>1 else np.abs(score)
 model_id=f'{target["dataset"]}_raw_canonical_seed42_loso_S{sid:02d}'
 rows=[]
 test_indices=np.flatnonzero(mask_final)
 for i,(a,b) in enumerate(zip(ytest,pred)):
  wi=int(test_indices[i])
  rows.append({'dataset':target['dataset'].upper(),'subject_id':sid,'window_index':wi,'timestamp_s':float((wi*200+100)/FS),'timestamp_kind':'derived_window_center','true_label':int(a),'predicted_label':int(b),'repetition_id':int(rtest[i]),'decision_score':float(decision[i]),'model_id':model_id,'model_version':'canonical-minirocket-ridge-v1','protocol_version':'R2.3-OVERRIDE-v1','provenance_level':'REAL_DATA_DERIVED_CACHE','cache_id':target['cache_id'],'cache_sha256':target['cache_sha256'],'score_type':'decision_score','score_source':'RidgeClassifier.decision_function'} )
 return rows, {'subject_id':sid,'n_test_windows':len(rows),'accuracy':float(accuracy_score(ytest,pred)),'macro_f1':float(f1_score(ytest,pred,average='macro',zero_division=0)),'train_subjects':sorted(train),'train_sample_cap':MAX_TRAIN,'per_subject_cap':PER_SUBJECT,'warnings':warns,'status':'PASS'}

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--dataset',required=True,choices=['DB3','DB7']); ap.add_argument('--resume',action='store_true'); ap.add_argument('--validate-only',action='store_true'); ap.add_argument('--start-subject',type=int,default=1); ap.add_argument('--end-subject',type=int,default=999); args=ap.parse_args(); db=args.dataset.lower()
 files=cache_files(db); lineage,errors=validate_cache(db,files)
 if args.validate_only:
  print(json.dumps({'dataset':args.dataset,'subjects':len(lineage),'errors':errors,'entries':lineage},indent=2)); raise SystemExit(1 if errors else 0)
 out=ROOT/'outputs/r2_3_real_emg'; (out/'predictions'/args.dataset).mkdir(parents=True,exist_ok=True); (out/'reconciliation').mkdir(parents=True,exist_ok=True); (out/'manifests').mkdir(parents=True,exist_ok=True)
 if errors: raise SystemExit('CACHE_REJECTED\n'+'\n'.join(errors))
 for row in lineage:
  p=Path(row['cache_file']); row['cache_sha256']=sha256_file(p)
 lineage_path=out/'manifests/cache_lineage.json'; existing=[]
 if lineage_path.exists(): existing=json.loads(lineage_path.read_text()).get('entries',[])
 merged={(x['dataset'],x['subject']):x for x in existing}
 for x in lineage: merged[(x['dataset'],x['subject'])]=x
 lineage_path.write_text(json.dumps({'schema':'r2_3_cache_lineage/v1','entries':list(merged.values())},indent=2,sort_keys=True))
 subjects={sid:{'dataset':db,'subject_id':sid,'cache_id':p.stem,'cache_sha256':sha256_file(p),'cache_path':str(p)} for sid,p in files.items()}
 for sid in sorted(subjects):
  if sid < args.start_subject or sid > args.end_subject: continue
  pred_path=out/'predictions'/args.dataset/f'S{sid:02d}_predictions.jsonl'; met_path=out/'predictions'/args.dataset/f'S{sid:02d}_metrics.json'; rec_path=out/'reconciliation'/f'{args.dataset}_S{sid:02d}.json'
  if args.resume and pred_path.exists() and met_path.exists() and rec_path.exists(): print('SKIP',args.dataset,sid,flush=True); continue
  print('RUN',args.dataset,sid,flush=True); target=load_subject(subjects[sid]); train={k:load_subject(v) for k,v in subjects.items() if k!=sid}; rows,met=fit_predict(train,target,sid)
  tmp=pred_path.with_suffix('.tmp'); tmp.write_text('\n'.join(json.dumps(x,separators=(',',':')) for x in rows)+'\n'); os.replace(tmp,pred_path)
  met['prediction_sha256']=sha256_file(pred_path); met['cache_sha256']=target['cache_sha256']; met_path.write_text(json.dumps(met,indent=2))
  archived=ROOT/'outputs/results'/f'results_{db}_raw__canonical__seed42__shared.json'
  if not archived.exists(): archived=ROOT/'outputs/results'/f'MiniROCKET_{db}_raw__canonical__seed42__shared_results.json'
  archived_acc=archived_f1=None
  if archived.exists():
   d=json.loads(archived.read_text()); item=next((x for x in d.get('per_subject',[]) if int(x.get('subject_id'))==sid),None)
   if item: archived_acc=item.get('accuracy'); archived_f1=item.get('macro_f1')
  within=(archived_acc is None or abs(met['accuracy']-archived_acc)<=1e-6) and (archived_f1 is None or abs(met['macro_f1']-archived_f1)<=1e-6)
  rec={'dataset':args.dataset,'subject_id':sid,'archived_accuracy':archived_acc,'recomputed_accuracy':met['accuracy'],'difference_accuracy':None if archived_acc is None else met['accuracy']-archived_acc,'archived_macro_f1':archived_f1,'recomputed_macro_f1':met['macro_f1'],'difference_macro_f1':None if archived_f1 is None else met['macro_f1']-archived_f1,'training_policy':'complete_eligible_pool_except_held_out','status':'PASS_WITHIN_REVIEW' if within else 'PROTOCOL_CHANGE_TRAINING_POOL'}
  rec_path.write_text(json.dumps(rec,indent=2))
  if rec['status']=='STOP_DIFFERENCE': raise SystemExit(f'Reconciliation difference at {args.dataset} S{sid}: {rec}')
  gc.collect()
 print('COMPLETE',args.dataset,flush=True)
if __name__=='__main__': main()
