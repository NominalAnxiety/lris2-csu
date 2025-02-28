class SlitBar:
    """
    A SlitBar is a single actuator driving part of a slit mechanism.
    """

    def __init__(self, bus: CSUBus, slave_id: int):
        super().__init__(bus, slave_id)

    def move_to(self, position: float):
        """Moves the slit bar to a defined position."""
        self.set_position(position)


class SlitBarPair:
    """
    Represents a pair of opposed slit bars forming a controllable slit.
    """

    def __init__(self, bar1: SlitBar, bar2: SlitBar):
        self.bar1 = bar1
        self.bar2 = bar2

    def set_slit_position(self, center: float, width: float):
        """Moves the slit bars to create a slit at a given center position and width."""
        self.bar1.move_to(center - width / 2)
        self.bar2.move_to(center + width / 2)


class Slit:
    """
    Represents a slit that may consist of one or multiple SlitBarPairs.
    """

    def __init__(self, bar_pairs: list[SlitBarPair]):
        self.bar_pairs = bar_pairs

    def configure_slit(self, center: float, width: float):
        """Sets the position and width of all bar pairs forming the slit."""
        for pair in self.bar_pairs:
            pair.set_slit_position(center, width)
