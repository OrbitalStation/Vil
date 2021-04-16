"""
.vhl - header file
.vil - source file

/usr/vil - standard library

Example:

"test.vhl"
fun hello :: void -> void

"test.vil"
source for "test.vhl"
import console inside
fun hello :: void -> void
   console.put("Hello, world!")

"main.vil"
import test
fun main :: void -> void
    test.hello()
"""

import sys
import tokenizer as tk
import disassembler as ds


args = {}

i = 1
while i < len(sys.argv):
    if sys.argv[i] == '-o':
        i += 1
        try:
            args.__getitem__('out')
            print("Duplicate of '-o' option")
            exit(1)
        except KeyError:
            args['out'] = sys.argv[i]
    else:
        try:
            # noinspection PyUnresolvedReferences
            args.__getitem__('in')
            print("Duplicate of filename")
            exit(1)
        except KeyError:
            args['in'] = sys.argv[i]
    i += 1

if not hasattr(args, 'out'):
    args['out'] = args['in'][:args['in'].rfind('.')] + '.s'


code = open(args['in']).read()

i = 0
while i < len(code):
    try:
        if code[i] == '\n':
            i += 1
            while code[i] + code[i + 1] + code[i + 2] + code[i + 3] == ' ' * 4:
                code = code[:i] + '\t' + code[i + 4:]
                i += 1
        else: i += 1
    except IndexError:
        pass


tokens = tk.parse(tk.tokenize(tk.decomment(code)))
ds.disassemble(tokens, args['out'], args['in'])
