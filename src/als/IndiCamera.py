# Basic stuff
import io
import json
import logging

# Numerical stuff
import numpy as np

# Indi stuff
import PyIndi

# Local stuff
from als.IndiDevice import IndiDevice
from als.IndiClient import IndiClientGlobalBlobEvent

# Imaging and Fits stuff
from astropy.io import fits

# Astropy
import astropy.units as u

_LOGGER = logging.getLogger(__name__)

class IndiCamera(IndiDevice):
    """ Indi Camera """

    UploadModeDict = {
        'local': 'UPLOAD_LOCAL',
        'client': 'UPLOAD_CLIENT',
        'both': 'UPLOAD_BOTH'}
    DEFAULT_EXP_TIME_SEC = 5
    MAXIMUM_EXP_TIME_SEC = 3601

    def __init__(self, indi_client, config=None,
                 connect_on_create=True):
        if config is None:
            config = dict(camera_name = 'CCD Simulator')

        device_name = config['camera_name']
        _LOGGER.debug(f"Indi camera, camera name is: {device_name}")
      
        # device related intialization
        IndiDevice.__init__(self, device_name=device_name,
                            indi_client=indi_client)

        # Frame Blob: reference that will be used to receive binary
        self.frame_blob = None

        # Default exposureTime, gain
        self.exp_time_sec=5
        self.gain=400

        if connect_on_create:
            self.connect()
            self.prepare_shoot()

        # Finished configuring
        _LOGGER.debug(f"Configured Indi Camera successfully")

    @property
    def dynamic(self):
        return 2**self.get_dynamic()

    '''
      Indi CCD related stuff
    '''
    def prepare_shoot(self):
        '''
          We should inform the indi server that we want to receive the
          "CCD1" blob from this device
        '''
        _LOGGER.debug(f"Indi client will register to server in order to "
                      f"receive blob CCD1 when it is ready")
        self.indi_client.setBLOBMode(PyIndi.B_ALSO, self.device_name, 'CCD1')
        self.frame_blob = self.get_prop(propName='CCD1', propType='blob')

    def synchronize_with_image_reception(self):
        try:
            global IndiClientGlobalBlobEvent
            _LOGGER.debug("synchronizeWithImageReception: Start waiting")
            IndiClientGlobalBlobEvent.wait()
            IndiClientGlobalBlobEvent.clear()
            _LOGGER.debug(f"synchronizeWithImageReception: Done")
        except Exception as e:
            _LOGGER.error(f"Indi Camera Error in "
                          f"synchronizeWithImageReception: {e}")

    def get_received_image(self):
        try:
            ret = []
            _LOGGER.debug(f"getReceivedImage frame_blob: {self.frame_blob}")
            for blob in self.frame_blob:
                _LOGGER.debug(f"Indi camera, processing blob with name: "
                              f"{blob.name}, size: {blob.size}, format: "
                              f"{blob.format}")
                # pyindi-client adds a getblobdata() method to IBLOB item
                # for accessing the contents of the blob, which is a bytearray
                return fits.open(io.BytesIO(blob.getblobdata()))
        except Exception as e:
            _LOGGER.error(f"Indi Camera Error in getReceivedImage: {e}")

    def shoot_async(self):
        try:
            _LOGGER.info(f"Launching acquisition with {self.exp_time_sec} "
                         f"sec exposure time")
            self.setNumber('CCD_EXPOSURE',
                           {'CCD_EXPOSURE_VALUE': self.sanitize_exp_time(
                               self.exp_time_sec)}, sync=False)
        except Exception as e:
            _LOGGER.error(f"Indi Camera Error in shoot: {e}")


    def abort_shoot(self, sync=True):
        self.setNumber('CCD_ABORT_EXPOSURE', {'ABORT': 1}, sync=sync)

    def launch_streaming(self):
        self.setSwitch('VIDEO_STREAM',['ON'])

    def set_upload_path(self, path, prefix = 'IMAGE_XXX'):
        self.setText('UPLOAD_SETTINGS', {'UPLOAD_DIR': path,\
        'UPLOAD_PREFIX': prefix})

    def get_binning(self):
        return self.getPropertyValueVector('CCD_BINNING', 'number')

    def set_binning(self, hbin, vbin = None):
        if vbin == None:
            vbin = hbin
        self.setNumber('CCD_BINNING', {'HOR_BIN': hbin, 'VER_BIN': vbin })

    def get_roi(self):
        return self.getPropertyValueVector('CCD_FRAME', 'number')

    def set_roi(self, roi):
        """"
            X: Left-most pixel position
            Y: Top-most pixel position
            WIDTH: Frame width in pixels
            HEIGHT: Frame width in pixels
            ex: cam.setRoi({'X':256, 'Y':480, 'WIDTH':512, 'HEIGHT':640})
        """
        self.setNumber('CCD_FRAME', roi)

    def get_dynamic(self):
        return self.get_number('CCD_INFO')['CCD_BITSPERPIXEL']['value']

    def get_maximum_dynamic(self):
        return get_dynamic()

    def get_temperature(self):
        return self.get_number(
            'CCD_TEMPERATURE')['CCD_TEMPERATURE_VALUE']['value']

    def set_temperature(self, temperature):
        """ It may take time to lower the temperature of a ccd """
        if isinstance(temperature, u.Quantity):
            temperature = temperature.to(u.deg_C).value
        if np.isfinite(temperature):
            self.setNumber('CCD_TEMPERATURE',
                           { 'CCD_TEMPERATURE_VALUE' : temperature },
                           sync=True, timeout=1200)

    def set_cooling_on(self):
        self.setSwitch('CCD_COOLER',['COOLER_ON'])

    def set_cooling_off(self):
        self.setSwitch('CCD_COOLER',['COOLER_OFF'])

    def set_gain(self, value):
        pass
        #TODO TN, Try to solve this
        #self.setNumber('DETECTOR_GAIN', [{'Gain': value}])

    def get_gain(self):
        gain = self.get_number('CCD_GAIN')
        print('returned Gain is {}'.format(gain))
        return gain

    def get_frame_type(self):
        return self.get_prop('CCD_FRAME_TYPE','switch')

    def set_frame_type(self, frame_type):
        """
        FRAME_LIGHT Take a light frame exposure
        FRAME_BIAS Take a bias frame exposure
        FRAME_DARK Take a dark frame exposure
        FRAME_FLAT Take a flat field frame exposure
        """
        self.setSwitch('CCD_FRAME_TYPE', [frame_type])

    def sanitize_exp_time(self, exp_time_sec):
        if isinstance(exp_time_sec, u.Quantity):
            exp_time_sec = exp_time_sec.to(u.s).value
        if not isinstance(exp_time_sec, float):
            try:
                float_exp_time_sec = float(exp_time_sec)
            except Exception as e:
                float_exp_time_sec = self.DEFAULT_EXP_TIME_SEC
        elif exp_time_sec < 0:
            float_exp_time_sec = abs(float_exp_time_sec)
        elif exp_time_sec == 0:
            float_exp_time_sec = self.DEFAULT_EXP_TIME_SEC
        elif exp_time_sec > self.MAXIMUM_EXP_TIME_SEC:
            float_exp_time_sec = self.MAXIMUM_EXP_TIME_SEC
        else:
            float_exp_time_sec = exp_time_sec
        # Show warning if needed
        if float_exp_time_sec != exp_time_sec:
            _LOGGER.warning(f"Sanitizing exposition time: cannot accept "
                "{exp_time_sec}, using {float_exp_time_sec} instead")

        return float_exp_time_sec

    def get_exp_time_sec(self):
        return self.sanitize_exp_time(self.exp_time_sec)

    def set_exp_time_sec(self, exp_time_sec):
        self.exp_time_sec = self.sanitize_exp_time(exp_time_sec)

    def __str__(self):
        return f"INDI Camera {self.name}"

    def __repr__(self):
        return self.__str__()


