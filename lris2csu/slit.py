class Slit:
    """
    A slit defined by a bar pair id, a position (treated as the lower left corner of the slit opening), and a
     width. millimeters.
    """

    def __init__(self, id: int, x: float, width: float):
        self.id = id
        self.x = x
        self.width = width

    def __repr__(self):
        return f"Slit(id={self.id} x={self.x}, width={self.width})"


class MaskConfig:
    """
    Holds a collection of Slit objects, ensuring that no two Slits share a bar center.
    """

    def __init__(self, slits: tuple[Slit,...]):
        used_bars = set(s.id for s in slits)
        if len(used_bars) != len(slits):
            raise ValueError(f"SlitBar collision detected - multiple slits share bar pair.")
        self.slits = tuple(slits)

    def __repr__(self):
        return f"MaskConfig(slits={self.slits})"

    def to_dict(self):
        return {s.id: (s.x, s.width) for s in self.slits}

    @classmethod
    def from_dict(cls,d):
        return cls(tuple([Slit(int(i), pos, wid) for i, (pos, wid) in d.items()]))