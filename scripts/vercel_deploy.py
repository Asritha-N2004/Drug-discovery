"""Deploy this workspace with the existing authenticated Vercel CLI session.

Only selected application source is uploaded. Tokens, database credentials,
local databases, virtual environments and test files are never packaged.
"""
import argparse
import base64
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from vercel_account import request

ROOT=Path(__file__).resolve().parents[1]
TEAM='team_mBSnW4BbFvfU9uw4ou3uFFqn'
PROJECT='prj_R6Ngjqxh21QHllgIsgyxq9LRf7DM'
SCHEMA='nexus_inventory_v1'
STATE=ROOT/'.vercel-deploy-state.json'

def configure():
    values={'DATABASE_SCHEMA':SCHEMA,'APP_ENV':'production','VITE_REALTIME_MODE':'polling','CLOUD_INITIALIZE':'true','CORS_ORIGINS':'https://nexus-retail-allocation.vercel.app'}
    for key,value in values.items():
        request(f'/v10/projects/{PROJECT}/env?teamId={TEAM}&upsert=true','POST',{'key':key,'value':value,'type':'encrypted','target':['production','preview']})
    print('Configured isolated database schema, production mode and polling. Existing secrets retained.')

def package():
    paths=[ROOT/n for n in ['package.json','vercel.json','requirements.txt','backend/requirements-runtime.txt','backend/alembic.ini','frontend/package.json','frontend/index.html','frontend/tsconfig.json','frontend/vite.config.ts']]
    for directory in ['backend/app','backend/migrations','frontend/src','api']:
        paths.extend(p for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.db') and '.test.' not in p.name)
    return [{'file':p.relative_to(ROOT).as_posix(),'data':base64.b64encode(p.read_bytes()).decode(),'encoding':'base64'} for p in sorted(set(paths))]

def deploy(production=False):
    body={'name':'nexus-retail-allocation','project':PROJECT,'files':package(),'projectSettings':{'framework':None,'nodeVersion':'24.x','buildCommand':'npm run build','outputDirectory':'frontend/dist','installCommand':'npm install --no-audit --no-fund'},'meta':{'source':'codex-retail-inventory-workspace'}}
    if production:body['target']='production'
    deployment=request('/v13/deployments?teamId='+TEAM,'POST',body)
    state={'id':deployment['id'],'url':'https://'+deployment['url'],'target':deployment.get('target'),'project':PROJECT,'team':TEAM}
    STATE.write_text(json.dumps(state,indent=2))
    print(json.dumps(state))

def status():
    state=json.loads(STATE.read_text())
    deployment=request(f"/v13/deployments/{state['id']}?teamId={TEAM}")
    print(json.dumps({k:deployment.get(k) for k in ['id','url','readyState','errorCode','errorMessage','alias']}))

def promote():
    state=json.loads(STATE.read_text())
    deployment=request(f"/v13/deployments/{state['id']}?teamId={TEAM}")
    if deployment['readyState']!='READY':raise RuntimeError('Only a ready deployment can be promoted')
    request(f"/v10/projects/{PROJECT}/promote/{state['id']}?teamId={TEAM}",'POST')
    state['target']='production'
    state['production_url']='https://nexus-retail-allocation.vercel.app'
    STATE.write_text(json.dumps(state,indent=2))
    print(json.dumps({'promoted_deployment':state['id'],'url':state['production_url']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['configure','preview','production','status','promote'])
    args=parser.parse_args()
    try:
        {'configure':configure,'preview':deploy,'production':lambda:deploy(True),'status':status,'promote':promote}[args.action]()
    except HTTPError as error:
        payload=json.loads(error.read().decode())
        print(json.dumps({'http_status':error.code,'error':payload.get('error',{}).get('code'),'message':payload.get('error',{}).get('message')}))
        raise SystemExit(1)
    except Exception as error:
        # Database driver errors can embed connection information; avoid dumping them.
        print('Deployment operation failed:',type(error).__name__)
        raise SystemExit(1)
