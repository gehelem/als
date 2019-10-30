# Basic stuff
import json
import logging
import threading

# Indi stuff
import PyIndi

# configure global variables
global IndiClientGlobalBlobEvent
IndiClientGlobalBlobEvent = threading.Event()

_LOGGER = logging.getLogger(__name__)

class IndiClient(PyIndi.BaseClient):
  '''
    This Indi Client class can be used as a singleton, so that it can be used
    to interact with multiple devices, instead of declaring one client per
    device to manage.

    Every virtual function instanciated is called asynchronously by an external
    C++ thread, and not by the python main thread, so be careful.
  '''

  def __init__(self, config, connect_on_create=True):
      # Call indi client base classe ctor
      PyIndi.BaseClient.__init__(self)

      if config is None:
            config = dict(indi_host = "localhost",
                          indi_port = 7624)
     
      self.remoteHost = config['indi_host']
      self.remotePort = int(config['indi_port'])

      self.setServer(self.remoteHost, self.remotePort)
      _LOGGER.debug(f"Indi Client, remote host is: {self.getHost()}:"
                    f"{self.getPort()}")

      if connect_on_create:
          self.connect()

      # Finished configuring
      _LOGGER.debug(f"Configured Indi Client successfully")

  def connect(self):
      if self.isServerConnected():
          _LOGGER.warning(f"Already connected to server")
      else:
          _LOGGER.info(f"Connecting to server at {self.getHost()}:{self.getPort()}")

          if not self.connectServer():
              _LOGGER.error(f"No indiserver running on {self.getHost()}:"
                  f"{self.getPort()} - Try to run "
                  f"indiserver indi_simulator_telescope indi_simulator_ccd")
          else:
              _LOGGER.info(f"Successfully connected to server at "
                           f"{self.getHost()}:{self.getPort()}")

  '''
    Indi related stuff (implementing BaseClient methods)
  '''
  def device_names(self):
      return [d.getDeviceName() for d in self.getDevices()]

  def newDevice(self, d):
      pass

  def newProperty(self, p):
      pass

  def removeProperty(self, p):
      pass

  def newBLOB(self, bp):
      # this threading.Event is used for sync purpose in other part of the code
      _LOGGER.debug(f"new BLOB received: {bp.name}")
      global IndiClientGlobalBlobEvent
      IndiClientGlobalBlobEvent.set()

  def newSwitch(self, svp):
      pass

  def newNumber(self, nvp):
      pass

  def newText(self, tvp):
      pass

  def newLight(self, lvp):
      pass

  def newMessage(self, d, m):
      pass

  def serverConnected(self):
      _LOGGER.debug(f"Server connected")

  def serverDisconnected(self, code):
      _LOGGER.debug(f"Server disconnected")

  def __str__(self):
      return f"INDI client connected to {self.remoteHost}:{self.remotePort}"

  def __repr__(self):
      return self.__str__()

