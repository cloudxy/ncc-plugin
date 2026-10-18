"""合成运行兼容探针：只归一插件/工作目录与生成时间，保留业务字段。"""
import hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path


def probe(root, work):
    root=Path(root).resolve();work=Path(work).resolve();assert not work.exists();work.mkdir();book=work/'book';prep=work/'prep';lib=work/'lib';lib.mkdir()
    env = {**os.environ, 'NCC_ACTOR': 'architecture-probe'}
    def norm(text):
     text=text.replace(str(root),'$PLUGIN').replace(str(work),'$WORK')
     return re.sub(r'\d{4}-\d\d-\d\d[ T]\d\d:\d\d:\d\d(?:\.\d+)?(?:\+00:00|Z)?','<TIME>',text)
    def files():return {p.relative_to(work).as_posix():norm(p.read_text()) for p in sorted(work.rglob('*')) if p.is_file()}
    commands=[('init', ['ncc_state.py','init',str(book),'--title','合成兼容测试'],0,False),
     ('status',['ncc_state.py','status',str(book)],0,True),
     ('chapter',['ncc_state.py','chapter','add',str(book),'1','--file','04-正文/ch-0001.md'],0,False),
     ('promise',['ncc_state.py','promise','add',str(book),'--type','悬念','--content','工牌是谁留下的','--ch','1'],0,False),
     ('promise-list',['ncc_state.py','promise','list',str(book)],0,True),
     ('gate-check',['ncc_state.py','gate',str(book),'soul','--action','check'],1,True),
     ('invalid-value',['ncc_state.py','gate',str(book),'unknown'],2,True),
     ('missing-argument',['ncc_state.py','chapter','add',str(book)],2,True),
     ('decon-coverage',['ncc_state.py','decon','coverage',str(lib)],1,True),
     ('prepare-init',['ncc_prepare.py','init',str(prep),'--title','合成准备','--purpose','接口验证','--scope','当前主题'],0,False),
     ('prepare-status',['ncc_prepare.py','status',str(prep)],0,True)]
    results=[]
    try:
     for name,args,expected,readonly in commands:
      before={str(p): (p.read_bytes(),p.stat().st_mtime_ns,p.stat().st_ino) for p in work.rglob('*') if p.is_file()};p=subprocess.run([sys.executable,str(root/'scripts'/args[0]),*args[1:]],cwd=work,capture_output=True,text=True,env=env);after=files()
      assert p.returncode==expected,(name,p.returncode,p.stdout,p.stderr)
      if readonly:assert before=={str(p): (p.read_bytes(),p.stat().st_mtime_ns,p.stat().st_ino) for p in work.rglob('*') if p.is_file()},(name,'read-only wrote data')
      results.append({'name':name,'code':p.returncode,'stdout':norm(p.stdout),'stderr':norm(p.stderr),'files':after})
     return results
    finally:shutil.rmtree(work)
