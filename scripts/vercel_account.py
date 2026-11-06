"""Inspect Vercel project metadata using the user's existing CLI session.

Credentials stay in process memory and are never printed or copied into source.
"""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

auth_path = Path(os.environ['APPDATA']) / 'com.vercel.cli' / 'Data' / 'auth.json'
auth = json.loads(auth_path.read_text(encoding='utf-8'))
token = auth.get('token')
if not token:
    raise SystemExit('Vercel CLI session has no access token. Sign in with the Vercel CLI.')

def request(path, method='GET', body=None):
    req = Request('https://api.vercel.com'+path, method=method,
                  headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'},
                  data=json.dumps(body).encode() if body is not None else None)
    with urlopen(req, timeout=60) as response:
        return json.load(response)

if __name__ == '__main__':
    teams=request('/v2/teams')
    team=next((t for t in teams.get('teams',[]) if t['slug']=='resum-projects'),None)
    if not team:raise SystemExit('Requested Vercel team not accessible with the CLI session.')
    print(json.dumps({'team_id':team['id'],'slug':team['slug']}))
    projects=request('/v9/projects?teamId='+team['id'])
    print(json.dumps([{'id':p['id'],'name':p['name'],'framework':p.get('framework')} for p in projects.get('projects',[]) if 'nexus' in p['name']]))
