#!/usr/bin/env /proj/sot/ska/bin/python

#####################################################################################################
#                                                                                                   #
#       violation_estimate_data.py: save violation estimated times in sqlite database v_table       #
#                                                                                                   #
#           author: t. isobe (tisobe@cfa.harvard.edu)                                               #
#                                                                                                   #
#           last update: Jun 16, 2016                                                               #
#                                                                                                   #
#####################################################################################################

import os
import sys
import re
import string
import random
import math
import sqlite3
import unittest
import time
from time import gmtime, strftime, localtime

#
#--- reading directory list
#
path = '/data/mta/Script/Envelope_trending/house_keeping/dir_list'
f    = open(path, 'r')
data = [line.strip() for line in f.readlines()]
f.close()

for ent in data:
    atemp = re.split(':', ent)
    var  = atemp[1].strip()
    line = atemp[0].strip()
    exec "%s = %s" %(var, line)
#
#--- append path to a private folder
#
sys.path.append(mta_dir)
sys.path.append(bin_dir)
#
import convertTimeFormat        as tcnv #---- converTimeFormat contains MTA time conversion routines
import mta_common_functions     as mcf  #---- mta common functions
import envelope_common_function as ecf  #---- collection of functions used in envelope fitting
#
#--- set a temporary file name
#
rtail  = int(time.time())
zspace = '/tmp/zspace' + str(rtail)
#
#--- set location of the database
#
v_table = house_keeping + '/v_table.sqlite3'
db      = sqlite3.connect(v_table)

#-----------------------------------------------------------------------------------
#-- read_v_estimate: read data for a given msid                                  ---
#-----------------------------------------------------------------------------------

def read_v_estimate(msid):
    """
    read data for a given msid
    input:  msid    --- msid
    output: (msid, yl_time, yt_time, rl_time, rt_time)
    """
    cursor  = db.cursor()

    msid    = msid.lower()
    cursor.execute("SELECT * FROM v_table WHERE msid='%s' " %msid)
    vout = cursor.fetchall()

    if len(vout) == 0:
        return []
    else:
        out = list(vout[0])
        out = out[1:]

        return out 

#-----------------------------------------------------------------------------------
#-- create_table: create table                                                    --
#-----------------------------------------------------------------------------------

def create_table():
    """
    create table
    input:  none
    output: sql database: v_table
    """
    cursor  = db.cursor()
    cursor.execute('''CREATE TABLE v_table (msid, yl_time, yt_time, rl_time, rt_time)''')    

#-----------------------------------------------------------------------------------
#-- incert_data: incert a new data set                                           ---
#-----------------------------------------------------------------------------------

def incert_data(msid, data):
    """
    incert a new data set
    input:  msid    ---msid
            data    --- a list of:
                yl_time --- yellow low violation time
                yt_time --- yellow top violation time
                rl_time --- red low violation time
                rt_time --- red top violation time
    ouput:  updated sql database
    """

    cmd = 'INSERT INTO v_table VALUES ("' + msid + '", ' 
    cmd = cmd + str(data[0]) + ', '
    cmd = cmd + str(data[1]) + ', '
    cmd = cmd + str(data[2]) + ', '
    cmd = cmd + str(data[3]) + ') '
#
#--- check whether the entry is already in the database
#--- if so, just update. otherwise, create a new entry
#
    try:
        out = read_v_estimate(msid)
        if out ==  []:
            cursor  = db.cursor()
            cursor.execute(cmd)
            db.commit()
        else:
            update_data(msid, data)
    except:
        cursor  = db.cursor()
        cursor.execute(cmd)
        db.commit()

#-----------------------------------------------------------------------------------
#-- update_data: update an existing data set                                     ---
#-----------------------------------------------------------------------------------

def update_data(msid, data):
    """
    update an existing data set
    input:  msid    --- msid
            data    --- a list of:
                yl_time --- yellow low violation time
                yt_time --- yellow top violation time
                rl_time --- red low violation time
                rt_time --- red top violation time
    output: updated sql database
    """
    cmd = 'UPDATE v_table SET  '
    cmd = cmd + ' yl_time='    + str(data[0]) + ', '
    cmd = cmd + ' yt_time='    + str(data[1]) + ', '
    cmd = cmd + ' rl_time='    + str(data[2]) + ', '
    cmd = cmd + ' rt_time='    + str(data[3])
    cmd = cmd + ' WHERE msid="' + msid + '"'

    cursor  = db.cursor()
    cursor.execute(cmd)
    db.commit()

#-----------------------------------------------------------------------------------
#-- delete_entry: delete entry with msid                                         ---
#-----------------------------------------------------------------------------------

def delete_entry(msid):
    """
    delete entry with msid
    input:  msid    --- msid
    output: updated database
    """

    cmd = 'DELETE FROM v_table  WHERE msid="' + msid + '"'

    cursor  = db.cursor()
    cursor.execute(cmd)
    db.commit()

#-----------------------------------------------------------------------------------------
#-- TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST    ---
#-----------------------------------------------------------------------------------------

class TestFunctions(unittest.TestCase):
    """
    testing functions
    """
#------------------------------------------------------------

#    def test_create_table(self):
#
#        create_table()

#------------------------------------------------------------

    def test_incert_data(self):

        msid = '1cbat_test'
        delete_entry(msid)
        data = [2017.11, 0, 2020.11, 0]
        incert_data(msid, data)

        out = read_v_estimate(msid)
        print  msid + ' ' + str(out)

        out[3] = 2021.12
        update_data(msid, out)

        out = read_v_estimate(msid)
        print msid + ' ' +  str(out)

        delete_entry(msid)

        msid = '1cbbt_test'
        data = [0.0, 0.0, 0.0, 0.0]
        incert_data(msid, data)

        out = read_v_estimate(msid)
        print  msid + ' ' + str(out)

        delete_entry(msid)

#-----------------------------------------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) > 1:
        msid = sys.argv[1]
        msid.strip()
        out  = read_v_estimate(msid)
        print str(out)
    else:
        unittest.main()

