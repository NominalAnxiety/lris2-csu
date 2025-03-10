from logging import getLogger
from cooethercat import EPOS4Motor
from cooethercat.helpers import makePDOMapping


class Bar(EPOS4Motor):
    def home(self):
        pass

    def goto(self, x):
        pass

    def position(self):
        return 0

    def status(self):
        return {}

    def config_func(self, bus_id):
        """ Configures an EPOS4 Micro TRB 12CC device """
        getLogger(__name__).debug(f"Configuring device {self} (EPOS4 Micro 24/5)")
        assert bus_id == self.node  #TODO check that this is actually an attribute
            #
        # Define the Process Data Objects for PPM (Rx and Tx)
        ppm_rx = [
            self.objectDictionary.CONTROLWORD,
            self.objectDictionary.TARGET_POSITION,
            self.objectDictionary.PROFILE_ACCELERATION,
            self.objectDictionary.PROFILE_DECELERATION,
            self.objectDictionary.PROFILE_VELOCITY,
            self.objectDictionary.MODES_OF_OPERATION,
            self.objectDictionary.PHYSICAL_OUTPUTS
        ]
        ppm_tx = [
            self.objectDictionary.STATUSWORD,
            self.objectDictionary.POSITION_ACTUAL_VALUE,
            self.objectDictionary.VELOCITY_ACTUAL_VALUE,
            self.objectDictionary.FOLLOWING_ERROR_ACTUAL_VALUE,
            self.objectDictionary.MODES_OF_OPERATION_DISPLAY,
            self.objectDictionary.DIGITAL_INPUTS
        ]

        # Create rx and tx map integers
        rx_address_ints = makePDOMapping(ppm_rx)
        tx_address_ints = makePDOMapping(ppm_tx)

        # Assign rx map
        self._sdo_write(self.objectDictionary.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, 0)
        for i, addressInt in enumerate(rx_address_ints):
            self._sdo_write((0x1600, i + 1, 'I'), addressInt)
        self._sdo_write(self.objectDictionary.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, len(ppm_rx))

        # Assign tx map
        self._sdo_write(self.objectDictionary.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, 0)
        for i, addressInt in enumerate(tx_address_ints):
            self._sdo_write((0x1A00, i + 1, 'I'), addressInt)
        self._sdo_write(self.objectDictionary.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, len(ppm_tx))

        self.currentRxPDOMap = ppm_rx
        self.currentTxPDOMap = ppm_tx

        # Configure Digital Inputs (example)
        self._sdo_write(self.objectDictionary.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 255)
        self._sdo_write(self.objectDictionary.DIGITAL_INPUT_CONFIGURATION_DGIN_2, 1)
        self._sdo_write(self.objectDictionary.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 0)

        # Set the home offset move distance
        self._sdo_write(self.objectDictionary.HOME_OFFSET_MOVE_DISTANCE, -622080)
        getLogger(__name__).debug(f"Configuring device {self} complete.")



class Break(EPOS4Motor):
    def engage(self):
        pass

    def disengage(self):
        pass

    def config_func(self, bus_id):
        """ Configures an EPOS4 Micro TRB 12CC device """
        getLogger(__name__).debug(f"Configuring device {self} (EPOS4 Micro 24/5)")
        assert bus_id == self.id  #TODO check that this is actually an attribute
            #
        # Define the Process Data Objects for PPM (Rx and Tx)
        ppm_rx = [
            self.objectDictionary.CONTROLWORD,
            self.objectDictionary.TARGET_POSITION,
            self.objectDictionary.PROFILE_ACCELERATION,
            self.objectDictionary.PROFILE_DECELERATION,
            self.objectDictionary.PROFILE_VELOCITY,
            self.objectDictionary.MODES_OF_OPERATION,
            self.objectDictionary.PHYSICAL_OUTPUTS
        ]
        ppm_tx = [
            self.objectDictionary.STATUSWORD,
            self.objectDictionary.POSITION_ACTUAL_VALUE,
            self.objectDictionary.VELOCITY_ACTUAL_VALUE,
            self.objectDictionary.FOLLOWING_ERROR_ACTUAL_VALUE,
            self.objectDictionary.MODES_OF_OPERATION_DISPLAY,
            self.objectDictionary.DIGITAL_INPUTS
        ]

        # Create rx and tx map integers
        rx_address_ints = makePDOMapping(ppm_rx)
        tx_address_ints = makePDOMapping(ppm_tx)

        # Assign rx map
        self.sdo_write(self.objectDictionary.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, 0)
        for i, addressInt in enumerate(rx_address_ints):
            self.sdo_write((0x1600, i + 1, 'I'), addressInt)
        self.sdo_write(self.objectDictionary.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, len(ppm_rx))

        # Assign tx map
        self.sdo_write(self.objectDictionary.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, 0)
        for i, addressInt in enumerate(tx_address_ints):
            self.sdo_write((0x1A00, i + 1, 'I'), addressInt)
        self.sdo_write(self.objectDictionary.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, len(ppm_tx))

        self.currentRxPDOMap = ppm_rx
        self.currentTxPDOMap = ppm_tx

        # Configure Digital Inputs (example)
        self.sdo_write(self.objectDictionary.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 255)
        self.sdo_write(self.objectDictionary.DIGITAL_INPUT_CONFIGURATION_DGIN_2, 1)
        self.sdo_write(self.objectDictionary.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 0)

        # Set the home offset move distance
        self.sdo_write(self.objectDictionary.HOME_OFFSET_MOVE_DISTANCE, -622080)
        getLogger(__name__).debug(f"Configuring device {self} complete.")
