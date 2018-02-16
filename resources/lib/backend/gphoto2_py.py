import os
from datetime import datetime

from __main__ import log

#####################################################
##Check if backend library exist
#####################################################
import pkgutil
if pkgutil.find_loader('gphoto2') is None:
    raise Exception('Please install gphoto2 package.')

import gphoto2 as gp
#####################################################

from .common import *

##make alias for exception
BackendError=gp.GPhoto2Error

class BackendCamera(object):
    def __init__(self):
        self.camera = gp.Camera()
        self.camera.init()
        abilities = self.camera.get_abilities()

        ##later can be converted to @property
        self.usb_vendor  = abilities.usb_vendor
        self.usb_product = abilities.usb_product
        self.model       = abilities.model

    def __del__(self):
        log('>>>> Destructor for %s'%self.__class__.__name__)
        if self.camera:
            self.camera.exit()
            del self.camera

    def list_files(self, path):
        for name, err in self.camera.folder_list_files(path):
            cam_file=BackendFile(path, name, self.camera)
            yield cam_file

        for name, err in self.camera.folder_list_folders(path):
            for cam_file in self.list_files(os.path.join(path, name)):
                yield cam_file

class BackendFile(CamFile):
    def __init__(self, path, name, camera):
        CamFile.__init__(self, path, name, camera)
        self.path=path
        self.name=name
        self.camera=camera
        self.__info=None
        #self.type=None

    def __repr__(self):
        return os.path.join(self.path, self.name)

    def __del__(self):
        log('>>>> Destructor for %s'%self.__class__.__name__)
        if self.camera:
            self.camera=None

    @property
    def _info(self):
        if self.__info is None:
            ##Get file info from backend
            self.__info=self.camera.file_get_info(self.path, self.name)

        return self.__info

    @property
    def size(self):
        return self._info.file.size

    @property
    def mimetype(self):
        return self._info.file.type

    @property
    def last_modified(self):
        return datetime.fromtimestamp(self._info.file.mtime)

    def save(self, target_path, ftype='normal'):
        if ftype == 'preview':
            ft=gp.GP_FILE_TYPE_PREVIEW
        else:
            ft=gp.GP_FILE_TYPE_NORMAL
        camera_file = self.camera.file_get(self.path, self.name, ft)
        camera_file.save(target_path)

    def iter_data(self, chunk_size=1024*1024, ftype='normal'):
        data = bytearray(chunk_size)
        view = memoryview(data)
        # Iterate over a file's content
        offset=0
        bytes_read=chunk_size
        while True:
            bytes_read = self.camera.file_read(self.path, self.name, gp.GP_FILE_TYPE_NORMAL,
                    offset, view[0:chunk_size])
            if bytes_read > 0:
                offset += bytes_read
                yield view[0:bytes_read]
            if bytes_read < chunk_size:
                break


