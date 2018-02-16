##########
import sys
import os
from datetime import datetime

from __main__ import log

#####################################################
##Check if backend library exist
#####################################################
import pkgutil
from __main__ import CWD
if pkgutil.find_loader('cffi') is None:
    raise Exception('Please install cffi package.')
cwd = os.getcwd()
lib_dir=os.path.join(CWD,'resources/lib/gphoto2cffi')
lib=os.path.join(lib_dir, '_backend.so')
if not os.path.isfile(lib):
    log(">>>> Building "+lib)
    os.chdir(lib_dir)
    os.system('python backend_build.py')
    os.chdir(CWD)
if not os.path.isfile(lib):
    raise Exception('Cant build binary module.')

from resources.lib.gphoto2cffi import gphoto2 as gp
#####################################################


from .common import *
##make alias for exception
BackendError=gp.errors.GPhoto2Error

class BackendCamera(gp.Camera):
    def __init__(self):
        gp.Camera.__init__(self)

        ##later can be converted to @property
        self.usb_vendor  = self.usb_info.vendor
        self.usb_product = self.usb_info.product
        self.model       = self.model_name

    def __del__(self):
        log('>>>> Destructor for %s'%self.__class__.__name__)
        gp.Camera.__del__(self)

    def list_files(self, path):
        camera_dir=gp.Directory(path,self.filesystem,self)
        for f in camera_dir.files:
            yield BackendFile(f)

        for d in camera_dir.directories:
            for camera_file in self.list_files(d.path):
                yield camera_file

        del camera_dir

class BackendFile(gp.File, CamFile):
    def __init__(self, f):
        gp.File.__init__(self, f.name, f.directory, f._cam)
        CamFile.__init__(self)

    def __repr__(self):
        return '%s%s'%(self.directory.path, self.name)

#    def __del__(self):
#        log('>>>> Destructor for %s'%self.__class__.__name__)

