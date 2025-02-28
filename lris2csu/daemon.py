"""
Entry point for LRIS2's soft etherCAT master. Sets up listening socket and initializes the soft master.

Currently, assumes that all connected controllers are EPOS4 Micro 24/5.
"""
import yaml
import logging
import struct
import socket
import argparse

from cooethercat import EPOS4Bus, EPOS4MicroTRB_12CC_Config, StatuswordStates


class SocketServer:

    def __init__(self, host_addr: tuple, csu_bus: EPOS4Bus):
        self.bus = csu_bus

        self.host, self.port = host_addr

        # Initialize server socket
        try:
            self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.serverSocket.bind((self.host, self.port))
            self.serverSocket.listen(5)
            logging.info(f"Server listening on {self.host}:{self.port}")
        except Exception as e:
            logging.error(f"Error setting up server socket: {e}")
            raise

    def run(self):
        while True:
            connection, address = self.serverSocket.accept()
            logging.info(f"Accepted connection from {address}")
            try:
                buf = connection.recv(2)
                if len(buf) > 0:  # Received a message
                    messageLength = struct.unpack('<H', buf)[0]  # Get message length
                    logging.debug(f"Message length: {messageLength}")

                    buf = connection.recv(1)  # Get action type byte
                    if not buf:
                        logging.error("Failed to receive action type byte")
                        continue
                    actionType = struct.unpack('<B', buf)[0]

                    logging.debug(f"Action type: {actionType}")

                    # Process based on action type
                    match actionType:
                        case 0:
                            self.HomingPDO(connection, messageLength)
                        case 1:
                            self.PPMPDO(connection, messageLength)
                        case 2:
                            self.get_slaves_info(connection)
                        case _:
                            logging.error('Invalid action type received')

            except Exception as e:
                logging.error(f"Error while processing message: {e}")
                connection.close()

    def get_slaves_info(self, connection: socket.socket):
        """Handle request to send slave information to the client."""
        # Start with a base message length (e.g., 2 bytes for the length and 1 byte for action type)
        info = self.bus.getSlavesInfo()
        connection.send(info) #TODO this will break, but at least finishes demonstrating intent.

    def PPMPDO(self, connection: socket.socket, messageLength: int, slave_ids: list[int] = None):
        """
        Message Length:  2 bytes
        Action Type:     1 byte
        Slave ID 1:      1 byte
        Target Position 1: 4 bytes
        Slave ID 2:      1 byte
        Target Position 2: 4 bytes
        """
        try:
            logging.info("Moving to target positions")
            targetPositions = []
            slaveIds = []
            remainingLength = messageLength - 3  # Subtract 3 bytes already read (length and action type)
            logging.debug(f"Remaining length to process: {remainingLength}")

            # Read slave IDs and target positions from the connection
            while remainingLength > 0:  # Loop through the message and extract slave IDs and target positions
                # Read the slave ID (1 byte)
                slave_id_buf = connection.recv(1)
                if not slave_id_buf:
                    logging.warning("Failed to receive slave ID byte")
                    break
                slave_id = struct.unpack('<B', slave_id_buf)[0]
                slaveIds.append(slave_id)
                remainingLength -= len(slave_id_buf)
                logging.debug(f"Received slave ID: {slave_id}, remaining length: {remainingLength}")

                # Read the target position (4 bytes)
                target_position_buf = connection.recv(4)
                if not target_position_buf:
                    logging.warning("Failed to receive target position byte")
                    break
                target_position = struct.unpack('<i', target_position_buf)[0]
                targetPositions.append(target_position)
                remainingLength -= len(target_position_buf)
                logging.debug(f"Received target position: {target_position}, remaining length: {remainingLength}")

            # If no slave_ids are provided, use the list of slave IDs we've just read
            if slave_ids is None:
                slave_ids = slaveIds  # Use the slave IDs received in the message

            # Check that the number of positions matches the number of slaves (or slave_ids)
            if len(targetPositions) != len(slave_ids):
                raise ValueError("The number of target positions must match the number of slave IDs provided.")

            # Handle the movement process
            self.bus.enablePDO()
            self.bus.sendPDO()
            self.bus.receivePDO()
            self.bus.changeDeviceStatesPDO(StatuswordStates.OPERATION_ENABLED)

            # Use slave_ids to assign target positions to specific slaves
            self.bus.goToPositions(targetPositions, slave_ids=slave_ids, printActualPosition=True)

            self.bus.changeDeviceStatesPDO(StatuswordStates.QUICK_STOP_ACTIVE)
            self.bus.disablePDO()

            logging.info("Done moving")

        except Exception as e:
            logging.error(f"Error in PPMPDO: {e}")

    def HomingPDO(self, connection: socket.socket, messageLength: int):
        try:
            logging.info("Homing all axes")
            self.bus.enablePDO()
            self.bus.sendPDO()
            self.bus.receivePDO()
            self.bus.changeDeviceStatesPDO(StatuswordStates.OPERATION_ENABLED)
            self.bus.performHoming()
            logging.info("Target reached/homing attained")
            self.bus.changeDeviceStatesPDO(StatuswordStates.QUICK_STOP_ACTIVE)
            self.bus.disablePDO()
            logging.info("Done homing")
        except Exception as e:
            logging.error(f"Error in HomingPDO: {e}")



def main():

    # Set up logging for the application startup process
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    """ Main entry point to initialize the EtherCAT soft master and start the server """
    parser = argparse.ArgumentParser(description="The CSU daemon")
    parser.add_argument('host', type=str, help='Server host IP address')
    parser.add_argument('port', type=int, help='Server port')
    parser.add_argument('--config', type=str, help='A yaml config file')

    args = parser.parse_args()

    # Load the master settings from YAML file
    try:
        with open('settings/masterSettings.yaml', 'r') as f:
            masterSettings = yaml.safe_load(f)
            logging.info("Loaded master settings.")
    except Exception as e:
        logging.error(f"Error loading master settings: {e}")
        return

    try:
        # Initialize the soft master with the slave configuration functions
        EPOS4MicroMaster = EPOS4Bus(
            masterSettings['networkInterfaceName'],
            slaveConfigFuncs=[EPOS4MicroTRB_12CC_Config, EPOS4MicroTRB_12CC_Config, EPOS4MicroTRB_12CC_Config]
        )
        logging.info(f"Initialized master with network interface: {masterSettings['networkInterfaceName']}")

        # Open network interface and initialize slaves
        EPOS4MicroMaster.openNetworkInterface()
        EPOS4MicroMaster.initializeSlaves()
        EPOS4MicroMaster.configureSlaves()
        logging.info("Slaves initialized and configured.")

    except Exception as e:
        logging.error(f"Error initializing the master or slaves: {e}")
        return

    # Start the EtherCAT Socket Server to listen for client connections
    try:
        server = SocketServer(EPOS4MicroMaster)
        logging.info("EtherCAT Socket Server initialized.")
        server.run()
    except Exception as e:
        logging.error(f"Error starting EtherCAT Socket Server: {e}")
        return

if __name__ == '__main__':
    main()
