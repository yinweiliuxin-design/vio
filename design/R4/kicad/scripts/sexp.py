"""Minimal lossless S-expression parser/serializer for KiCad files (compact one-line style)."""
import re
class Sym(str):
    """bare atom (not quoted)"""
    pass
class QStr(str):
    """quoted string"""
    pass
TOK=re.compile(r'\s*(\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+)', re.S)
def parse(text):
    stack=[[]]; pos=0; n=len(text)
    while True:
        m=TOK.match(text,pos)
        if not m:
            if text[pos:].strip(): raise ValueError('junk at %d'%pos)
            break
        t=m.group(1); pos=m.end()
        if t=='(':
            stack.append([])
        elif t==')':
            l=stack.pop(); stack[-1].append(l)
        elif t[0]=='"':
            stack[-1].append(QStr(unescape(t[1:-1])))
        else:
            stack[-1].append(Sym(t))
    assert len(stack)==1
    return stack[0][0] if len(stack[0])==1 else stack[0]
def unescape(s):
    return re.sub(r'\\(.)', lambda m: {'n':'\n','t':'\t','\\':'\\','"':'"'}.get(m.group(1),'\\'+m.group(1)), s)
def escape(s):
    return s.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n').replace('\t','\\t')
def dumps(x):
    if isinstance(x,list):
        return '('+' '.join(dumps(e) for e in x)+')'
    if isinstance(x,QStr):
        return '"'+escape(x)+'"'
    if isinstance(x,(int,)): return str(x)
    if isinstance(x,float):
        r=repr(round(x,4))
        if r.endswith('.0'): r=r[:-2]
        return r
    return str(x)
def head(x): return x[0] if isinstance(x,list) and x else None
def find(x,name):
    for e in x:
        if isinstance(e,list) and e and e[0]==name: return e
    return None
def findall(x,name):
    return [e for e in x if isinstance(e,list) and e and e[0]==name]
def prop(sym,name):
    for e in findall(sym,'property'):
        if e[1]==name: return e
    return None
