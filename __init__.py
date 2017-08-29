from cudatext import *
import cudatext as ct
import cudatext_cmd
import os
import codecs
import re


class Command:

    def __init__(self):
    
        self.vars = []
        self.functions = []
        acpfile = os.path.join(os.path.dirname(__file__), 'AutoIt.acp')

        if os.path.isfile(acpfile):
            with codecs.open(acpfile, 'r', encoding='utf-8', errors='ignore') as fin:
                for line in fin:
                    sx = line.split(' ', 1)
                    if len(sx) == 1:
                        continue
                    s1 = sx[0]
                    sx = sx[1].split('|', 1)
                    s2 = sx[0]
                    s3 = sx[1] if len(sx) > 1 else ''
                    
                    if s2.find('('):
                        sx = s2.split('(', 1)
                        s2 = sx[0]
                        s3 = sx[1].strip('( )') if len(sx) > 1 else ''
                    
                    self.functions.append([s1, s2, s3])
        

    def on_change_slow(self, ed):
    
        if ed.get_prop(PROP_LEXER_CARET) == 'AutoIt':
            self.parse_text(ed)


    def parse_text(self, ed):
    
        file = ed.get_filename()
        text = ed.get_text_all()
        text = re.split('\r|\n',text)
        self.find_keywords(text)


    def find_keywords(self, text):   
        
        self.vars = []
        regvars = re.compile(r'\$(\w*)(?:\s|\[)', re.I)
        iscomment = False
            
        for line in text:
            ls = line.strip()
            
            if ls.find(';') == 0:
                continue
            if ls.find('#cs') == 0 or ls.find('#comments-start') == 0:
                iscomment = True
            if ls.find('#ce') >= 0 or ls.find('#comments-end') >= 0:
                iscomment = False
            if iscomment == True:
                continue
                    
            line = ' ' + line
            foundvars = regvars.findall(line)
            for fvar in foundvars:
                fvar = '$' + fvar.strip(' ,()[]')
                if fvar != '$':
                    if fvar not in self.vars:
                        self.vars.append(fvar)


    def on_func_hint(self, ed_self):
    
        params = self.get_params()
        if not params:
            return

        item = self.handle_func_hint(*params)
        if item is None:
            return
        else:
            return ' '+item
        

    def handle_func_hint(self, text, fn, row, col):

        line = ed.get_text_line(row).lower()
        search = line[:col].strip()
        end = search.rfind('(')
        start = search.rfind(' ', 0, end) + 1
        search = search[start:end].strip('( )')
        
        pars = ''
        for f in self.functions:
            if f[1].lower() == search:
                if f[2]:
                    pars = '( ' + f[2] + ' )'

        return pars


    def on_complete(self, ed_self):
    
        params = self.get_params()
        if not params:
            return

        text, fn, y0, x0 = params
        line = ed.get_text_line(y0)
        if not 0 < x0 <= len(line):
            return True

        x = x0
        while x>0 and is_wordchar(line[x-1]):
            x -= 1
        len1 = x0-x

        x = x0
        while x<len(line) and is_wordchar(line[x]):
            x += 1
        len2 = x-x0

        text = self.handle_autocomplete(*params)
        if not text: return True

        ed.complete(text, len1, len2)
        return True


    def handle_autocomplete(self, text, fn, row, col):
    
        line = ed.get_text_line(row).lower()
        search = line[:col]
        for s in ',([&\t':
            if s in search:
                search = search.replace(s, ' ')
        start = search.rfind(' ') + 1
        search = search[start:]
        text = ''
        
        for f in self.functions:
            if f[1].lower().find(search) == 0:
                pars = ''
                if f[2]:
                    pars = '(' + f[2] + ')'
                text += f[0] + '|' + f[1] + '|' + pars + '\n'
                
        for f in self.vars:
            if f.lower().find(search) == 0:
                text += 'var|' + f.strip('$') + '|\n'
                    
        return text


    def get_params(self):
    
        fn = ed.get_filename()
        carets = ed.get_carets()
        
        if len(carets)!=1:
            return
            
        x0, y0, x1, y1 = carets[0]

        if not 0 <= y0 < ed.get_line_count():
            return
            
        line = ed.get_text_line(y0)
        
        if not 0 <= x0 <= len(line):
            return

        text = ed.get_text_all()
        if not text:
            return
            
        return (text, fn, y0, x0)
        
        
def is_wordchar(s):
    return s.isalnum() or '#' in s or '@' in s or '<' in s or '_' in s

