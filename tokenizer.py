from utypes import *
from typing import List, Union


# Hotkeys
T = Token
L = TokenList
S = TokenSrc


def decomment(string: str) -> str:
    i = 0
    while i < len(string):
        try:
            if string[i] == '#':
                while string[i] != '\n': string = string[:i] + string[i + 1:]
            if string[i: i + 2] == '/*':
                while True:
                    if string[i] == '\n': i += 1
                    elif string[i: i + 2] == '*/':
                        string = string[:i] + string[i + 2:]
                        break
                    else: string = string[:i] + string[i + 1:]
        except IndexError: pass
        i += 1
    return string


def tokenize(string: str) -> List[S]:
    result = []
    while len(string) > 0:
        if string[0] == ' ':
            string = string[1:]
        elif string[0] == '\n':
            string = string[1:]
            result.append(S(type=T.Newline))
        elif string[0] == '\t':
            string = string[1:]
            result.append(S(type=T.Tab))
        else:
            for i in L:
                temp = re.match(i, string, re.RegexFlag.VERBOSE | re.RegexFlag.MULTILINE)
                if temp is not None:
                    temp2 = string[:temp.regs[0][1]]
                    result.append(S(temp2, L[temp2]))
                    string = string[temp.regs[0][1]:]
                    break
    return result


def parse(tokens: List[S]) -> List[Union[S, list]]:
    r = []
    i = 0
    while i < len(tokens):
        j = i
        while tokens[i].type == T.Newline: i += 1
        if tokens[i].type == T.Tab:
            r.append([])
            for k in range(i - j): r[-1].append(tokens[j])
            i += 1
            while i < len(tokens):
                try:
                    while tokens[i].type != T.Newline:
                        if tokens[i].type != T.Tab: r[-1].append(tokens[i])
                        i += 1
                    if tokens[i + 1].type != T.Tab and tokens[i + 1].type != T.Newline:
                        r.append(tokens[i])
                        break
                    else: r[-1].append(tokens[i])
                except IndexError: break
                i += 1
        else:
            for k in range(i - j): r.append(tokens[j])
            r.append(tokens[i])
        i += 1
    return r
