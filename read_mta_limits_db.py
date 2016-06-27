#!/usr/bin/env /proj/sot/ska/bin/python

#####################################################################################################
#                                                                                                   #
#       read_mta_limits_db.py: read mta_limit_db  and return yellow and red lower and upper limits  #
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
import convertTimeFormat    as tcnv     #---- converTimeFormat contains MTA time conversion routines
import mta_common_functions as mcf      #---- mta common functions
#import envelope_common_function as ecf #---- collection of functions used in envelope fitting
                                        #---- don't use this as it also refers to this module and gets conflict
#
#--- set a temporary file name
#
rtail  = int(time.time())
zspace = '/tmp/zspace' + str(rtail)
#
#--- general end time
#
etime = 3218831995      #---- 2100:001:00:00:00

#-----------------------------------------------------------------------------------
#-- read_mta_limits_db: read mta_limit_databse  and return yellow and red lower and upper limits 
#-----------------------------------------------------------------------------------

def read_mta_limits_db():
    """
    read mta_limit_databse  and return yellow and red lower and upper limits
    input:  msid        --- msid
    output: ldict       --- a dictionary of msid <---> a list of lists of:
                                time    --- starting time in seconds from 1998.1.1
                                ntime   --- ending time in seconds from 1998.1.1
                                y_min   --- lower yellow limit
                                y_max   --- upper yellow limit
                                r_min   --- lower red limit
                                r_max   --- upper red limit
    """
    efile = house_keeping + 'mta_limits.db'
    f     = open(efile, 'r')
    data  = [line.strip() for line in f.readlines()]
    f.close()

    ldict  = {}
    s_list = []
    prev   = ''
    for ent in data:
        if ent == '':
            continue

        line = str(ent)
        if line[0] == '#':
            continue

        atemp = re.split('\s+', ent)
        msid  = atemp[0].lower()
        time  = int(float(atemp[5]))

        yl    = float(atemp[1])
        yl    =  round_up(yl)

        yu    = float(atemp[2])
        yu    =  round_up(yu)

        rl    = float(atemp[3])
        rl    =  round_up(rl)

        ru    = float(atemp[4])
        ru    =  round_up(ru)
#
#--- the current msid is the same as the previous one; so replace the end time in the last data
#--- and save it in the list
#
        if msid == prev:
            tlist[1] = time
            s_list.append(tlist)

            tlist = [time, etime, yl, yu, rl, ru]
        else:
#
#--- the first time, just set up the prev and tlist
#
            if prev == '':
                prev = msid
#
#--- msid changed; so save the previous msid limit data in the dictionary
#
            else:
                s_list.append(tlist)
                ldict[prev] = s_list
                prev   = msid
                s_list = []

            tlist = [time, etime, yl, yu, rl, ru]

    return ldict

#-----------------------------------------------------------------------------------
#-- round_up: round out the value in two digit                                  ----
#-----------------------------------------------------------------------------------

def round_up(val):
    """
    round out the value in two digit
    input:  val --- value
    output: val --- rounded value
    """

    val = "%3.2f" % (round(val, 2))
    val = float(val)

    return val

#-----------------------------------------------------------------------------------------
#-- TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST    ---
#-----------------------------------------------------------------------------------------

class TestFunctions(unittest.TestCase):
    """
    testing functions
    """

#------------------------------------------------------------

    def test_read_mta_limits_db(self):

        mdict  = read_mta_limits_db()

        comp =  [84585599, 118627199, 141.0, 168.0, 131.0, 183.06]
        msid = '1crbt'
        out  = mdict[msid]
        self.assertEquals(out[1], comp)

        msid = 'oobthr07'
        comp = [573227507, 3218831995, 321.15, 333.15, 264.15, 368.15]
        out  = mdict[msid]
        self.assertEquals(out[3], comp)

#-----------------------------------------------------------------------------------

if __name__ == "__main__":

    unittest.main()
