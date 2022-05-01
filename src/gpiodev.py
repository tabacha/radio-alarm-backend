#!/usr/bin/python3
from inspect import GEN_CLOSED
import sys
from enum import Enum
from abc import ABC, abstractmethod
import tty
import termios
from time import sleep
from smbus import SMBus

DISPLAY_ADDR=0x27
DISPLAY_BUS=0x1
KY040_CLOCKPIN = 27
KY040_DATAPIN = 22
KY040_SWITCHPIN = 24

# other commands
LCD_CLEARDISPLAY = 0x01
LCD_RETURNHOME = 0x02
LCD_ENTRYMODESET = 0x04
LCD_DISPLAYCONTROL = 0x08
LCD_CURSORSHIFT = 0x10
LCD_FUNCTIONSET = 0x20
LCD_SETCGRAMADDR = 0x40
LCD_SETDDRAMADDR = 0x80

# flags for display entry mode
LCD_ENTRYRIGHT = 0x00
LCD_ENTRYLEFT = 0x02
LCD_ENTRYSHIFTINCREMENT = 0x01
LCD_ENTRYSHIFTDECREMENT = 0x00

# flags for display on/off control
LCD_DISPLAYON = 0x04
LCD_DISPLAYOFF = 0x00
LCD_CURSORON = 0x02
LCD_CURSOROFF = 0x00
LCD_BLINKON = 0x01
LCD_BLINKOFF = 0x00

# flags for display/cursor shift
LCD_DISPLAYMOVE = 0x08
LCD_CURSORMOVE = 0x00
LCD_MOVERIGHT = 0x04
LCD_MOVELEFT = 0x00

# flags for function set
LCD_8BITMODE = 0x10
LCD_4BITMODE = 0x00
LCD_2LINE = 0x08
LCD_1LINE = 0x00
LCD_5x10DOTS = 0x04
LCD_5x8DOTS = 0x00

# flags for backlight control
LCD_BACKLIGHT = 0x08
LCD_NOBACKLIGHT = 0x00
CHAR_BELL=[
     "00000",
     "00000",
     "00100",
     "01110",
     "01110",
     "11111",
     "11111",
     "00100"
    ]

PROGRESS00000=[
     "11111",
     "00000",
     "00000",
     "00000",
     "00000",
     "00000",
     "00000",
     "11111"
    ]

PROGRESS10000=[
     "11111",
     "10000",
     "10000",
     "10000",
     "10000",
     "10000",
     "10000",
     "11111"
    ]

PROGRESS11000=[
     "11111",
     "11000",
     "11000",
     "11000",
     "11000",
     "11000",
     "11000",
     "11111"
    ]

PROGRESS11100=[
     "11111",
     "11100",
     "11100",
     "11100",
     "11100",
     "11100",
     "11100",
     "11111"
    ]

PROGRESS11110=[
     "11111",
     "11110",
     "11110",
     "11110",
     "11110",
     "11110",
     "11110",
     "11111"
    ]

PROGRESS11111=[
     "11111",
     "11111",
     "11111",
     "11111",
     "11111",
     "11111",
     "11111",
     "11111"
    ]


CUST_CHARS = [
    PROGRESS00000,
    PROGRESS10000,
    PROGRESS11000,
    PROGRESS11100,
    PROGRESS11110,
    PROGRESS11111,
    CHAR_BELL,
]

CHAR_LOAD_CMD=[0x40, 0x48, 0x50, 0x58, 0x60, 0x68, 0x70, 0x78]

En = 0b00000100  # Enable bit
Rw = 0b00000010  # Read/Write bit
Rs = 0b00000001  # Register select bit

class GPIO_INPUT(Enum):
    LEFT=0
    RIGHT=1
    BUTTON=2
    TIMEOUT=999

class GPIOBaseDev(ABC):

    @abstractmethod
    def write_display_line(self, line_no:int, line:str):
        pass

    def clear(self):
        pass

    def get_pfeil_rechts(self):
        return '>'

    def get_pfeil_links(self):
        return '<'

    @abstractmethod
    def wait_for_gpio_event(self, timeout_secs:int)->GPIO_INPUT:
        return GPIO_INPUT.TIMEOUT

    def get_number_of_lines(self)->int:
        return 4

class TestGPIODev(GPIOBaseDev):

    def clear(self):
        print(chr(27) + "[H" + chr(27) + "[J")

    def write_display_line(self,line_no:int, line:str):
        print(' '+line[:20])

    def backlight(self, state:bool):
        pass

    def wait_for_gpio_event(self, timeout_secs:int) -> GPIO_INPUT:
        while True:
            orig_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin)
            ch=sys.stdin.read(1)[0]
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, orig_settings)
            if (ch=='d') or (ch=='-'):
                return GPIO_INPUT.RIGHT
            elif (ch=='u') or (ch=='+'):
                return GPIO_INPUT.LEFT
            elif (ch=="x") or (ch==' ') or (ch==chr(10)):
                return GPIO_INPUT.BUTTON
            elif (ch=='t'):
                return GPIO_INPUT.TIMEOUT
            else:
                print('Unbekanter Tastendruck %d "%s"',ord(ch),ch)

class I2CDevice:
    def __init__(self, addr, bus):
        self.addr = addr
        self.bus = SMBus(bus)

    # write a single command
    def write_cmd(self, cmd):
        self.bus.write_byte(self.addr, cmd)
        sleep(0.0001)

    # write a command and argument
    def write_cmd_arg(self, cmd, data):
        self.bus.write_byte_data(self.addr, cmd, data)
        sleep(0.0001)

    # write a block of data
    def write_block_data(self, cmd, data):
        self.bus.write_block_data(self.addr, cmd, data)
        sleep(0.0001)

    # read a single byte
    def read(self):
        return self.bus.read_byte(self.addr)

    # read
    def read_data(self, cmd):
        return self.bus.read_byte_data(self.addr, cmd)

    # read a block of data
    def read_block_data(self, cmd):
        return self.bus.read_block_data(self.addr, cmd)
try:
    from ky040 import KY040
except:
    pass

class RealGPIODev(GPIOBaseDev):
    def __init__(self, addr, bus):
        self.addr = addr
        self.lcd = I2CDevice(addr=self.addr, bus=bus)
        self.lcd_write(0x03)
        self.lcd_write(0x03)
        self.lcd_write(0x03)
        self.lcd_write(0x02)
        self.lcd_write(LCD_FUNCTIONSET | LCD_2LINE | LCD_5x8DOTS | LCD_4BITMODE)
        self.lcd_write(LCD_DISPLAYCONTROL | LCD_DISPLAYON)
        self.lcd_write(LCD_CLEARDISPLAY)
        self.lcd_write(LCD_ENTRYMODESET | LCD_ENTRYLEFT)
        for char_num in range(len(CUST_CHARS)):
            self.lcd_write(CHAR_LOAD_CMD[char_num])
            for line_num in range(8):
                binary_str_cmd="0b000{0}".format(CUST_CHARS[char_num][line_num])
                self.lcd_write(int(binary_str_cmd,2), Rs)

        sleep(0.2)
        def rotaryChange(direction):
            nonlocal self
            if direction==0:
                self.ky040_event=GPIO_INPUT.LEFT
            else:
                self.ky040_event=GPIO_INPUT.RIGHT

        def switchPressed(pin):
            nonlocal self
            self.ky040_event=GPIO_INPUT.BUTTON

        self.ky040 = KY040(KY040_CLOCKPIN,
            KY040_DATAPIN,
            KY040_SWITCHPIN,
            rotaryChange,
            switchPressed)
        self.ky040.start()

    def get_pfeil_rechts(self):
        return chr(126)

    def get_pfeil_links(self):
        return chr(127)

    def lcd_write_four_bits(self, data):
        self.lcd.write_cmd(data | LCD_BACKLIGHT)
        self.lcd_strobe(data)

    # write a command to lcd
    def lcd_write(self, cmd, mode=0):
        self.lcd_write_four_bits(mode | (cmd & 0xF0))
        self.lcd_write_four_bits(mode | ((cmd << 4) & 0xF0))

    # clocks EN to latch command
    def lcd_strobe(self, data):
        self.lcd.write_cmd(data | En | LCD_BACKLIGHT)
        sleep(.0005)
        self.lcd.write_cmd(((data & ~En) | LCD_BACKLIGHT))
        sleep(.0001)

    def write_display_line(self, line: int, string:str):
        short_string=string[:20]
        if line == 1:
            self.lcd_write(0x80)
        if line == 2:
            self.lcd_write(0xC0)
        if line == 3:
            self.lcd_write(0x94)
        if line == 4:
            self.lcd_write(0xD4)
        for char in short_string:
            # ä 225
            # ß 226
            # ö 239
            # ü 245
            if (char=='ä') or (char=='Ä'):
                self.lcd_write(225,Rs)
            elif (char=='ß'):
                self.lcd_write(226,Rs)
            elif (char=='ä') or (char=='Ä'):
                self.lcd_write(239,Rs)
            elif (char=='ü') or (char=='Ü'):
                self.lcd_write(245,Rs)
            else:
                self.lcd_write(ord(char), Rs)

    # clear lcd and set to home
    def clear(self):
        self.lcd_write(LCD_CLEARDISPLAY)
        self.lcd_write(LCD_RETURNHOME)

    # backlight control (on/off)
    def backlight(self, state:bool):
        if state:
            self.lcd.write_cmd(LCD_BACKLIGHT)
        else:
            self.lcd.write_cmd(LCD_NOBACKLIGHT)

    def wait_for_gpio_event(self,timeout_secs:int) -> GPIO_INPUT:
        self.ky040_event=None
        remaining_secs=timeout_secs
        while (self.ky040_event==None) and (remaining_secs>0):
            sleep(0.2)
            remaining_secs-=0.2
        if (self.ky040_event==None):
            return GPIO_INPUT.TIMEOUT
        return self.ky040_event
        #FIXME self.ky040.stop()
