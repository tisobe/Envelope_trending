#!/usr/bin/env /proj/sot/ska/bin/python

#########################################################################################################
#                                                                                                       #
#           update_sub_html_pages.py: creates html pages for different categories of msids              #
#                                                                                                       #
#               author: t. isobe (tisobe@cfa.harvard.edu)                                               #
#                                                                                                       #
#               last update: June 27, 2016                                                              #
#                                                                                                       #
#########################################################################################################

import os
import sys
import re
import string
import math
import numpy
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
    var   = atemp[1].strip()
    line  = atemp[0].strip()
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
import violation_estimate_data  as ved  #---- save violation estimated times in sqlite database v_table
#
#--- set a temporary file name
#
rtail  = int(time.time())
zspace = '/tmp/zspace' + str(rtail)

web_address = 'https://cxc.cfa.harvard.edu/mta_days/mta_envelope_trending/'

#----------------------------------------------------------------------------------
#-- create_sub_html: creates html pages for different categories of msids        --
#----------------------------------------------------------------------------------

def create_sub_html():
    """
    creates html pages for different categories of msids
    input:  none but read from <house_keeping>/sub_html_list_all
    output: <web_address>/Htmls/<category>_main.html
    """
#
#--- get today's date in fractional year
#
    sec1998 = ecf.find_current_stime()
    ytime   = ecf.stime_to_frac_year(sec1998)
#
#--- create dictionary of unit and dictionary of descriptions for msid
#
    [udict, ddict] = ecf.read_unit_list()

    lfile = house_keeping + 'sub_html_list_all'
    data  = ecf.read_file_data(lfile)
#
#--- create indivisual html pages under each category
#
    for ent in data:
        atemp = re.split('::', ent)
        catg  = atemp[0]
        msids = re.split(':', atemp[1])

        create_html(catg, msids, ytime, udict, ddict)


#----------------------------------------------------------------------------------
#-- create_html: create a html page for category <catg>                         ---
#----------------------------------------------------------------------------------

def create_html(catg, h_list, ytime, udict, ddict):
    """
    create a html page for category <catg>
    input:  catg    --- category of the msids
            h_list  --- a list of msids of the category
            ytime   --- current time
            udict   --- a dictionary of unit: <msid> <---> <unit>
            ddict   --- a dictionary of description: <msid> <---> <description>
    output: <catg>_main.html
    """

    line = '<!DOCTYPE html>\n<html>\n<head>\n\t<title>Envelope Trending  Plots: ' + catg.upper() + '</title>\n'
    line = line + '</head>\n<body style="width:95%;margin-left:10px; margin-right;10px;background-color:#FAEBD7;'
    line = line + 'font-family:Georgia, "Times New Roman", Times, serif">\n\n'
    line = line + '<a href="' + web_address + 'envelope_main.html" '
    line = line + 'style="float:right;padding-right:50px;font-size:120%"><b>Back to Top</b></a>\n'

    line = line + '<h3>' + catg.upper() + '</h3>\n'

    line = line + '<div style="text-align:center">\n\n'
    line = line + '<table border=1 cellspacing=2 style="margin-left:auto;margin-right:auto;text-align:center;">\n'
    line = line + '<th>MSID</th><th>Unit</th><th>Description</th><th>Limit Violation</th>\n'
#
#--- create a table with one row for each msid
#
    for ent in h_list:
        atemp = re.split('_plot', ent)
        msid  = atemp[0]
#
#--- check whether plot html file exist
#
        if check_plot_existance(msid, pchk=0) == False:
            continue
#
#--- hrc has 4 different entries (all, hrc i, hrc s, and off cases) but share the same unit and descriptions
#
        msidp = msid.replace('_i', '')
        msidp = msidp.replace('_s', '')
        msidp = msidp.replace('_off', '')
        try:
            unit  = udict[msidp]
            discp = ddict[msidp]
#
#--- convert all F and most C temperature to K, exception: if the uint is "C", leave as it is
#
            if unit == 'DEGF':
                unit = 'K'
            elif unit == 'DEGC':
                if msid[:-2].lower() != 'tc':
                    unit = 'K'
        except:
            unit  = '---'
            discp = msid
#
#--- check violation status; if it is 'na', there is no data
#
        vout  = ved.read_v_estimate(msid)

        [vnote, color] = create_status(msid, ytime)

        if check_plot_existance(msid) == False:
            line = line + '<tr>\n<th>' + msid +'</a></th>'
            line = line + '<td>' + unit +'</td><td>' + discp + '</td>'
            line = line + '<th style="font-size:90%;color:#B22222;padding-left:10px;padding-right:10px">No Data</th>\n</tr>\n'
        else:
            line = line + '<tr>\n<th><a href="'+ web_address  + 'Htmls/' + ent + '">' + msid +'</a></th>'
            line = line + '<td>' + unit +'</td><td>' + discp + '</td>'
            line = line + '<th style="font-size:90%;color:' + color + ';padding-left:10px;padding-right:10px">' + vnote + '</th>\n</tr>\n'

    line = line + '</table>\n'

    line = line + '</div>\n'

    line = line + '</body>\n</html>\n'
#
#--- category html has the tail of "_main.html"
#
    name = web_dir + catg.lower() + '_main.html'
    fo   = open(name, 'w')
    fo.write(line)
    fo.close()

#----------------------------------------------------------------------------------
#-- check_plot_existance: check whether a html file exist for the given msid and/or interactive plot exists
#----------------------------------------------------------------------------------

def check_plot_existance(msid, pchk = 1):
    """
    check whether a html file exist for the given msid and/or interactive plot exists
    input:  msid    --- msid
            pchk    --- if 1, check whether the interactive plot is created: default: 1
    output: True/False
    """

    cfile = web_dir + msid + '_plot.html'
    try:
        f     = open(cfile, 'r')
        test  = f.read()
        f.close()

        if pchk == 0:
            return True
    except:
        return False

    mc    = re.search('No Data\/No Plot', test)
    if mc is not None:
        return False
    else:
        return True

#----------------------------------------------------------------------------------
#-- create_status: check the status of the msid and return an appropriate comment -
#----------------------------------------------------------------------------------

def create_status(msid, ytime):
    """
    check the status of the msid and return an appropriate comment
    input:  msid    --- msid
            ytime   --- corrent time
    output: [<comment>, <font color>]
    """
#
#--- read violation status of the msid
#
    out   = ved.read_v_estimate(msid)
#
#--- if there is no data, tell so and return
#
    if len(out) < 4:
        return ["No Violation Check", 'black']
#
#--- if all entries are "0", no violation
#
    chk = 0
    for k in range(0, 4):
        if out[k] != 0.0:
            chk =1
            break

    if chk == 0:
        return ["No Violation", 'black']
#
#--- if there are violation, create the description and choose a color for it
#
    else:
        line  = ''
        line0 = ''
        line1 = ''
        line2 = ''
        line3 = ''
        color = 'black'
        if out[0] != 0:
            if out[0] < ytime:
                line0 = 'Already Lower Yellow Violation'
                color = '#FF8C00'
            else:
                line0 = "Yellow Lower Violation: " + clean_the_input(out[0])
                color = '#FF8C00'

        if out[1] != 0:
            if out[1] < ytime:
                line1 = 'Already Upper Yellow Violation'
                color = '#FF8C00'
            else:
                line1 = "Yellow Upper Violation: " + clean_the_input(out[1])
                color = '#FF8C00'

        if out[2] != 0:
            if out[2] < ytime:
                line2 = 'Already Lower Red Violation'
                color = 'red'
            else:
                line2 = "Red Lower Violation: " + clean_the_input(out[2])
                color = 'red'

        if out[3] != 0:
            if out[3] < ytime:
                line3 = 'Already Upper Red Violation'
                color = 'red'
            else:
                line3 = "Red Upper Violation: " + clean_the_input(out[3])
                color = 'red'

        if line2 != '':
            line =  line2
            color = 'red'
        else:
            if line0 != '':
                line = line0
                color = '#FF8C00'


        if line3 != '':
            if line != '':
                line = line + '<br />' + line3
                color = 'red'
            else:
                line = line3
                color = 'red'
        else:
            if line1 != '':
                if line != '':
                    line = line + '<br />' + line1
                    if color == 'black':
                        color = '#FF8C00'
                else:
                    line = line1
                    color = '#FF8C00'


        return [line, color]

#----------------------------------------------------------------------------------
#-- clean_the_input: check the input is numeric and if so, round to two decimal   -
#----------------------------------------------------------------------------------

def clean_the_input(line):
    """
    check the input is numeric and if so, round to two decimal
    input:  line    --- input quantity
    output: line    --- if it is a numeric value, a value of two decimal, 
                        otherwise, just return the value as it was
    """

    if mcf.chkNumeric(line):
        line = str(ecf.round_up(float(line)))

    return line
        

#---------------------------------------------------------

if __name__ == "__main__":

    create_sub_html()
