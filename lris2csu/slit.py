from cooethercat.epos4 import EPOS4Bus

class Bar:
    """
    A SlitBar is a single actuator driving part of a slit mechanism.
    """

    def __init__(self, y, bus: EPOS4Bus, slave_id: int):
        self._epos_bus = bus
        self._id = slave_id
        self.y = y

    def move_to(self, position: float):
        """Moves the slit bar to a defined position."""
        self._epos_bus.move_to(position, slave_ids=self._id)

    def engineering_status(self):
        pass

    def get_positon(self):
        #TODO
        #self._epos_bus.
        pass

class BarPair:
    """
    Represents a pair of opposed slit bars forming a controllable slit.
    """

    def __init__(self, bar1: Bar, bar2: Bar):
        assert bar1.y == bar2.y
        self.bar1 = bar1
        self.bar2 = bar2

    @property
    def y(self):
        return self.bar1.y

    def set_position(self, center: float, width: float):
        """Moves the slit bars to create a slit at a given center position and width."""
        self.bar1.move_to(center - width / 2)
        self.bar2.move_to(center + width / 2)

    def get_position(self):
        x1 = self.bar1.get_positon()
        x2 = self.bar2.get_positon()
        return (x1+x2)/2, self.y, (x2-x1)


class SlitInstance:
    def __init__(self, center: float, width:float, bar_pairs:BarPair|list[BarPair]):
        self.bars = [bar_pairs] if isinstance(bar_pairs, BarPair) else bar_pairs
        self.center = center
        self.width = max(width, 0)

    def go(self):
        for b in self.bars:
            b.set_position(self.center, self.width)


class SlitBar:
    """
    Encapsulates a single slit bar, identified by its center.
    The center is always snapped to the center of the slit bar it is on
    """

    SLIT_BAR_HEIGHT = 2.0  # Example placeholder value

    def __init__(self, center: float):
        assert center >=0
        # Round to the bar's center
        bar_number = center // self.SLIT_BAR_HEIGHT
        self.center = (bar_number + 0.5 ) * self.SLIT_BAR_HEIGHT

    @property
    def y_bottom(self) -> float:
        """
        Returns the bottom edge of this slit bar,
        which is (center - SLIT_BAR_HEIGHT/2).
        """
        return self.center - (self.SLIT_BAR_HEIGHT / 2.0)

    @property
    def y_top(self) -> float:
        """
        Returns the top edge of this slit bar,
        which is (center + SLIT_BAR_HEIGHT/2).
        """
        return self.center + (self.SLIT_BAR_HEIGHT / 2.0)

    def __eq__(self, other):
        if not isinstance(other, SlitBar):
            return False
        return self.center == other.center

    def __hash__(self):
        # Hash based on the bar’s center so it can be used in sets/dicts
        return hash(self.center)

    def __repr__(self):
        return f"SlitBar(center={self.center})"


class Slit:
    """
    A slit defined by an (x, y) position (treated as the midpoint of the lower edge of the bottom slit bar),
     width, and length.
    The 'y' position is snapped to a multiple of SlitBar.SLIT_BAR_HEIGHT.
    The 'length' is forced to be an integer multiple of SlitBar.SLIT_BAR_HEIGHT via rounding,
    the slit center is automatically computed from the bottom to top of the slit.
    """

    def __init__(self, x: float, y: float, width: float, length: float):
        # Snap y to bar
        self.bottom_y = SlitBar.SLIT_BAR_HEIGHT * (y // SlitBar.SLIT_BAR_HEIGHT)

        # Ensure 'length' is an integer multiple of SLIT_BAR_HEIGHT
        n_bars = round(length / SlitBar.SLIT_BAR_HEIGHT)
        self.length = n_bars * SlitBar.SLIT_BAR_HEIGHT

        self.x = x
        self.width = width
        self.y = self.length/2+self.bottom_y

        # Create the bars (each bar has a unique center)
        self._bars = [SlitBar(self.bottom_y + (i * SlitBar.SLIT_BAR_HEIGHT)) for i in range(n_bars)]

    def get_bar_positions(self) -> dict[float, tuple[float, float]]:
        """
        Returns a dictionary keyed by bar center, with (x, width) as the value
        for each SlitBar in this Slit.
        """
        return {bar.center: (self.x, self.width) for bar in self._bars}

    @property
    def bars(self) -> list[SlitBar]:
        return self._bars

    def __repr__(self):
        return (f"Slit(x={self.x}, y={self.y}, width={self.width}, "
                f"length={self.length}, bars={self._bars})")


class MaskConfig:
    """
    Holds a collection of Slit objects, ensuring that no two Slits share a bar center.
    """

    def __init__(self, slits: list[Slit]):
        used_bars = set()
        for slit in slits:
            for bar in slit.bars:
                if bar in used_bars:
                    raise ValueError(
                        f"SlitBar collision detected - multiple Slits share bar at center {bar.center}."
                    )
                used_bars.add(bar)
        self.slits = slits

    def __repr__(self):
        return f"MaskConfig(slits={self.slits})"
