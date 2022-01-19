"""
  ____       __                        __    __   __      _ __
 /_  / ___ _/ /  ___  ___ ___________ / /__ / /__/ /_____(_) /__
  / /_/ _ `/ _ \/ _ \/ -_) __/___/ -_) / -_)  '_/ __/ __/ /  '_/
 /___/\_,_/_//_/_//_/\__/_/      \__/_/\__/_/\_\\__/_/ /_/_/\_\

Copyright 2022 Zahner-Elektrik GmbH & Co. KG

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the Software
is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH
THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import numpy as np
import datetime
import io
import struct
import re


class IscImport():
    """ Class to be able to read out isc files (CV).
    
    This class extracts the data from the isc files.
    
    :param file: The path to the ism file, or the ism file as bytes or bytearray.
    :type file: str, bytes, bytearray
    """

    def __init__(self, file):
        if isinstance(file, bytes) or isinstance(file, bytearray):
            iscFile = io.BytesIO(file)
        else:
            iscFile = open(file, 'rb')
        
        self.Pstart = self._readDoubleFromFile(iscFile)
        self.Tstart = self._readDoubleFromFile(iscFile)
        self.Pupper = self._readDoubleFromFile(iscFile)
        self.Plower = self._readDoubleFromFile(iscFile)
        self.Tend = self._readDoubleFromFile(iscFile)
        self.Pend = self._readDoubleFromFile(iscFile)
        self.Srate = self._readDoubleFromFile(iscFile)
        self.Periods = self._readDoubleFromFile(iscFile)
        self.PpPer = self._readDoubleFromFile(iscFile)
        self.Imi = self._readDoubleFromFile(iscFile)
        self.Ima = self._readDoubleFromFile(iscFile)
        self.Odrop = self._readDoubleFromFile(iscFile)
        self.Sstart = self._readDoubleFromFile(iscFile)
        self.Send = self._readDoubleFromFile(iscFile)
        self.AZeit = self._readDoubleFromFile(iscFile)
        self.ZpMp = self._readDoubleFromFile(iscFile)
        self.delay = self._readDoubleFromFile(iscFile)
        
        numberOfElements = int.from_bytes(iscFile.read(6), "big", signed=True) + 1
        intVoltageRead = np.ndarray(shape=(numberOfElements,), dtype='>i2', buffer=iscFile.read(2 * numberOfElements))
        self.current = np.ndarray(shape=(numberOfElements,), dtype='>f8', buffer=iscFile.read(8 * numberOfElements))
        
        self.Date = self._readZahnerString(iscFile)
        self.System = self._readZahnerString(iscFile)
        self.Temperature = self._readZahnerString(iscFile)
        self.Time = self._readZahnerString(iscFile)
        self.Slew_Rate = self._readZahnerString(iscFile)
        self.Comment_1 = self._readZahnerString(iscFile)
        self.Comment_2 = self._readZahnerString(iscFile)
        self.Comment_3 = self._readZahnerString(iscFile)
        self.Comment_4 = self._readZahnerString(iscFile)
        self.Comment_5 = self._readZahnerString(iscFile)
        self.ElecArea = self._readZahnerString(iscFile)
        self.POPF = self._readZahnerString(iscFile)
        
        starttime, endtime = self.Time.split("-")
        
        self.measurementStartDateTime = datetime.datetime.strptime(self.Date + starttime, "%d%m%y%H:%M:%S")
        self.measurementEndDateTime = datetime.datetime.strptime(self.Date + endtime, "%d%m%y%H:%M:%S")
        
        offset = 0.0
        factor = 1.0
        
        popfPattern = "^\s*(.*?),\s*(.*?)\s*PO.PF *(.*?), *(.*)$"
        
        popfMatch = re.search(popfPattern, self.POPF)
        
        if popfMatch:
            offset = float(popfMatch.group(1))
            factor = float(popfMatch.group(2))
            PowerOfPotentialScaling = float(popfMatch.group(3))
            ExtraOffsetX = float(popfMatch.group(4))
        else:
            #fallback to old format for older ISC files:
            
            popfPattern = "^\s*(.*?),\\s*(.*?)\s*PO.PF.*"
            popfMatch = re.search(popfPattern, self.POPF)
            
            if popfMatch:
                offset = float(popfMatch.group(1))
                factor = float(popfMatch.group(2))
        
        self.voltage = intVoltageRead * (factor/8000.0) + offset        
        self.time = np.array(range(numberOfElements)) * self.ZpMp + self.Sstart
                
        return
    
    def getMeasurementStartDateTime(self):
        """ Get the start date time of the measurement.
        
        Returns the start datetime of the measurement.
        
        :returns: datetime object with the start time of the measurement.
        """
        return self.measurementStartDateTime
    
    def getMeasurementEndDateTime(self):
        """ Get the end date time of the measurement.
        
        Returns the end datetime of the measurement.
        
        :returns: datetime object with the end time of the measurement.
        """
        return self.measurementEndDateTime
    
    def getTimeArray(self):
        """ Reading the measurement time stamps.
        
        :returns: Numpy array with the time points.
        """
        return self.time
    
    def getCurrentArray(self):
        """ Reading the measurement current points.
        
        :returns: Numpy array with the current points.
        """
        return self.current
    
    def getVoltageArray(self):
        """ Reading the measurement voltage points.
        
        :returns: Numpy array with the voltage points.
        """
        return self.voltage
    
    def getScanRate(self):
        """ Read the scan rate or slew rate.
        
        :returns: The scan rate in V/s.
        """
        return self.Srate/1000.0
    
    def _readDoubleFromFile(self, file):
        bytesRead = file.read(8)
        retval = struct.unpack('>d', bytesRead)
        return retval[0]
    
    def _readZahnerString(self, file):
        length = int.from_bytes(file.read(2), "big", signed=True)
        content = bytearray()
        
        for i in range(length):
            content.append(file.read(1)[0])         
        
        return content.decode("ASCII").swapcase()
        
            
            
            
    