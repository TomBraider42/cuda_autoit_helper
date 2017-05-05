from cudatext import *
import cudatext as ct
import cudatext_cmd
import os


class Command:

    def __init__(self):
    
        self.functions = []
        
        if os.path.isfile(os.path.join(app_path(APP_DIR_DATA), 'autocomplete', 'AutoIt.acp')):
            with open(os.path.join(app_path(APP_DIR_DATA), 'autocomplete', 'AutoIt.acp')) as fin:
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
