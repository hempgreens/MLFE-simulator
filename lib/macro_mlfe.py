from enum import Enum

class Macros(Enum):
    IN = "IN"
    OUT = "OUT"
    RPUSH = "RPUSH"
    RPOP = "RPUSH"
    RANDINT = "RANDINT"
    ABS = "ABS"
    
    SOUND = "SOUND"


def expand_macros(number, list_macro):
    isLabeled = list_macro[1] in Macros.__members__ if 2 <= len(list_macro) else False
    macro_name = list_macro[1] if isLabeled else list_macro[0]
    macros = {
        "OUT":OUT,
        "IN":IN,
        "RPUSH":RPUSH,
        "RPOP":RPOP,
        "RANDINT":RANDINT,
        "ABS":ABS,
        "SOUND":SOUND,
    }
    return macros[macro_name](number, list_macro, isLabeled)


def IN(number, list_macro, isLabeled):
    adj_label = lambda : 1 if isLabeled else 0
    if(len(list_macro) == 3 + adj_label()):
        _buf = list_macro[1 + adj_label()]
        _len = list_macro[2 + adj_label()]
        expanded = [
            ["PUSH", "0", "GR0"],
            ["PUSH", "0", "GR1"],
            ["PUSH", "0", "GR2"],
            ["PUSH", "0", "GR3"],
            ["LD", "GR0", f"_{number}ZERO"],
            ["LD", "GR1", f"_{number}ZERO"],
            ["LD", "GR3", f"_{number}ONE"],
            [f"_{number}LOOP", "CPL", "GR1", _len],
            ["JZE", f"_{number}LOOPEND"],
            ["READ", "GR0", "GR2"],
            ["ST", "GR2", _buf, "GR1"],
            ["ADDL", "GR1", "GR3"],
            ["JUMP", f"_{number}LOOP"],
            [f"_{number}LOOPEND", "POP", "GR3"],
            ["POP", "GR2"],
            ["POP", "GR1"],
            ["POP", "GR0"],
            ["JUMP", f"_{number}MACROEND"],
            [f"_{number}ZERO", "DC", "0"],
            [f"_{number}ONE", "DC", "1"],
            [f"_{number}MACROEND", "NOP"]
        ]
        label = get_labels(expanded)
        if isLabeled:
            expanded[0].insert(0, list_macro[0])
        return expanded, label
    else:
        synerror("IN", list_macro, number)

def OUT(number, list_macro, isLabeled):
    adj_label = lambda : 1 if isLabeled else 0
    if(len(list_macro) == 3 + adj_label()
        or len(list_macro) == 4 + adj_label()
        ):
        _buf = list_macro[1 + adj_label()]
        _len = list_macro[2 + adj_label()]
        _mode = list_macro[3 + adj_label()] if len(list_macro) == 4 + adj_label() else f"_{number}ZERO"
        expanded = [
            ["PUSH", "0", "GR0"],
            ["PUSH", "0", "GR1"],
            ["PUSH", "0", "GR2"],
            ["PUSH", "0", "GR3"],
            ["LD", "GR0", _mode],
            ["LD", "GR1", f"_{number}ZERO"],
            ["LD", "GR3", f"_{number}ONE"],
            [f"_{number}LOOP", "CPL", "GR1", _len],
            ["JZE", f"_{number}LOOPEND"],
            ["LD", "GR2", _buf, "GR1"],
            ["WRITE", "GR0", "GR2"],
            ["ADDL", "GR1", "GR3"],
            ["JUMP", f"_{number}LOOP"],
            [f"_{number}LOOPEND", "POP", "GR3"],
            ["POP", "GR2"],
            ["POP", "GR1"],
            ["POP", "GR0"],
            ["JUMP", f"_{number}MACROEND"],
            [f"_{number}ZERO", "DC", "0"],
            [f"_{number}ONE", "DC", "1"],
            [f"_{number}MACROEND", "NOP"]
        ]
        label = get_labels(expanded)
        if isLabeled:
            expanded[0].insert(0, list_macro[0])
        return expanded, label
    else:
        synerror("OUT", list_macro, number)

def RPUSH(number, list_macro, isLabeled):
    adj_label = lambda : 1 if isLabeled else 0
    if(len(list_macro) == 3 + adj_label()):
        _left = int(list_macro[1 + adj_label()]) if len(list_macro) == 3 + adj_label() else 1
        _right = int(list_macro[2 + adj_label()]) if len(list_macro) == 3 + adj_label() else 7
        reg_list = []
        if(_left < _right):
            reg_list = [i for i in range(_left, _right + 1)]
        elif(_left > _right):
            reg_list = [i for i in range(_right, _left + 1)]
        elif(_left == _right):
            reg_list = [_left, ]
        expanded = [["PUSH", "0", f"GR{n}"] for n in reg_list]
        if isLabeled:
            expanded[0].insert(0, list_macro[0])
        return expanded, {}
    else:
        synerror("RPUSH", list_macro, number)

def RPOP(number, list_macro, isLabeled):
    adj_label = lambda : 1 if isLabeled else 0
    if(len(list_macro) == 3 + adj_label()):
        _left = int(list_macro[1 + adj_label()]) if len(list_macro) == 3 + adj_label() else 1
        _right = int(list_macro[2 + adj_label()]) if len(list_macro) == 3 + adj_label() else 7
        reg_list = []
        if(_left < _right):
            reg_list = [i for i in range(_left, _right + 1)]
        elif(_left > _right):
            reg_list = [i for i in range(_right, _left + 1)]
        elif(_left == _right):
            reg_list = [_left, ]
        expanded = [["POP", f"GR{n}"] for n in reversed(reg_list)]
        if isLabeled:
            expanded[0].insert(0, list_macro[0])
        return expanded, {}
    else:
        synerror("RPOP", list_macro, number)

def RANDINT(number, list_macro, isLabeled):
    adj_label = lambda : 1 if isLabeled else 0
    if(len(list_macro) == 1 + adj_label()
        or len(list_macro) == 3 + adj_label()
        ):
        expanded = [
            ["LAD", "GR0", 0],
            ["SUBA", "GR0", f"_{number}ONE"],
            ["CPA", "GR2", "GR1"],
            ["JMI", f"_{number}RANDRET"],
            ["JZE", f"_{number}RANDRET"],
            ["PUSH", 0, "GR1"],
            ["PUSH", 0, "GR2"],
            ["PUSH", 0, "GR3"],
            ["PUSH", 0, "GR4"],
            ["PUSH", 0, "GR5"],
            ["PUSH", 0, "GR6"],
            ["PUSH", 0, "GR7"],
            ["PUSH", 0, "GR1"],
            ["PUSH", 0, "GR2"],
            ["SVC", "time"],
            ["ST", "GR2", f"_{number}S"],
            ["MULA", "GR6", "GR1"],
            ["ST", "GR6", f"_{number}X"],
            ["MULA", "GR5", "GR1"],
            ["ST", "GR5", f"_{number}Y"],
            ["MULA", "GR4", "GR1"],
            ["ST", "GR4", f"_{number}Z"],
            ["MULA", "GR3", "GR1"],
            ["ST", "GR3", f"_{number}W"],
            ["POP", "GR2"],
            ["POP", "GR1"],
            ["LD", "GR6", f"_{number}S"],
            [f"_{number}RANDLP", "CPA", "GR6", f"_{number}ZERO"],
            ["JZE", f"_{number}RANDEND"],
            ["LD", "GR3", f"_{number}X"],
            ["SLL", "GR3", 11],
            ["XOR", "GR3", f"_{number}X"],
            ["LD", "GR4", f"_{number}Y"],
            ["ST", "GR4", f"_{number}X"],
            ["LD", "GR4", f"_{number}Z"],
            ["ST", "GR4", f"_{number}Y"],
            ["LD", "GR4", f"_{number}W"],
            ["ST", "GR4", f"_{number}Z"],
            ["SRL", "GR4", 19],
            ["XOR", "GR4", f"_{number}W"],
            ["LD", "GR5", "GR3"],
            ["SRL", "GR5", 8],
            ["XOR", "GR3", "GR5"],
            ["XOR", "GR4", "GR3"],
            ["ADDA", "GR4", "GR1"],
            ["DIVA", "GR5", "GR4", "GR2"],
            ["MULA", "GR5", "GR2"],
            ["SUBA", "GR0", "GR4", "GR5"],
            ["SUBA", "GR6", f"_{number}ONE"],
            ["JUMP", f"_{number}RANDLP"],
            [f"_{number}RANDEND", "POP", "GR7"],
            ["POP", "GR6"],
            ["POP", "GR5"],
            ["POP", "GR4"],
            ["POP", "GR3"],
            ["POP", "GR2"],
            ["POP", "GR1"],
            ["JUMP", f"_{number}RANDRET"],
            [f"_{number}X", "DC", 0],
            [f"_{number}Y", "DC", 0],
            [f"_{number}Z", "DC", 0],
            [f"_{number}W", "DC", 0],
            [f"_{number}S", "DC", 0],
            [f"_{number}ZERO", "DC", 0],
            [f"_{number}ONE", "DC", 1],
            [f"_{number}RANDRET", "NOP"],
            
        ]
        
        if(len(list_macro) == 3 + adj_label()
            and list_macro[1+adj_label()].isalnum()
            and list_macro[2+adj_label()].isalnum()
            ):
            a = int(list_macro[1+adj_label()])
            b = int(list_macro[2+adj_label()])
            expanded.insert(0, ["LAD", "GR2", b])
            expanded.insert(0, ["LAD", "GR1", a])

        label = get_labels(expanded)
        if isLabeled:
            expanded[0].insert(0, list_macro[0])
        return expanded, label
    else:
        synerror("RANDINT", list_macro, number)

def ABS(number, list_macro, isLabeled):
    import sys
    adj_label = lambda : 1 if isLabeled else 0
    if(len(list_macro) == 2 + adj_label()
        and type(list_macro[1+adj_label()]) == str
        and list_macro[1+adj_label()][0:2] == "GR"
        ):
        reg = list_macro[1+adj_label()]
        expanded = [
            ["ADDA", reg, f"_{number}ZERO"],
            ["JMI", f"_{number}ABSREV"],
            ["JUMP", f"_{number}ABSED"],
            [f"_{number}ABSREV", "XOR", reg, f"_{number}ALL"],
            ["ADDA", reg, f"_{number}ONE"],
            ["JUMP", f"_{number}ABSED"],
            [f"_{number}ZERO", "DC", 0],
            [f"_{number}ONE", "DC", 1],
            [f"_{number}ALL", "DC", -1],
            [f"_{number}ABSED", "NOP"]
            
        ]
        label = get_labels(expanded)
        if isLabeled:
            expanded[0].insert(0, list_macro[0])
        return expanded, label
    else:
        synerror("ABS", list_macro, number)

# SOUND _time, _freq, _sampling

def SOUND(number, list_macro, isLabeled):
    adj_label = lambda : 1 if isLabeled else 0
    if(len(list_macro) == (4 + adj_label())
        and len([e for e in list_macro[1 + adj_label():] if type(e)==str])==3
        ):
        _time = list_macro[1 + adj_label()]
        _freq = list_macro[2 + adj_label()]
        _sampling = list_macro[3 + adj_label()]
        expanded = [
            ["PUSH", 0, "GR0"],
            ["PUSH", 0, "GR1"],
            ["PUSH", 0, "GR2"],
            ["LAD", "GR0", 0],
            ["LAD", "GR1", 1],
            ["LD", "GR2", _time],
            ["WRITE", "GR0", "GR2", f"_{number}time"],
            ["LD", "GR2", _freq],
            ["WRITE", "GR0", "GR2", f"_{number}freq"],
            ["LD", "GR2", _sampling],
            ["WRITE", "GR0", "GR2", f"_{number}sampl"],
            ["LAD", "GR0", 10],
            ["WRITE", "GR0", "GR1"],
            ["LAD", "GR0", 0],
            ["WRITE", "GR0", "GR0", f"_{number}time"],
            ["WRITE", "GR0", "GR0", f"_{number}freq"],
            ["WRITE", "GR0", "GR0", f"_{number}sampl"],
            ["POP", "GR2"],
            ["POP", "GR1"],
            ["POP", "GR0"],
            ["JUMP", f"_{number}SOUNDEND"],
            [f"_{number}time", "DC", 11],
            [f"_{number}freq", "DC", 12],
            [f"_{number}sampl", "DC", 13],
            [f"_{number}SOUNDEND", "NOP"],
        ]
        if isLabeled:
            expanded[0].insert(0, list_macro[0])
        label = get_labels(expanded)
        return expanded, label
    else:
        synerror("SOUND", list_macro, number)

def get_labels(expanded):
    label = {}
    for i, line in enumerate(expanded):
        if line[0] not in Instruction.__members__:
            label[line[0]] = i
    return label

def synerror(name, list_macro, i):
    import sys
    x = " ".join(list_macro)
    msg_error = f"{name} macro syntax error: {x}"
    print(msg_error, file=sys.stderr)
    raise MacroSyntaxException()

class MacroSyntaxException(Exception):
    pass

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
    DIVA = "DIVA"
    MULL = "MULL"
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
    JUMP = "JUMP"
    JPL = "JPL"
    JMI = "JMI"
    JNZ = "JNZ"
    JZE = "JZE"
    JOV = "JOV"
    PUSH = "PUSH"
    POP = "POP"
    CALL = "CALL"
    RET = "RET"
    SVC = "SVC"
    NOP = "NOP"
    READ = "READ"
    WRITE = "WRITE"