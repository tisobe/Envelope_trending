#!/usr/bin/env /proj/sot/ska/bin/python

#####################################################################################################
#                                                                                                   #
#       glimmon_sql_read.py: extract limit information from glimmon database                        #
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
#--- set location of glimmon 
#
glimmon      = house_keeping + '/glimmondb.sqlite3'

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
    if tchk == 1 :
        add = 273.15

    else:
        add = 0

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
#--- if tchk is 2, convert the temperature from F to K
#
        y_min = float(tup[11]) + add
        if tchk == 2:
            y_min = ecf.f_to_k(y_min)
        y_min = ecf.round_up(y_min)

        y_max = float(tup[10]) + add
        if tchk == 2:
            y_max = ecf.f_to_k(y_max)
        y_max = ecf.round_up(y_max)

        r_min = float(tup[13]) + add
        if tchk == 2:
            r_min = ecf.f_to_k(r_min)
        r_min = ecf.round_up(r_min)

        r_max = float(tup[12]) + add
        if tchk == 2:
            r_max = ecf.f_to_k(r_max)
        r_max = ecf.round_up(r_max)

        alist = [time, ntime,  y_min, y_max, r_min, r_max]
        limit_list.append(alist)
#
#--- if glimmon does not give the limits, keep it open
#
    if len(limit_list) == 0:
        limit_list = [[0, 3218831995, 'na', 'na', 'na', 'na']]

    return limit_list

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

#-----------------------------------------------------------------------------------

if __name__ == "__main__":

    unittest.main()
