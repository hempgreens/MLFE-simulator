class Ports:
    def __init__(self):
        self.ports = [0 for _ in range(2 ** 16)]

# io input true, output false
def port_run(ports: Ports, io: bool, number: int, value=0):
    global map_in_port, map_out_port
    v = None
    if(ports == None):
        ports = Ports()
    if(io):
        v = map_in_port[number](ports)
    else:
        map_out_port[number](ports, value)
    return ports, v

# Out Ports Functions
# function(ports, value)

def printChar(ports, value):
    import sys
    try:
        sys.stdout.write(f"{value:c}")
        sys.stdout.flush()
    except KeyboardInterrupt:
        pass

def printDecimal(ports, value):
    import sys
    try:
        sys.stdout.write(f"{value:d}")
        sys.stdout.flush()
    except KeyboardInterrupt:
        pass

def printHex(ports, value):
    import sys
    try:
        sys.stdout.write(f"{value:x}")
        sys.stdout.flush()
    except KeyboardInterrupt:
        pass

def printBin(ports, value):
    import sys
    try:
        sys.stdout.write(f"{value:b}")
        sys.stdout.flush()
    except KeyboardInterrupt:
        pass

def printUnsignedDecinal(ports, value):
    import sys
    value = value if 0 <= value else value + (2 ** 32)
    try:
        sys.stdout.write(f"{value:d}")
        sys.stdout.flush()
    except KeyboardInterrupt:
        pass

def playSound(ports, value):
    import wave
    import struct
    import math
    import os
    
    ports.ports[10] = value
    
    if(ports.ports[10] != 0):
        def arrange(start, end):
            l = []
            x = start
            while(x < end):
                l.append(x)
                x += 1.0
            return l
        
        mul = lambda x, l: [x * e for e in l]
        div = lambda x, l: [(lambda a,b: a/b if b!=0 else 0)(e, x) for e in l]
        sin = lambda l: [math.sin(e) for e in l]
        
        sec = ports.ports[11] / 1000.0
        frq = ports.ports[12]
        sample = ports.ports[13]
        name = "sound_mlfe.wav"
        
        try:
            t = arrange(0, sample * sec)
            wv = sin(div(sample, mul(2 * math.pi * frq, t)))
            max_num = 32767.0 / max(wv)
            wv16 = [int(x * max_num) for x in wv]
            bi_wv = struct.pack("h" * len(wv16), *wv16)
            file = wave.open(name, mode='wb')
            param = (1, 2, sample, len(bi_wv), 'NONE', 'not compressed')
            file.setparams(param)
            file.writeframes(bi_wv)
            file.close()
            if(os.name == "nt"):
                import winsound
                winsound.PlaySound(name, winsound.SND_FILENAME)
            else:
                pass
            os.remove(name)
        except:
            pass
        
    
    ports.ports[10] = 0

def timePlayMiliSec(ports, value):
    ports.ports[11] = value if 0 <= value else value + (2 ** 32)

def frequency(ports, value):
    ports.ports[12] = value if 0 <= value else value + (2 ** 32)

def sampleFrequency(ports, value):
    ports.ports[13] = value if 0 <= value else value + (2 ** 32)

# In Ports Functions
# function(ports) -> int

def keyboardHit(ports) -> int:
    import os
    if(os.name == "nt"):
        import msvcrt
        return int(msvcrt.kbhit())
    elif(os.name == "posix"):
        if(ports.ports[32778] == 0):
            ports.ports[32778] = getKeyboardEventPosix()
        return ports.ports[32778].keyboardHit()
    else:
        return -1

def getKeyboardCharctor(ports) -> int:
    import os
    if(os.name == "nt"):
        import msvcrt
        if msvcrt.kbhit():
            return int.from_bytes(msvcrt.getch(), "little")
        return -1
    elif(os.name == "posix"):
        if(ports.ports[32778] == 0):
            ports.ports[32778] = getKeyboardEventPosix()
        return ports.ports[32778].getKeyboardCharctor()
    else:
        return -1

# For keyboardHit, getKeyboardCharctor in Posix
def getKeyboardEventPosix():
    import sys
    import select
    import tty
    import termios
    class NonBlocking:
        def __init__(self):
            self.old_fn = sys.stdin.fileno()
            self.old_tt = termios.tcgetattr(sys.stdin.fileno())
            tty.setcbreak(self.old_fn)
        def keyboardHit(self):
            return int(select.select([sys.stdin],[],[],0)==([sys.stdin],[],[]))
        def getKeyboardCharctor(self):
            return ord(sys.stdin.read(1)) if self.keyboardHit() else -1
        def close(self):
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_tt)
        def __del__(self):
            self.close()
    return NonBlocking()

# Out Ports Assign

map_out_port = {
    0: printChar,
    1: printDecimal,
    2: printHex,
    3: printBin,
    4: printUnsignedDecinal,
    
    10: playSound,
    11: timePlayMiliSec,
    12: frequency,
    13: sampleFrequency,
}

# In Ports Assign

map_in_port = {
    0: None,
    
    10: keyboardHit,
    11: getKeyboardCharctor,
    
}