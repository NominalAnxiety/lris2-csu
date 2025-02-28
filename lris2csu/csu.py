
class CSURemote:
    pass

class CSUManager:
    """
    Manages multiple slits and provides a higher-level interface.
    """

    def __init__(self, slits: list[Slit]):
        self.slits = slits

    def configure_all_slits(self, slit_configs: list[tuple[float, float]]):
        """Configures all slits according to given center and width pairs."""
        for slit, (center, width) in zip(self.slits, slit_configs):
            slit.configure_slit(center, width)
