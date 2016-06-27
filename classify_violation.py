#!/usr/bin/env /proj/sot/ska/bin/python

#####################################################################################################
#                                                                                                   #
#       classify_violation.py: create a top html page with violation tables                         #
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
import violation_estimate_data  as ved  #---- save violation estimated times in sqlite database v_table
#
#--- set a temporary file name
#
rtail  = int(time.time())
zspace = '/tmp/zspace' + str(rtail)

na = 'na'

web_address = ' https://cxc.cfa.harvard.edu/mta_days/mta_envelope_trending/'
#
#-----------------------------------------------------------------------------------
#-- create_violation_htmls: create a top html page with violation tables          --
#-----------------------------------------------------------------------------------

def create_violation_htmls():
    """
    create a top html page with violation tables
    input:  none but use <house_keeping>/envelope_main.html tamplate
    output: <web_top_dir>/envelope_main.html
    """

    [yl_in, yl_will, yt_in, yt_will, rl_in, rl_will, rt_in, rt_will, yl_list, yt_list] = classify_violation()

    plot_output            = select_example_trend()

    yellow_lower_violation = make_table(yl_in, 'Lower Yellow Limit Violations', 'orange')
    yellow_upper_violation = make_table(yt_in, 'Upper Yellow Limit Violations', 'orange')

    red_lower_violation    = make_table(rl_in, 'Lower Red Limit Violations', 'red')
    red_upper_violation    = make_table(rt_in, 'Upper Red Limit Violations', 'red')

    yellow_lower_future    = make_table_with_year(yl_will, yl_list, 'Lower Yellow Limit', 'orange')
    yellow_upper_future    = make_table_with_year(yt_will, yt_list, 'Upper Yellow Limit', 'orange')
#
#--- read the top page template
#
    template = house_keeping + 'envelope_main.html'
    f        = open(template, 'r')
    data     = f.read()
    f.close()
#
#--- insert the example plot, potential future violation table, etc
#
    data     = data.replace('#PLOT#', plot_output)

    data     = data.replace('#YLLIM#', yellow_lower_violation)

    if (yellow_lower_violation == '') and (yellow_upper_violation == ''):
        yellow_upper_violation = 'No Yellow Violation'
    data     = data.replace('#YULIM#', yellow_upper_violation)

    data     = data.replace('#RLLIM#', red_lower_violation)

    if (red_lower_violation == '') and (red_upper_violation == ''):
        red_upper_violation = 'No Red Violation'
    data     = data.replace('#RULIM#', red_upper_violation)

    data     = data.replace('#YLFUT#', yellow_lower_future) 

    if (yellow_lower_future == '') and (yellow_upper_future == ''):
        yellow_upper_future = 'No Violation Expected'
    data     = data.replace('#YUFUT#', yellow_upper_future) 

    today    = strftime("%a, %d %b %Y %H:%M:%S", gmtime())
    data     = data.replace('#UPDATE#', today)
#
#--- print out the top page
#
    ofile    = web_top_dir + 'envelope_main.html'
    fo       = open(ofile, 'w')
    fo.write(data)
    fo.close()


#-----------------------------------------------------------------------------------
#-- make_table: creata a html table for a give list of sub html page              --
#-----------------------------------------------------------------------------------

def make_table(hlist, title, color):
    """
    creata a html table for a give list of sub html page
    input:  hlist   --- a list of sub html page names
    output: line    --- a line contain html descriptions of a table
    """
    if len(hlist) == 0:
        line = ''
    else:
        line  = '<table border=1 cellpadding=5 style="margin-left:auto;margin-right:auto">\n'
        line  = line + '<tr><th colspan=5 style="color:' + color +'">' + title + '</th></tr>\n<tr>'
        ecnt  = 0
        for msid in hlist:
            line = line + '<td><a href="' + web_address + 'Htmls/' + msid + '_plot.html">' + msid + '</a></td>\n'
            ecnt += 1
            if ecnt >= 5:
                line = line + '</tr>\n<tr>\n'
                ecnt = 0
    
        if (ecnt > 0) and (ecnt < 4):
            for k in range(ecnt, 5):
                line = line + '<td>&#160;</td>'
    
        line  = line + '</tr></table>\n'

    return line


#-----------------------------------------------------------------------------------
#-- make_table_with_year: creata a html table for a give list of sub html page with year of violation 
#-----------------------------------------------------------------------------------

def make_table_with_year(hlist, y_list, title, color):
    """
    creata a html table for a give list of sub html page with year of violation
    input:  hlist   --- a list of sub html page names
    output: line    --- a line contain html descriptions of a table
    """
    if len(hlist) == 0:
        line = ''
    else:
        line  = '<table border=1 cellpadding=5 style="margin-left:auto;margin-right:auto">\n'
        line  = line + '<tr><th style="color:' + color +'">' + title + '</th><th>Predicted Year</th></tr>\n<tr>'
        ecnt  = 0
        for k in range(0, len(hlist)):
            msid = hlist[k]
            year = y_list[k]
            line = line + '<td><a href="' + web_address + 'Htmls/' + msid + '_plot.html">' + msid + '</a></td>\n'
            line = line + '<td>' + str(ecf.round_up(year)) + '</td></tr>\n'
    
        line  = line + '</table>\n'

    return line


#-----------------------------------------------------------------------------------
#-- classify_violation: classify the types of violation                           --
#-----------------------------------------------------------------------------------

def classify_violation():
    """
    classify the types of violation
    input:  none but read from sqlite database
    output: yl_in   : a list of msid which are already in the lower yellow violation
            yl_will : a list of msid which will be in the lower yellow violation
            yt_in   : a list of msid which are already in the top yellow violation
            yt_will : a list of msid which will be in the lower yellow violation
            rl_in   : a list of msid which are already in the lower red violation
            rl_will : a list of msid which will be in the lower red violation (not used)
            rt_in   : a list of msid which are already in the top red violation
            rt_will : a list of msid which will be in the top red violation (not used)
            yl_list : a list of low yellow violation estimated time correspoinding to yl_will
            yt_list : a list of top yellow violation estimated time correspoinding to yt_will
    """

    [v_list, vdict] = find_violation()
    yl_in   = []
    yl_will = []
    yl_list = []
    yt_in   = []
    yt_will = []
    yt_list = []
    rl_in   = []
    rl_will = []
    rt_in   = []
    rt_will = []
    for msid in v_list:
        [yl, yt, rl, rt] = vdict[msid]
        if rl == -1:
            rl_in.append(msid)
        elif rl != 0:
            rl_will.append(msid)
        elif yl == -1:
            yl_in.append(msid)
        elif yl != 0:
            yl_will.append(msid)
            yl_list.append(yl)

        if rt == -1:
            rt_in.append(msid)
        elif rt != 0:
            rt_will.append(msid)
        elif yt == -1:
            yt_in.append(msid)
        elif yt != 0:
            yt_will.append(msid)
            yt_list.append(yt)

    return [yl_in, yl_will, yt_in, yt_will, rl_in, rl_will, rt_in, rt_will, yl_list, yt_list]

#-----------------------------------------------------------------------------------
#-- find_violation: find msids which violate yellow and/or red upper and lower limits
#-----------------------------------------------------------------------------------

def find_violation():
    """
    find msids which violate yellow and/or red upper and lower limits
    input:  none but read from sqlite database (<house_keeping>/v_table.sqlite3
    output: v_list  --- a list of msids
            vdict   --- a dictionary of msids<--->[yl_lim, yt_lim, rl_lim, rt_lim]
    """
#
#--- find which msids have the sub html page cared
#
    cmd = 'ls ' + web_dir + '*_plot.html > ' + zspace
    os.system(cmd)

    data  = ecf.read_file_data(zspace, 1)

    v_list = []
    vdict  = {}
    for ent in data:
        atemp = re.split('\/', ent)
        btemp = re.split('_plot', atemp[-1])
        msid  = btemp[0]
#
#--- check the violation status of the msid from the database
#
        out   = ved.read_v_estimate(msid)
        chk   = 0
        for test in out:
            if (test != 0) or (test != na):
                chk = 1
                break
        if  chk > 0:
            v_list.append(msid)
            vdict[msid] = out

    return [v_list, vdict]

#-----------------------------------------------------------------------------------
#-- select_example_trend: select one plot as an example for the front page        --
#-----------------------------------------------------------------------------------

def select_example_trend():
    """
    select one plot as an example for the front page
    input:  none but read from the <web_dir>/Futre directory
    ouput:  cont    --- plot in a html formt
    """
#
#--- <web_dir>/Future contains file with html formated plot output 
#--- of those with future violation potentials
#
    cmd  = 'ls ' + web_dir + 'Future/* > ' + zspace
    os.system(cmd)
#
#--- choose one of the plot using random #
#
    data = ecf.read_file_data(zspace, 1)
    dlen = len(data)

    if dlen > 0:
        pos  = int(dlen * random.random())
        f    = open(data[pos], 'r')
        cont = f.read()
        f.close()
    else:
        cont = ''

    return cont

#-----------------------------------------------------------------------------------------
#-- TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST    ---
#-----------------------------------------------------------------------------------------

class TestFunctions(unittest.TestCase):
    """
    testing functions
    """
#------------------------------------------------------------

    def test_find_violation(self):

        [v_list, vdict] = find_violation()

#        for msid in v_list:
#            print msid  + '<-->' + str(vdict[msid])

#------------------------------------------------------------

    def test_classify_violation(self):

        [yl_in, yl_will, yt_in, yt_will, rl_in, rl_will, rt_in, rt_will, yl_list, yt_list] = classify_violation()
        print 'yl_in:   ' + str(len(yl_in))
        print 'yl_will: ' + str(len(yl_will))
        print 'rl_in:   ' + str(len(rl_in))
        print 'rl_will: ' + str(len(rl_will))

        print 'yt_in:   ' + str(len(yt_in))
        print 'yt_will: ' + str(len(yt_will))
        print 'rt_in:   ' + str(len(rt_in))
        print 'rt_will: ' + str(len(rt_will))

        for k in range(0, len(yl_will)):
            print yl_will[k] + ':  ' + str(round(yl_list[k], 2))

#-----------------------------------------------------------------------------------

if __name__ == "__main__":

    test = 0
    if len(sys.argv) > 1:
        test = sys.argv[1]
    else:
        create_violation_htmls()
    if test == 'test':
        unittest.main()
    else:
        create_violation_htmls()

