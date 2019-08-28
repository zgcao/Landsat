#!/usr/bin/env python
# coding: utf-8

# Download the data files of Landsat T1 from google cloud storage
# Before you used the script to download, two things need to be prepared
# 1. install the gstuil toolbox as referenced:
# 2. Order a list of data in earthexplorer.usgs.gov
#    then, save their scenced ID from the Traking Bulkorders
#    input template:
#    https://github.com/zgcao/Landsat/blob/master/template_input_gcs

from __future__ import print_function
import subprocess
from datetime import datetime


def down_lc8oli_gcs(scene_list, outdir):
    #
    f = open(outdir + '/download_log_'+ datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'w')

    for scene_name in open(filename, 'r').readlines():
        fileparts = scene_name.strip().split('_')
        mission = fileparts[0]
        url = 'gs://gcp-public-data-landsat/' + mission + '/01/'
        path, row = fileparts[2][0:3], fileparts[2][3:]

        download_url = url + path + '/' + row + '/' + scene_name.strip() + '/'
        # cmd = '/Users/zhigang/Scripts/google-cloud-sdk/bin/gsutil'
        cmd = 'gsutil -m cp -r ' + download_url + ' ' + outdir
        print(cmd)

        status = subprocess.call(cmd, shell=True)
        if status != 0:
            print(scene_name + ' Failed!')
            f.write(scene_name + ' -- failed.\n')
        else:
            f.write(scene_name + ' -- successful!\n')

    f.close()

def down_s2msi_gcs(xml_file, outdir):
    import xml.etree.cElementTree as ET

    f = open(out_dir + '/download_log_'+ datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'w')

    tree = ET.ElementTree(file=xml_file)
    url = 'gs://gcp-public-data-sentinel-2/tiles/'    
    for item in tree.iter(tag='{urn:ietf:params:xml:ns:metalink}file'):
        file_name = item.attrib['name']
        #print(file_name)
        foos = file_name.split('_')
        UTM_ZONE,LATITUDE_BAND,GRID_SQUARE = foos[5][1:3],foos[5][3],foos[5][4:]
        #print(UTM_ZONE,LATITUDE_BAND,GRID_SQUARE,sep=',')
        GRANULE_ID = file_name.split('.')[0] + '.SAFE'
        download_url = url + UTM_ZONE + '/' + LATITUDE_BAND + '/' + GRID_SQUARE + '/' + GRANULE_ID

        cmd = 'gsutil -m cp -r ' + download_url + ' ' + outdir
        print(cmd)

        status = subprocess.call(cmd, shell=True)
        if status != 0:
            print(GRANULE_ID + ' Failed!')
            f.write(GRANULE_ID + ' Failed!\n')
        else:
            f.write(cmd + ' -- successful!\n')

    f.close()



"""Main"""
filename = '/Users/zhigang/Downloads/bulk_1033158.txt'
outdir = '/Users/zhigang/Downloads'
down_lc8oli_gcs(filename, outdir)

xml_file = '/Users/zhigang/Downloads/products-2.meta4'
out_dir = '/Volumes/Data2/MSI_Taihu_2015_2018'
down_s2msi_gcs(xml_file, out_dir)
