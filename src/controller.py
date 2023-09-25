import pygame


pygame.joystick.init()

class Controller:
    def __init__(self):
        self.joystick = None
        self.joysticks = {}
        self.names = {}
        self.last = None
        self.map = {
            "PS5 Controller": {
                "buttons": {
                    "up": 11,
                    "down": 12,
                    "left": 13,
                    "right": 14,
                    "cross": 0,
                    "circle": 1,
                    "square": 2,
                    "triangle": 3,
                    "L3": 7,
                    "R3": 8,
                    "PS": 5,
                    "mute": 16,
                    "L1": 9,
                    "R1": 10,
                },
                "axes": {
                    "Jleft": (0, 1),
                    "Jright": (2, 3),
                    "L2": 4,
                    "R2": 5,
                },

                "last_axismo": {},
                "axis_down": {},
            },
            "PS3 Controller": {
                "buttons": {

                },

                "axes": {

                }
            }
        }
        for k, v in self.map.items():
            self.map[k]["last_axismo"] = dict.fromkeys(self.map[k]["axes"].keys(), 0)
            self.map[k]["axis_down"] = dict.fromkeys(self.map[k]["axes"].keys(), False)
            self.map[k]["can_up"] = True
            self.map[k]["can_down"] = True
        self.rmap = {controller_type: {key_type: {v: k for k, v in binds.items()} if isinstance(binds, dict) else binds for key_type, binds in data.items()} for controller_type, data in self.map.items()}
        self.button_protocol = {}
        self.next_protocol = {}

    @property
    def name(self):
        return self.joystick.get_name()

    def init(self, index):
        joystick = pygame.joystick.Joystick(index)
        iid = joystick.get_instance_id()
        self.joysticks[iid] = joystick
        self.names[iid] = joystick.get_name()
        self.last = iid

    def activate(self):
        self.joystick = self.joysticks[self.last]

    def remove(self, iid):
        del self.joysticks[iid]
        if index == self.joystick.get_instance_id():
            self.joystick = None


controller = Controller()
