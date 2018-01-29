import time
from cudatext import *
import os
import codecs
import re
import cudatext as ct
import cudatext_cmd


def is_wordchar(s):

    return s.isalnum() or s in '#@<_'


class Command:

    options_filename = os.path.join(app_path(APP_DIR_SETTINGS), 'cuda_autoit_helper.json')
    options = {'autoit_dir': 'C:\\Programs\\AutoIt3'}
    found_autoitdir = False
    vars = []
    functions = []
    times = []
    defs = []

    def __init__(self):

        acpfile = os.path.join(os.path.dirname(__file__), 'AutoIt.acp')

        if os.path.isfile(self.options_filename):
            with open(self.options_filename) as fin:
                self.options = json.load(fin)

        self.check_autoit_dir()

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


    def on_open(self, ed_self):

        if ed_self.get_prop(PROP_LEXER_CARET) == 'AutoIt':
#           print(time.strftime('[%H:%M:%S]'), 'open start')
            self.parse_text(ed_self, 1)
#           print(time.strftime('[%H:%M:%S]'), 'open end')


    def on_change_slow(self, ed_self):

        if ed_self.get_prop(PROP_LEXER_CARET) == 'AutoIt':
#           print(time.strftime('[%H:%M:%S]'), 'change start')
            self.parse_text(ed_self, 0)
#           print(time.strftime('[%H:%M:%S]'), 'change end')


    def on_save(self, ed_self):

        if ed_self.get_prop(PROP_LEXER_CARET) == 'AutoIt':
#           print(time.strftime('[%H:%M:%S]'), 'save start')
            self.parse_text(ed_self, 1)
#           print(time.strftime('[%H:%M:%S]'), 'save end')

    def parse_text(self, ed_self, withincludes=0):

        # with_includes: 0 - without or 1 - with included files
        file = ed_self.get_filename()
        text = ed_self.get_text_all()
        text = re.split('\r|\n', text)
        self.find_keywords(text, file, False, withincludes)


    def find_keywords(self, text, file, isincluded=False, withincludes=0):

        regvars = re.compile(r'\$(\w+)\s*(=|)', re.I)  # varname, maybe '=' -> gotodef
#       regvars = re.compile(r'[^(?:Const)]\s+\$(\w+)\s*(=|)', re.I)  # varname, maybe '=' -> gotodef
        regcons = re.compile(r'Const\s+\$(\w+)\s*(=.*)', re.I)  # var, value - Global Const $COLOR_AQUA = 0x00FFFF
        regfuns = re.compile(r'Func\s+(\w+)\s*\((.*?)\)', re.I)  # funcname, params
        regincs = re.compile(r'#include\s*(<|")(.*?)[>|"]', re.I)  # [<|"], filename
        iscomment = False

        filepath = os.path.dirname(file)
        line_nr = 0

        for line in text:
            line_nr += 1
            ls = line.strip()

            if ls.find(';') == 0:
                continue
            if ls.find('#cs') == 0 or ls.find('#comments-start') == 0:
                iscomment = True
            if ls.find('#ce') >= 0 or ls.find('#comments-end') >= 0:
                iscomment = False
            if iscomment is True:
                continue

            line = ' ' + line

            # find variables, not in includes files, only constants
            if not isincluded:
                foundvars = regvars.findall(line)
                for f in foundvars:
                    fx = '$' + f[0].strip(' ,()[]')
                    if fx != '$':
                        if fx not in self.vars:
                            self.vars.append(fx)
                        if f[1] == '=':
                            self.update_defs(fx, '', file, line_nr)

            # find constants
            foundcons = regcons.findall(line)
            for f in foundcons:
                fx = ''.join(['$', f[0].strip(), '|', f[1].strip()])
                if fx not in self.vars:
                    self.vars.append(fx)
                self.update_defs('$' + f[0].strip(), '', file, line_nr)

            # find functions
            foundfuns = regfuns.findall(line)
            for f in foundfuns:
                fx = ['Function', f[0], f[1]]
                if fx not in self.functions:
                    self.functions.append(fx)
                self.update_defs(f[0].strip(), '', file, line_nr)

            if withincludes == 0:
                continue

            # scan included files too
            foundincs = regincs.findall(line)
            for f in foundincs:
                if f[0] == '<':
                    # AutoIt UDFs <filename>
                    filei = os.path.join(self.options['autoit_dir'], 'Include', f[1])
                else:
                    # locale files "filename"
                    filei = os.path.join(filepath, f[1])

                if os.path.isfile(filei):
                    for t in self.times:
                        if t[0] == filei and os.path.getmtime(filei) == t[1]:
                            # file not changed
                            continue

                    for t in self.times:
                        if t[0] == filei:
                            self.times.remove(t)

                    self.times.append([filei, os.path.getmtime(filei)])
                    self.update_defs(f[1], '', filei, 0)

                    with codecs.open(filei, 'r', encoding='utf-8', errors='ignore') as text:
                        self.find_keywords(text, filei, True)


    def update_defs(self, x, y, file, line_nr):

        for dx in self.defs:
            if dx[0] == x and dx[1] == y:
                self.defs[self.defs.index(dx)] = ''
        self.defs = [z for z in self.defs if z != '']

        self.defs.append([x, y, file, line_nr])


    def on_goto_def(self, ed_self):

        params = self.get_params()
        if not params:
            return

        res = self.handle_goto_def(*params)
        if res is None:
            return True

        self.goto_file(*res)
        return True


    def handle_goto_def(self, text, fn, row, col):

        search = self.get_word_under_cursor(row, col)

        l_dlg = ''
        l_files = []
        for f in self.defs:
            if f[0].lower() == search:
                if os.path.isfile(f[2]) and [f[2], f[3]] not in l_files:
                    l_dlg += f[0] + ' - ' + f[1] + '\n'
                    l_files.append([f[2], f[3]])

        if len(l_files) == 1:
            # 1 result
            return (l_files[0][0], l_files[0][1], 0)
        elif len(l_files) > 1:
            # > 1 results
            goto = dlg_menu(MENU_LIST, l_dlg)
            return (l_files[goto][0], l_files[goto][1], 0)
        else:
            # 0 results
            msg_status('Goto - no definition found for : ' + search)

        return


    def get_word_under_cursor(self, row, col):

        line = ed.get_text_line(row).lower().replace('\t', ' ')
        line1 = ' ' + line[:col]
        line2 = line[col:] + ' '

        seps = ',:-!<>()[]{}\'"\t\n\r'
        for sep in seps:
            line1 = line1.replace(sep, ' ')
            line2 = line2.replace(sep, ' ')

        search = line1[line1.rfind(' ')+1:] + line2[:line2.find(' ')]
        return search


    def goto_file(self, filename, num_line, num_col=0):
        if not os.path.isfile(filename):
            return

        file_open(filename)
        ed.set_prop(PROP_LINE_TOP, str(max(0, num_line - 5)))  # 5 = Offset
        ed.set_caret(num_col, num_line - 1)
        msg_status('Goto "%s", Line %d' % (filename, num_line))


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
        while x > 0 and is_wordchar(line[x-1]):
            x -= 1
        len1 = x0 - x

        x = x0
        while x < len(line) and is_wordchar(line[x]):
            x += 1
        len2 = x - x0

        text = self.handle_autocomplete(*params)
        if not text:
            return True

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
                    pars = ''.join(['(', f[2].strip(), ')'])
                text += '|'.join([f[0].strip(), f[1].strip(), pars]) + '\n'

        for f in self.vars:
            if f.lower().find(search) == 0:
                text += '|'.join(['var', f.strip('$'), '\n'])

        return text


    def get_params(self):

        fn = ed.get_filename()
        carets = ed.get_carets()

        if len(carets) != 1:
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


    def show_config(self):

        if not os.path.isfile(self.options_filename):
            with open(self.options_filename, mode="w", encoding='utf8') as fout:
                json.dump(self.options, fout, indent=4)

        file_open(self.options_filename)


    def check_autoit_dir(self):

        if self.found_autoitdir:
            return

        if not os.path.isdir(self.options['autoit_dir']):
            self.show_config()
            msg_box('Please correct the AutoIt directory and restart CudaText.', MB_ICONERROR + MB_OK)
        else:
            self.found_autoitdir = True
