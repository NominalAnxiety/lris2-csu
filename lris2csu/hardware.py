from logging import getLogger
from cooethercat import EPOS4Motor
from cooethercat.helpers import make_pdo_mapping
import yaml
from typing import NamedTuple


# class CSU_motor_config_defaults(NamedTuple):
#     motor_type: int = 10
#     nominal_current_ma: int = 1000
#     output_current_limit_ma: int = 1000
#     number_of_pole_pairs: int = 7
#     thermal_time_constant_winding_ms: int = 100
#     torque_constant_uNm_A: int = 100
#     max_motor_speed_rpm: int = 1000
#
# class CSU_gear_config_defaults(NamedTuple):
#     gear_reduction_numerator: int = 1
#     gear_reduction_denominator: int = 1
#     gear_max_input_speed_rpm: int = 1000
#     orientation: int = 1
#
# class CSU_digital_incremental_encoder_config_defaults(NamedTuple):
#     number_of_pulses_per_turn: int = 1000
#     encoder_type: int = 1
#     direction: int = 1
#     method: int = 1
#
# class CSU_ssi_encoder_config_defaults(NamedTuple):
#     data_rate: int = 1000000
#     number_of_bits: int = 24
#     encoding_type: int = 1
#     direction: int = 1
#     check_frame: int = 1
#     timeout_time_ms: int = 1000
#     number_of_multi_turn_bits: int = 12
#     number_of_single_turn_bits: int = 12



class CSUHardwareConfig:
    yaml_tag = u'!CSUHardwareConfig'

    def __init__(self, ethercat_device:str, bar_pairs:list["BarPairConfig"], left_brake, right_brake):
        self.ethercat_device = ethercat_device
        self.bar_pairs = {x.id: x for x in bar_pairs}
        self.left_brake = left_brake
        self.right_brake = right_brake

    @classmethod
    def from_yaml(cls, loader, node):
        # Construct mapping from the YAML node
        values = loader.construct_mapping(node, deep=True)
        return cls(**values)

    @classmethod
    def to_yaml(cls, dumper, data):
        # Convert the Python object into a mapping
        mapping = {
            'ethercat_device': data.ethercat_device,
            'bar_pairs': data.bar_pairs,
            'left_brake': data.left_brake,
            'right_brake': data.right_brake,
        }
        return dumper.represent_mapping(cls.yaml_tag, mapping)


# Register the representer and constructor with PyYAML
yaml.add_representer(CSUHardwareConfig, CSUHardwareConfig.to_yaml)
yaml.add_constructor(u'!CSUHardwareConfig', CSUHardwareConfig.from_yaml)


class BarPairConfig:
    yaml_tag = u'!BarPairConfig'

    def __init__(self, id:int, left:"BarConfig", right:"BarConfig"):
        self.id = id
        self.left = left  # Expected to be a BarConfig instance
        self.right = right  # Expected to be a BarConfig instance

    def __repr__(self):
        return f"BarPairConfig(id={self.id}, left={self.left}, right={self.right})"

    @classmethod
    def from_yaml(cls, loader, node):
        values = loader.construct_mapping(node, deep=True)
        return cls(**values)

    @classmethod
    def to_yaml(cls, dumper, data):
        mapping = {'id': data.id, 'left': data.left, 'right': data.right}
        return dumper.represent_mapping(cls.yaml_tag, mapping)

# Register the representer and constructor with PyYAML
yaml.add_representer(BarPairConfig, BarPairConfig.to_yaml)
yaml.add_constructor(u'!BarPairConfig', BarPairConfig.from_yaml)


class BarConfig:
    yaml_tag = u'!BarConfig'

    def __init__(self, bus_id, speed=0, torque_limit=0, mm_per_count=1.0, reversed=False):
        self.bus_id = bus_id
        self.speed = speed
        self.torque_limit = torque_limit
        self.mm_per_count = mm_per_count
        self.reversed = reversed
        assert self.mm_per_count!=0
        if self.mm_per_count<0:
            assert reversed==True, 'If mm_per_count is negative, reversed must be True'
        if reversed and self.mm_per_count>0:
            getLogger(__name__).warning(f'Inverting mm_per_count ({mm_per_count}) for bus_id {bus_id} as reversed is set.')
            self.mm_per_count=-self.mm_per_count

    def __repr__(self):
        return (f"BarMotor(bus_id={self.bus_id}, speed={self.speed}, "
                f"torque_limit={self.torque_limit}, mm_per_count={self.mm_per_count}, "
                f"reversed={self.reversed})")

    @classmethod
    def from_yaml(cls, loader, node):
        # Create a dictionary from the YAML node.
        values = loader.construct_mapping(node, deep=True)
        # Manual initialization from parameters.
        return cls(**values)

    @classmethod
    def to_yaml(cls, dumper, data):
        # Convert the BarMotor instance back into a YAML mapping.
        mapping = {
            'bus_id': data.bus_id,
            'speed': data.speed,
            'torque_limit': data.torque_limit,
            'mm_per_count': data.mm_per_count,
            'reversed': data.reversed
        }
        return dumper.represent_mapping(cls.yaml_tag, mapping)


# Register the representer and constructor with PyYAML.
yaml.add_representer(BarConfig, BarConfig.to_yaml)
yaml.add_constructor(u'!BarConfig', BarConfig.from_yaml)


class BarMotor(EPOS4Motor):
    # def home(self):
    #     pass
    #
    # def goto(self, x):
    #     pass
    #
    # def position(self):
    #     return 0
    #
    # def status(self):
    #     return {}

    def config_func(self, bus_id):
        getLogger(__name__).debug(f"Configuring device {self} via config_func (EPOS4 Micro 24/5)")
        assert bus_id == self.node

        # Define the Process Data Objects for PPM (Rx and Tx)
        ppm_rx = [
            self.object_dict.CONTROLWORD,
            self.object_dict.TARGET_POSITION,
            self.object_dict.PROFILE_ACCELERATION,
            self.object_dict.PROFILE_DECELERATION,
            self.object_dict.PROFILE_VELOCITY,
            self.object_dict.MODES_OF_OPERATION,
            self.object_dict.PHYSICAL_OUTPUTS
        ]
        ppm_tx = [
            self.object_dict.STATUSWORD,
            self.object_dict.POSITION_ACTUAL_VALUE,
            self.object_dict.VELOCITY_ACTUAL_VALUE,
            self.object_dict.FOLLOWING_ERROR_ACTUAL_VALUE,
            self.object_dict.MODES_OF_OPERATION_DISPLAY,
            self.object_dict.DIGITAL_INPUTS
        ]

        # Create rx and tx map integers
        rx_address_ints = make_pdo_mapping(ppm_rx)
        tx_address_ints = make_pdo_mapping(ppm_tx)

        # Assign rx map
        self._sdo_write(self.object_dict.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, 0)
        for i, addressInt in enumerate(rx_address_ints):
            self._sdo_write((0x1600, i + 1, 'I'), addressInt)
        self._sdo_write(self.object_dict.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, len(ppm_rx))

        # Assign tx map
        self._sdo_write(self.object_dict.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, 0)
        for i, addressInt in enumerate(tx_address_ints):
            self._sdo_write((0x1A00, i + 1, 'I'), addressInt)
        self._sdo_write(self.object_dict.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, len(ppm_tx))

        self.currentRxPDOMap = ppm_rx
        self.currentTxPDOMap = ppm_tx

        # Configure Digital Inputs (example)
        self._sdo_write(self.object_dict.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 255)
        self._sdo_write(self.object_dict.DIGITAL_INPUT_CONFIGURATION_DGIN_2, 1)
        self._sdo_write(self.object_dict.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 0)

        # Set the home offset move distance
        getLogger(__name__).debug(f"Configuring device {self} complete.")


    # def config_func(self, motor_configuration=CSU_motor_config_defaults(),
    #                     gear_configuration=CSU_gear_config_defaults(),
    #                     digital_incremental_encoder_configuration=CSU_digital_incremental_encoder_config_defaults(),
    #                     ssi_encoder_configuration=CSU_ssi_encoder_config_defaults()):
    #     """! Configure the slave
    #     @param slave: the slave to configure
    #     @param motor_configuration: the motor configuration
    #     @param gear_configuration: the gear configuration
    #     @param digital_incremental_encoder_configuration: the digital incremental encoder configuration
    #     @param ssi_encoder_configuration: the SSI encoder configuration
    #     """
    #
    #     if slave == None:
    #         logging.error('configure_slave: no slave available')
    #         return
    #
    #     set_node_id(slave, 1)
    #     set_motor_data(slave, motor_configuration.nominal_current_ma, motor_configuration.output_current_limit_ma,
    #                    motor_configuration.thermal_time_constant_winding_ms, motor_configuration.torque_constant_uNm_A)
    #     set_gear_data(slave, gear_configuration.gear_reduction_numerator,
    #                   gear_configuration.gear_reduction_denominator, gear_configuration.gear_max_input_speed_rpm,
    #                   gear_configuration.orientation)
    #     set_digital_incremental_encoder_data(slave, digital_incremental_encoder_configuration.number_of_pulses_per_turn,
    #                                          digital_incremental_encoder_configuration.encoder_type,
    #                                          digital_incremental_encoder_configuration.direction,
    #                                          digital_incremental_encoder_configuration.method)
    #     set_ssi_encoder_data(slave, ssi_encoder_configuration.data_rate, ssi_encoder_configuration.number_of_bits,
    #                          ssi_encoder_configuration.encoding_type, ssi_encoder_configuration.direction,
    #                          ssi_encoder_configuration.check_frame, ssi_encoder_configuration.timeout_time_ms,
    #                          ssi_encoder_configuration.number_of_multi_turn_bits,
    #                          ssi_encoder_configuration.number_of_single_turn_bits)
    #     slave.dc_sync(act=True, sync0_cycle_time=1000000)


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
            self.object_dict.CONTROLWORD,
            self.object_dict.TARGET_POSITION,
            self.object_dict.PROFILE_ACCELERATION,
            self.object_dict.PROFILE_DECELERATION,
            self.object_dict.PROFILE_VELOCITY,
            self.object_dict.MODES_OF_OPERATION,
            self.object_dict.PHYSICAL_OUTPUTS
        ]
        ppm_tx = [
            self.object_dict.STATUSWORD,
            self.object_dict.POSITION_ACTUAL_VALUE,
            self.object_dict.VELOCITY_ACTUAL_VALUE,
            self.object_dict.FOLLOWING_ERROR_ACTUAL_VALUE,
            self.object_dict.MODES_OF_OPERATION_DISPLAY,
            self.object_dict.DIGITAL_INPUTS
        ]

        # Create rx and tx map integers
        rx_address_ints = make_pdo_mapping(ppm_rx)
        tx_address_ints = make_pdo_mapping(ppm_tx)

        # Assign rx map
        self.sdo_write(self.object_dict.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, 0)
        for i, addressInt in enumerate(rx_address_ints):
            self.sdo_write((0x1600, i + 1, 'I'), addressInt)
        self.sdo_write(self.object_dict.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, len(ppm_rx))

        # Assign tx map
        self.sdo_write(self.object_dict.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, 0)
        for i, addressInt in enumerate(tx_address_ints):
            self.sdo_write((0x1A00, i + 1, 'I'), addressInt)
        self.sdo_write(self.object_dict.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, len(ppm_tx))

        self.currentRxPDOMap = ppm_rx
        self.currentTxPDOMap = ppm_tx

        # Configure Digital Inputs (example)
        self.sdo_write(self.object_dict.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 255)
        self.sdo_write(self.object_dict.DIGITAL_INPUT_CONFIGURATION_DGIN_2, 1)
        self.sdo_write(self.object_dict.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 0)

        # Set the home offset move distance
        self.sdo_write(self.object_dict.HOME_OFFSET_MOVE_DISTANCE, -622080)
        getLogger(__name__).debug(f"Configuring device {self} complete.")
