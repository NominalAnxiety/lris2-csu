from dataclasses import dataclass
from logging import getLogger
import yaml
from typing import NamedTuple

from cooethercat import EPOS4Motor
from cooethercat.helpers import make_pdo_mapping, EPOS4Obj


class CSUHardwareConfig:
    yaml_tag = u'!CSUHardwareConfig'

    def __init__(self, ethercat_device:str, bar_pairs:list["BarPairConfig"], left_brake, right_brake):
        self.ethercat_device = ethercat_device
        self.bar_pairs = {x.id: x for x in bar_pairs}
        self.left_brake = left_brake
        self.right_brake = right_brake
        self.opening_width_mm = 260

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

    @property
    def bar_configs(self)->dict[int, "BarConfig"]:
        return {b.bus_id: b for bp in self.bar_pairs.values() for b in (bp.left, bp.right)}

    def bar_by_dev_id(self, id):
        return self.bar_configs()[id]

    def compute_bar_count_positions(self, pos_width_dict: dict[int, tuple[float, float]]) -> dict[int]:
        """
        Computes the bar count positions for a given bar pair configuration.

        Args:
            pos_width_dict: A dictionary keyed on bar pair id with a tuple (position, width) in mm.
            bar_pair: An instance of BarPairConfig containing 'id', 'left' (BarConfig), and 'right' (BarConfig).

        Returns:
            A dictionary with bus_id as keys and the computed bar count positions as values.
            For the left side, count position = (position - width/2) / left.um_per_count.
            For the right side, count position = (position + width/2) / right.um_per_count.
        """
        # Retrieve the requested (position, width) tuple for this bar pair.
        ret = {}
        for id in pos_width_dict:

            if id not in self.bar_pairs:
                raise KeyError(f"No bar pair with id {id} found in the bar pair configuration.")

            position, width = pos_width_dict[id]
            bar_pair = self.bar_pairs[id]

            # Compute the absolute physical positions in mm for left and right.
            # lower left is origin
            left_mm = (position - width / 2.0) - bar_pair.left.offset_mm
            right_mm = (position + width / 2.0)

            right_travel_mm = self.opening_width_mm - right_mm - bar_pair.right.offset_mm

            # Convert mm to counts using the respective um_per_count conversion factors.
            left_count = left_mm*1000 / bar_pair.left.um_per_count
            right_count = right_travel_mm*1000 / bar_pair.right.um_per_count

            ret[bar_pair.left.bus_id] = int(round(left_count))
            ret[bar_pair.right.bus_id] = int(round(right_count))

        return ret

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

    def __init__(self, bus_id, speed:int=0, torque_limit=0, um_per_count:float=1.0, reversed:bool=False,
                 offset_mm:float=0, use_ssi_encoder:bool=False):
        self.bus_id = bus_id
        self.speed = speed
        self.torque_limit = torque_limit
        self.um_per_count = um_per_count
        self.reversed = reversed
        self.offset_mm = offset_mm
        self.use_ssi_encoder = use_ssi_encoder
        assert self.um_per_count!=0
        if self.um_per_count<0:
            assert reversed==True, 'If um_per_count is negative, reversed must be True'
        if reversed and self.um_per_count>0:
            getLogger(__name__).warning(f'Inverting um_per_count ({um_per_count}) for bus_id {bus_id} as '
            f'reversed is set. Consider defining with a negative for better clarity.')
            self.um_per_count=-self.um_per_count

    def __repr__(self):
        return (f"BarMotor(bus_id={self.bus_id}, speed={self.speed}, "
                f"torque_limit={self.torque_limit}, um_per_count={self.um_per_count}, "
                f"reversed={self.reversed} offset_mm={self.offset_mm} use_ssi_encoder={self.use_ssi_encoder})")

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
            'um_per_count': data.um_per_count,
            'reversed': data.reversed,
            'offset_mm': data.offset_mm,
            'use_ssi_encoder': data.use_ssi_encoder,
        }
        return dumper.represent_mapping(cls.yaml_tag, mapping)


# Register the representer and constructor with PyYAML.
yaml.add_representer(BarConfig, BarConfig.to_yaml)
yaml.add_constructor(u'!BarConfig', BarConfig.from_yaml)


class CSU_ECmax16_283828_config(NamedTuple):
    motor_type: int = 10  # 6-227
    nominal_current_ma: int = 456  # max continuous current
    output_current_limit_ma: int = 762
    number_of_pole_pairs: int = 1
    thermal_time_constant_winding_ms: int = 914
    torque_constant_uNm_A: int = 7800
    max_motor_speed_rpm: int = 20000


class CSU_ENC16EASY_499361_config(NamedTuple):
    number_of_pulses_per_turn: int = 1024
    direction: int = 0  #0=maxon 1=inverted (on output shaft)
    index: int = 1
    method: int = 1  # edges per control cycle, 0 is edges per time  6.152


class CSU_planetary_gearhead_GP16A_138342_config(NamedTuple):
    gear_reduction_numerator: int = 29198
    gear_reduction_denominator: int = 79
    gear_max_input_speed_rpm: int = 8000
    gear_orientation: int = 0  # 0: output = input


#pole length 2mm
#ssi+incremental, no line driver, 5v
#12bit period counter
#2048 interpolation factor 0.977um
#1us/1MHz minimum edge separation (I'd guess then 2mm/1us = 2m/s max speed so we are VERY safe)
class CSU_SSI_encoder_RLM2sJF11B_config(NamedTuple):
    data_rate_kbps: int = 2000  #encode min 50 max 4000 epos max 2000
    # number_of_bits: int = 13
    encoding_type: int = 0 #TODO 0=binary 1=gray
    direction: int = 1 #TODO  0=maxon 1=inverted or mounted on output shaft
    # check_frame: int = 1
    timeout_time_us: int = 20
    number_of_multi_turn_bits: int = 11 #TODO
    number_of_single_turn_bits: int = 12
    number_of_error_bits: int = 2
    power_up_time: int = 50


@dataclass
class CSU_PID_CONFIG:
    position_controller_p_gain: int
    position_controller_i_gain: int
    position_controller_d_gain: int
    position_controller_ff_velocity_gain: int
    position_controller_ff_acceleration_gain: int
    current_controller_p_gain: int
    current_controller_i_gain: int
    velocity_controller_p_gain: int
    velocity_controller_i_gain: int
    velocity_controller_ff_velocity_gain: int
    velocity_controller_ff_acceleration_gain: int


class BarMotor(EPOS4Motor):
    DUAL_LOOP_PID_PARAMS = CSU_PID_CONFIG(0,0,0,0,0,0,0,0,0,0,0)  #TODO
    SINGLE_LOOP_PID_PARAMS = CSU_PID_CONFIG(0,0,0,0,0,0,0,0,0,0,0)  #TODO

    def __init__(self, *args, use_ssi_encoder=False, **kwargws):
        super().__init__(*args, **kwargws)
        self.use_ssi_encoder = use_ssi_encoder

    def config_func(self, node_id):
        getLogger(__name__).debug(f"Configuring BarMotor device {self} via config_func"
                                  f" (EPOS4 Micro 24/5) at bus node {self.node}")
        assert node_id == self.node

        # Define the Process Data Objects for PPM (Rx and Tx)
        ppm_rx = [
            self.ADDRESS.CONTROLWORD,
            self.ADDRESS.TARGET_POSITION,
            self.ADDRESS.PROFILE_ACCELERATION,
            self.ADDRESS.PROFILE_DECELERATION,
            self.ADDRESS.PROFILE_VELOCITY,
            self.ADDRESS.MODES_OF_OPERATION,
            self.ADDRESS.PHYSICAL_OUTPUTS
        ]
        ppm_tx = [
            self.ADDRESS.STATUSWORD,
            self.ADDRESS.POSITION_ACTUAL_VALUE,
            self.ADDRESS.VELOCITY_ACTUAL_VALUE,
            self.ADDRESS.FOLLOWING_ERROR_ACTUAL_VALUE,
            self.ADDRESS.MODES_OF_OPERATION_DISPLAY,
            self.ADDRESS.DIGITAL_INPUTS
        ]

        # Create rx and tx map integers
        rx_address_ints = make_pdo_mapping(ppm_rx)
        tx_address_ints = make_pdo_mapping(ppm_tx)

        # Assign rx map
        self._sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, 0)
        for i, addressInt in enumerate(rx_address_ints):
            self._sdo_write(EPOS4Obj(0x1600, i + 1, 'I', 32), addressInt)
        self._sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, len(ppm_rx))

        # Assign tx map
        self._sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, 0)
        for i, addressInt in enumerate(tx_address_ints):
            self._sdo_write(EPOS4Obj(0x1A00, i + 1, 'I', 32), addressInt)
        self._sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, len(ppm_tx))

        self.currentRxPDOMap = ppm_rx
        self.currentTxPDOMap = ppm_tx

        # Configure Digital Inputs (example)
        self._sdo_write(self.ADDRESS.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 255)
        self._sdo_write(self.ADDRESS.DIGITAL_INPUT_CONFIGURATION_DGIN_2, 1)
        self._sdo_write(self.ADDRESS.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 0)

        # Set the home offset move distance
        getLogger(__name__).debug(f"Configuring device {self} complete.")

        self.config_drive(enable_magnetic_tape=self.use_ssi_encoder)

    def config_drive(self, enable_magnetic_tape=False, motor_configuration=CSU_ECmax16_283828_config(),
                        gear_configuration=CSU_planetary_gearhead_GP16A_138342_config(),
                        digital_incremental_encoder_configuration=CSU_ENC16EASY_499361_config(),
                        ssi_encoder_configuration=CSU_SSI_encoder_RLM2sJF11B_config()):

        self._sdo_write(self.ADDRESS.NODE_ID, self.node)

        # Teach the EPOS about the motor
        self._set_motor_data(motor_configuration.nominal_current_ma, motor_configuration.output_current_limit_ma,
                       motor_configuration.thermal_time_constant_winding_ms, motor_configuration.torque_constant_uNm_A)
        self._set_gear_data(gear_configuration.gear_reduction_numerator,
                      gear_configuration.gear_reduction_denominator, gear_configuration.gear_max_input_speed_rpm,
                      gear_configuration.gear_orientation)
        self._set_incremental_encoder_data(digital_incremental_encoder_configuration.number_of_pulses_per_turn,
                                             digital_incremental_encoder_configuration.index,
                                             digital_incremental_encoder_configuration.direction,
                                             digital_incremental_encoder_configuration.method)
        self._set_ssi_encoder_data(ssi_encoder_configuration.data_rate_kbps,
                                  ssi_encoder_configuration.encoding_type, ssi_encoder_configuration.direction,
                                  ssi_encoder_configuration.timeout_time_us,
                                  ssi_encoder_configuration.number_of_multi_turn_bits,
                                  ssi_encoder_configuration.number_of_single_turn_bits)


        self._set_control_scheme(enable_magnetic_tape=enable_magnetic_tape)
        self.dc_sync(act=True, sync0_cycle_time=1000000)

    def _set_motor_data(self, nominal_current_ma, output_current_limit_ma, number_of_pole_pairs,
                       thermal_time_constant_winding_s, torque_constant_uNm_A):
        self._sdo_write(self.ADDRESS.NOMINAL_CURRENT_MA, nominal_current_ma)
        self._sdo_write(self.ADDRESS.OUTPUT_CURRENT_LIMIT_MA,  output_current_limit_ma)
        self._sdo_write(self.ADDRESS.NUMBER_OF_POLE_PAIRS, number_of_pole_pairs)
        self._sdo_write(self.ADDRESS.THERMAL_TIME_CONSTANT_WINDING_DS, thermal_time_constant_winding_s*10)
        self._sdo_write(self.ADDRESS.TORQUE_CONSTANT_UNM_A, torque_constant_uNm_A)

    def _set_incremental_encoder_data(self, number_of_pulses_per_turn, index, direction, method):
        direction_offset = 4
        method_offset = 9
        type = index | (direction << direction_offset) | (method << method_offset)
        self._sdo_write(self.ADDRESS.DIGITAL_INCREMENTAL_ENCODER_1, number_of_pulses_per_turn)
        self._sdo_write(self.ADDRESS.DIGITAL_INCREMENTAL_ENCODER_1_TYPE, type)

    def _set_gear_data(self, gear_reduction_numerator, gear_reduction_denominator,
                 gear_max_input_speed_rpm, gear_orientation):
        self._sdo_write(self.ADDRESS.GEAR_REDUCTION_NUMERATOR, gear_reduction_numerator)
        self._sdo_write(self.ADDRESS.GEAR_REDUCTION_DENOMINATOR, gear_reduction_denominator)
        self._sdo_write(self.ADDRESS.GEAR_MAX_INPUT_SPEED_RPM, gear_max_input_speed_rpm)
        self._sdo_write(self.ADDRESS.GEAR_ORIENTATION, gear_orientation)

    def _set_ssi_encoder_data(self, data_rate, encoding_type, direction, check_frame, timeout_time_us,
                             number_of_multiturn_bits, number_of_singleturn_bits, power_up_time_ms):

        direction_offset = 4
        check_frame_offset = 8
        encoding = encoding_type | (direction << direction_offset)

        multiturn_offset = 16
        singleturn_offset = 8
        position_bits = (number_of_multiturn_bits << multiturn_offset) | (number_of_singleturn_bits << singleturn_offset)

        self._sdo_write(self.ADDRESS.SSI_DATA_RATE_KBPS, data_rate)
        self._sdo_write(self.ADDRESS.SSI_NUMBER_OF_BITS, position_bits)
        self._sdo_write(self.ADDRESS.SSI_ENCODING_TYPE, encoding)
        self._sdo_write(self.ADDRESS.SSI_TIMEOUT_TIME_US , timeout_time_us)
        self._sdo_write(self.ADDRESS.SSI_POWER_UP_TIME_MS, power_up_time_ms)
        # self._sdo_write(self.ADDRESS.SSI_COMMUTATION_OFFSET_VALUE, commutation_offset)

    def _set_control_scheme(self, enable_magnetic_tape=False):

        sensor_type1 = 0x1  # 0=none 1=dig inc 1

        # 0=none, 1=dig inc 2, 2=analog, 3=ssi
        sensor_type2 = 0x3 if enable_magnetic_tape else 0x0

        sensor_type3 = 0x10 # 0=none 0x10=hall EC motors

        types = [sensor_type1, sensor_type2, sensor_type3]
        offsets = [0, 8, 16]
        sensor_type = 0
        for t, o in zip(types, offsets):
            sensor_type |= t << o

        self._sdo_write(self.ADDRESS.AXIS_SENSORS_CONFIG, sensor_type) #1048577 w/o ssi

        SENSOR_NONE = 0
        SENSOR1 = 1     #digital inc 1
        SENSOR2 = 2     #ssi mag tape
        SENSOR3 = 3     #motor hall sensor

        ON_MOTOR = 0
        ON_GEAR = 1

        #communtation sensors (SEN1&3) must be "on motor"
        #aux sensor must be "on shaft" if enabled
        #process ref val gear pos must be that of the main sensor
        aux_sen = SENSOR1 if enable_magnetic_tape else SENSOR_NONE  #cf. 6.2.49.2 must be on motor shaft
        main_sen = SENSOR2 if enable_magnetic_tape else SENSOR1

        position_control_structure = 2 if enable_magnetic_tape else 1
        velocity_control_structure = 1

        control = (ON_MOTOR<<28 | # sen3 position on motor
                   enable_magnetic_tape<<26 | # sen2 undefined or on gear
                   ON_MOTOR<<24 | #sen1 on motor
                   aux_sen << 20 |
                   main_sen << 16 |
                   (ON_GEAR if enable_magnetic_tape else ON_MOTOR) <<14 | # process value ref
                   1<<12 |#gear is present
                   position_control_structure << 8 |
                   velocity_control_structure <<4 |
                   1 # current_control_tructure )
                   )

        #w/o ssi (initial ishaft and hall only testing
        #control was 0x11111
        # main_sen = 1 = sensor 1 = digital encoder
        # aux_sen = 0
        # velocity_control_structure = 1
        # position_control_structure = 1
        # proc_val_ref = 0
        self._sdo_write(self.ADDRESS.AXIS_CONTROL_STRUCTURE, control) # 69905 w/o ssi

        #default is 0x31 which is what we want
        # self._sdo_write(self.ADDRESS.AXIS_COMMUTATION_SENSORS, 0x31) #0x31 w/o ssi

        clockwise_positive = False
        axis_polarity = 0x1 if clockwise_positive else 0x0
        axis_config_misc = axis_polarity # see 6.2.49.4
        self._sdo_write(self.ADDRESS.AXIS_CONFIG_MISC, axis_config_misc) # 0 w/o ssi

        pid_params = self.DUAL_LOOP_PID_PARAMS if enable_magnetic_tape else self.SINGLE_LOOP_PID_PARAMS

        self._sdo_write(self.ADDRESS.CURRENT_CONTROLLER_P_GAIN, pid_params.current_controller_p_gain)
        self._sdo_write(self.ADDRESS.CURRENT_CONTROLLER_I_GAIN, pid_params.current_controller_i_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_P_GAIN, pid_params.position_controller_p_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_I_GAIN, pid_params.position_controller_i_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_D_GAIN, pid_params.position_controller_d_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_FF_VELOCITY_GAIN, pid_params.position_controller_ff_velocity_gain)
        self._sdo_write(self.ADDRESS.POSITION_CONTROLLER_FF_ACCELERATION_GAIN, pid_params.position_controller_ff_acceleration_gain)
        self._sdo_write(self.ADDRESS.VELOCITY_CONTROLLER_P_GAIN, pid_params.velocity_controller_p_gain)
        self._sdo_write(self.ADDRESS.VELOCITY_CONTROLLER_I_GAIN, pid_params.velocity_controller_i_gain)
        self._sdo_write(self.ADDRESS.VELOCITY_CONTROLLER_FF_VELOCITY_GAIN, pid_params.velocity_controller_ff_velocity_gain)
        self._sdo_write(self.ADDRESS.VELOCITY_CONTROLLER_FF_ACCELERATION_GAIN, pid_params.velocity_controller_ff_acceleration_gain)


class BrakeMotor(EPOS4Motor):
    def engage(self):
        raise NotImplementedError

    def disengage(self):
        raise NotImplementedError

    def config_func(self, bus_id):
        getLogger(__name__).debug(f"Configuring BrakeMotor device {self} via "
                                  f"config_func (EPOS4 Micro 24/5) at bus node {self.node}")
        assert bus_id == self.node
            #
        # Define the Process Data Objects for PPM (Rx and Tx)
        ppm_rx = [
            self.ADDRESS.CONTROLWORD,
            self.ADDRESS.TARGET_POSITION,
            self.ADDRESS.PROFILE_ACCELERATION,
            self.ADDRESS.PROFILE_DECELERATION,
            self.ADDRESS.PROFILE_VELOCITY,
            self.ADDRESS.MODES_OF_OPERATION,
            self.ADDRESS.PHYSICAL_OUTPUTS
        ]
        ppm_tx = [
            self.ADDRESS.STATUSWORD,
            self.ADDRESS.POSITION_ACTUAL_VALUE,
            self.ADDRESS.VELOCITY_ACTUAL_VALUE,
            self.ADDRESS.FOLLOWING_ERROR_ACTUAL_VALUE,
            self.ADDRESS.MODES_OF_OPERATION_DISPLAY,
            self.ADDRESS.DIGITAL_INPUTS
        ]

        # Create rx and tx map integers
        rx_address_ints = make_pdo_mapping(ppm_rx)
        tx_address_ints = make_pdo_mapping(ppm_tx)

        # Assign rx map
        self.sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, 0)
        for i, addressInt in enumerate(rx_address_ints):
            self.sdo_write((0x1600, i + 1, 'I'), addressInt)
        self.sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_RXPDO_1, len(ppm_rx))

        # Assign tx map
        self.sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, 0)
        for i, addressInt in enumerate(tx_address_ints):
            self.sdo_write((0x1A00, i + 1, 'I'), addressInt)
        self.sdo_write(self.ADDRESS.NUMBER_OF_MAPPED_OBJECTS_IN_TXPDO_1, len(ppm_tx))

        self.currentRxPDOMap = ppm_rx
        self.currentTxPDOMap = ppm_tx

        # Configure Digital Inputs (example)
        self.sdo_write(self.ADDRESS.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 255)
        self.sdo_write(self.ADDRESS.DIGITAL_INPUT_CONFIGURATION_DGIN_2, 1)
        self.sdo_write(self.ADDRESS.DIGITAL_INPUT_CONFIGURATION_DGIN_1, 0)



