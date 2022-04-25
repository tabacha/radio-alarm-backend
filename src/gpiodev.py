#!/usr/bin/python3
from inspect import GEN_CLOSED
import sys
from enum import Enum
from abc import ABC, abstractmethod
import tty
import termios
class GPIO_INPUT(Enum):
    LEFT=0
    RIGHT=1
    BUTTON=2

class GPIOBaseDev(ABC):

    @abstractmethod
    def write_display_line(self, line_no:int, line:str):
        pass

    @abstractmethod
    def wait_for_gpio_event(self)->GPIO_INPUT:
        return GPIO_INPUT.LEFT

    def get_number_of_lines(self)->int:
        return 4

class TestGPIODev(GPIOBaseDev):

    def clear(self):
        print(chr(27) + "[H" + chr(27) + "[J")

    def write_display_line(self,line_no:int, line:str):
        if line_no==1:
            self.clear()
        print(' '+line[:20])


    def wait_for_gpio_event(self) -> GPIO_INPUT:
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
            else:
                print('Unbekanter Tastendruck %d "%s"',ord(ch),ch)

