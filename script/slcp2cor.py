#!/usr/bin/env python3

from __future__ import division
from builtins import range
from past.utils import old_div
import os
import sys
import glob
import shutil
import ntpath
import pickle
import datetime
import argparse
import numpy as np
import numpy.matlib
from xml.etree.ElementTree import ElementTree
from subprocess import check_call


import isce
import isceobj
from imageMath import IML


SCR_PATH = os.path.abspath(os.path.dirname(__file__))
BIN_PATH = os.path.join(os.path.dirname(SCR_PATH), "src")


def runCmd(cmd):
    print("{}".format(cmd))
    #status = os.system(cmd)
    status = check_call(cmd, shell=True)
    if status != 0:
        raise Exception('error when running:\n{}\n'.format(cmd))


def getWidth(xmlfile):
    xmlfp = None
    try:
        xmlfp = open(xmlfile,'r')
        print('reading file width from: {0}'.format(xmlfile))
        xmlx = ElementTree(file=xmlfp).getroot()
        tmp = xmlx.find("component[@name='coordinate1']/property[@name='size']/value")
        if tmp == None:
            tmp = xmlx.find("component[@name='Coordinate1']/property[@name='size']/value")
        width = int(tmp.text)
        print("file width: {0}".format(width))
    except (IOError, OSError) as strerr:
        print("IOError: %s" % strerr)
        return []
    finally:
        if xmlfp is not None:
            xmlfp.close()
    return width


def getLength(xmlfile):
    xmlfp = None
    try:
        xmlfp = open(xmlfile,'r')
        print('reading file length from: {0}'.format(xmlfile))
        xmlx = ElementTree(file=xmlfp).getroot()
        tmp = xmlx.find("component[@name='coordinate2']/property[@name='size']/value")
        if tmp == None:
            tmp = xmlx.find("component[@name='Coordinate2']/property[@name='size']/value")
        length = int(tmp.text)
        print("file length: {0}".format(length))
    except (IOError, OSError) as strerr:
        print("IOError: %s" % strerr)
        return []
    finally:
        if xmlfp is not None:
            xmlfp.close()
    return length


def create_xml(fileName, width, length, fileType):
    
    if fileType == 'slc':
        image = isceobj.createSlcImage()
    elif fileType == 'int':
        image = isceobj.createIntImage()
    elif fileType == 'amp':
        image = isceobj.createAmpImage()
    elif fileType == 'rmg':
        image = isceobj.Image.createUnwImage()
    elif fileType == 'float':
        image = isceobj.createImage()
        image.setDataType('FLOAT')

    image.setFilename(fileName)
    image.setWidth(width)
    image.setLength(length)
        
    image.setAccessMode('read')
    #image.createImage()
    image.renderVRT()
    image.renderHdr()
    #image.finalizeImage()


def create_amp(width, length, master, slave, amp):
    amp_data = np.zeros((length, width*2), dtype=np.float)
    amp_data[:, 0:width*2:2] = np.absolute(master) * (np.absolute(slave)!=0)
    amp_data[:, 1:width*2:2] = np.absolute(slave) * (np.absolute(master)!=0)
    amp_data.astype(np.float32).tofile(amp)
    create_xml(amp, width, length, 'amp')


def cmdLineParse():
    '''
    Command line parser.
    '''
    parser = argparse.ArgumentParser( description='log ratio')
    parser.add_argument('-mdir', dest='mdir', type=str, required=True,
            help = 'master directory containing the bursts')
    parser.add_argument('-sdir', dest='sdir', type=str, required=True,
            help = 'slave directory containing the bursts')
    parser.add_argument('-gdir', dest='gdir', type=str, required=True,
            help = 'geometric directory containing the lat/lon files ')
    parser.add_argument('-rlks',dest='rlks', type=int, default=0,
            help = 'number of range looks')
    parser.add_argument('-alks',dest='alks', type=int, default=0,
            help = 'number of azimuth looks')
    parser.add_argument('-ssize', dest='ssize', type=float, default=1.0,
            help = 'output geocoded sample size. default: 1.0 arcsec')
    return parser.parse_args()


if __name__ == '__main__':

    SCR_DIR = SCR_PATH

    inps = cmdLineParse()

    mbursts = sorted(glob.glob(os.path.join(inps.mdir, 'burst_*.slc')))
    #sbursts = sorted(glob.glob(os.path.join(inps.sdir, 'burst_*.slc')))
    #sbursts2 = sorted(glob.glob(os.path.join(inps.sdir2, 'burst_*.slc')))

    nmb = len(mbursts) #number of master bursts
    #nsb = len(sbursts) #number of slave bursts
    #nsb2 = len(sbursts2) #number of burst interferograms

    #lats = sorted(glob.glob(os.path.join(inps.gdir, 'lat_*.rdr')))
    #lons = sorted(glob.glob(os.path.join(inps.gdir, 'lon_*.rdr')))

    #if nmb != nsb:
    #    raise Exception('nmb != nsb\n')
    #if nmb != nsb2:
    #    raise Exception('nmb != nsb2\n')

    nb = nmb

    for i in range(nb):
        print('+++++++++++++++++++++++++++++++++++')
        print('processing burst {} of {}'.format(i+1, nb))
        print('+++++++++++++++++++++++++++++++++++')

        mslc = ntpath.basename(mbursts[i])
        if os.path.isfile(os.path.join(inps.sdir, mslc)) == False:
            print('skipping this burst')
            continue

        width = getWidth(mbursts[i] + '.xml')
        length = getLength(mbursts[i] + '.xml')

        width_looked = int(old_div(width,inps.rlks))
        length_looked = int(old_div(length,inps.alks))

        master = np.fromfile(mbursts[i], dtype=np.complex64).reshape(length, width)
        slave = np.fromfile(os.path.join(inps.sdir, mslc), dtype=np.complex64).reshape(length, width)
        #ifg = master * np.conj(slave)
        ifg = master * np.conj(slave) * (np.absolute(master)!=0) * (np.absolute(slave)!=0)

        ifgFile = 'ifg.int'
        ifg.astype(np.complex64).tofile(ifgFile)
        create_xml(ifgFile, width, length, 'int')

        ampFile = 'amp_%02d.amp' % (i+1)
        create_amp(width, length, master, slave, ampFile)

        ampLookedFile = 'b%02d_%dr%dalks.amp' % (i+1,inps.rlks,inps.alks)
        cmd = "{}/look.py -i {} -o {} -r {} -a {}".format(SCR_DIR,
            ampFile, 
            ampLookedFile,
            inps.rlks,
            inps.alks)
        runCmd(cmd)

        ifgLookedFile = 'b%02d_%dr%dalks.int' % (i+1,inps.rlks,inps.alks)
        cmd = "{}/look.py -i {} -o {} -r {} -a {}".format(SCR_DIR,
            ifgFile, 
            ifgLookedFile,
            inps.rlks,
            inps.alks)
        runCmd(cmd)

        corLookedFile = 'b%02d_%dr%dalks.cor' % (i+1,inps.rlks,inps.alks)
        #cmd = "{}/coherence.py -i {} -a {} -c {}".format(SCR_DIR,
        #    interferogram_looked, 
        #    amp_looked,
        #    cor_looked)
        cmd = "imageMath.py -e='sqrt(b_0*b_0+b_1*b_1)*(abs(a)!=0)*(b_0!=0)*(b_1!=0);abs(a)/(b_0*b_1+(b_0*b_1==0))*(abs(a)!=0)*(b_0!=0)*(b_1!=0)' --a={} --b={} -o {} -t float -s BIL".format(
            ifgLookedFile,
            ampLookedFile,
            corLookedFile)
        runCmd(cmd)

        latLookedFile = 'lat_%02d_%dr%dalks.rdr' % (i+1,inps.rlks,inps.alks)
        cmd = "{}/look.py -i {} -o {} -r {} -a {}".format(SCR_DIR,
            os.path.join(inps.gdir, 'lat_%02d.rdr' % (i+1)), 
            latLookedFile,
            inps.rlks,
            inps.alks)
        runCmd(cmd)

        lonLookedFile = 'lon_%02d_%dr%dalks.rdr' % (i+1,inps.rlks,inps.alks)
        cmd = "{}/look.py -i {} -o {} -r {} -a {}".format(SCR_DIR,
            os.path.join(inps.gdir, 'lon_%02d.rdr' % (i+1)), 
            lonLookedFile,
            inps.rlks,
            inps.alks)
        runCmd(cmd)

        latLooked = np.fromfile(latLookedFile, dtype=np.float64).reshape(length_looked, width_looked)
        lonLooked = np.fromfile(lonLookedFile, dtype=np.float64).reshape(length_looked, width_looked)

        latMax = np.amax(latLooked)
        latMin = np.amin(latLooked)
        lonMax = np.amax(lonLooked)
        lonMin = np.amin(lonLooked)
        bbox = "{}/{}/{}/{}".format(latMin, latMax, lonMin, lonMax)

        corLookedGeoFile = 'b%02d_%dr%dalks.cor.geo' % (i+1,inps.rlks,inps.alks)
        cmd = "{}/geo_with_ll.py -input {} -output {} -lat {} -lon {} -bbox {} -ssize {} -rmethod {}".format(SCR_DIR,
            corLookedFile, 
            corLookedGeoFile,
            latLookedFile,
            lonLookedFile,
            bbox,
            inps.ssize,
            1)
        runCmd(cmd)

        ampLookedGeoFile = 'b%02d_%dr%dalks.amp.geo' % (i+1,inps.rlks,inps.alks)
        cmd = "{}/geo_with_ll.py -input {} -output {} -lat {} -lon {} -bbox {} -ssize {} -rmethod {}".format(SCR_DIR,
            ampLookedFile, 
            ampLookedGeoFile,
            latLookedFile,
            lonLookedFile,
            bbox,
            inps.ssize,
            1)
        runCmd(cmd)

        os.remove(ifgFile)
        os.remove(ampFile)
        #os.remove(ampLookedFile)
        #os.remove(ifgLookedFile)
        #os.remove(corLookedFile)
        #os.remove(latLookedFile)
        #os.remove(lonLookedFile)

        os.remove(ifgFile+'.xml')
        os.remove(ampFile+'.xml')
        #os.remove(ampLookedFile+'.xml')
        #os.remove(ifgLookedFile+'.xml')
        #os.remove(corLookedFile+'.xml')
        #os.remove(latLookedFile+'.xml')
        #os.remove(lonLookedFile+'.xml')

        os.remove(ifgFile+'.vrt')
        os.remove(ampFile+'.vrt')
        #os.remove(ampLookedFile+'.vrt')
        #os.remove(ifgLookedFile+'.vrt')
        #os.remove(corLookedFile+'.vrt')
        #os.remove(latLookedFile+'.vrt')
        #os.remove(lonLookedFile+'.vrt')


# USAGE
# > slcp2cor.py -mdir ${dirm} -sdir ${dirs} -gdir ${dirg} -rlks 7 -alks 3 -ssize 1.0  

