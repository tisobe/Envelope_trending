#!/usr/bin/env /proj/sot/ska/bin/python

#####################################################################################################
#                                                                                                   #
#       glimmon_sql_read.py: extract limit information from glimmon database                        #
#                                                                                                   #
#           author: t. isobe (tisobe@cfa.harvard.edu)                                               #
#                                                                                                   #
#           last update: Jul 01, 2016                                                               #
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
#--- set location of glimmon 
#
glimmon      = house_keeping + '/glimmondb.sqlite3'
#
#--- speical msid database
#
sp_msid_list =  ["cpa1pwr", "cpa2pwr", "cpcb15v", "cpcb5v", "csitb15v", "csitb5v", "ctsb15v", "ctsb5v", \
                 "ctub15v", "ctxbpwr", "eepb5v", "eoecnv1c", "eoecnv2c", "eoecnv3c", "eoesac1c", "eoesac2c",\
                 "epb15v", "epb5v", "acpb5cv", "ade2p5cv", "aspeb5cv", "eoeb3cic", "eoeb3cic", "ai1ax2x", \
                 "eoeb1cic", "eoeb2cic"]

#-----------------------------------------------------------------------------------
#-- read_glimmon: read glimmondb.sqlite3 and return yellow and red lower and upper limits 
#-----------------------------------------------------------------------------------

def read_glimmon(msid, tchk):
    """
    read glimmondb.sqlite3 and return yellow and red lower and upper limits
    input:  msid        --- msid
            tchk        --- whether this is temp and need to be converted into k
                            if degc tchk = 1
                               degf tchk = 2
                               psia tchk = 3
    output: limit_list  --- a list of lists which contain:
                        time    --- starting time in seconds from 1998.1.1
                        ntime   --- ending time in seconds from 1998.1.1
                        y_min   --- lower yellow limit
                        y_max   --- upper yellow limit
                        r_min   --- lower red limit
                        r_max   --- upper red limit
    """
#
#--- check the msid is in the special database list
#
    if msid.lower() in sp_msid_list:
        limit_list = special_case_database(msid)
#
#--- otherwise use glimmon database
#
    else:
        limit_list = read_glimmon_main(msid, tchk)

    return limit_list

#-----------------------------------------------------------------------------------
#-- read_glimmon_main: read glimmondb.sqlite3 and return yellow and red lower and upper limits 
#-----------------------------------------------------------------------------------

def read_glimmon_main(msid, tchk):
    """
    read glimmondb.sqlite3 and return yellow and red lower and upper limits
    input:  msid        --- msid
            tchk        --- whether this is temp and need to be converted into k
                            if degc tchk = 1
                               degf tchk = 2
                               psia tchk = 3
    output: limit_list  --- a list of lists which contain:
                        time    --- starting time in seconds from 1998.1.1
                        ntime   --- ending time in seconds from 1998.1.1
                        y_min   --- lower yellow limit
                        y_max   --- upper yellow limit
                        r_min   --- lower red limit
                        r_max   --- upper red limit
    """

#
#--- connect to sqlite database
#
    db      = sqlite3.connect(glimmon)
    cursor  = db.cursor()

    msid    = msid.lower()
    cursor.execute("SELECT * FROM limits WHERE msid='%s'" %msid)
    allrows = cursor.fetchall()

    if len(allrows) == 0:
        return []
#
#--- glimmon keeps the temperature related quantities in C. convert it into K, if needed.
#
    limit_list = []

    for k in range(0, len(allrows)):
        tup   = allrows[k]

        time  = int(float(tup[3]))
#
#--- if the first time is later than 1999 Jul 21, set it to 0 (1998.1.1)
#
        if k == 0:
            if time > 48902399:             #---- 1999:202:00:00:00 
                time = 0
#
#--- the last interval goes to 2100
#
        try:
            ntup  = allrows[k+1]
            ntime = int(float(ntup[3]))
        except:
            ntime = 3218831995              #---- 2100:001:00:00:00
#
#--- get the values and convert unit if necessary
#
        y_min = float(tup[11])
        y_min = unit_modification(y_min, tchk)

        y_max = float(tup[10])
        y_max = unit_modification(y_max, tchk)

        r_min = float(tup[13])
        r_min = unit_modification(r_min, tchk)

        r_max = float(tup[12])
        r_max = unit_modification(r_max, tchk)

        alist = [time, ntime,  y_min, y_max, r_min, r_max]
        limit_list.append(alist)
#
#--- if glimmon does not give the limits, keep it open
#
    if len(limit_list) == 0:
        limit_list = [[0, 3218831995, 'na', 'na', 'na', 'na']]

    return limit_list

#-----------------------------------------------------------------------------------
#-- unit_modification: modify value depending on unit                             --
#-----------------------------------------------------------------------------------

def unit_modification(val, tchk):
    """
    modify value depending on unit
    input:  val         --- original value
            tchk        --- whether this is temp and need to be converted into k
                            if degc tchk = 1
                               degf tchk = 2
                               psia tchk = 3
    output: val         --- updated value
    """

    if tchk == 1:
        val += 273.15               #--- C to K conversion
    elif tchk == 2:
        val = ecf.f_to_k(val)       #--- F to K conversion
    elif tchk == 3:
        val /= 0.145038             #--- kp to psia conversion
#
#--- round off the value to 2 dicimal points
#
    val = ecf.round_up(val)

    return val


#-----------------------------------------------------------------------------------
#-- special_case_database: read special glimmon entry limit database and create list 
#-----------------------------------------------------------------------------------

def special_case_database(msid):
    """
    read special glimmon entry limit database and create list
    input:  msid        --- a msid
    output: l_list      --- a list of limits
    """

    file = house_keeping + 'glimmon_special_limit'
    data = ecf.read_file_data(file)

    bstart = 48902399.0             #---- 1999:202:00:00:00
    mstop  = 3218831995.0           #---- 2100:001:00:00:00

    l_list = []
    for ent in data:
        atemp  = re.split('\s+', ent)
        tmsid  = atemp[0].strip()
        tmsid  = tmsid.lower()

        if tmsid != msid:
            continue

        start  = float(atemp[5])
        limit  = [start, mstop, float(atemp[1]), float(atemp[2]), float(atemp[3]), float(atemp[4])]
#
#--- check glimmon to find any limit data previous to starting date
#
        glimit = read_glimmon_main(msid, 0)

        l_list = []
        for lent in glimit:
            stime = float(lent[0])
            ltime = float(lent[1])

            if ltime < start:
                l_list.append(lent)

            elif (stime < start) and (ltime >=start):
                lent[1] = start
                l_list.append(lent)
                break

            elif ltime > start:
                break

        l_list.append(limit)
        
    return l_list


#-----------------------------------------------------------------------------------------
#-- TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST    ---
#-----------------------------------------------------------------------------------------

class TestFunctions(unittest.TestCase):
    """
    testing functions
    """

#------------------------------------------------------------

    def test_read_glimmon(self):

        comp1 = [0,         119305230, -137.0, -100.0, -142.0,  100.0]
        comp2 = [119305230, 123774707,  136.15, 173.15, 131.15, 183.15]

        msid = '1crbt'
        tchk = 0
        out1 = read_glimmon(msid, tchk)

        tchk = 1
        out2 = read_glimmon(msid, tchk)

        self.assertEquals(out1[0], comp1)
        self.assertEquals(out2[1], comp2)

        tchk = 0
        msid = '1hoprapr'
        out1 = read_glimmon(msid, tchk)
        msid = 'oobthr07'
        out2 = read_glimmon(msid, tchk)
        print "HOPRAPR: "  + str(out1)
        print "OOBTHR07: " + str(out2)

        msid = 'ohrthr20'
        out2 = read_glimmon(msid, tchk)
        print "OHRTHR20: " + str(out2)

        tchk = 2
        msid = '4prt1at'
        out2 = read_glimmon(msid, tchk)
        print "4PRT1AT: " + str(out2)

        tchk = 0
        msid = 'eoeb1cic'
        out2 = read_glimmon(msid, 0)
        print "EOEB1CIC: " + str(out2)

#------------------------------------------------------------

    def test_special_case_database(self):

        

        for msid in sp_msid_list:
            print "Secondary-- " +  msid + ': ' +  str(special_case_database(msid))

#-----------------------------------------------------------------------------------

if __name__ == "__main__":

    unittest.main()
