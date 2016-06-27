#!/usr/bin/env /proj/sot/ska/bin/python

#####################################################################################################
#                                                                                                   #
#       update_database.py: updata database for all msids                                           #
#                                                                                                   #
#           author: t. isobe (tisobe@cfa.harvard.edu)                                               #
#                                                                                                   #
#           last update: Jun 23, 2016                                                               #
#                                                                                                   #
#####################################################################################################

import os
import sys
import re
import string
import random
import math
import numpy
import astropy.io.fits  as pyfits
import sqlite3
import unittest
import time
from datetime import datetime
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
import glimmon_sql_read         as gsr  #---- glimmon database reading
import read_mta_limits_db       as rmld #---- mta databse reading
import envelope_common_function as ecf  #---- collection of functions used in envelope fitting
#
#--- set a temporary file name
#
rtail  = int(time.time())
zspace = '/tmp/zspace' + str(rtail)

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
Ebase_t  = time.mktime((1998, 1, 1, 0, 0, 0, 5, 1, 0))

NA       = 'na'
#
#--- read mta limit data base as back up limit database
#
mta_db = rmld.read_mta_limits_db()

#------------------------------------------------------------------------------------------------------
#-- run_update_envelop_database: contorl function to updata database for all msids                   --
#------------------------------------------------------------------------------------------------------

def run_update_envelop_database():
    """
    contorl function to updata database for all msids
    input:  none but read from several static list and get data with dataseeker
    outpu:  updated data file: <data_dir>/<msid>_data
    """
    update_glimmon_database()

    update_mta_comp_database()

#------------------------------------------------------------------------------------------------------
#-- update_glimmon_database: updata database related glimmon msids                                   --
#------------------------------------------------------------------------------------------------------

def update_glimmon_database():
    """
    updata database related glimmon msids
    input:  none but read from several static list and get data with dataseeker
    outpu:  updated data file: <data_dir>/<msid>_data
    """
#
#--- read all msids and go through one by one
#
    msid_list = read_msids()

    for   msid in msid_list:
#
#--- read limit table for the msid
#
        try:
            l_list = ecf.set_limit_list(msid)
        except:
            l_list = []

        print "MSID: " + str(msid)

        update_data(msid, l_list)

#------------------------------------------------------------------------------------------------------
#-- update_mta_comp_database: updata database of mta computed msids                                  --
#------------------------------------------------------------------------------------------------------

def update_mta_comp_database():
    """
    updata database of mta computed msids
    input:  none but read from /data/mta4/Deriv/*fits files
    outpu:  updated data file: <data_dir>/<msid>_data
    """
#
#--- get a list of data fits file names
#
    infile = house_keeping + 'mta_comp_fits_files'
    data   = ecf.read_file_data(infile)

    for fits in data:
#
#--- hrc has 4 different cases (all data, hrc i, hrc s, and off). tail contain which one this one is
#--- if this is not hrc (or hrc all), tail = 2
#
        mc = re.search('hrc', fits)
        if mc is not None:
            atemp = re.split('_', fits)
            btemp = re.split('.fits', atemp[1])
            tail  =  btemp[0]
        else:
            tail  = 2

        [cols, tbdata] = ecf.read_fits_file(fits)

        time = []
        for ent in tbdata.field('time'):
            stime = float(ent)
#
#--- check whether the time is in dom 
#   
            if stime < 31536000:
                stime = ecf.dom_to_stime(float(ent))

            time.append(stime)

        for col in cols:
            col = col.lower()
#
#--- we need only *_avg columns
#
            mc = re.search('_avg', col)
            if mc is not None:

                vals = tbdata.field(col)
             
                ctime = []
                cvals = []
                for m in range(0, len(time)):
#
#--- skip the data value "nan" and dummy values (-999, -998, -99, 99, 998, 999)
#
                    if str(vals[m]) in  ['nan', 'NaN', 'NAN']:
                        continue

                    nval = float(vals[m])
                    if nval in [-999, -998, -99, 99, 998, 999]:
                        continue
                    else:
                        ctime.append(time[m])
                        cvals.append(nval)
    
                atemp = re.split('_', col)
                msid  = atemp[-2]

                if mcf.chkNumeric(tail):
                    oname = msid
                else:
                    oname = msid + '_' + tail
    
                print "MSID: " + str(oname)

                cmd = 'rm ' + data_dir + oname + '_data'
                os.system(cmd)
#
#--- read limit table for the msid
#
                l_list   = ecf.set_limit_list(msid)
                if len(l_list) == 0:
                    try:
                        l_list = mta_db[msid]
                    except:
                        l_list = []
    
                update_data(msid, l_list, dset = tail, time=ctime, vals=cvals)

#------------------------------------------------------------------------------------------------------
#-- update_data: update data for the given msid                                                      --
#------------------------------------------------------------------------------------------------------

def update_data(msid, l_list, dset = 1, time=[], vals=[]):
    """
    update data for the given msid
    input:  msid    --- msid
            l_list  --- a list of list of [<start time>, <stop time>, <yellow min>, <yellow max>, <red min>, <red max>]
            dset    --- indicate which data set we are handling. 1: main, 2: secondary, i, s, off: hrc sub category
            time    --- a list of time entry for secondary case
            vals    --- a list of msid values for secondary case
    output: data for msid updated (<data_dir>/<msid>_data
    """
#
#--- set which data periods we need to process the data; start from the one after the last one
#
    periods = set_data_periods(msid)

    tc = 0
    for tlist in periods:
        start = tlist[0]
        stop  = tlist[1]
#
#--- occasionally the data period accross the date of  limit changes.
#--- if that happens, devide the period into before and after the date
#--- lperiods has atmost two entries, but usually only one
#
        lperiods = set_limits_for_period(l_list, start, stop)

        if dset != 1:               #--- setting for mta comp case only
            kcnt = 0             
            dcnt = len(time)

        for limits in lperiods:

            tstart = limits[0]
            tstop  = limits[1]
            y_min  = limits[2]
            y_max  = limits[3]
            r_min  = limits[4]
            r_max  = limits[5]
#
#--- main trend case: need to extract data
#
            if dset == 1:
                sdata  = get_data(msid, tstart, tstop)
#
#--- secondary trend case: data are passed from the calling function
#
            else:
                sdata  = []
                for m in range(0, dcnt):
                    if (time[m] >= tstart) and (time[m] < tstop):
                        sdata.append(vals[m])
                    if time[m] >=tstop:
                        kcnt = m -1
                        break
#
#--- if the data is too small, just skip the period
#
            if len(sdata) < 5:
                continue
#
#--- compute statistics
#
            stat_results = compute_stats(sdata, y_min, y_max, r_min, r_max)
#
#--- special treatment for mta comp hrc values: it has i, s, or off suffix
#
            if mcf.chkNumeric(dset):
                oname = msid
            else:
                oname = msid + '_' + dset
#
#--- append data to the data file
#
            print_results(oname, start, stop, stat_results, y_min, y_max, r_min, r_max)


#------------------------------------------------------------------------------------------------------
#-- set_limits_for_period: set yellow/red upper/lower limits for the given period                   ---
#------------------------------------------------------------------------------------------------------

def set_limits_for_period(l_list, start, stop):
    """
    set yellow/red upper/lower limits for the given period
    if the limit range changes during the given data period, two limit lists will be returned
    input:  l_list  --- a list of lists of limit data: [lstart, lstop, y_min, y_max, r_min, r_max]
            start   --- the data start time in seconds from 1998.1.1
            stop    --- the data stop time in seconds from 1998.1.1
    output  limit_list  --- a list of list(s) of limits. it contains atmost two lists in the form of
                            [<start time>, <stop time>, <y_min>, <y_max>, <r_min>, <r_max>]
    """
    if len(l_list) == 0:
        limit_list = [[start, stop, -999, 999, -999, 999]]

    else:
        limit_list = []
        for k in range(0, len(l_list)):
    
            limit_p = l_list[k]
            lstart  = limit_p[0]
            lstop   = limit_p[1]
#
#--- find the period where start time is in the range
#
            if(start >= lstart) and (start < lstop):
                y_min = limit_p[2]
                y_max = limit_p[3]
                r_min = limit_p[4]
                r_max = limit_p[5]
#
#--- check whether limit range changed before ending data collection period. 
#--- if so, devide the period into two however, if the the data colleciton period passes 
#--- less than 5% of data colleciton period, ignore the change
#
                if (stop > lstop + 0.05 * (stop-start)) and (k < len(l_list) -1):
                    out = [start, lstop, y_min, y_max, r_min, r_max]
                    limit_list.append(out)
    
                    limit_p = l_list[k+1]
                    y_min = limit_p[2]
                    y_max = limit_p[3]
                    r_min = limit_p[4]
                    r_max = limit_p[5]
                    out = [lstop, stop, y_min, y_max, r_min, r_max]
                    limit_list.append(out)
    
                else:
                    out = [start, stop, y_min, y_max, r_min, r_max]
                    limit_list.append(out)
    
                break
    
        if len(limit_list) == 0:
            limit_list = [[start, stop, -999, 999, -999, 999]]
    
    return limit_list

#------------------------------------------------------------------------------------------------------
#-- get_data: extract data for the given data period                                                 --
#------------------------------------------------------------------------------------------------------

def get_data(msid, start, stop):
    """
    extract data for the given data period
    input:  msid    --- msid
            start   --- starting time in seconds from 1998.1.1
            stop    --- stopping time in seconds from 1998.1.1
    output: data    --- a list of msid values
    """
#
#--- extract data with dataseeker
#
    try:
        ecf.data_seeker(start, stop, msid)
        [col, tbdata] = ecf.read_fits_file('temp_out.fits')
        mcf.rm_file('temp_out.fits')
    except:
        return []

    time = tbdata.field('time')
#
#--- if the dataseeker's data is not filled for the given data period
#--- stop any farther data proccess
#
    if time[-1] < 0.95 * stop:
        data = []
    else:
        try:
            name = msid + '_avg'
            data = tbdata.field(name)
        except:
            data = []

    return data

#------------------------------------------------------------------------------------------------------
#-- compute_stats: compute basic statistics for the given data                                      ---
#------------------------------------------------------------------------------------------------------

def compute_stats(data, y_min, y_max, r_min, r_max):
    """
    compute basic statistics for the given data
    input:  data    --- data
            y_min   --- yellow lower limit
            y_max   --- yellow upper limit
            r_min   --- red lower limit
            r_max   --- red upper limit
    output: a list of stat results:
            cnt     --- number of the data points
            avg     --- mean
            med     --- median
            dmin    --- min
            dmax    --- max
            y_min_cnt   --- the number of times the data violoated the lower yellow limit
            y_max_cnt   --- the number of times the data violoated the upper yellow limit
            r_min_cnt   --- the number of times the data violoated the lower red limit
            r_max_cnt   --- the number of times the data violoated the upper red limit
    """
#
#--- remove out layers
#
    data.sort()
    dlen  = len(data)
    cut   = int(0.025 * dlen)
    ndata = data[cut:dlen-cut]
    if len(ndata) == 0:
        ndata = data

    darray = numpy.array(ndata)
#
#--- compute data statistics
#
    cnt  = len(data)
    avg  = ecf.round_up(numpy.mean(darray))
    med  = ecf.round_up(numpy.median(darray))
    std  = ecf.round_up(numpy.std(darray))
    dmin = ecf.round_up(min(ndata))
    dmax = ecf.round_up(max(ndata))
#
#--- fine the numbers of times the data violated limits
#--- if they is no limit (998, 999 etc), just use huge numbers as limit
#
    if r_min in [-999, -998, -99]:
        r_min = -1.0e12
    if y_min in [-999, -998, -99]:
        y_min = -1.0e12

    if r_max in [999, 998, 99]:
        r_max = 1.0e12
    if y_max in [999, 998, 99]:
        y_max = 1.0e12

    y_min_cnt = 0
    y_max_cnt = 0
    r_min_cnt = 0
    r_max_cnt = 0
    for k in range(0, cnt):

        if data[k] < r_min:
            r_min_cnt += 1

        elif data[k] < y_min:
            y_min_cnt += 1

        if data[k] > r_max:
            r_max_cnt += 1

        elif data[k] > y_max:
            y_max_cnt += 1

    return [cnt, avg, med, std, dmin, dmax, y_min_cnt, y_max_cnt, r_min_cnt, r_max_cnt]

#------------------------------------------------------------------------------------------------------
#-- print_results: append the stat results to the data file                                          --
#------------------------------------------------------------------------------------------------------

def print_results(msid, start, stop, stat_results, y_min, y_max, r_min, r_max):
    """
    append the stat results to the data file
    input:  msid    --- msid
            start   --- starting time in seconds from 1998.1.1
            stop    --- stopping time in seconds from 1998.1.1
            stat_results    --- a list of stat results
                    = [cnt, avg, med, dmin, dmax, y_min_cnt, y_max_cnt, r_min_cnt, r_max_cnt]
            y_min           --- yellow lower limit
            y_max           --- yellow upper limit
            r_min           --- red lower limit
            r_max           --- red upper limit
    output: <data_dir>/<msid>_data
    """

    [cnt, avg, med, std,  dmin, dmax, y_min_cnt, y_max_cnt, r_min_cnt, r_max_cnt] = stat_results
#
#--- append the new data to the data file
#
    line = str(start)   + '\t'
    line = line + str(stop)      + '\t'
    line = line + str(cnt)       + '\t'
    line = line + str(avg)       + '\t'
    line = line + str(med)       + '\t'
    line = line + str(std)       + '\t'
    line = line + str(dmin)      + '\t'
    line = line + str(dmax)      + '\t'
    line = line + str(y_min_cnt) + '\t'
    line = line + str(y_max_cnt) + '\t'
    line = line + str(r_min_cnt) + '\t'
    line = line + str(r_max_cnt) + '\t'
    line = line + str(y_min)     + '\t'
    line = line + str(y_max)     + '\t'
    line = line + str(r_min)     + '\t'
    line = line + str(r_max)     + '\n'

    dname = data_dir + msid.lower() + '_data'
    fo    = open(dname, 'a')
    fo.write(line)
    fo.close()

#------------------------------------------------------------------------------------------------------
#-- set_limit_list_old: read upper and lower yellow and red limits for each period-- replaced by the same name in ecf
#------------------------------------------------------------------------------------------------------

def set_limit_list_old(msid):
    """
    read upper and lower yellow and red limits for each period
    input:  msid    --- msid
    output: l_list  --- a list of list of [<start time>, <stop time>, <yellow min>, <yellow max>, <red min>, <red max>]
    """

    udict  = ecf.read_unit_list()
    tchk = 0
    try:
        unit = udict[msid.lower()]
        if unit.lower() == 'degc':
            tchk = 1
        elif unit.lower() == 'degf':
            tchk = 2
    except:
        pass

    l_list = gsr.read_glimmon(msid, tchk)

    if len(l_list) == 0:
        try:
            l_list = mta_db[msid]
        except:
            l_list = []

    return l_list

#------------------------------------------------------------------------------------------------------
#-- create_data_period_list: create a list of data collection time intervals                        ---
#------------------------------------------------------------------------------------------------------

def create_data_period_list():
    """
    create a list of data collection time intervals. the interval 
    is every month of 1-10, 10-20, 20-1 of the next month
    input:  none
    output: period  --- a list of lists of data collection time interval. time is in seconds from 1998.1.1
    
    """

    start = 47174399                    #--- 1999:182:00:00:00 (1999-07-01)
    stop  = ecf.find_current_stime()    #--- today's date in seconds from 1998.1.1

    today  = time.localtime()
    tyear  = today.tm_year
    tmonth = today.tm_mon
    tday   = today.tm_mday

    period = []
    for year in range(1999, tyear+1):
        for month in range(1, 13):
            if (year == 1999) and (month < 7):
                continue
            elif (year == tyear) and (month > tmonth):
                break

            d1 = time.mktime((year, month,  1, 0, 0, 0, 5, 1, 0)) - Ebase_t
            d2 = time.mktime((year, month, 10, 0, 0, 0, 5, 1, 0)) - Ebase_t
            d3 = time.mktime((year, month, 20, 0, 0, 0, 5, 1, 0)) - Ebase_t
#
#--- check whether the next month is in the next year
#
            nyear  = year
            nmonth = month + 1
            if nmonth > 12:
                nmonth = 1
                nyear += 1
            d4 = time.mktime((nyear, nmonth, 1, 0, 0, 0, 5, 1, 0)) - Ebase_t

            period.append([d1,d2])
            period.append([d2,d3])
            period.append([d3,d4])

    return period

#------------------------------------------------------------------------------------------------------
#-- set_data_periods: find unprocessed data periods                                                  --
#------------------------------------------------------------------------------------------------------

def set_data_periods(msid):
    """
    find unprocessed data periods
    input:  msid    --- msid
    output: periods --- a list of list of data collection interval (in seconds from 1998.1.1)
    """

    all_periods = create_data_period_list()

    dname = data_dir + msid + '_data'

    try:
        odata = ecf.read_file_data(dname)

        if len(odata) > 0:
            lent  = odata[-1]
            atemp = re.split('\s+', lent)
            lstop = float(atemp[1])
    
            periods = []
            for ltime in all_periods:
                if ltime[0] >= lstop:
                    periods.append(ltime)
        else:
            periods = all_periods
    except:
#
#--- if there is no data yet, start from beginning and also create the output file
#
        periods = all_periods
        fo  = open(dname, 'w')
        fo.close()

    if len(periods) == 0:
        periods = all_periods

    return periods

#------------------------------------------------------------------------------------------------------
#-- read_msids: create a list of all msids                                                           --
#------------------------------------------------------------------------------------------------------

def read_msids():
    """
    create a list of msids which can get from dataseeker
    input:  none but read from <house_keeping>/dataseeker_entry_list
    output: msid_list   --- a list of msids
    """
    dfile = house_keeping + 'mta_env_msid_list'
    data  = ecf.read_file_data(dfile)
    
    msid_list = []
    ulist     = []
    for ent in data:
        if ent[0] == '#':
            continue
        msid_list.append(ent)

    return msid_list


#-----------------------------------------------------------------------------------------
#-- TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST    ---
#-----------------------------------------------------------------------------------------

class TestFunctions(unittest.TestCase):
    """
    testing functions
    """

#------------------------------------------------------------
    
    def test_create_data_period_list(self):

        comp = [155088000.0, 155865600.0]
        out  = create_data_period_list()

        self.assertEquals(out[123], comp)

#------------------------------------------------------------

    def test_read_msids(self):

        comp = ['1dahacu', '1dahavo', '1dahhavo', '1de28avo', '1deicacu', '1den0avo']
        out  = read_msids()
        
        self.assertEquals(out[0:6], comp)

#------------------------------------------------------------

    def test_set_limit_list(self):

        msid   = '1crbt'
        l_list = set_limit_list_old(msid)
#
#--- list test
#
        comp = [119305230, 123774707, 136.15, 173.15, 131.15, 183.15]
        out  = l_list[1]
        self.assertEquals(out, comp)
#
#--- the data separated correctely
#

        start = 119059199               #--- 2001:283:00:00:00 (2001-10-10)
        stop  = 119923199               #--- 2001:293:00:00:00 (2001_10-20)
        out   = set_limits_for_period(l_list, start, stop)
        comp  = [[119059199, 119305230, 136.15, 173.15, 131.15, 373.15], [119305230, 119923199, 136.15, 173.15, 131.15, 183.15]]
        self.assertEquals(out, comp)

#------------------------------------------------------------

    def test_get_data(self):

        msid  = '1crbt'
        start = 155088000.0
        stop  = 155865600.0

        data = get_data(msid, start, stop)

        self.assertEquals(len(data), 2592)
        self.assertEquals(round(data[0],2), 145.22)
        self.assertEquals(round(data[1000],2), 145.22)

#------------------------------------------------------------
    
    def test_compute_stats(self):

        msid  = '1crbt'
        start = 155088000.0
        stop  = 155865600.0
        comp  = [2592, 145.86, 145.22, 1.04, 145.22, 147.61, 0, 0, 0, 0]

        l_list = ecf.set_limit_list(msid)
        out   = set_limits_for_period(l_list, start, stop)

        [start, stop,  y_min, y_max, r_min, r_max] = out[0]

        data = get_data(msid, start, stop)
        out = compute_stats(data, y_min, y_max, r_min, r_max)

        self.assertEquals(out, comp)


#-----------------------------------------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) > 1:
        chk = sys.argv[1]
    else:
        chk = 0
    if chk == 'test':
        del sys.argv[1:]
        unittest.main()
    else:
        run_update_envelop_database()
