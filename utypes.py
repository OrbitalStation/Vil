import re
import enum
from typing import Union, List
from copy import copy


class Type:

    def __init__(self, name: str = '', size: int = 0, arithmetic: bool = False):
        self.name = name
        self.size = size
        self.arithmetic = arithmetic

    def __repr__(self):
        return f'{self.name}'


class TypeIndex:

    class Type(enum.IntEnum):
        Imm = 0,
        Ref = 1,
        Ptr = 2

    def isInt(self) -> bool:
        return 0 < self.index < 9

    def __init__(self, index: int = 0, tp: Type = Type.Imm, count: int = 0):
        """
        :param index: pos in 'types'
        :param tp:    T, T& or T*
        :param count: number of stars if tp is Type.Ptr
        """
        self.index = index
        self.type = tp
        self.count = count

    def __repr__(self):
        return f'types{self.index}' + ('&' if self.type == TypeIndex.Type.Ref else ('*' * self.count if self.type == TypeIndex.Type.Ptr else ''))

    def __eq__(self, other):
        return self.index == other.index and \
               self.type  == other.type  and \
               self.count == other.count

    def __copy__(self):
        r = TypeIndex()
        r.type = copy(self.type)
        r.index = copy(self.index)
        r.count = copy(self.count)
        return r


class Module:

    def __init__(self, name: str = ''):
        while name.find('.') != -1: name = name[:name.rfind('.')]
        self.name, self.exports, self.imports = name, [], []

    def __repr__(self):
        return f"Module '{self.name}'"


class Token(enum.IntEnum):
    Unknown = -1,

    Newline = 0,
    Number  = 1,
    Keyword = 2,
    Punct   = 3,
    User    = 4,
    Tab     = 5,
    Type    = 6


class TokenList:

    def __init__(self, dictionary: dict):
        self.dict = dictionary

    def __getitem__(self, item):
        for i in self.dict.keys():
            temp = re.match(i, item, re.RegexFlag.VERBOSE | re.RegexFlag.MULTILINE)
            if temp is not None: return self.dict[i]
        raise AttributeError

    def __iter__(self):
        return self.dict.__iter__()


class TokenSrc:

    # noinspection PyShadowingBuiltins
    def __init__(self, string: str = '', type: Token = Token.Unknown):
        self.string, self.type = string, type

    def __repr__(self):
        if self.type.value == Token.Type: return f"\nToken('{int(self.string)}')"
        else: return "Token(" + (f"'{self.string}', " if len(self.string) != 0 else '') + f"{self.type.name})"


class Pos:

    class Reg:

        def __init__(self, name: str = ''):
            self.name = name

    class Stack:

        def __init__(self, offset: int = 0):
            self.offset = offset

    class Mem:

        def __init__(self, address: str = ''):
            self.address = address

    def __init__(self, pos: Union[Reg, Stack, Mem] = None):
        self.pos = pos


class Fun:

    class Arg:

        def __init__(self, tp: TypeIndex = 0, name: str = '', pos: Pos = Pos()):
            self.type, self.name, self.pos = tp, name, pos

        def __str__(self):
            return str(self.type)

    def __init__(self, name: str = ''):
        self.name: str = name
        self.args: List[Fun.Arg] = []
        self.ret: TypeIndex = TypeIndex()
        self.code: Union[str, List[Union[Operand, str]]] = []

    def repr(self, add: str = '') -> str:
        s = f'fun{add} {self.name} :: '
        for i in range(len(self.args)):
            s += str(self.args[i]) + (', ' if i + 1 != len(self.args) else ' ')
        s += f'-> {self.ret}'
        return s

    def __repr__(self):
        return self.repr()


class OpList(list):

    class Obj:

        def __init__(self, possible: List[str], tp: Union[str, bool], arithmetic: bool, fun):
            self.possible = possible
            self.function = fun
            self.inline = tp if type(tp) == bool else tp == 'inline'
            self.arithmetic = arithmetic

        def __repr__(self):
            s = ('inline' if self.inline else '') + ' :: '
            for i in range(len(self.possible)):
                s += str(self.possible[i]) + (' ' if i + 1 != len(self.possible) else '')
            return s + '\n'

    class Operator:

        class Properties(enum.IntEnum):
            Nothing     = 0,
            Commutative = 1 << 0

        def __init__(self, name: str = '',
                     priority: int = 0,
                     operands: int = 0,
                     order: str = '',
                     props: int = Properties.Nothing,
                     funs: list = None,
                     fix: str = ''):
            self.name = name
            self.priority = priority
            self.funs: List[OpList.Obj] = funs
            self.operands = operands
            self.order = order == 'left'
            self.props = props
            self.fix = fix == 'postfix'

        def __repr__(self):
            return f"OPERATOR '{self.name}' => {self.funs}"

    def __init__(self, values: List[Operator], types: list):
        super().__init__(values)
        for cur in range(len(self)):
            for over in range(len(self[cur].funs)):
                for op in range(len(self[cur].funs[over].possible)):
                    for tp in range(len(types)):
                        s = self[cur].funs[over].possible[op]
                        if s.startswith(types[tp].name):
                            if s[-1] == '&':
                                c = len(s) - s.find('*') - 1 if s[-2] == '*' else 0
                                # noinspection PyTypeChecker
                                self[cur].funs[over].possible[op] = TypeIndex(tp, TypeIndex.Type.Ref, c)
                            elif s[-1] == '*':
                                # noinspection PyTypeChecker
                                self[cur].funs[over].possible[op] = TypeIndex(tp, TypeIndex.Type.Ptr, len(s) - s.find('*'))
                            else:
                                # noinspection PyTypeChecker
                                self[cur].funs[over].possible[op] = TypeIndex(tp, TypeIndex.Type.Imm)
                            break
        self.sort(key=lambda operator: operator.priority)


class Temp:

    class Imm:

        def __init__(self, value: str = ''):
            self.value = value

    class Mem:

        def __init__(self, address: str = ''):
            self.address = address

    class Reg:

        def __init__(self, reg: str = ''):
            self.name = reg

    class Stk:

        def __init__(self, offset: int = 0):
            self.offset = offset

    def __init__(self, tp: TypeIndex, value: Union[Imm, Mem, Reg, Stk], truetype: TypeIndex):
        self.type = tp
        self.truetype = truetype
        self.value = value

    def __eq__(self, other):
        return self.type == other.type and self.value == other.value


class Var(Fun.Arg):

    def __repr__(self):
        return f'let {self.name} :: {self.type}'


class Operand:

    def __init__(self, lvalue: bool = False, pos: int = 0):
        self.lvalue = lvalue
        self.pos = pos

    def __repr__(self):
        return ('var' if self.lvalue else 'tmp') + f'{self.pos}'

    def __eq__(self, other):
        return self.lvalue == other.lvalue and self.pos == other.pos


class OperandItself:

    def __init__(self, operand: Operand = Operand(), var: List[Var] = None, tmp: List[Temp] = None):
        self.type = copy(var[operand.pos].type if operand.lvalue else tmp[operand.pos].type)
        self.lvalue = operand.lvalue
        self.pos = operand.pos

    def __copy__(self):
        r = OperandItself()
        r.type = copy(self.type)
        r.lvalue = copy(self.lvalue)
        r.pos = copy(self.pos)
        return r


class Convert:

    def __init__(self, frm: str = '', to: str = '', fun=None):
        self.frm = frm
        self.to  = to
        self.fun = fun


class Block:

    def __init__(self, *too):
        self._b = False
        self._c = ''
        self._t = too

    def blocked(self) -> bool:
        for i in range(len(self._t)):
            if self._t[i].blocked(): return True
        return self._b

    def free(self) -> bool:
        return not self.blocked()

    def context(self) -> str:
        return self._c

    def block(self, context: str = '') -> None:
        self._b = True
        self._c = context
        for i in range(len(self._t)):
            self._t[i].block(context)

    def unblock(self) -> None:
        self._b = False
        self._c = ''
        for i in range(len(self._t)):
            self._t[i].unblock()


class Optimization:

    def __init__(self, what: str, into: str):
        self.what = what
        self.into = into


class TreeNode:

    def __init__(self, operator: int = 0, *operands):
        self.op = operator
        self.args = list(operands)

    def __repr__(self):
        return f'({self.op}, {self.args})'

    def __copy__(self):
        return TreeNode(copy(self.op), *copy(self.args))


# class CList:
#
#     def __init__(self, l = None, v = None):
#         if l is not None and v is not None:
#             self._l = l
#             self._v = v
#         else:
#             self._l = []
#             self._v = []
#
#     def clear(self):
#         self._l.clear()
#         self._v.clear()
#
#     def append(self, elem):
#         self._l.append(elem)
#         self._v.append(True)
#
#     def pop(self, item: int):
#         self._v[self._wrap(item)] = False
#
#     def _wrap(self, n: int):
#         if n < 0: n += len(self) - 1
#         i = 0
#         while i < len(self._l):
#             if self._v[i]:
#                 if n == 0: return i
#                 n -= 1
#             i += 1
#         raise IndexError(f'Bad index: {n}, size is {len(self)} (actually {len(self._l)})')
#
#     def find(self, item, start: int = None, stop: int = None, step: int = 1) -> int:
#         if stop is None: stop = len(self) if step > 0 else -1
#         if start is None: start = 0 if step > 0 else len(self) - 1
#         try:
#             for i in range(start, stop, step):
#                 if type(self[i]) == type(item):
#                     if self[i] == item: return i
#         except IndexError: pass
#         raise ValueError(f'{item} is not in list')
#
#     def __copy__(self):
#         return CList(copy(self._l), copy(self._v))
#
#     def __len__(self):
#         return len(self._l) - self._v.count(False)
#
#     def __getitem__(self, item: int):
#         return self._l[self._wrap(item)]
#
#     def __setitem__(self, index: int, item):
#         self._l[self._wrap(index)] = item
#
#     def __repr__(self):
#         s = '['
#         for i in range(len(self._l)):
#             if self._v[i]: s += repr(self._l[i]) + (', ' if i + 1 != len(self._l) else '')
#         s += ']'
#         return s


Opt = Optimization

nothing     = OpList.Operator.Properties.Nothing
commutative = OpList.Operator.Properties.Commutative


TokenList = TokenList({
    r'fun': Token.Keyword,
    r'ret': Token.Keyword,
    r'export': Token.Keyword,

    r'\$': Token.Keyword,

    r'::':  Token.Punct,
    r',':   Token.Punct,
    r'->':  Token.Punct,
    r'&':   Token.Punct,

    r'\+=': Token.Punct,
    r'-=':  Token.Punct,

    r'\*':  Token.Punct,
    r'\+':  Token.Punct,
    r'-':   Token.Punct,
    r'/':   Token.Punct,

    r'=': Token.Punct,

    r'[a-zA-Z][a-zA-Z0-9]*': Token.User,
    r'[0-9][0-9boxd]?[0-9a-fA-F]*': Token.Number,

    r'.*': Token.Unknown
})
