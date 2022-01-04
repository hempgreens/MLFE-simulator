def time(reg, data):
    from datetime import datetime as dt
    try:
        dt_now = dt.now()
        reg.gr[7] = dt_now.year
        reg.gr[6] = dt_now.month
        reg.gr[5] = dt_now.day
        reg.gr[4] = dt_now.hour
        reg.gr[3] = dt_now.minute
        reg.gr[2] = dt_now.second
        reg.gr[1] = dt_now.microsecond
        reg.gr[0] = 0
    except:
        reg.gr[0] = 1

def scanf(reg, data):
    import sys
    def is_ds(addr):
        return data.mem[addr][0] == "DATA"
    def set_data(addr, value):
        data.mem[addr][1] = value
    def is_in16bit(n):
        return n if -32768 <= n < 32767 else 0
    try:
        input_line = input()
        b_addr = reg.gr[1]
        f = chr(reg.gr[2])
        v = 0
        if(0 != len(input_line)):
            if(f == "d" and is_ds(b_addr) and is_ds(b_addr + 1)):
                v = is_in16bit(int(input_line))
            elif(f in ["X", "x"] and is_ds(b_addr) and is_ds(b_addr + 1)):
                v = is_in16bit(int(input_line, 16))
            elif(f == "b" and is_ds(b_addr) and is_ds(b_addr + 1)):
                v = is_in16bit(int(input_line, 2))
            elif(f == "s"):
                i = 0
                for i, e in enumerate(input_line):
                    if(is_ds(b_addr + i)):
                        set_data(b_addr + i, is_in16bit(ord(e)))
                else:
                    if(is_ds(b_addr + i + 1)):
                        set_data(b_addr + i + 1, 0)
            elif(is_ds(b_addr) and is_ds(b_addr + 1)):
                v = is_in16bit(ord(input_line[0]))
            if(f != "s"):
                set_data(b_addr, v)
                set_data(b_addr + 1, 0)
            reg.gr[0] = 0
        else:
            reg.gr[0] = 1
    except KeyboardInterrupt:
        print("KeyboardInterrupt", file=sys.stderr)
        reg.gr[0] = 1
    except:
        reg.gr[0] = 1

def printf(reg, data):
    import sys
    try:
        b_addr = reg.gr[1]
        f = chr(reg.gr[2])
        p = reg.gr[3]
        if(f == "s"):
            buf = []
            x = data.mem[b_addr][1]
            while(x != 0): 
                buf.append(chr(x))
                b_addr += 1
                x = data.mem[b_addr][1]
            print("".join(buf), end="")
        else:
            if(f == "p"):
                print(f"{b_addr:04}", end="")
            elif(f == "c"):
                print(f"{chr(data.mem[b_addr][1]):>{p}}", end="")
            elif(f == 'u'):
                e = data.mem[b_addr][1]
                if(e < 0):
                    e += 2 ** 32
                print(e, end="")
            else:
                print(f"{data.mem[b_addr][1]:0{p}{f}}", end="")
        reg.gr[0] = 0
    except:
        reg.gr[0] = 1

def malloc(reg, data):
    try:
        if(65536 < (len(data.mem) + len(data.stack) + reg.gr[1]) or reg.gr[1] == 0):
            reg.gr[0] = 0
        else:
            reg.gr[0] = len(data.mem) - 1
            n = reg.gr[1]
            n = n if 0 <= n < 2**32//2-1 else n+(2**32-1)
            for i in range(n):
                data.mem.insert(-1, ["DATA", 0])
    except:
        reg.gr[0] = 0

subroutines = {
    "time":time,
    "scanf":scanf,
    "printf":printf,
    "malloc":malloc,
}