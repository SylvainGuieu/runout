import re
import os
import numpy as np

from . import compute 
from . import io
from . import config

from scipy.ndimage.interpolation import shift
import glob

confLoockup = { # loockup by at 
     1: dict( fluxTreshold = 1550,  pupLocation =  [ [367,404], [682,670]] ), 
     2: dict( fluxTreshold = 1550,  pupLocation = [ [367,350], [682,700]] ), 
     3: dict(  fluxTreshold = 2050,  pupLocation = [ [380,345], [720,632]] ), 
     4: dict(  fluxTreshold = 2100,  pupLocation = [ [413,250], [682,511]] ), 
     0: dict( fluxTreshold = 1550,  pupLocation =  [ [380,404], [682,670]] ), 
}

class M6Pupill:
    _fluxTreshold = None
    _pupLocation  = None
    file = None
    def __init__(self, file=None, data=None, header=None):
        self.header = {'az':-999.99,'derot':-999.99, 'at':0}               
        header = {} if header is None else header
        
        if file is not None:
            self.data, fitsHeader = io.readFitsData(file)            
            self.file = file
            header = dict(header, **fitsHeader)
        else:
            self.data = data

        self.header = dict(self.header, **header)
    
    @property
    def at(self):
        return self.header['at']

    @property
    def az(self):
        return self.header['az']

    @property
    def derot(self):
        return self.header['derot']
        
    @property
    def fluxTreshold(self):
        return config.atConfLoockup[self.at]['fluxTreshold'] if self._fluxTreshold is None else self._fluxTreshold

    @property
    def pupLocation(self):
        return config.atConfLoockup[self.at]['pupLocation'] if self._pupLocation is None else self._pupLocation

    @pupLocation.setter
    def pupLocation(self, loc):
        self._pupLocation = loc

    @fluxTreshold.setter
    def fluxTreshold(self, t):
        self._fluxTreshold = t

    def getCenter(self):
        return compute.center(self.getMask())
    
    def getMask(self):
        
        shape = self.data.shape
        X, Y = np.meshgrid(range(shape[1]), range(shape[0]) )
        return (self.data>self.fluxTreshold)   *\
            (X>self.pupLocation[0][0])  *\
            (X<self.pupLocation[1][0])  *\
            (Y>self.pupLocation[0][1])  *\
            (Y<self.pupLocation[1][1])
    
    def synthesize(self, center, bckg=None, flux=None):
        img = self.data
        dCenter = self.getCenter()
        mask  = self.getMask()
        
        dx = center[0]-dCenter[0]
        dy = center[1]-dCenter[1]
        
        
        bckg = self.fluxTreshold * 0.95 if bckg is None else bckg
        flux = p.mean(img[mask]) if flux is None else flux

        flatImg =  img.copy()
        flatImg[mask]  = flux
        flatImg[~mask] = bckg        
        newData = shift(flatImg,  [dy,dx], mode='constant', cval=bckg)        
        return M6Pupill(data=newData, header=dict(self.header))             
    
class M6PupillList:
    def __init__(self, iterable):
        self.lst = list(iterable)
        
    def append(self, p):
        self.lst.append(p)

    def extend(self, iterable):
        self.lst.extend(iterable)
    
    def byKey(self, key, nMin=1):
        items = {}
        for p in self.lst:
            items.setdefault(p.header[key], self.__class__([])).append(p)
        if nMin>1:
            items = {k:v  for k,v in items.items() if len(v)>=nMin}
        return items
    
    def byAt(self):
        return self.byKey('at',1)

    def byAz(self):
        return self.byKey('az',2)

    def byDerot(self):
        return self.byKey('derot',2)

    def increasingKey(self, key):
        return self.__class__(sorted(self.lst, key=lambda x:x.header[key] ))

    def increasingAz(self):
        return self.increasingKey('az')

    def increasingDerot(self):
        return self.increasingKey('derot')

    def find(self, az, derot):
        for P in self.lst:
            if p.az==az and p.derot==derot:
                return p
        return None

    def getCenters(self):
        return np.array([p.getCenter() for p in self])
    
    def __iter__(self):
         return self.lst.__iter__()

    def __getitem__(self, item):
         out = self.lst[item]
         if hasattr(out, "__iter__"):
             return self.__class__(out)
         return out

    def __len__(self):
        return len(self.lst)
    
    @classmethod
    def fromGlob(cl, glb, header=None):
        return cl((M6Pupill(file, header=header) for file in glob.glob(glb)))
    
        
    