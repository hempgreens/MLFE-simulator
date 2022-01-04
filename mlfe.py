version = 0.24
svc_mlfe_path = "lib.svc_mlfe"
macro_mlfe_path = "lib.macro_mlfe"
port_mlfe_path = "lib.port_mlfe"

import sys
import re
from enum import Enum
from time import sleep
from importlib import import_module

class Register:
    def __init__(self, adr_start):
        self.number_reg = 14
        self.gr = [0 for _ in range(self.number_reg)]
        self.pc = adr_start
        self.sp = get_bit_limit("logi", b=16)
        self.zf = False
        self.sf = False
        self.of = False
    def setGR(self, name: str, value: int):
        if(name[0:2] == "GR" and 0 <= int(name[2:]) < self.number_reg and type(value) == int):
            if(self.of):
                value = round_overflow(value)
            self.gr[int(name[2:])] = value
        elif(name == "SP"):
            print("Do not write Stack Pointer", file=sys.stderr)
        elif(name == "PC"):
            print("Do not write Program Counter", file=sys.stderr)
    def getGR(self, name: str):
        if(name[0:2] == "GR" and 0 <= int(name[2:]) < self.number_reg):
            return self.gr[int(name[2:])]
        elif(name == "SP"):
            return self.sp
        elif(name == "PC"):
            return self.pc
    def setFR(self, value: int):
        if(0 < value <= get_bit_limit("top")):
            self.of = False
            self.sf = False
            self.zf = False
        elif(value == 0):
            self.of = False
            self.sf = False
            self.zf = True
        elif(get_bit_limit("under") <= value < 0):
            self.of = False
            self.sf = True
            self.zf = False
        else:
            self.of = True
            self.sf = False
            self.zf = False
    def isREG(self, exp):
        return (
            type(exp) == str
            and exp[0:2]=="GR"
            and 0<=int(exp[2:])<self.number_reg
        ) or exp in ["SP", "PC"]

class Data():
    def __init__(self, data: list):
        self.mem = data
        self.stack = [-1, ]
    def isADDR(self, exp):
        return type(exp) == int and get_bit_limit("under", b=16) <= exp <= get_bit_limit("logi", b=16)
    def get_by_addr(self, p, reg, x=0):
        adr = arth_to_logi(round_overflow(x, b=16), bit=16) if x < 0 else x
        p = arth_to_logi(p, bit=16) if p < 0 else p
        to = (p+adr) % (get_bit_limit("logi", b=16)+1)
        if(reg.sp <= x <= get_bit_limit("logi", b=16) 
            and 0 <= (get_bit_limit("logi", b=16) - x - p) < len(self.stack)):
            return self.stack[65535 - x - p]
        elif(to < len(self.mem) and self.mem[to][0] == "DATA"):
            return self.mem[to][1]
        else:
            raise ExecutorException(f"Memory access failed: p={p} x={x}")

def print_all(_list, f='d'):
    if(f in {"d", "x", "b", "o"}):
        for i, e in enumerate(_list):
            print_line(e, i, f=f)
    else:
        raise ExecutorException("Option format error. Format character are d, x, b, o")

def print_line(line, num, f='d'):
    pad = {"d":5, "x":4, "b":8}
    sfx = {"d":"_d", "x":"_x", "b":"_b"}
    try:
        print(f"{num:{pad[f]}{f}}", end=" ")
        for e in line:
            if(type(e) is str):
                print(f"{e:<7}", end=" ")
            elif(type(e) is int):
                print(f"{e:<7{f}}", end=" ")
        print()
    except KeyboardInterrupt:
        raise ExecutorException("Interrupt Program")

def get_bit_limit(m, b=32) -> int:
    bit = b
    if(m == "top"):
        return (2 ** bit) // 2 - 1
    elif(m == "under"):
        return -(2 ** bit // 2)
    elif(m == "logi"):
        return (2 ** bit) - 1

def main(arg):
    if(len(arg) == 1 or arg[1] in ["--help", "-h"]):
        message_option_help()
        return
    elif(arg[1] in ["--version", "-v"]):
        global version
        print(f"Version: {version}")
        return

    x, adr_start = parse_data(arg[1])
    data = Data(x)
    if(data.mem is None or get_bit_limit("logi", b=16) <= len(data.mem) + 1):
        raise ExecutorException("Memory empty or length over 16bit")
    reg = Register(adr_start)
    state = Status.CONTINUE
    option = arg[2] if 3 <= len(arg) else None
    f = arg[3][-1] if len(arg) == 4 else 'd'
    if(option in ["--dry-assembly", "-d"]):
        if(4 < len(arg) and arg[4].isdecimal()):
            print_all(data.mem[:int(arg[4])], f=f)
        else:
            print_all(data.mem, f=f)
        return
    
    elif(option in ["--show-assembly", "-s", "-a"]):
        print_all(data.mem, f=f)
        print()
    while(True):
        if(option in ["--trace-line", "-t", "-a"]):
            f = f if f in ["d", "x", "b", "o"] else "d"
            print_line(data.mem[reg.pc], reg.pc, f=f)
        state = executor(data.mem[reg.pc], reg, data)
        if(option in ["--clock-speed", "-c"]):
            sleep(float(arg[3]))
        if(Status.ERROR == state):
            raise ExecutorException(f"Error raised. Address = {reg.pc}")
        elif(Status.EXIT == state):
            return
        
def calc_num(reg:Register, typ:str, name:str, a:int, b:int):
    v = 0
    if(typ == "aa"):
        v = a + b
    elif(typ == "al"):
        v = arth_to_logi(a) + arth_to_logi(b)
    elif(typ == "sa"):
        v = a - b
    elif(typ == "sl"):
        v = arth_to_logi(a) - arth_to_logi(b)
    elif(typ == "ma"):
        v = a * b
    elif(typ == "ml"):
        v = arth_to_logi(a) * arth_to_logi(b)
    elif(typ == "da"):
        v = a // b
    elif(typ == "dl"):
        v = arth_to_logi(a) // arth_to_logi(b)
    
    if(typ[1] == "l" and (v < 0 or get_bit_limit("top") < v)):
        reg.of = True
        top = get_bit_limit("top")
        if(0 < v):
            v = v % (top+1)
        else:
            while(0 < v):
                v += top+1
        v = logi_to_arth(v)
    else:
        reg.setFR(v)
    reg.setGR(name, v)

def calc_logi(reg:Register, typ:str, name, x:int, y:int):
    x = arth_to_logi(x)
    y = arth_to_logi(y)
    v = 0
    if(typ == "and"):
        v = logi_to_arth(x & y)
    elif(typ == "or"):
        v = logi_to_arth(x | y)
    elif(typ == "xor"):
        v = logi_to_arth(x ^ y)
    reg.setFR(v)
    reg.setGR(name, v)

def compare(reg:Register, typ:str, x:int, y:int):
    if(typ == "l"):
        x = arth_to_logi(x)
        y = arth_to_logi(y)
    if(x > y):
        reg.sf = False
        reg.zf = False
    elif(x == y):
        reg.sf = False
        reg.zf = True
    else:
        reg.sf = True
        reg.zf = False
    reg.of = False

def shift(reg: Register, dirc: str, typ: str, name:str, v: int, s: int):
    v = f"{arth_to_logi(v):032b}"
    f_last = False
    if(dirc == "left" and typ == "l"):
        f_last = v[s - 1] == "1"
        v = v[s:] + "0" * s
    elif(dirc == "right" and typ == "l"):
        f_last = v[-s] == "1"
        v = "0" * s + v[0:-s]
    elif(dirc == "left" and typ == "a"):
        f_last = v[-s] == "1"
        sign = v[0]
        v = v[:] + "0" * s
        v = v[-31:-1]
        v = sign + v[1:]
    elif(dirc == "right" and typ == "a"):
        f_last = v[s] == "1"
        sign = v[0]
        v = sign * s + v[0:-s]
    v = logi_to_arth(int(v, 2))
    reg.setFR(v)
    reg.of = f_last
    reg.setGR(name, v)



def arth_to_logi(arth:int, bit=32) -> int:
    if(0 <= arth <= get_bit_limit("top", b=bit)):
        return arth
    elif(get_bit_limit("under", b=bit) <= arth < 0):
        return arth + get_bit_limit("logi", b=bit)+1
    else:
        raise ExecutorException(f"Something wrong in arth_to_logi: arth={arth} bit={bit}")

def logi_to_arth(n_logi: int, bit=32) -> int:
    if(0 <= n_logi <= get_bit_limit("top", b=bit)):
        return n_logi
    elif(get_bit_limit("top", b=bit) < n_logi <= get_bit_limit("logi", b=bit)):
        return n_logi - (get_bit_limit("logi", b=bit) + 1)
    else:
        raise ExecutorException(f"Something wrong in logi_to_arth: n_logi={n_logi} bit={bit}")

def round_overflow(arth, b=32) -> int:
    _max = get_bit_limit("top", b)
    _min = get_bit_limit("under", b)
    _lmax = get_bit_limit("logi", b)
    if(_min <= arth <= _max):
        return arth
    elif(arth % _lmax <= _max):
        return arth % _lmax
    else:
        arth %= _lmax
        return arth - _max + _min - 1
    

def executor(line: list, reg: Register, data: Data):
    global port_mlfe_path, ports
    f = lambda x: line[0] == x
    l = lambda x: len(line) == x
    is_wrong_opecode = False
    if(f("START")):
        if(l(1)):
            reg.pc += 1
            return Status.CONTINUE
        elif(l(2) and data.isADDR(line[1])):
            reg.pc = line[1]
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("END")):
        if(l(1)):
            print("END appear.Program exit", file=sys.stderr)
            return Status.ERROR
        else:
            is_wrong_opecode = True
    elif(f("DATA")):
        if(l(2)):
            print(f"{line[0]} appear. Program exit", file=sys.stderr)
            return Status.ERROR
        else:
            is_wrong_opecode = True
    elif(f("LD")):
        v = None
        if(l(3)):
            if(reg.isREG(line[2])):
                v = reg.getGR(line[2])
            elif(data.isADDR(line[2])):
                v = data.get_by_addr(line[2], reg)
        elif(l(4) and reg.isREG(line[1]) and data.isADDR(line[2]) and reg.isREG(line[3])):
            v = data.get_by_addr(line[2], reg, x=reg.getGR(line[3]))
        if(not reg.isREG(line[1]) or v is None):
            is_wrong_opecode = True
        else:
            reg.setFR(v)
            reg.of = False
            reg.setGR(line[1], v)
            reg.pc += 1
            return Status.CONTINUE
    elif(f("ST")):
        if(l(3) and reg.isREG(line[1]) and data.isADDR(line[2])):
            if(0 <= (65535 - line[2]) < len(data.stack)):
                data.stack[65535 - line[2]] = reg.getGR(line[1])
            elif(0 <= line[2] < len(data.mem) and data.mem[line[2]][0] == "DATA"):
                data.mem[line[2]][1] = reg.getGR(line[1])
            reg.pc += 1
            return Status.CONTINUE
        elif(l(4) and reg.isREG(line[1]) and data.isADDR(line[2]) and reg.isREG(line[3])):
            if(0 <= (65535 - line[2] - reg.getGR(line[3])) < len(data.stack)):
                data.stack[65535 - line[2] - reg.getGR(line[3])] = reg.getGR(line[1])
            elif(
                0<=(line[2]+reg.getGR(line[3]))<len(data.mem)
                and data.mem[line[2]+reg.getGR(line[3])][0] == "DATA"
                ):
                    data.mem[line[2]+reg.getGR(line[3])][1] = reg.getGR(line[1])
            reg.pc += 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("LAD")):
        if(l(3) and reg.isREG(line[1]) and (data.isADDR(line[2]))):
            v = logi_to_arth(line[2], bit=16) if 0 <= line[2] < get_bit_limit("logi", b=16) else line[2]
            reg.setGR(line[1], v)
            reg.pc += 1
            return Status.CONTINUE
        elif(l(4) and reg.isREG(line[1]) and data.isADDR(line[2]) and reg.isREG(line[3])):
            v = logi_to_arth(line[2], bit=16) if 0 <= line[2] < get_bit_limit("logi", b=16) else line[2]
            x = arth_to_logi(round_overflow(reg.getGR(line[3]), b=16), bit=16)
            reg.setGR(line[1], round_overflow(v + x, b=16))
            reg.pc += 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
            
    elif(
            f("ADDA") or f("SUBA") or f("ADDL") or f("SUBL") or 
            f("MULA") or f("MULL") or f("DIVA") or f("DIVL")
        ):
        arths = {
            "ADDA":"aa", "SUBA":"sa",
            "ADDL":"al", "SUBL":"sl",
            "MULA":"ma", "MULL":"ml",
            "DIVA":"da", "DIVL":"dl"
        }
        a = reg.getGR(line[1]) if reg.isREG(line[1]) else None
        b = None
        if(l(3)):
            if(reg.isREG(line[2])):
                b = reg.getGR(line[2])
            elif(data.isADDR(line[2])):
                b = data.get_by_addr(arth_to_logi(line[2], bit=16), reg)
        elif(l(4) and reg.isREG(line[1]) and data.isADDR(line[2]) and reg.isREG(line[3])):
            b = data.get_by_addr(line[2], reg, x=reg.getGR(line[3]))
        elif(l(4) and reg.isREG(line[1]) and reg.isREG(line[2]) and reg.isREG(line[3])):
            a = reg.getGR(line[2])
            b = reg.getGR(line[3])
        if(a is None or b is None):
            is_wrong_opecode = True
        else:
            calc_num(reg, arths[line[0]], line[1], a, b)
            reg.pc += 1
            return Status.CONTINUE
            
    elif(f("AND") or f("OR") or f("XOR")):
        logis = {"AND":"and", "OR":"or", "XOR":"xor"}
        x = reg.getGR(line[1]) if reg.isREG(line[1]) else None
        y = None
        if(l(3)):
            if(reg.isREG(line[2])):
                y = reg.getGR(line[2])
            elif(data.isADDR(line[2])):
                y = data.get_by_addr(line[2], reg)
        elif(l(4) and reg.isREG(line[1]) and data.isADDR(line[2]) and reg.isREG(line[3])):
            y = data.get_by_addr(line[2], reg, x=reg.getGR(line[3]))
        if(x is None or y is None):
            is_wrong_opecode = True
        else:
            calc_logi(reg, logis[line[0]], line[1], x, y)
            reg.pc += 1
            return Status.CONTINUE
            
    elif(f("CPA") or f("CPL")):
        compares = {"CPA": "a", "CPL": "l"}
        x = reg.getGR(line[1]) if l(3) and reg.isREG(line[1]) else None
        y = None
        if(l(3)):
            if(reg.isREG(line[2])):
                y = reg.getGR(line[2])
            elif(data.isADDR(line[2])):
                y = data.get_by_addr(line[2], reg)
        elif(l(4) and data.isADDR(line[2]) and reg.isREG(line[3])):
            y = data.get_by_addr(line[2], reg, x=reg.getGR(line[3]))
        if(x is None or y is None):
            is_wrong_opecode = True
        else:
            compare(reg, compares[line[0]], x, y)
            reg.pc += 1
            return Status.CONTINUE
    
    elif(f("SLA") or f("SRA") or f("SLL") or f("SRL")):
        dirc = ""
        typ = ""
        x = reg.getGR(line[3]) if l(4) and reg.isREG(line[3]) else 0
        shifts = {
            "SLA":("left", "a"), "SRA":("right", "a"),
            "SLL":("left", "l"), "SRL":("right", "l")
        }
        dirc, typ = shifts[line[0]]
        if((reg.isREG(line[1]) and data.isADDR(line[2]))
            and (l(3) or (l(4) and reg.isREG(line[3])))):
            shift(reg, dirc, typ,
                line[1], reg.getGR(line[1]),
                line[2] + x
            )
            reg.pc += 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    
    elif(f("JPL") or f("JMI") or f("JNZ") 
        or f("JZE") or f("JOV") or f("JUMP")):
        flags = {
            "JPL":(not reg.sf and not reg.zf),
            "JMI":(reg.sf), "JNZ":(not reg.zf),
            "JZE":(reg.zf), "JOV":(reg.of),
            "JUMP":(True)
        }
        if(l(2) and data.isADDR(line[1])):
            to = line[1] if flags[line[0]] else reg.pc+1
            if(type(to) == int):
                reg.pc = to
            else:
                return Status.ERROR
        elif(l(3) and data.isADDR(line[1]) and reg.isREG(line[2])):
            to = line[1] + reg.getGR(line[2]) if flags[line[0]] else reg.pc+1
            if(type(to) is int):
                reg.pc = to
            else:
                return Status.ERROR
        else:
            is_wrong_opecode = True
            return Status.ERROR
        return Status.CONTINUE
        
    elif(f("PUSH")):
        if(l(2) and data.isADDR(line[1])):
            data.stack.append(line[1])
            reg.pc += 1
            reg.sp -= 1
            return Status.CONTINUE
        elif(l(3) and data.isADDR(line[1]) and reg.isREG(line[2])):
            data.stack.append(line[1] + reg.getGR(line[2]))
            reg.pc += 1
            reg.sp -= 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("POP")):
        if(l(2) and reg.isREG(line[1])):
            try:
                reg.setGR(line[1], data.stack.pop())
            except IndexError:
                print("Stack Empty Error", file=sys.stderr)
                return Status.ERROR
            reg.pc += 1
            reg.sp += 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("CALL")):
        if(l(2) and data.isADDR(line[1])):
            data.stack.append(reg.pc)
            reg.sp -= 1
            reg.pc = line[1]
            return Status.CONTINUE
        elif(l(3) and data.isADDR(line[1]) and reg.isREG(line[2])):
            data.state.append(reg.pc)
            reg.sp -= 1
            reg.pc = line[1] + reg.getGR(line[2])
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("RET")):
        if(l(1)):
            to = data.stack.pop()
            reg.sp += 1
            if(to == -1):
                return Status.EXIT
            else:
                reg.pc = to + 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("SVC")):
        global svc_mlfe_path
        subroutines = import_module(svc_mlfe_path).subroutines
        if(line[1] in subroutines.keys()):
            subroutines[line[1]](reg, data)
            reg.pc += 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("NOP")):
        if(l(1)):
            reg.pc += 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
            
    elif(f("READ")):
        global buffer_stdin
        if(reg.isREG(line[1])):
            port = reg.getGR(line[1]) \
                + (data.get_by_addr(line[3], reg) \
                    if (l(4) and data.isADDR(line[3])) \
                    else 0)
            map_in_port = import_module(port_mlfe_path).map_in_port
            if(port == 0):
                if(len(buffer_stdin) == 0):
                    try:
                        buffer_stdin = input()
                    except KeyboardInterrupt:
                        raise ExecutorException(f"KeyboardInterrupt Address = {reg.pc}")
                try:
                    c = buffer_stdin[0]
                    buffer_stdin = buffer_stdin[1:]
                    reg.setGR(line[2], ord(c))
                except IndexError:
                    reg.setGR(line[2], 0)
            elif(port in map_in_port):
                port_run = import_module(port_mlfe_path).port_run
                try:
                    ports, v = port_run(ports, True, port)
                except KeyboardInterrupt:
                    raise ExecutorException(f"KeyboardInterrupt Address = {reg.pc}")
                if(type(v) == int):
                    reg.setGR(line[2], v)
                else:
                    raise ExecutorException(f"A non-integer value was returned from port {port}")
            else:
                print(f"Port Not Found: {port}")
                return Status.ERROR
        reg.pc += 1
        return Status.CONTINUE
    elif(f("WRITE")):
        if(reg.isREG(line[1])):
            port = reg.getGR(line[1]) \
                + (data.get_by_addr(line[3], reg) \
                    if (l(4) and data.isADDR(line[3])) \
                    else 0)
            map_out_port = import_module(port_mlfe_path).map_out_port
            if(port in map_out_port):
                port_run = import_module(port_mlfe_path).port_run
                ports, _ = port_run(ports, False, port, reg.getGR(line[2]))
            else:
                print(f"Port Not Found: {port}")
                return Status.ERROR
        reg.pc += 1
        return Status.CONTINUE
    
    elif(f("DREG")):
        if(l(2) and data.isADDR(line[1])):
            for i in range(8):
                sys.stdout.write(chr(data.get_by_addr(line[1], reg, x=i)))
            print("\nGR    =",reg.gr)
            print(f"FLAG  = [SF:{int(reg.sf)}, ZF:{int(reg.zf)}, OF:{int(reg.of)}]")
            print(f"PC,SP = [{reg.pc}, {reg.sp}]")
            reg.pc += 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("DMEM")):
        if(l(4)
            and data.isADDR(line[1])
            and data.isADDR(line[2])
            and data.isADDR(line[3])):
            for i in range(8):
                sys.stdout.write(chr(data.get_by_addr(line[1], reg, x=i)))
            print(f" Start:{line[2]} End:{line[3]}\n  ", end="")
            for i in range(line[2], line[3]+1):
                d = data.get_by_addr(i, reg)
                print(f"[{i:05} {d:4} {chr(d) if chr(d).isprintable() else ' '}]",
                    end=" ")
                if((i+1) % 4 == 0):
                    print("  \n  ", end="")
            print()
            reg.pc += 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("DSTK")):
        if(l(2) and data.isADDR(line[1])):
            for i in range(8):
                sys.stdout.write(chr(data.get_by_addr(line[1], reg, x=i)))
            print()
            for i, e in enumerate(reversed(data.stack)):
                print(f"{reg.sp + i:7}: {e}")
            reg.pc += 1
            return Status.CONTINUE
    elif(f("SAVE")):
        if(l(2) and line[1] == "ALL"):
            for i in range(1,15):
                data.stack.append(reg.gr[i])
                data.stack.append(i)
            data.stack.append(15)
            reg.pc += 1
            return Status.CONTINUE
        elif(2 <= len(line)):
            if(len(line) == sum([reg.isREG(e) for e in line[1:]]) + 1):
                for gr in line[1:]:
                    data.stack.append(reg.getGR(gr))
                    data.stack.append(int(gr[-1]))
            data.stack.append(len(line) - 1)
            reg.pc += 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    elif(f("RETURN")):
        if(l(1)):
            count = data.stack.pop()
            for _ in range(count):
                suffix = data.stack.pop()
                value = data.stack.pop()
                reg.setGR(f"GR{suffix}", value)
            reg.pc += data.stack.pop() + 1
            return Status.CONTINUE
        else:
            is_wrong_opecode = True
    if(is_wrong_opecode):
        print(f"{line[0]} opecode is wrong", file=sys.stderr)
    return Status.ERROR

def parse_data(file_name):
    import os
    inc_data = []
    if(os.path.isfile(file_name)):
        with open(file_name, encoding="utf-8") as f:
            inc_data = list(
                filter(lambda x:x!=[],
                    [split_line(e.strip()) for e in f.readlines()]
                )
            )
    else:
        raise FileNotFoundError(f"File name: {file_name}")
        
    inc_data = allocate_ds_dc(inc_data)
    data, macrolabel = set_macro(inc_data)
    label = get_label(inc_data)
    label.update(macrolabel)
    return get_decision_data(data, label)

def split_line(line):
    line += ";"
    data_line = []
    word = ""
    is_instring = False
    is_firstblank = True
    for e in line:
        if((" " == e or "\t" == e) and not is_instring):
            if(is_firstblank):
                data_line.append(word)
                is_firstblank = False
                word = ""
        elif("\'" == e):
            if(is_instring
                and len(word) != 0
                and (word[-1] == "\\"
                and word[-2:-1] == "\\\\")):
                word += e
            else:
                word += e
                is_instring = not is_instring
        elif(is_instring):
            word += e
        elif("," == e):
            data_line.append(word)
            word = ""
        elif(";" == e):
            data_line.append(word)
            break
        else:
            is_firstblank = True
            word += e
    else:
        data_line.append(word)
        if(is_instring):
            raise AssemblySyntaxException(f"{line} String error")
    return [x for x in data_line if x != ""]

def allocate_ds_dc(data):
    for i, e in enumerate(data):
        for x, word in enumerate(e):
            if(type(word) == str and word[0] == "="):
                name_label = f"_adr{i:02}{x}"
                value = word[1:]
                data.insert(-1, [name_label, "DC", value])
                data[i][x] = name_label
            if(
                type(word) == str
                and word.upper() in Instruction.__members__
                and word.islower()
                ):
                data[i][x] = word.upper()
        if (2 < len(e) and e[1] == "DS"):
            if(0 < int(e[2])):
                allc = int(e[2]) - 1
                for j in range(allc):
                    data.insert(i+1, ["DS", 0])
            else:
                data.pop(i)
        elif(2 < len(e)
            and e[1] == "DC"
            and e[2] is not None
            and "\'" in e[2]):
            allc = len(e[2][1:-1].replace("\\", "")) - 1 + e[2].count("\\\\")
            for j in range(allc):
                data.insert(i+1, ["DC", None])
        elif(e[0] == "DS" and len(e) == 2):
            if(0 < int(e[1])):
                allc = int(e[1]) - 1
                for j in range(allc):
                    data.insert(i+1, ["DS", 0])
            elif(type(e[1]) != int):
                data.pop(i)
        elif(e[0] == "DC"
            and len(e) == 2
            and e[1] is not None
            and "\'" in e[1]):
            allc = len(e[1][1:-1].replace("\\", "")) - 1 + e[1].count("\\\\")
            for j in range(allc):
                data.insert(i+1, ["DC", None])
    return data

def set_macro(data):
    global macro_mlfe_path
    expand_macros = import_module(macro_mlfe_path).expand_macros
    Macros = import_module(macro_mlfe_path).Macros
    macrolabel = {}
    for i, line in enumerate(data):
        for j, word in enumerate(line):
            if type(word) == str and word.islower() and word.upper() in Macros.__members__:
                line[j] = word.upper()
                word = word.upper()
            if word in Macros.__members__:
                expanded, macrolabel = expand_macros(i, line)
                for k in macrolabel.keys():
                    macrolabel[k] += i
                for e in reversed(expanded):
                    data.insert(i + 1, e)
                data.pop(i)
    return data, macrolabel

def get_label(data):
    global macro_mlfe_path
    Macros = import_module(macro_mlfe_path).Macros
    label = {}
    for i, e in enumerate(data):
        flag = e[0] not in Instruction.__members__ \
                and e[0] != 0 \
                and e[0] not in Macros.__members__
        if e[0] in label:
            msg = " ".join(e)
            raise AssemblySyntaxException(f"Same label is defined: {msg}")
        if flag:
            label[e[0]] = i
    return label

def get_decision_data(data, label):
    global macro_mlfe_path
    expand_macros = import_module(macro_mlfe_path).expand_macros
    Macros = import_module(macro_mlfe_path).Macros
    for i, line in enumerate(data):
        if(2 <= len(line) and (line[0] == "SVC" or line[1] == "SVC")):
            continue
        for j, e in enumerate(line[1:]):
            if e in label.keys():
                data[i][j+1] = label[e]
    for i, e in enumerate(data):
        if(e[0] not in Instruction.__members__ and e[0] != 0):
            data[i].pop(0)
    for i, e in enumerate(data):
        if(len(e) == 0):
            raise AssemblySyntaxException("Label line is blank")
        elif(e[0] == "DS"):
            data[i] = ["DS", 0]
        elif(e[0] == "DC" and 2 <= len(e) and type(e[1]) != int):
            if(e[1].isdecimal() or (e[1][1:].isdecimal() and e[1][0] == "-")):
                n = int(e[1])
                if(not(get_bit_limit("under", b=32) <= n <= get_bit_limit("top", b=32))):
                    data[i][1] = round_overflow(n)
                else:
                    data[i][1] = n
                    
            elif("\'" in e[1]):
                s = e[1][1:-1]
                if(len(s) == 0):
                    raise AssemblySyntaxException("Length of string is zero")
                elif(len(s) == 1):
                    data[i][1] = round_overflow(ord(s))
                else:
                    s = parse_with_esc_seq(s)
                    for j, e_s in enumerate(s):
                        data[i+j][1] = round_overflow(ord(e_s)) if e_s != 0 else 0
            elif(e[1][0] == "#"):
                x = 0
                try:
                    x = int(e[1][1:], 16)
                except ValueError:
                    raise AssemblySyntaxException(f"{e[1]} is Invalid literal to hex")
                if(e[0] == "DC"):
                    data[i][1] = logi_to_arth(x, bit=32)
                else:
                    data[i][1] = round_overflow(x, bit=16)
        else:
            for j, x in enumerate(e):
                if(type(x) == int or "=" in x or x in Instruction.__members__):
                    pass
                elif(x[0] == "#"):
                    v = int(x[1:], 16)
                    if(0 <= v <= get_bit_limit("logi", b=16)):
                        data[i][j] = logi_to_arth(int(v), bit=16)
                    else:
                        msg = " ".join([str(x) for x in e])
                        raise AssemblySyntaxException(f"Immediate value is a 16bit arithmatic value: {msg}")
                elif(x[0] == "\'" and x[-1] == "\'"):
                    if(len(x) == 3):
                        c = ord(x[1])
                        if(0 <= c <= get_bit_limit("logi", b=16)):
                            data[i][j] = logi_to_arth(c, bit=16)
                        else:
                            raise AssemblySyntaxException(f"This character can not be included in 16bit: {c}")
                    elif(len(x) == 4 and x[1] == "\\"):
                        data[i][j] = ord(parse_with_esc_seq(x)[1])
                    else:
                        msg = " ".join([str(x) for x in e])
                        raise AssemblySyntaxException(f"The immediate value can not contain a string: {msg}")
                elif((x.isdecimal()) or (x[1:].isdecimal() and x[0] == "-")):
                    if(get_bit_limit("under", b=16) <= int(x) <= get_bit_limit("top", b=16)):
                        data[i][j] = int(x)
                    else:
                       msg = " ".join([str(x) for x in e])
                       raise AssemblySyntaxException(f"Immediate value is a 16bit arithmatic value: {msg}")
    c = [0, 0]
    adr_start = 0
    adr_end = 0
    for i, e in enumerate(data):
        if(e[0] == "START"):
            adr_start = i
            c[0] += 1
        elif(e[0] == "END"):
            adr_end = i+1 if adr_end==0 else adr_end
            c[1] += 1
        if(e[0] in ["DC", "DS"]):
            data[i][0] = "DATA"
        if(e[0] == "DATA" and len(e) == 1):
            msg = " ".join([str(x) for x in e])
            raise AssemblySyntaxException(f"Invalid Definition No Data Defined: {msg}")
        elif(e[0] == "DATA" and 2 < len(e)):
            msg = " ".join([str(x) for x in e])
            raise AssemblySyntaxException(f"Invalid Definition Multiple Data Defined: {msg}")
        for j, w in enumerate(e):
            if(e[0] != "DATA"
                and int == type(w)
                and not(get_bit_limit("under", b=16) <= w <= get_bit_limit("logi", b=16))):
               msg = " ".join([str(x) for x in e])
               raise AssemblySyntaxException(f"Immediate value is a 16bit value: {msg}")
            if(e[0] == "DATA"
                and int == type(w)
                and not(get_bit_limit("under", b=32) <= w <= get_bit_limit("top", b=32))):
               msg = " ".join([str(x) for x in e])
               raise AssemblySyntaxException(f"Data is a 32bit arithmatic value: {msg}")
            if(not(w in Instruction.__members__ or type(w) is int or w == "DATA" or w[:2] in ["GR", "SP", "PC"])):
                if(e[0] != "SVC"):
                    msg = " ".join([str(x) for x in e])
                    raise AssemblySyntaxException(f"This Label have not been Resolved by Name: {msg}")
                    
            
        if(e[0] not in Instruction.__members__ and e[0] != "DATA"):
            raise AssemblySyntaxException(f"There is a line with not instruction: {i} {e}")
            
    else:
        if(c[0] == 1 and c[1] == 1):
            return data, adr_start
        else:
            raise AssemblySyntaxException("START and END are required one by one")
            
def parse_with_esc_seq(raw):
    is_ckey = False
    result_list = []
    dict_ecs_seq = {
        "\\":"\\", "\'":"\'",
        "a":"\a", "b":"\b", "f":"\f",
        "n":"\n", "r":"\r", "t":"\t",
        "v":"\v", "e":'\x1b', "0":0
    }
    for i, e in enumerate(raw):
        c = e
        if(is_ckey):
            try:
                c = dict_ecs_seq[e]
            except KeyError:
                raise AssemblySyntaxException(f"Uncorrect escape sequence: \\{e}")
            is_ckey = False
        elif("\\" == e):
            is_ckey = True
            continue
        result_list.append(c)
    return result_list

class Instruction(Enum):
    START = "START"
    END = "END"
    DC = "DC"
    DS = "DS"
    
    LD = "LD"
    ST = "ST"
    LAD = "LAD"
    ADDA = "ADDA"
    SUBA = "SUBA"
    ADDL = "ADDL"
    SUBL = "SUBL"
    MULA = "MULA"
    MULL = "MULL"
    DIVA = "DIVA"
    DIVL = "DIVL"
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    CPA = "CPA"
    CPL = "CPL"
    SLA = "SLA"
    SRA = "SRA"
    SLL = "SLL"
    SRL = "SRL"
    JPL = "JPL"
    JMI = "JMI"
    JNZ = "JNZ"
    JZE = "JZE"
    JOV = "JOV"
    JUMP = "JUMP"
    PUSH = "PUSH"
    POP = "POP"
    CALL = "CALL"
    RET = "RET"
    READ = "READ"
    WRITE = "WRITE"
    SVC = "SVC"
    NOP = "NOP"
    
    DREG = "DREG"
    DMEM = "DMEM"
    DSTK = "DSTK"
    SAVE = "SAVE"
    RETURN = "RETURN"
    

class Status(Enum):
    CONTINUE = 0
    EXIT = 1
    ERROR = -1

def message_option_help():
    print("Usage:\n    $ python mlfe.py [hoge.fe] [(--some-option | -o)] [--format(-d|-x|-b)]")
    print("Trace instruction line:\n    $ python mlfe.py hoge.fe (--trace-line | -t) [--format]")
    print("Show assembly and run:\n    $ python mlfe.py hoge.fe (--show-assembly | -s) [--format]")
    print("Trace instruction and Show assembly:\n    $ python mlfe.py hoge.fe -a [--format]")
    print("Set clock time(second):\n    $ python mlfe.py hoge.fe (--clock-speed | -c) t")
    print("Show assembly without run:\n    $ python mlfe.py hoge.fe (--dry-assembly | -d) [--format]")
    print("Print version information:\n    $ python mlfe.py (--version | -v)")
    print("Print help message:\n    $ python mlfe.py (--help | -h)")
    

def debug(s):
    print("DEBUG> ", s, file=sys.stderr)

class AssemblySyntaxException(Exception):
    def __init__(self, msg):
        global msg_error
        msg_error = msg

class ExecutorException(Exception):
    def __init__(self, msg):
        global msg_error
        msg_error = msg

def interface_mlfe(argv):
    buffer_stdin = ""
    msg_error = ""
    ports = None
    main(argv)

if __name__ == "__main__":
    try:
        MacroSyntaxException = import_module(macro_mlfe_path).MacroSyntaxException
    except ModuleNotFoundError:
        print("Not found svc_mlfe or macro_mlfe.", file=sys.stderr)
        sys.exit(1)
    except:
        print("Some Error has occurd:", sys.exc_info()[1], file=sys.stderr)
        sys.exit(1)
    buffer_stdin = ""
    msg_error = ""
    ports = None
    try:
        main(sys.argv)
    except(AssemblySyntaxException, ExecutorException, MacroSyntaxException):
        print(msg_error, file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError as e:
        print("Not found File.", e, file=sys.stderr)
        sys.exit(1)
    except ModuleNotFoundError as e:
        print("Not found svc_mlfe or macro_mlfe", file=sys.stderr)
        sys.exit(1)
    except:
        #debug(sys.exc_info())
        print("Some Error has occurd:", sys.exc_info()[1], file=sys.stderr)
        sys.exit(1)