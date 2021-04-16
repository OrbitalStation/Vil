from typing import NoReturn, Tuple
from sys import stderr
from os import path
from utypes import *


modules: List[Module] = []
i = 0
j = 0
line = 1
file = ''
funcs: List[Fun] = []
esp = 0
var: List[Var] = []
tmp: List[Temp] = []
clist = [] # CList()
prior: int = 0
tks = None

types: List[Type] = [
    Type('void', 0, True),
    Type('i8',   1, True),
    Type('u8',   1, True),
    Type('i16',  2, True),
    Type('u16',  2, True),
    Type('i32',  4, True),
    Type('u32',  4, True),
    Type('i64',  8, True),
    Type('u64',  8, True),
]


converts = []


al  = Block()
ah  = Block()
ax  = Block(al, ah)
eax = Block(ax)
rax = Block(eax)

bl  = Block()
bh  = Block()
bx  = Block(bl, bh)
ebx = Block(bx)
rbx = Block(ebx)

cl  = Block()
ch  = Block()
cx  = Block(cl, ch)
ecx = Block(cx)
rcx = Block(ecx)

dl  = Block()
dh  = Block()
dx  = Block(dl, dh)
edx = Block(dx)
rdx = Block(edx)


result: Union[str, None] = None
resultOp = Operand()


def end(description: str, exitcode: int = 1) -> NoReturn:
    print(f'Error:\n\tline: {line}\n\tfile: {file}\n\tdescription: {description}', file=stderr)
    exit(exitcode)


def findIn(name: str, seq) -> int:
    for k in range(len(seq)):
        if seq[k].name == name: return k
    return -1


def numberType(number: str) -> TypeIndex:
    n = int(number)

    if 0 <= n <= 2 ** 8  - 1: return TypeIndex(findIn('u8', types))
    if 0 <= n <= 2 ** 16 - 1: return TypeIndex(findIn('u16', types))
    if 0 <= n <= 2 ** 32 - 1: return TypeIndex(findIn('u32', types))
    if 0 <= n <= 2 ** 64 - 1: return TypeIndex(findIn('u64', types))

    if -(2 ** (8  - 1)) <= n <= 2 ** (8  - 1) - 1: return TypeIndex(findIn('i8', types))
    if -(2 ** (16 - 1)) <= n <= 2 ** (16 - 1) - 1: return TypeIndex(findIn('i16', types))
    if -(2 ** (32 - 1)) <= n <= 2 ** (32 - 1) - 1: return TypeIndex(findIn('i32', types))
    if -(2 ** (64 - 1)) <= n <= 2 ** (64 - 1) - 1: return TypeIndex(findIn('i64', types))


def decT(value, d: int):
    if type(value) == Temp.Imm:
        return Temp.Imm(str(int(value.value) & (2 ** (8 * d) - 1)))
    elif type(value) == Temp.Reg:
        if value.name[1] == 'r':
            if d == 7: return Temp.Reg(f'%{value.name[2]}l')
            if d == 6: return Temp.Reg(f'%{value.name[2]}x')
            if d == 4: return Temp.Reg(f'%e{value.name[2]}x')
        if value.name[1] == 'e':
            if d == 3: return Temp.Reg(f'%{value.name[2]}l')
            if d == 2: return Temp.Reg(f'%{value.name[2]}x')
        if value.name[2] == 'x':
            return Temp.Reg(f'%{value.name[1]}l')
    return value # Mem & Stk


def varTtoTempT(v: Pos) -> Union[Temp.Stk, Temp.Reg]:
    return Temp.Reg(v.pos.name) if type(v.pos) == Pos.Reg else Temp.Stk(v.pos.offset)


def convert(op: Operand, to: TypeIndex) -> Union[Operand, None]:
    global prior
    op = OperandItself(op, var, tmp)
    if op.type.type == TypeIndex.Type.Ref and to.type != TypeIndex.Type.Ref:
        prior += 10
        op.type.type = to.type
    if op.type == to:
        if not op.type.isInt() or op.lvalue: prior += 100
        return Operand(op.lvalue, op.pos)
    if op.type.isInt() and to.isInt():
        prior += 3
        if _sizeof(op.type) <= _sizeof(to):
            if op.lvalue: return Operand(False, pushTemp(varTtoTempT(var[op.pos].pos), to,
                                                         optype(Operand(op.lvalue, op.pos))))
            return Operand(False, pushTemp(tmp[op.pos].value, to,  optype(Operand(op.lvalue, op.pos))))
        else:
            prior -= 2
            if op.lvalue: return Operand(False, pushTemp(
                varTtoTempT(var[op.pos].pos), to,
                optype(Operand(op.lvalue, op.pos))))
            return Operand(False, pushTemp(decT(tmp[op.pos].value, _sizeof(op.type) - _sizeof(to)), to,
                                           optype(Operand(op.lvalue, op.pos))))
    return None


def _frreg(sz: int) -> str:
    if sz == 64:
        if rax.free(): return '%rax'
        if rbx.free(): return '%rbx'
        if rcx.free(): return '%rcx'
        if rdx.free(): return '%rdx'
    if sz == 32:
        if eax.free(): return '%eax'
        if ebx.free(): return '%ebx'
        if ecx.free(): return '%ecx'
        if edx.free(): return '%edx'
    if sz == 16:
        if ax.free():  return '%ax'
        if bx.free():  return '%bx'
        if cx.free():  return '%cx'
        if dx.free():  return '%dx'
    if sz == 8:
        if al.free():  return '%al'
        if bl.free():  return '%bl'
        if cl.free():  return '%cl'
        if dl.free():  return '%dl'

        if ah.free():  return '%ah'
        if bh.free():  return '%bh'
        if ch.free():  return '%ch'
        if dh.free():  return '%dh'


def _regchkctx(ctx: str):
    if rax.context() == ctx: return '%rax'
    if rbx.context() == ctx: return '%rbx'
    if rcx.context() == ctx: return '%rcx'
    if rdx.context() == ctx: return '%rdx'

    if eax.context() == ctx: return '%eax'
    if ebx.context() == ctx: return '%ebx'
    if ecx.context() == ctx: return '%ecx'
    if edx.context() == ctx: return '%edx'

    if ax.context() == ctx: return '%ax'
    if bx.context() == ctx: return '%bx'
    if cx.context() == ctx: return '%cx'
    if dx.context() == ctx: return '%dx'

    if al.context() == ctx: return '%al'
    if bl.context() == ctx: return '%bl'
    if cl.context() == ctx: return '%cl'
    if dl.context() == ctx: return '%dl'

    if ah.context() == ctx: return '%ah'
    if bh.context() == ctx: return '%bh'
    if ch.context() == ctx: return '%ch'
    if dh.context() == ctx: return '%dh'


def _regbyname(name: str) -> Block:
    if name == '%rax': return rax
    if name == '%rbx': return rbx
    if name == '%rcx': return rcx
    if name == '%rdx': return rdx

    if name == '%eax': return eax
    if name == '%ebx': return ebx
    if name == '%ecx': return ecx
    if name == '%edx': return edx

    if name == '%ax': return ax
    if name == '%bx': return bx
    if name == '%cx': return cx
    if name == '%dx': return dx

    if name == '%al': return al
    if name == '%bl': return bl
    if name == '%cl': return cl
    if name == '%dl': return dl

    if name == '%ah': return ah
    if name == '%bh': return bh
    if name == '%ch': return ch
    if name == '%dh': return dh


def opteq(op: Operand, top: TypeIndex) -> bool:
    return optype(op) == top


def _sizeof(tp: TypeIndex) -> int:
    if tp.count > 0: return 8
    return types[tp.index].size


def zon(n: int) -> str:
    return '' if n is 0 else str(n)


def _opgettmp(t: Union[Temp.Imm, Temp.Reg, Temp.Mem, Temp.Stk]) -> str:
    if type(t) == Temp.Imm: return f"${t.value}"
    if type(t) == Temp.Mem: return f"({t.address})"
    if type(t) == Temp.Stk: return f"{zon(t.offset)}(%rbp)"
    return f"{t.name}"


def _opget(op: Operand) -> str:
    if op.lvalue:
        if type(var[op.pos].pos.pos) == Pos.Stack: return f"{zon(var[op.pos].pos.pos.offset)}(%rbp)"
        elif type(var[op.pos].pos.pos) == Pos.Reg: return f"{var[op.pos].pos.pos.name}"
    if tmp[op.pos].type.isInt(): return _opgettmp(tmp[op.pos].value)


def pushTemp(where: Union[Temp.Imm, Temp.Mem, Temp.Reg], tp2: TypeIndex, true: TypeIndex):
    r = Temp(tp2, where, true)
    for k in range(len(tmp)):
        if tmp[k] == r: return k
    tmp.append(r)
    return len(tmp) - 1


def _regget(s: str, base: str = 'a') -> str:
    if s == 'b': return f'%{base}l'
    if s == 'w': return f'%{base}x'
    if s == 'l': return f'%e{base}x'
    return f'%r{base}x'


def _reggetr(reg: str) -> str:
    if reg[2] == 'l' or reg[2] == 'h': return 'b'
    if reg[2] == 'x': return 'w'
    if reg[1] == 'e': return 'l'
    if reg[1] == 'r': return 'q'


def _pairreg(a: int, b: int, free: str = None) -> Tuple[str, str]:
    _max = max(a, b)
    _min = min(a, b)
    dif =  _max - _min
    if free is None: r = _frreg(_min)
    else: r = free

    if r[1] == 'r': raise ValueError(f"Cannot extend register '{r}' on {dif} bits, because it's maximum level")
    if r[1] == 'e':
        if dif == 32:
            return r, f'%r{r[2]}x'
        raise ValueError(f"Cannot extend register '{r}' on {dif} bits, possible is only '%r{r[2]}x'")
    if r[2] == 'x':
        if dif == 48:
            return r, f'%r{r[1]}x'
        if dif == 16:
            return r, f'%e{r[1]}x'
        raise ValueError(f"Cannot extend register '{r}' on {dif} bits, possible are '%r{r[1]}x', '%e{r[1]}x'")
    if r[2] == 'l':
        if dif == 56:
            return r, f'%r{r[1]}x'
        if dif == 24:
            return r, f'%e{r[1]}x'
        if dif == 8:
            return r, f'%{r[1]}x'
        raise ValueError(f"Cannot extend register '{r}' on {dif} bits, possible are '%r{r[1]}x', '%e{r[1]}x', '%{r[1]}x'")
    if r[2] == 'h':
        raise ValueError(f"Umm... Seriously? That's not a good idea to extend register, that is stored in HIGH bytes, not in LOW")
    raise ValueError(f"Bad register '{r}' (wants to be extended on {dif} bits)")


def optype(op: Operand) -> TypeIndex:
    return var[op.pos].type if op.lvalue else tmp[op.pos].type


def optruetp(op: Operand) -> TypeIndex:
    return var[op.pos].type if op.lvalue else tmp[op.pos].truetype


def opsz(op: Operand) -> int:
    if not op.lvalue and type(tmp[op.pos].value) == Temp.Imm: return 64
    return _sizeof(optruetp(op)) * 8


def opmaxsz(a: Operand, b: Operand) -> int:
    return max(opsz(a), opsz(b))


def ismem(op: Operand) -> bool:
    return type(var[op.pos].pos.pos) == Pos.Mem or type(var[op.pos].pos.pos) == Pos.Stack if op.lvalue else type(tmp[op.pos].value) == Temp.Mem or type(tmp[op.pos].value) == Temp.Stk


def isRvalue(op: Operand) -> bool:
    return not op.lvalue and type(tmp[op.pos].value) == Temp.Imm


def _base0(a: Operand, b: Operand, cmd: str, onlyop: bool) -> Tuple[str, Operand]:
    asz = opsz(a)
    bsz = asz if isRvalue(b) else opsz(b)
    ret = b if bsz > asz else a
    if onlyop: return '', ret
    if isRvalue(a): end(f"'{tmp[a.pos].value.value}' is not an l-value")
    if asz == bsz:
        if ismem(a) and ismem(b):
            free = _frreg(asz)
            return f'\tmov{_suffix(asz)}  {_opget(b)}, {free}\n\t{cmd}{_suffix(asz)}  {free}, {_opget(a)}\n', ret
        return f'\t{cmd}{_suffix(asz)}  {_opget(b)}, {_opget(a)}\n', ret
    else:
        if asz > bsz:
            if result is not None and _regbyname(result).context() == 'calculating':
                r, rb = _pairreg(asz, bsz, result)
                s = ''
            else:
                r, rb = _pairreg(asz, bsz)
                s = f'\txor{_suffix(asz)}  {rb}, {rb}\n\tmov{_suffix(bsz)}  {_opget(b)}, {r}\n'
            return f'\t{s}{cmd}{_suffix(asz)}  {rb}, {_opget(a)}\n', ret
        _b = _opgettmp(decT(varTtoTempT(var[b.pos].pos) if b.lvalue else tmp[b.pos].value, (bsz - asz) // 8))
        if ismem(a) and ismem(b):
            r = _frreg(asz)
            return f'\tmov{_suffix(asz)}  {_b}, {r}\n\t{cmd}{_suffix(asz)}  {r}, {_opget(a)}\n', ret
        else: return f'\t{cmd}{_suffix(asz)}  {_b}, {_opget(a)}\n', ret


def _base1(a: Operand, b: Operand, cmd: str, fun, onlyop: bool) -> Tuple[str, Operand]:
    global result, resultOp

    asz = opsz(a)
    bsz = opsz(b)

    if isRvalue(a):
        if isRvalue(b):
            n = fun(tmp[a.pos].value.value, tmp[b.pos].value.value)
            return '', Operand(False, pushTemp(Temp.Imm(n), numberType(n), TypeIndex(8)))
        asz = bsz

    msz = max(asz, bsz)
    lsz = min(asz, bsz)
    if bsz > asz:
        maxop = b
        minop = a
    else:
        maxop = a
        minop = b

    little = ''
    if result is None:
        if asz != bsz: little, result = _pairreg(asz, bsz)
        else:
            result = _frreg(msz)
            little = result
        _regbyname(result).block('calculating')
        was = True
    else:
        was = False

    if resultOp is None: resultOp = Operand(False, pushTemp(Temp.Reg(result), optype(maxop), optruetp(maxop)))

    if onlyop: return '', resultOp

    s = _reggetr(result)

    if was:
        if asz == bsz: return f'\tmov{_reggetr(result)}  {_opget(a)}, {result}\n\t{cmd}{_reggetr(result)}  {_opget(b)}, {result}\n', resultOp
        return f'\txor{_suffix(msz)}  {result}, {result}\n\tmov{_suffix(lsz)}  {_opget(minop)}, {little}\n\t{cmd}{s}  {_opget(maxop)}, {result}\n', resultOp
    little, free = _pairreg(_suffixr(_reggetr(result)), bsz)
    return f'\txor{_reggetr(result)}  {free}, {free}\n\tmov{_suffix(bsz)}' \
           f'  {_opget(b)}, {little}\n\t{cmd}{_reggetr(result)}  {free}, {result}\n', resultOp


def mov(a, b, o): return _base0(a, b, 'mov', o)
def add(a, b, o): return _base0(a, b, 'add', o)
def sub(a, b, o): return _base0(a, b, 'sub', o)


def plus(a, b, o):  return _base1(a, b, 'add', lambda x, y: int(x) + int(y), o)
def minus(a, b, o): return _base1(a, b, 'sub', lambda x, y: int(x) - int(y), o)


# def div(a, b):
#     pass


def _suffix(sz: int):
    if sz ==  8: return 'b'
    if sz == 16: return 'w'
    if sz == 32: return 'l'
    if sz == 64: return 'q'


def _suffixr(s: str):
    if s == 'b': return 8
    if s == 'w': return 16
    if s == 'l': return 32
    if s == 'q': return 64


def _opgetnum2(lvalue: bool, inline: str, fun) -> list:
    r = []
    k = 8
    lvalue = '&' if lvalue else ''
    inline = inline == 'inline'
    while k < 128:
        r.append(OpList.Obj([f'i{k}{lvalue}', f'i{k}'], inline, True, fun))
        r.append(OpList.Obj([f'u{k}{lvalue}', f'u{k}'], inline, True, fun))
        if not lvalue:
            r.append(OpList.Obj([f'i{k}', f'u{k}'], inline, True, fun))
            r.append(OpList.Obj([f'u{k}', f'i{k}'], inline, True, fun))
        k *= 2
    return r


opList: List[OpList.Operator] = OpList([
    OpList.Operator('=',  1, 2, 'left',  nothing,     _opgetnum2(True,  'inline', mov)),
    OpList.Operator('+=', 1, 2, 'left',  nothing,     _opgetnum2(True,  'inline', add)),
    OpList.Operator('-=', 1, 2, 'left',  nothing,     _opgetnum2(True,  'inline', sub)),
    OpList.Operator('+',  2, 2, 'right', commutative, _opgetnum2(False, 'inline', plus)),
    OpList.Operator('-',  2, 2, 'right', nothing,     _opgetnum2(False, 'inline', minus))
], types)


def _next(on: int, order: bool):
    return on if order else -on


def _build(ops: list, ret: TreeNode):
    operator = 0
    while operator < len(opList):
        prev = operator
        changed = False
        k = 0 if opList[operator].order else len(ops) - 1
        while True:
            if opList[operator].operands == 2:
                try:
                    if type(ops[k + _next(1, opList[operator].order)]) != str or \
                            ops[k + _next(1, opList[operator].order)] != opList[operator].name:
                        try:
                            while True:
                                operator += 1
                                if opList[operator].priority != opList[prev].priority:
                                    break
                                try:
                                    if ops[k + _next(1, opList[operator].order)] == opList[operator].name:
                                        changed = True
                                        break
                                except AttributeError:
                                    break
                            if not changed:
                                operator = prev
                                k += _next(1, opList[operator].order)
                                continue
                        except IndexError:
                            pass
                except IndexError:
                    break

                ret.op = operator
                if opList[operator].order:
                    if k == 0:
                        ret.args.append(ops[k])
                    else:
                        ret.args.append(TreeNode())
                        _build(ops[:k - 1], ret.args[0])
                        ops = ops[k:]

                    if k == len(ops) - 3:
                        ret.args.append(ops[len(ops) - 1])
                    else:
                        ret.args.append(TreeNode())
                        _build(ops[k + 2:], ret.args[1])
                        ops = ops[:k + 3]
                else:
                    if k == 2:
                        ret.args.append(ops[0])
                    else:
                        ret.args.append(TreeNode())
                        _build(ops[:k - 1], ret.args[0])
                        ops = ops[k:]
                        k = len(ops) - 1

                    if k == len(ops) - 1:
                        ret.args.append(ops[len(ops) - 1])
                    else:
                        ret.args.append(TreeNode())
                        _build(ops[k + 2:], ret.args[1])
                        ops = ops[:k + 3]

                if len(ops) == 1: return ret

                if not opList[operator].order: k -= 1
                ops.pop(k + 1)
                if not opList[operator].order: k -= 1
                ops.pop(k + 1)

                if changed: operator = prev
            else:
                k += _next(1, opList[operator].order)
            if opList[operator].order and k >= len(ops):
                break
            elif k < 0:
                break
            if len(ops) == 1: return ret
        operator += 1


def build_tree(ops) -> Union[TreeNode, None]:
    global j, opList, prior, result, resultOp

    if len(ops) == 1:
        ops.clear()
        return None

    ret = TreeNode()

    if result is not None:
        _regbyname(result).unblock()
        result = None
        resultOp = None
    _build(ops, ret)
    return ret


def extendTree(tree: TreeNode, self: bool = False) -> Union[str, Tuple[str, TreeNode]]:

    code = ''
    if type(tree.args[0]) == TreeNode:
        s, tree.args[0] = extendTree(tree.args[0], True)
        code += s
    if type(tree.args[1]) == TreeNode:
        s, tree.args[1] = extendTree(tree.args[1], True)
        code += s

    f = 0
    closest = []
    found = 0
    prr = 0
    first = True
    while f < len(opList[tree.op].funs):
        # noinspection PyTypeChecker
        if opteq(tree.args[0], opList[tree.op].funs[f].possible[0]) and opteq(tree.args[1], opList[tree.op].funs[f].possible[1]):
            closest = [tree.args[0], tree.args[1], f]
            break
        else:
            chg = len(tmp)
            # noinspection PyShadowingNames
            prior = 0
            # noinspection PyTypeChecker
            op1 = convert(tree.args[0], opList[tree.op].funs[f].possible[0])
            chg = len(tmp) - chg
            if op1 is not None:
                chg2 = len(tmp)
                # noinspection PyTypeChecker
                op2 = convert(tree.args[1], opList[tree.op].funs[f].possible[1])
                chg += len(tmp) - chg2
                if op2 is not None:
                    if first:
                        closest = [op1, op2, f]
                        prr = prior
                        found += 1
                        first = False
                    else:
                        if prr < prior:
                            closest = [op1, op2, f]
                            prr = prior
                            found = 0
                        else:
                            if prr == prior:
                                if not opList[tree.op].funs[closest[2]].possible[1].isInt() or not opList[tree.op].funs[f].possible[1].isInt():
                                    found += 1
                            for kk in range(chg):
                                tmp.pop(len(tmp) - 1)
        f += 1

    if len(closest) == 0: end(f"No overloads for operator '{opList[tree.op].name}'")
    elif found > 1: end(f"Multiple overloads for operator '{opList[tree.op].name}'")
    s, tree = opList[tree.op].funs[closest[2]].function(closest[0], closest[1], o=False)
    code += s
    if self: return code, tree
    else: return code


def disassemble(code: List[Union[TokenSrc, list]], to: str, fil: str):
    global modules, i, line, esp, funcs, types, var, opList, file, result
    file = fil

    def punct(name) -> bool:
        return tp() == Token.Punct and src() == name

    def comma() -> bool:
        return punct(',')

    def newline() -> bool:
        return tp() == Token.Newline

    def user() -> bool:
        return tp() == Token.User

    def src() -> str:
        return tok().string

    def tp() -> Token:
        try: return tok().type
        except AttributeError: pass

    def inc() -> None:
        global i, line
        try:
            if newline(): line += 1
            i += 1
        except IndexError: pass

    def jinc() -> None:
        global j, line
        try:
            if tok()[j].type == Token.Newline: line += 1
            j += 1
        except IndexError: pass

    def tok() -> Union[TokenSrc, List[TokenSrc]]:
        try: return code[i]
        except IndexError: pass

    def token(name: str) -> bool:
        return src() == name

    def isType(name) -> bool:
        for k in types:
            if k.name == name: return True
        return False

    def typeid(name) -> int:
        for k in range(len(types)):
            if types[k].name == name: return k
        return -1

    def grabType(Inc, Src, finish: bool = True) -> TypeIndex:
        if not isType(Src()):
            if finish: end(f"Unknown type '{Src()}'")
            else: return tuple()
        r1 = TypeIndex(typeid(Src()))
        Inc()
        r1.type = TypeIndex.Type.Ref
        if punct('*'):
            r1.type = TypeIndex.Type.Ptr
            while punct('*'):
                r1.count += 1
                Inc()
        return r1

    def fun():
        global esp, funcs, var, j
        try:
            if not token('fun'): return
        except AttributeError: pass
        inc()
        if not user(): end(f"bad name for function '{src()}'")
        funcs.append(Fun(src()))
        inc()
        if not punct('::'): end(f"incorrect syntax '{src()}'")
        while True:
            inc()
            tpid = grabType(inc, src)
            esp += _sizeof(tpid)
            pos = Pos(Pos.Stack(esp))
            funcs[-1].args.append(Fun.Arg(tpid, pos=pos))
            if user():
                funcs[-1].args[-1].name = src()
                inc()
            if punct('->'):
                inc()
                if not isType(src()): end(f"Unknown type '{src()}'")
                funcs[-1].ret = TypeIndex(typeid(src()))
                inc()
                break
            elif not comma(): end(f"Expected comma")
        types.append(Type(funcs[-1].repr('&'), 8))
        if type(tok()) != list: end(f"Expected tab")
        j = 0
        try:
            while j < len(tok()):
                if tok()[j].string == 'let':
                    jinc()
                    if tok()[j].type != Token.User: end(f"bad name for variable '{src()}'")
                    name = tok()[j].string
                    jinc()
                    if tok()[j].string != '::': end(f"incorrect syntax '{src()}'")
                    jinc()
                    tpid = grabType(jinc, lambda: tok()[j].string)
                    esp += _sizeof(tpid)
                    var.append(Var(tpid, name, Pos(Pos.Stack(esp))))
                elif tok()[j].type != Token.Newline: # noinspection PyTypeChecker
                    funcs[-1].code.append(findOps())
                try: jinc()
                except IndexError: inc()
        except TypeError: pass

    def findOps():
        global clist, j
        clist.clear()
        while tok()[j].type == Token.Newline: jinc()
        while len(tok()) > j and tok()[j].type != Token.Newline:
            if findIn(tok()[j].string, opList) != -1:
                clist.append(tok()[j].string)
            else:
                t = findIn(tok()[j].string, var)
                if t != -1: clist.append(Operand(True, t))
                else:
                    if tok()[j].type == Token.Number:
                        clist.append(Operand(False, pushTemp(Temp.Imm(tok()[j].string), numberType(tok()[j].string),
                                                             TypeIndex(8))))
            jinc()
        return copy(clist)

    modules.append(Module(file))

    while i < len(code):
        fun()
        inc()

    le = 0
    to = path.abspath(to)
    code = f'\t.file    "{to}"\n\t.code64\n\t.text\n\n'
    sz = 0
    for j in var:
        if type(j.pos.pos) == Pos.Stack: sz += types[j.type.index].size
    for j in range(len(funcs)):
        code += f'\t.globl   {funcs[j].name}\n\t.type    {funcs[j].name}, @function\n{funcs[j].name}:\n'
        if sz > 0: code += f'\tpushq %rbp\n\tmovq  %rsp, %rbp\n\tsubq  ${sz}, %rbp\n\n'
        for i in range(len(funcs[j].code)):
            cur = funcs[j].code[i]
            tree = build_tree(cur)
            # if tree.op == 0: # '='
            #     result =
            code += extendTree(tree)

            # find_ops(cur, False)
            #
            # k = 0
            # #
            # # while k < len(cur):
            # #     if type(cur[k]) == Operand:
            # #         if
            # #         # noinspection PyUnresolvedReferences
            # #         if not cur[k].lvalue:
            # #
            # #     k += 1
            #
            # for k in range(len(cur)):
            #     if type(cur[k]) == int:
            #         # noinspection PyUnresolvedReferences,PyTypeChecker
            #         cur[k] = opList[cur[k]].name
            # s = find_ops(cur, True)
            # code += s

        code += f'\n.LE{le}:\n'
        le += 1
        if sz > 0: code += f'\taddq  ${sz}, %rbp\n\tpopq  %rbp\n'
        code += f'\tretq\n\n\t.size    {funcs[j].name}, . - {funcs[j].name}\n'

    open(to, 'w').write(code)
