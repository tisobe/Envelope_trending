#!/usr/bin/env /proj/sot/ska/bin/python

#####################################################################################################
#                                                                                                   #
#       envelope_common_function.py:    collection of functions used in envelope trending           #
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
import astropy.io.fits  as pyfits
import os.path
import sqlite3
import unittest
import time
from datetime import datetime
from time import gmtime, strftime, localtime
#
#--- from ska
#
from Ska.Shell import getenv, bash
ascdsenv = getenv('source /home/ascds/.ascrc -r release; source /home/mta/bin/reset_param', shell='tcsh')
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
import glimmon_sql_read         as gsr  #---- glimmon database reading
import read_mta_limits_db       as rmld #---- mta databse reading
#
#--- set a temporary file name
#
rtail  = int(time.time())
zspace = '/tmp/zspace' + str(rtail)
#
#--- need a special treatment for the following msids
#
special_list = ['3FAMTRAT', '3FAPSAT', '3FASEAAT', '3SMOTOC', '3SMOTSTL', '3TRMTRAT']
#
#--- other settings
#
NULL   = 'null'
#
#--- month list
#
m_list = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
#
#--- set base time at 1998.1.1
#
BTFMT    = '%m/%d/%y,%H:%M:%S'
FMT2     = '%Y-%m-%d,%H:%M:%S'
FMT3     = '%Y-%m-%dT%H:%M:%S'
basetime = datetime.strptime('01/01/98,00:00:00', BTFMT)
#
#--- set epoch
#
Epoch    = time.localtime(0)
Ebase_t  = time.mktime((1998, 1,  1, 0, 0, 0, 5, 1, 0))
Domstart = time.mktime((1999, 7, 21, 0, 0, 0, 5, 1, 0)) - Ebase_t
#
#--- read mta limit data base as back up limit database
#
mta_db = rmld.read_mta_limits_db()

#------------------------------------------------------------------------------------------------------
#-- find_current_stime: find the current time in seconds from 1998.1.1                              ---
#------------------------------------------------------------------------------------------------------

def find_current_stime():
    """
    find the current time in seconds from 1998.1.1
    input:  none
    output: sec1998 --- the current time in seconds from 1998.1.1
    """
    
    current = time.gmtime()
    sec1998 = time.mktime(current) - Ebase_t

    return sec1998

#------------------------------------------------------------------------------------------------------
#-- covertfrom1998sec: convert second from 1998.1.1 to yyyy-mm-ddThh:mm:ss format                    --
#------------------------------------------------------------------------------------------------------

def covertfrom1998sec(stime):
    """
    convert second from 1998.1.1 to yyyy-mm-ddThh:mm:ss format 
    input:  stime   --- second from 1998.1.1
    output: etime   --- time in yyyy-mm-ddThh:mm:ss
    """

    etime = Ebase_t + stime
    etime = time.localtime(etime)
    etime = time.strftime(FMT3, etime)

    return etime

#------------------------------------------------------------------------------------------------------
#-- stime_to_frac_year: convert seconds from 1998.1.1 to fractional year format                     ---
#------------------------------------------------------------------------------------------------------

def stime_to_frac_year(stime):
    """
    convert seconds from 1998.1.1 to fractional year format
    input:  stime   --- seconds from 1998.1.1
            etime   --- time in fractinal year;, e.g., 2012.223
    """

    etime = Ebase_t + stime
    etime = time.localtime(etime)
    etime = time.strftime( '%Y-%j', etime)
    atemp = re.split('-', etime)
    year  = float(atemp[0])
    ydate = float(atemp[1])

    if tcnv.isLeapYear(year):
        base = 366
    else:
        base = 365
        
    etime = year + ydate / base

    return etime

#------------------------------------------------------------------------------------------------------
#-- dom_to_stime: convert dom into seconds from 1998.1.1                                            ---
#------------------------------------------------------------------------------------------------------

def dom_to_stime(dom):
    """
    convert dom into seconds from 1998.1.1
    input:  dom     --- dom (day of mission)
    output: stime   --- seconds from 1998.1.1
    """

    stime = float(dom) * 86400 + Domstart

    return stime

#------------------------------------------------------------------------------------------------------
#-- current_time: return current time in fractional year                                            ---
#------------------------------------------------------------------------------------------------------

def current_time():
    """
    return current time in fractional year
    input:  none
    output: fyear
    """

    otime = time.gmtime()
    year  = otime.tm_year
    yday  = otime.tm_yday
    hr    = otime.tm_hour

    if tcnv.isLeapYear(year) == 1:
        base = 366
    else:
        base = 365

    fyear = year + (yday + hr/24.0) / base

    return fyear

#------------------------------------------------------------------------------------------------------
#-- c_to_k: convert the temperature from C to K                                                      --
#------------------------------------------------------------------------------------------------------

def c_to_k(c_temp):
    """
    convert the temperature from C to K
    input:  c_temp  --- temperature in C
    output: k_temp  --- temperature in K
    """

    k_temp = c_temp + 273.15

    return k_temp

#------------------------------------------------------------------------------------------------------
#-- f_to_k: convert the temperature from F to K                                                      --
#------------------------------------------------------------------------------------------------------

def f_to_k(f_temp):
    """
    convert the temperature from F to K
    input:  f_temp  --- temperature in F
    output: k_temp  --- temperature in K
    """

    k_temp = (f_temp -32.0) * 0.55555 + 273.15

    return k_temp

#------------------------------------------------------------------------------------------------------
#-- data_seeker: extract a fits file using data_seeker                                               --
#------------------------------------------------------------------------------------------------------

def data_seeker(start, stop, msid):
    """
    extract a fits file using data_seeker
    input:  start   --- starting time in seconds from 1998.1.1
            stop    --- stopping time in seconds from 1998.1.1
            msid    --- msid of the data you want to extract
    output: temp_out.fits   --- fits file extracted
    """
#
#--- check a dummy 'test' file exists. it also needs param directory
#
    if not os.path.isfile('test'):
        fo = open('./test', 'w')
        fo.close()
    
    try:
        clean_dir('param')
    except:
        cmd = 'mkdir ./param 2> /dev/null'
        os.system(cmd)

    mcf.rm_file('./temp_out.fits')
#
#--- name must starts with "_"
#
    mc  = re.search('deahk',  msid.lower())
    mc2 = re.search('oobthr', msid.lower())
#
#--- deahk cases
#
    if mc is not None:
        atemp = re.split('deahk', msid)
        val   = float(atemp[1])
        if val < 17:
            name = 'rdb..deahk_temp.' + msid.upper() + '_avg'
        else:
            name = 'rdb..deahk_elec.' + msid.upper() + '_avg'
#
#--- oobthr cases
#
    elif mc2 is not None:
        name = 'mtatel..obaheaters_avg._' + msid.lower() + '_avg'
#
#--- special cases (see the list at the top)
#
    elif msid.upper() in special_list:
        name = msid.upper() + '_AVG'

    else:
        name = '_' + msid.lower() + '_avg'
#
#--- create dataseeker command
#
    cmd1 = '/usr/bin/env PERL5LIB="" '

    cmd2 = ' source /home/mta/bin/reset_param; '
    cmd2 = ' ' 
    cmd2 = cmd2 + ' /home/ascds/DS.release/bin/dataseeker.pl '
    cmd2 = cmd2 + ' infile=test  outfile=temp_out.fits  '
    cmd2 = cmd2 + ' search_crit="columns=' + name
    cmd2 = cmd2 + ' timestart=' + str(start)
    cmd2 = cmd2 + ' timestop='  + str(stop) 
    cmd2 = cmd2 + '" loginFile='+ house_keeping + 'loginfile '

    cmd  = cmd1 + cmd2 
    bash(cmd,  env=ascdsenv)

    cmd  = 'rm /data/mta/dataseek* 2>/dev/null'
    os.system(cmd)


#-----------------------------------------------------------------------------------------------
#-- clean_dir: empty out the directory content                                                --
#-----------------------------------------------------------------------------------------------

def clean_dir(tdir):
    """
    empty out the directory content
    input:  tdir    --- a directory path
    output: tdir if it does not exist before
    """

    chk = 0
    if os.listdir(tdir):
        chk = 1

    if chk == 1:
        cmd   = 'rm -rf ' +  tdir + '/*'
        os.system(cmd)
    else:
        cmd   = 'mkdir ' + tdir
        os.system(cmd)


#------------------------------------------------------------------------------------------------------
#-- read_fits_file: read table fits data and return col names and data                               --
#------------------------------------------------------------------------------------------------------

def read_fits_file(fits):
    """
    read table fits data and return col names and data
    input:  fits    --- fits file name
    output: cols    --- column name
    tbdata  --- table data
                to get a data for a <col>, use:
                data = list(tbdata.field(<col>))
    """
    hdulist = pyfits.open(fits)
#
#--- get column names
#
    cols_in = hdulist[1].columns
    cols    = cols_in.names
#
#--- get data
#
    tbdata  = hdulist[1].data

    hdulist.close()

    return [cols, tbdata]

#-----------------------------------------------------------------------------------------------
#-- read_file_data: read the content of the file and return it                                --
#-----------------------------------------------------------------------------------------------

def read_file_data(infile, remove=0):
    """
    read the content of the file and return it
    input:  infile  --- file name
            remove  --- if 1, remove the input file after read it, default: 0
    output: out     --- output
    """

    f   = open(infile, 'r')
    out = [line.strip() for line in f.readlines()]
    f.close()

    if remove == 1:
        mcf.rm_file(infile)

    return out

#-----------------------------------------------------------------------------------
#-- round_up: round out the value in two digit                                  ----
#-----------------------------------------------------------------------------------

def round_up(val):
    """
    round out the value in two digit
    input:  val --- value
    output: val --- rounded value
    """

    try:
        dist = int(math.log10(abs(val)))
        if dist < -2:
            val *= 10 ** abs(dist)
    except:
        dist = 0

    val = "%3.2f" % (round(val, 2))
    val = float(val)

    if dist < -2:
        val *= 10**(dist)

    return val

#------------------------------------------------------------------------------------------------------
#-- read_unit_list: read unit list and make into a dictionary form                                   --
#------------------------------------------------------------------------------------------------------

def read_unit_list():
    """
    read unit list and make into a dictionary form
    input: none but read from <house_keeping>/unit_list
    output: udict   --- a dictionary of <msid> <---> <unit>
    """
#
#--- read the main unit file and description of msid
#
    ulist = house_keeping + 'unit_list'
    data  = read_file_data(ulist)

    udict = {}
    ddict = read_description_from_mta_list()

    for ent in data:
        atemp = re.split('\s+', ent)
        try:
            udict[atemp[0]] = atemp[1]
        except:
            pass
#
#--- read dataseeker unit list and replace if they are not same
#
    ulist = house_keeping + 'dataseeker_entry_list'
    data  = read_file_data(ulist)
    for ent in data:
        if ent[0] == '#':
            continue
        atemp = re.split('\t+', ent)
        if len(atemp) < 3:
            continue

        msid =atemp[0].lower()
        if mcf.chkNumeric(atemp[2]) == False:
            if atemp[2] != '':
                udict[msid] =  atemp[2]
        else:
            try:
                test = udict[msid]
            except:
                udict[msid] =  ''
        ddict[msid] = atemp[-1]
#
#--- farther read supplemental lists
#
    ulist = house_keeping + 'unit_supple'
    data  = read_file_data(ulist)
    for ent in data:
        atemp = re.split('\s+', ent)
        udict[atemp[0]] = atemp[1]

    dlist = house_keeping + 'description_supple'
    data  = read_file_data(dlist)
    for ent in data:
        atemp = re.split('\:\:', ent)
        msid  = atemp[0].strip()
        descr = atemp[1].strip()
        ddict[msid] = descr

    return [udict, ddict]

#------------------------------------------------------------------------------------------------------
#-- read_description_from_mta_list: read descriptions of msid from mta limit table                   --
#------------------------------------------------------------------------------------------------------

def read_description_from_mta_list():
    """
    read descriptions of msid from mta limit table
    input:  none but read from <house_keeping>/mta_limits.db
    outpu:  mdict   --- a dictionary of msid<--->description
    """

    mfile = house_keeping + 'mta_limits.db'
    data  = read_file_data(mfile)

    mdict = {}
    prev  = ''
    for ent in data:
        if ent == '':
            continue 
        if ent[0] == '#':
            continue
        atemp = re.split('\s+', ent)

        if atemp[0] == prev:
            continue
        prev  = atemp[0]

        msid  = atemp[0].lower()
        atemp = re.split('#', ent)
        try:
            btemp = re.split('\s+', atemp[1])
#
#--- quite often junk got in because the format of each line is not clean
#--- remove these junks from the end of the line
#
            discription = atemp[1].replace(btemp[-1],"")
            if btemp[-2] in ['K', 'V', 'AMP', 'RATE', 'CNT', 'uA', 'RPS', 'C', 'mm', 'CURRENT', 'STEP']:
                discription = discription.replace(btemp[-2],"")
    
            mdict[msid] = discription
        except:
            pass

    return mdict

#------------------------------------------------------------------------------------------------------
#-- set_limit_list: read upper and lower yellow and red limits for each period                       --
#------------------------------------------------------------------------------------------------------

def set_limit_list(msid):
    """
    read upper and lower yellow and red limits for each period
    input:  msid--- msid
    output: l_list  --- a list of list of [<start time>, <stop time>, <yellow min>, <yellow max>, <red min>, <red max>]
    """
    
    [udict, ddict]  = read_unit_list()
    tchk = 0
    try:
        unit = udict[msid.lower()]
        if unit.lower() in ['k', 'degc']:
            tchk = 1
        elif unit.lower() == 'degf':
            tchk = 2
        elif unit.lower() == 'psia':
            tchk = 3
    except:
        pass
    
    l_list = gsr.read_glimmon(msid, tchk)
    
    if len(l_list) == 0:
        try:
            l_list = mta_db[msid]
        except:
            l_list = []
#
#--- if there is no limt given, set dummy limits
#
    if len(l_list) == 0:
        tstart = 31536000                               #---- 1999:001:00:00:00
        tstop  = find_current_stime()
        l_list = [[tstart, tstop, -998, 998, -999, 999]]

        return l_list

    cleaned = []
    for alist in l_list:
        if alist[0] == alist[1]:
            continue
        else:
            cleaned.append(alist)
    
    cleaned2 = []
    alist = cleaned[0]
    for k in range(1, len(cleaned)):
        blist = cleaned[k]
        if (alist[2] == blist[2]) and (alist[3] == blist[3]) and (alist[4] == blist[4]) and (alist[5] == blist[5]):
            alist[1] = blist[1]
        else:
            cleaned2.append(alist)
            alist = blist

    cleaned2.append(alist)
    
    return cleaned2


#------------------------------------------------------------------------------------------------------
#-- check_dataseeker_entry: check msid is listed in dataseeker database                             ---
#------------------------------------------------------------------------------------------------------

def check_dataseeker_entry(msid):
    """
    check msid is listed in dataseeker database
    input: msid     --- msid
    output: True/False
    """

    cmd = 'grep -i ' + msid + ' ' +  house_keeping +  'dataseeker_entry_list >' + zspace
    os.system(cmd)
    if os.stat(zspace).st_size == 0:
        mcf.rm_file(zspace)
        return False
    else:
        mcf.rm_file(zspace)
        return True

#-----------------------------------------------------------------------------------------
#-- TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST    ---
#-----------------------------------------------------------------------------------------

class TestFunctions(unittest.TestCase):
    """
    testing functions
    """
#------------------------------------------------------------

    def test_find_current_stime(self):

        sec1998 = find_current_stime()
        print "current time: " + str(sec1998)


#------------------------------------------------------------

    def test_covertfrom1998sec(self):

        stime = 119305230
        out   = covertfrom1998sec(stime)

        self.assertEquals(out, '2001-10-12T21:20:30')

#------------------------------------------------------------
    
    def test_dom_to_stime(self):

        dom   = 0
        stime = dom_to_stime(dom)
        self.assertEquals(stime, 48902400.0)

        dom   = 10
        stime = dom_to_stime(dom)
        self.assertEquals(stime, 49766400.0)


#------------------------------------------------------------

    def test_data_seek(self):

        comp  = [147.6113739, 147.6113739, 147.6113739, 147.6113739, 147.6113739]

        msid  = '1crbt'
        name  = msid + '_avg'
        start = 536457596           #---- 2015:001:00:00:00
        stop  = 536543996           #---- 2015:002:00:00:00

        data_seeker(start, stop, msid)

        fits = 'temp_out.fits'
        [col, tbdata] = read_fits_file(fits)
        data = tbdata.field(name)

        test = []
        for k in range(0, 5):
            test.append(round(data[k], 7))

        self.assertEquals(test, comp)

#------------------------------------------------------------

    def test_stime_to_frac_year(self):

        stime  = 549590396
        fyear  = stime_to_frac_year(stime)

        print "I AM HERE: " + str(fyear) + '<--->2916,419'


#------------------------------------------------------------

    def test_read_unit_list(self):

        [mdict, ddict] = read_unit_list()

        msid = '1crbt'
        self.assertEquals(ddict[msid], 'COLD RADIATOR TEMP. B')
        self.assertEquals(mdict[msid], 'DEGC')

        msid = 'aorwspd2'
        self.assertEquals(mdict[msid], 'RPS')

        msid = '1deamztc'
        self.assertEquals(mdict[msid], 'C')

#------------------------------------------------------------

    def test_set_limit_list(self):

        msid = '1cbat'
        out = set_limit_list(msid)
        self.assertEquals(out[0], [0, 119305230, 202.65, 223.15, 197.65, 312.65])

#------------------------------------------------------------
    
    def test_round_up(self):

        val = 1.2342
        out = round_up(val)
        self.assertEquals(out, 1.23)

        val = 0.000134
        out = round_up(val)
        self.assertEquals(out, 0.00013)
        

#-----------------------------------------------------------------------------------


if __name__ == "__main__":

    unittest.main()

