"""冻结的 argparse 对外契约提取器，不运行命令处理器。"""
import argparse


def describe(parser):
    def value(v):
        if callable(v):return v.__module__+'.'+v.__qualname__
        if isinstance(v,dict):return {k:value(x) for k,x in v.items()}
        if isinstance(v,(tuple,list)):return [value(x) for x in v]
        return v
    result=[]
    def walk(p,path):
        actions=[]
        for a in p._actions:
            if isinstance(a,argparse._SubParsersAction):
                actions.append({'subparsers':list(a.choices),'dest':a.dest,'required':a.required})
            else:
                actions.append({k:value(getattr(a,k,None)) for k in ('dest','option_strings','type','choices','default','required','nargs','const','help')})
        result.append({'path':path,'actions':actions,'defaults':value(p._defaults)})
        for a in p._actions:
            if isinstance(a,argparse._SubParsersAction):
                for k,q in a.choices.items():walk(q,path+[k])
    walk(parser,[]);return result
