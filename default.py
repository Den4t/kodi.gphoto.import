#!/usr/bin/env python

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

###https://www.safaribooksonline.com/library/view/python-cookbook/0596001673/ch14s02.html

import sys
import traceback
import importlib

#import logging
import os
import re
from datetime import datetime

### XBMC part ######################################
#import xbmc
import xbmcaddon
import xbmcgui
import urlparse


##Script constants
ADDON      = xbmcaddon.Addon()
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_ID   = ADDON.getAddonInfo('id')
LANGUAGE   = ADDON.getLocalizedString
VERSION    = ADDON.getAddonInfo("version")
CWD        = ADDON.getAddonInfo('path')
PROFILE    = xbmc.translatePath( ADDON.getAddonInfo('profile') ).decode("utf-8")
RESOURCE   = xbmc.translatePath( os.path.join( CWD, 'resources', 'lib' ) ).decode("utf-8")

def ls(num):
    return LANGUAGE(num)


def getaddon_setting(name):
    return ADDON.getSetting(name)

#logging
def log(msg, level=xbmc.LOGDEBUG):
    xbmc.log(msg=msg, level=level)



## Structure constants
NAME=0
FOLDER=1
PREFIX=2
HOSTFOLDER=3
DIRMASK=4
FILEMASK=5

class Settings():
    def __init__(self):
        self.Read()

    def Read(self):
        '''parameters from addon settings'''
        self.force_flag      = True if getaddon_setting('ForceFlag')=='true' else False;
        self.check_size_flag = True if getaddon_setting('CheckSizeFlag') else False;
        self.auto_import     = True if getaddon_setting('AutoImport')=='true' else False;
        self.temp_dir        = getaddon_setting('TempDir')
        self.response_time   = 20000
        self.backend_lib     = getaddon_setting('BackendLib')
        self.skip_conv_video = True if getaddon_setting('SkipConvVideo')=='true' else False;

        self.preview_file=self.temp_dir+'/gp_preview'
        self.DEVICES={}

        for i in xrange(0,4):
            name  = getaddon_setting('PofieName'+str(i))
            usbid = getaddon_setting('USBID'+str(i))
            
            if name == '' or usbid == '':
                continue

            self.DEVICES[usbid]={
                    NAME:       name,
                    FOLDER:     getaddon_setting('DeviceFolder%d'%i),
                    HOSTFOLDER: getaddon_setting('HostFolder%d'%i),
                    DIRMASK:    getaddon_setting('DirMask%d'%i),
                    FILEMASK:   getaddon_setting('FilenameMask%d'%i),
                    PREFIX:     getaddon_setting('FilePfefix%d'%i)
            }
##########################################################################
class ScanDialog(xbmcgui.DialogProgressBG):
    '''only needed for close dialog window when object deleted'''
    def __del__(self):
        if not self.isFinished():
            self.close()

##########################################################
class MyMonitor(xbmc.Monitor):
    def __init__(self, *args, **kwargs):
        xbmc.Monitor.__init__(self, *args, **kwargs)
        self.runned=False
        self.settings_changed=False

    def onNotification(self, sender, method, data):
        global ADDON_ID
        log(">>>> Notification sender=[%s] method=[%s] <<<<"%(sender, method))
        if sender == ADDON_ID:
            if not self.runned:
                self.Run()
            else:
                ProgressView.show_dialog=True
    
    def onSettingsChanged(self):
        global s
        if s.backend_lib != getaddon_setting('BackendLib'):
            #xbmcgui.Dialog().ok('Warning', 'Backend library changed, restart kodi !')
            xbmcgui.Dialog().ok(ls(32400), ls(32401))
        if self.runned:
            self.settings_changed=True
        else:
            #reread settings
            s.Read()

    def Run(self):
        if self.runned:
            return
        else:
            self.runned=True
            try:
                ret=self.Main()
            except gp.BackendError as ex:
                log('>>>> %s'%traceback.format_exc(10))
                #xbmcgui.Dialog().ok('Backend error:', ex.message)
                xbmcgui.Dialog().ok(ls(32402), ex.message)
            except Exception as ex:
                log('>>>> %s'%traceback.format_exc(10))
                #xbmcgui.Dialog().ok('Unexpected error:', ex.message)
                xbmcgui.Dialog().ok(ls(32403), ex.message)
            log('>>>> Main finished, status=%s'%ret)
            self.runned=False

            if self.settings_changed:
                log('>>>> Settings was changed !')
                self.settings_changed=False
                s.Read()

    def Loop(self):
        self.Run()
        while not self.abortRequested():
            # Sleep/wait for abort for 10 seconds
            if self.waitForAbort(10):
                # Abort was requested while waiting. We should exit
                break

    def Main(self):
        scan_dialog=ScanDialog()
        tot_size=0

        #scan_dialog.create('Searching for devices ...')
        scan_dialog.create(ls(32404))

        dialog = xbmcgui.Dialog()

        try:
            log('>>>> Opening camera ...')
            cam = gp.BackendCamera()
        except gp.BackendError as ex:
            scan_dialog.close()
            #dialog.ok("Gphoto Error","Camera open error: %s"%ex.message)
            dialog.ok(ls(32405),"%s %s"%(ls(32406), ex.message))
            return False


        usb_id=('%04x:%04x'%(cam.usb_vendor,cam.usb_product))
        log('>>>> usb_id=: %s'%usb_id)
        if not usb_id  in s.DEVICES:
            usb_id=('%04x:*'%(cam.usb_vendor))
            if not usb_id  in s.DEVICES:
                usb_id='*:*'
                if not usb_id  in s.DEVICES:
                    scan_dialog.close()
                    #dialog.notification('Unknown device', 
                    #        'USBID: %04x:%04x\n'%(cam.usb_vendor,cam.usb_product),
                    #        xbmcgui.NOTIFICATION_INFO, 
                    #        5000)
                    dialog.notification(ls(32407),
                            'USBID: %04x:%04x\n'%(cam.usb_vendor,cam.usb_product),
                            xbmcgui.NOTIFICATION_INFO, 
                            5000)
                    return False


        device=s.DEVICES[usb_id]
        log('>>>> Use device profile: %s'%device[NAME])

        if not os.path.isdir(device[HOSTFOLDER]):
            try:
                os.makedirs(device[HOSTFOLDER])
            except:
                scan_dialog.close()
                #dialog.ok("Error","Cant create host filder %s: %s"%(device[HOSTFOLDER],ex.message))
                dialog.ok(ls(32408),"%s %s: %s"%(ls(32409), device[HOSTFOLDER],ex.message))
                return False

        #scan_dialog.update(heading='Scaning '+cam.model)
        scan_dialog.update(heading=ls(32410)+' '+cam.model)


        imp_files={}
        for f in cam.list_files(device[FOLDER]):
            scan_dialog.update(message='Files: '+str(len(imp_files))+' '+f.name)

            if not f.type:
                log('>>>> Skip unknown mime: %s'%f.mimetype)
                continue

            name, ext = os.path.splitext(f.name)
            ext=ext[1:]
            dest_dir=os.path.join(device[HOSTFOLDER], f.last_modified.strftime(device[DIRMASK]))
            dest_file=device[FILEMASK]
            dest_file=re.sub(r'%f',name,dest_file)
            dest_file=re.sub(r'%C',ext,dest_file)
            dest_file=device[PREFIX]+dest_file
            dest_path=os.path.join(dest_dir, f.last_modified.strftime(dest_file))

            if s.force_flag:
                log('>>>> Forcing: %s'%dest_path, xbmc.LOGINFO)
                imp_files[dest_path]=f
                tot_size+=f.size
                continue

            if os.path.isfile(dest_path): ##file exists
                if s.check_size_flag:
                    if f.size == os.path.getsize(dest_path):
                        log('>>>> Skip: %s'%dest_path, xbmc.LOGINFO)
                        continue

            ##check converted MOV to MP4
            if f.type == 'video' and s.skip_conv_video:
                   name,ext=os.path.splitext(dest_path)
                   skip=False
                   for e in ('mp4', 'avi', 'mov', 'mkv'):
                       if os.path.isfile(dest_path+'.'+e) or os.path.isfile(name+'.'+e):
                           skip=True
                           break
                   if skip:
                       log('>>>> Skip converted video: %s'%dest_path, xbmc.LOGINFO)
                       continue

            imp_files[dest_path]=f
            tot_size+=f.size
            log('>>>> Adding: %s'%dest_path, xbmc.LOGINFO)



        scan_dialog.close()
        log('>>>> Total files to import: %d'%len(imp_files))
        if not imp_files:
            #dialog.ok('Camera info',
            #    'Model: '+cam.model+'\n'+
            #    'USBID: %04x:%04x, Profile \"%s\"\n'%(cam.usb_vendor,cam.usb_product,device[NAME])+
            #    'No fresh files to import.')
            dialog.ok(ls(32411),
                '%s: %s\nUSBID: %04x:%04x, %s \"%s\"\n%s.'%(ls(32412), cam.model,
                    cam.usb_vendor, cam.usb_product, ls(32413), device[NAME], ls(32414)))
            return False


        if s.auto_import:
            #nolabel='Import'
            #yeslabel='Cancel'
            nolabel=ls(32416)
            yeslabel=ls(32417)
        else:
            #nolabel='Cancel'
            #yeslabel='Import'
            nolabel=ls(32417)
            yeslabel=ls(32416)

        #ret=dialog.yesno('Camera info',
        #    'Model: '+cam.model+'\n'+
        #    'USBID: %04x:%04x, Profile \"%s\"\n'%(cam.usb_vendor,cam.usb_product,device[NAME])+
        #    ('Total files to import: %d (%.1fMb)'%(len(imp_files), float(tot_size)/1024/1024)),
        #    '','',nolabel,yeslabel,s.response_time)
        ret=dialog.yesno(ls(32411),
            '%s: %s\nUSBID: %04x:%04x, %s \"%s\"\n'%(ls(32412),cam.model,  cam.usb_vendor,cam.usb_product,
                ls(32413), device[NAME])+
            ('%s: %d (%.1fMb)'%(ls(32415),len(imp_files), float(tot_size)/1024/1024)),
            '','',nolabel,yeslabel,s.response_time)


        types={'video': 0, 'image': 0}
        imp_size=0
        if ret ^ s.auto_import :
            log('>>>> Transfer files...')
            ui=ProgressView("import.xml", CWD)
            ui.show()
            ui.set_header(cam.model)

            for i, (dest_path,f) in enumerate(sorted(imp_files.items())):

                log('>>>> Transfer [%d]: %s => %s, sz: %d'%(i, f.name, dest_path, f.size), xbmc.LOGINFO)
                ui.update(len(imp_files), i+1, tot_size, imp_size, f.size, 0, f.name)

                if not ui.bg:
                    try:
                        f.save(s.preview_file, 'preview')
                        img=os.path.join(os.path.dirname(s.preview_file), 'gp_'+f.name)
                        os.symlink(s.preview_file, img)
                    except:
                        #raise
                        img=''
                    ui.set_image(img)

                if not os.path.isdir(os.path.dirname(dest_path)):
                    try:
                        os.makedirs(os.path.dirname(dest_path))
                    except:
                        log('>>>> Cant make dir "%s"'%os.path.dirname(dest_path), xbmc.LOGERROR)
                        #xbmcgui.Dialog().ok('Transfer error', 'Cant make dir "%s"'%os.path.dirname(dest_path))
                        xbmcgui.Dialog().ok(ls(32418), '%s "%s"'%(ls(32409),os.path.dirname(dest_path)))
                        return False

                try:
                    #if ui.bg:
                    if 0:
                        f.save(dest_path)
                    else:
                        if f.type=='video':
                            chunk_size=1024*1024*2
                        else:
                            chunk_size=1024*1024

                        # Iterate over a file's content
                        rsize=0
                        with open(dest_path, "wb") as fp:
                            for chunk in f.iter_data(chunk_size):
                                #log('-> %d'%len(chunk))
                                fp.write(chunk)
                                rsize+=len(chunk)
                                imp_size+=len(chunk)
                                ui.update(len(imp_files), i+1, tot_size, imp_size, f.size, rsize, f.name)
                                ##allow xbmc take control for event processing
                                xbmc.sleep(1)
                                if ui.iscanceled:
                                    fp.close()
                                    os.remove(dest_path)
                                    #ui.close()
                                    #del ui
                                    return False
                except Exception as ex:
                    log('>>>> Transfer error: %s'%ex.message)
                    os.remove(dest_path)
                    #xbmcgui.Dialog().ok('Transfer error', ex.message)
                    xbmcgui.Dialog().ok(ls(32418), ex.message)
                    ui.close()
                    return False

                if rsize != f.size:
                    #err='imported size for %s differ from file size (%d != %d)'%(f.name, rsize, f.size)
                    err='%s %s %s (%d != %d)'%(ls(32419),f.name, ls(32420), rsize, f.size)
                    log('>>>> Transfer error: %s'%err)
                    #xbmcgui.Dialog().ok('Transfer error',err)
                    xbmcgui.Dialog().ok(ls(32418),err)
                    ui.close()
                    return False

                types[f.type] += 1

            del ui

            #dialog.ok('Import done',
            #    ('Total files imported: %d'%len(imp_files))+"\n"+
            #    ('Images: %d'%types['image'])+"\n"+
            #    ('Videos: %d'%types['video'])+"\n"+
            #    "Dosconnect device.")
            dialog.ok(ls(32421),
                ('%s: %d\n'%(ls(32422),len(imp_files)))+
                ('%s: %d\n'%(ls(32423), types['image']))+
                ('%s: %d\n'%(ls(32424), types['video']))+
                ("%s."%ls(32425)))

        return True

class ProgressView(xbmcgui.WindowXMLDialog):
    show_dialog=True
    def __init__(self, *args, **kwargs):
        #reset static var
        ProgressView.show_dialog=True

        #flags
        self.iscanceled=False
        self.last_image=False
        self.bg=False
        #actions
        self.action_cancel_dialog = ( 9, 10, 92, 216, 247, 257, 275, 61467, 61448 )
        #controld
        self.id_label_header        = 100
        self.id_label_info          = 101
        self.id_progress1           = 102
        self.id_progress2           = 103
        self.id_preview             = 200
        self.id_button_cancel       = 300
        self.id_button_bkgr         = 301

        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def show(self):
        xbmcgui.WindowXMLDialog.show(self)
        try:
            sels.c_label_info
        except:
            #Let xbmc init window
            xbmc.sleep(1)

    def onInit(self):  
        self.c_label_header = self.getControl(self.id_label_header)
        self.c_label_info   = self.getControl(self.id_label_info)
        self.c_progress1    = self.getControl(self.id_progress1)
        self.c_progress2    = self.getControl(self.id_progress2)
        self.c_preview      = self.getControl(self.id_preview)


    def onClick(self, controlId):
        if controlId == self.id_button_cancel:
            self.iscanceled=True
            log('>>>> CANCEL BUTTON <<<<')
        elif controlId == self.id_button_bkgr:
            log('>>>> BKGR BUTTON <<<<')
            ProgressView.show_dialog=False
            self.SwitchView()

    def SwitchView(self):
        if not ProgressView.show_dialog and not self.bg:
            self.close()
            self.bg=xbmcgui.DialogProgressBG()
            self.bg.create(self.header)
            self.bg.update(int(self.c_progress2.getPercent()), message=self.info.replace("\n"," "))

        if ProgressView.show_dialog and self.bg:
            self.close()
            self.show()


    def onAction( self, action ):
        # Cancel
        if action.getId() in self.action_cancel_dialog:
            self.iscanceled=True
            log('>>>> CANCEL EVENT <<<<')

    def set_header(self, header):
        if self.bg:
            pass
        else:
            self.header=header
            self.c_label_header.setLabel(header)

    def update(self, tot_files, imp_files, tot_size, imp_size, curr_size, curr_imp_size, name):
        self.SwitchView()
        progress1=int(float(curr_imp_size)/curr_size*100.0)
        progress2=int(float(imp_size)/tot_size*100.0)
        self.info="%d of %d (%.1f / %.1f)\n%s"%(imp_files, tot_files,
                        float(imp_size)/1024/1024, float(tot_size)/1024/1024,
                        name)
        if self.bg:
            self.bg.update(int(progress2), message=self.info.replace("\n"," "))
        else:
            self.c_progress1.setPercent(progress1)
            self.c_progress2.setPercent(progress2)
            self.c_label_info.setLabel(self.info)
            self.c_label_header.setLabel(self.header + ": %d%%"%(int(progress2)))



    def _remove_preview(self):
        try:
            if self.last_image:
                os.remove(self.last_image)
        except:
            pass

    def set_image(self, f):
        if self.bg:
            pass
        else:
            self._remove_preview()
            self.last_image=f
            self.c_preview.setImage(f,False)

    def close(self):
        self._remove_preview()
        try:
            os.remove(s.preview_file)
        except:
            pass
        super(ProgressView, self).close()

        if self.bg:
            self.bg.close()
            del self.bg
            self.bg=None

    def __del__(self):
        log('>>>> Destructor for %s'%self.__class__.__name__)
        self.close()


if __name__ == "__main__":
    log('>>>> MY PID: %d Parent: %d'%(os.getpid(), os.getppid()))

    ##First time run
    if(xbmcgui.Window(10000).getProperty(ADDON_ID + '_running') != 'True'):
        ##Settings instance
        global s
        #script settings
        s=Settings()

        try:
            try:
                if s.backend_lib == 'gphoto2-cffi':
                        log('>>>> Using gphoto2-cffi backend')
                        from resources.lib.backend import gphoto2_cffi as gp
                else:
                        log('>>>> Using  python-gphoto2 backend')
                        from resources.lib.backend import gphoto2_py as gp
            except Exception as ex:
                    log('>>>> %s'%traceback.format_exc(10))
                    #xbmcgui.Dialog().ok('Error', ex.message)
                    xbmcgui.Dialog().ok(ls(32408), ex.message)
                    sys.exit(1)

            #set lock
            xbmcgui.Window(10000).setProperty(ADDON_ID + '_running', 'True')
            MyMonitor().Loop()

        finally:
            log('>>>> Finishing')
            #clear lock
            xbmcgui.Window(10000).setProperty(ADDON_ID + '_running', 'False')
    else:
        log('>>>> Allready running <<<<')
        command = 'XBMC.NotifyAll(%s,%s)'%(ADDON_ID, 'run')
        log('>>>> emit %s' % command)
        xbmc.executebuiltin(command)


