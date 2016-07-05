#!/usr/bin/env /proj/sot/ska/bin/python

###########################################################################################################
#                                                                                                         #
#       create_html_page.py: create indivisual html pages for all msids in database                       #
#                                                                                                         #
#           author: t. isobe (tisobe@cfa.harvard.edu)                                                     #
#                                                                                                         #
#           last update: Jun 28, 2016                                                                     #
#                                                                                                         #
###########################################################################################################

import sys
import os
import string
import re
import getpass
import fnmatch
import numpy
import getopt
import os.path
import time
#
#--- interactive plotting module
#
import mpld3
from mpld3 import plugins, utils
#
#--- pylab plotting routine related modules
#
import matplotlib as mpl

if __name__ == '__main__':

    mpl.use('Agg')
#
#--- read argv
#
try:
    option, remainder = getopt.getopt(sys.argv[1:],'t',['test'])
except getopt.GetoptError as err:
     print str(err)
     sys.exit(2)

path = '/data/mta/Script/Envelope_trending/house_keeping/dir_list'

f    = open(path, 'r')
data = [line.strip() for line in f.readlines()]
f.close()

for ent in data:
    atemp = re.split(':', ent)
    var  = atemp[1].strip()
    line = atemp[0].strip()
    exec "%s = %s" %(var, line)

sys.path.append(mta_dir)
sys.path.append(bin_dir)

import convertTimeFormat        as tcnv #---- converTimeFormat contains MTA time conversion routines
import mta_common_functions     as mtac #---- mta common functions
import envelope_common_function as ecf  #---- collection of functions used in envelope fitting
import glimmon_sql_read         as gsr  #---- glimmon database reading
import violation_estimate_data  as ved  #---- save violation estimated times in sqlite database v_table
import find_moving_average      as fma  #---- moving average 
import find_moving_average_bk   as fmab #---- moving average (backword fitting version)
import robust_linear            as rfit #---- robust fit rountine
#
#--- set a temporary file name
#
rtail  = int(time.time())
zspace = '/tmp/zspace' + str(rtail)
#
#--- other settings
#
na     = 'na'
#
#--- read category data
#
cfile         = house_keeping + 'sub_html_list_all'
category_list = ecf.read_file_data(cfile)
#
#--- set several values used in the plots
#
color_table  = ['red', 'blue', 'green', 'lime']
marker_table = ['s',   '*',    '^',     'o']
marker_size  = [50,    80,     70,      50]

css = """
    body{
        width:600px;
        height:300px;
        background-color:#FAEBD7;
        ;font-family:Georgia, "Times New Roman", Times, serif;
    }
    p{
        text-align:center;
    }
"""
web_address = 'https://cxc.cfa.harvard.edu/mta_days/mta_envelope_trending/'

#--------------------------------------------------------------------------------------------------------
#-- create_html_page: create indivisual html pages for all msids in database                           --
#--------------------------------------------------------------------------------------------------------

def create_html_page():
    """
    create indivisual html pages for all msids in database
    input:  none
    output: <web_dir>/<msid>_plot.html
    """
#
#--- clean out future estimate direcotry
#
    cmd = 'rm -rf ' + web_dir + 'Future/* 2>/dev/null'
    os.system(cmd)
#
#---  get dictionaries of msid<-->unit and msid<-->description
#
    [udict, ddict] = ecf.read_unit_list()
#
#--- get the list of the names of the data files
#
    cmd = 'ls ' + data_dir + '*_data > ' + zspace
    os.system(cmd)

    data = ecf.read_file_data(zspace, 1)
    for ent in data:
        atemp = re.split('\/', ent)
        btemp = re.split('_data', atemp[-1])
        msid  = btemp[0]

#    for msid in ['1dactbt']:               #--- test test test 
#    for msid in ['2detart_off']:               #--- test test test 
#    for msid in ["cpa1pwr", "pftankop"]:               #--- test test test 

        print 'Processing: ' + msid

        try: 
            unit    = udict[msid]
            descrip = ddict[msid]
        except:
            unit    = ''
            descrip = ''

        #try:
#
#--- create an interactive plot
#
        pout = plot_interactive_trend(msid, unit)
#
#--- if there is not enough data, clean out the limit violation database
#
        if pout == False:
            vtdata = [-999, -999, -999, -999]
            ved.incert_data(msid, vtdata)
  
            print "No plot for : " + msid + ' (data points < 10)'
#
#--- add the plot to the html page
#
        create_plot_html_page(msid, descrip, pout)

        #except:
        #    print "No plot for : " + msid + ' (failed create a plot)'

#--------------------------------------------------------------------------------------------------------
#-- plot_interactive_trend: create interactive trend plot                                             ---
#--------------------------------------------------------------------------------------------------------

def plot_interactive_trend(msid, unit):
    """
    create interactive trend plot
    input:  msid    --- msid
            unit    --- unit of msid
    output: pout    --- plot in html format
            <web_dir>/Future/<msid>_<loc>   --- plots in html format saved in the directory 
                                                if it may violate the limit in future loc: low or top
    """
#
#--- read data
#
    pdata    = read_data(msid)

    if pdata == na:
        print msid + ': empty data file'
        return na

    if len(pdata[0]) < 10:
        return False
#
#--- set the x plotting range
#
    xmin  = 1999
    xmax  = ecf.current_time() + 1
    xmax  = "%4.1f" % round(xmax, 1)
    xmax  = float(xmax)

    xdiff = xmax - xmin
    xpos  = xmin + 0.05 * xdiff
#
#--- compute predict trends
#
    [tlim, tmax, min_a, min_b, max_a, max_b, xcent, y_avg,  y_min, y_max] = predict_trend(pdata, xmin, xmax)
#
#--- set y plotting range
#
    [ymin, ymax] = set_y_range(pdata, y_min, y_max, msid)
    ydiff = ymax - ymin
    ypos  = ymax - 0.1 * ydiff
#
#--- create a limit table for this msid
#
    create_limit_table(msid, unit, xmin, xmax)
#
#--- hrc has 4 different categories (all, hrc i, hrc s, off); use the same limit range
#
    pmsid  =  msid.replace('_i^',   '')
    pmsid  = pmsid.replace('_s^',   '')
    pmsid  = pmsid.replace('_off^', '')

    l_list = ecf.set_limit_list(pmsid)

    l_len  = len(l_list)
    if l_len > 0:

        [trb_save, rb1_save, rb2_save, tyb_save, yb1_save, yb2_save, tyt_save, \
         yt1_save, yt2_save, trt_save, rt1_save, rt2_save] = set_warning_area(l_list, xmin, xmax, ymin, ymax)
#
#--- create violation notification
#
    if l_len == 0:
        vtdata = [0, 0, 0, 0]
        ved.incert_data(msid, vtdata)
        pchk_l = 0
        pchk_u = 0
        gchk   = 0
    elif xmax - tmax > 3.0: 
        vtdata = [0, 0, 0, 0]
        ved.incert_data(msid, vtdata)
        pchk_l = 0
        pchk_u = 0
        gchk   = -1 
    elif (abs(min_b) == 999)  or (abs(max_b) == 999):
        vtdata = [0, 0, 0, 0]
        ved.incert_data(msid, vtdata)
        pchk_l = 0
        pchk_u = 0
        gchk   = 0
    else:
        [wline, wline2, pchk_l, pchk_u] = create_violation_notification(msid, pdata, min_a, min_b, max_a, max_b, tmax)
        gchk  = 1
#
#--- readjust y plotting range
#
    if pchk_l > 0:
        if ymin  > yb2_save[-1]:
            ymin = yb2_save[-1] - abs(ymin - yb2_save[-1])
    if pchk_u > 0:
        if ymax  < yt1_save[-1]:
            ymax = yt1_save[-1] + abs(ymax - yt1_save[-1])
#
#--- open and set plotting surface
#
    plt.close('all')

    fig, ax = plt.subplots(1, figsize=(8,6))

    props = font_manager.FontProperties(size=14)
    mpl.rcParams['font.size']   = 14
    mpl.rcParams['font.weight'] = 'bold'
#
#--- set plotting axes
#
    ax.set_xlim(xmin, xmax)
    ax.set_ylim(ymin, ymax)
    ax.set_xlabel('Time (year)')

    if unit != '':
        if unit in ('DEGF', 'DEGC'):
            unit = 'K'
        uline = msid + ' (' + unit + ')'
    else:
        uline = msid

    ax.yaxis.labelpad = 30 
    ax.set_ylabel(uline)
#
#--- shade limit areas
#

    if l_len > 0:

        if len(trb_save) > 0:
            ax.fill_between(trb_save, rb1_save, rb2_save, facecolor='red',    alpha=0.2, interpolate=True)

        if len(tyb_save) > 0:
            ax.fill_between(tyb_save, yb1_save, yb2_save, facecolor='yellow', alpha=0.2, interpolate=True)

        if len(tyt_save) > 0:
            ax.fill_between(tyt_save, yt1_save, yt2_save, facecolor='yellow', alpha=0.2, interpolate=True)

        if len(trt_save) > 0:
            ax.fill_between(trt_save, rt1_save, rt2_save, facecolor='red',    alpha=0.2, interpolate=True)
#
#--- moving average
#
    try:
        ax.fill_between(xcent, y_min, y_max, facecolor='#00FFFF', alpha=0.3, interpolate=True)
    except:
        pass
#
#--- plot a future possible envelope
#
    if gchk > 0:
        pbegin = min_a + min_b * tlim
        pend   = min_a + min_b * xmax
        ax.plot([tlim, xmax], [pbegin, pend], color='green', lw=4, linestyle='dashed')

        pbegin = max_a + max_b * tlim
        pend   = max_a + max_b * xmax
        ax.plot([tlim, xmax], [pbegin, pend], color='green', lw=4, linestyle='dashed')

        if wline != '':
            plt.text(xpos, ypos, wline, color='red')

        if wline2 != '':
            ypos = ymax -0.15 * ydiff
            plt.text(xpos, ypos, wline2, color='red')
    elif gchk < 0:
        plt.text(xpos, ypos, 'More than the last 2 years of data are missing (no violation check)', color='red')
#
#---- trending plots
#
    points = ax.scatter(pdata[0], pdata[5], color=pdata[17], marker='o', s=80 ,lw=0)
#
#--- pop up page are created here
#
    labels = create_label_html(pdata[1:17], msid, unit)
#
#--- link the popup page to the plot
#
    plugins.connect(fig, mpld3.plugins.PointHTMLTooltip(points, labels, css=css, voffset=20, hoffset=-50)) 
#
#--- set the size of plot
#
    fig.set_size_inches(11.0, 8.0)
    fig.tight_layout()
#
#--- convert the plot into html format
#
    pout =  mpld3.fig_to_html(fig)
#
#--- save the trend plot separately if the future violation is predicted
#
    if pchk_l > 0:
        save_plot_html(msid, fig, 'low')

    if pchk_u > 0:
        save_plot_html(msid, fig, 'top')

    plt.close('all')
#
#--- return plot in html format
#
    return pout

#----------------------------------------------------------------------------------
#-- save_plot_html: save a html formated plot in a file                          --
#----------------------------------------------------------------------------------

def save_plot_html(msid, fig, tail):
    """
    save a html formated plot in a file
    input:  msid    --- msid
            fig     --- matplot format plot information
            tail    --- sufix to put on the file name
    output: oname   --- a file saving the plot: <web_dir>/Future/<msid>_<tail>
    """

    fig.set_size_inches(8.0, 5.8)
    fig.tight_layout()
    sout =  mpld3.fig_to_html(fig)

    oname = web_dir + 'Future/' + msid + '_' + tail
    fo    = open(oname, 'w')
    fo.write(sout)
    fo.close()

#----------------------------------------------------------------------------------
#-- create_violation_notification: check violation and create notification       --
#----------------------------------------------------------------------------------

def create_violation_notification(msid, pdata, min_a, min_b, max_a, max_b, tmax):
    """
    check violation and create notification
    input:  msid    --- msid
            pdata   --- data set (see "read_data" for details)
            min_a   --- intercept value of the lower envelope prediction
            min_b   --- slope value of the lower envelope prediction
            max_a   --- intercept value of the upper envelope prediction
            max_b   --- slope value of the upper envelope prediction
            tmax    --- prediction ending point in time
    output: line    --- lower violation description (can be empty)
            line2   --- upper violation description (can be empty0
            pchk_l  --- indicator of whether there is lower violation (if 1)
            pchk_u  --- indicator of whether there is upper violation (if 1)
    """
#
#--- predict violation
#
    line   = ''
    line2  = ''
    yl_time = 0.0
    yt_time = 0.0
    rl_time = 0.0
    rt_time = 0.0
    pchk_l  = 0
    pchk_u  = 0
#
#--- check lower violations
#
    vlimit = pdata[15][-1]
    if vlimit not in ['-999', '-998', '998', '999']:
        vtime1 = predict_violation(min_a, min_b, tmax, vlimit, side = 0)
        if vtime1 == tmax:
            line = 'The data are aready in Red Lower Violation'
            rl_time = -1.0
        else:
            vlimit = pdata[13][-1]
            vtime2 = predict_violation(min_a, min_b, tmax, vlimit, side = 0)
    
            if vtime2 == tmax:
                line = 'The data are aready in Yellow Lower Violation'
                yl_time = -1.0
    
            elif (vtime2 > 0) and (vtime2 < tmax + 5):
                line   = 'The data may violate the lower yellow limit at Year: ' + str(ecf.round_up(vtime2))
                yl_time = vtime2
                pchk_l  = 1
#
#--- check upper violations
#
    vlimit = pdata[16][-1]
    if vlimit not in ['-999', '-998', '998', '999']:
        vtime1 = predict_violation(min_a, min_b, tmax, vlimit, side = 1)
        if vtime1 == tmax:
            if line == '':
                line  = 'The data are aready in Red Upper Violation'
                line2 = ''
            else:
                line2 = 'The data are aready in Red Upper Violation'
    
            rt_time = -1.0
        else:
            vlimit = pdata[14][-1]
            vtime2 = predict_violation(max_a, max_b, tmax, vlimit, side = 1)
            if (vtime2 > 0) and (vtime2 < tmax + 5):
                if line == '':
                    if vtime2 == tmax:
                        line = 'The data are aready in Yellow Upper Violation'
                        yt_time = -1.0
                    else:
                        line   = 'The data may violate the upper yellow limit at Year: ' + str(ecf.round_up(vtime2))
                        line2  = ''
                        yt_time = vtime2
                        pchk_u  = 1
                else:
                    if vtime2 == tmax:
                        line2 = 'The data are aready in Yellow Upper Violation'
                        yt_time = -1.0
                    else:
                        line2  = 'The data may violate the upper yellow limit  at Year: ' + str(ecf.round_up(vtime2))
                        yt_time = vtime2
                        pchk_u  = 1
#
#-- update violation time estimate database
#
    vtdata = [yl_time, yt_time, rl_time, rt_time]
    ved.incert_data(msid, vtdata)

    return [line, line2, pchk_l, pchk_u]

#----------------------------------------------------------------------------------
#-- create_plot_html_page: create a html page to display the trend plot          --
#----------------------------------------------------------------------------------

def create_plot_html_page(msid, descrip, pout):
    """
    create a html page to display the trend plot
    input:  msid    --- msid
            descrip --- description of the msid
            pout    --- plot in html format
    output: plot <web_dir>/<msid>_plot.html
    """
#
#--- read javascript file
#
    jfile   = house_keeping + 'java_script_deposit'
    f       = open(jfile, 'r')
    jscript = f.read()
    f.close()

    #file_name = msid + '_limit_table'
    file_name = './Limit_table/' + msid + '_limit_table.html'
#
#--- start creating html page
#
    out = '<!DOCTYPE html>\n<html>\n<head>\n\t<title>Envelope Trending  Plots: ' + msid.upper() + '</title>\n'
    out = out + jscript + '\n'
    out = out + '<style>\n'
    out = out + 'body{width: 600px; height300px; background-color:#FAEBD7;\n'
    out = out + 'font-family:Georgia, "Times New Roman", Times, serif;}\n'
    out = out + '</style>\n'

    out = out + '</head>\n<body style="width:95%;margin-left:10px; margin-right;10px;background-color:#FAEBD7;'
    out = out + 'font-family:Georgia, "Times New Roman", Times, serif">\n\n'
    out = out + '<a href="' + web_address + 'envelope_main.html" '
    out = out + 'style="float:right;padding-right:50px;font-size:120%"><b>Back to Top</b></a>\n'

    if descrip == '':
        out = out + '<h2>' + msid.upper()  + '</h2>'
    else:
        out = out + '<h2>' + msid.upper() + ' (' + descrip.upper() + ')</h2>' 

    out = out + '<div style="paddng-top:10px"><h3>'
    out = out + 'Open <a href="javascript:popitup(\'' + file_name + '\')" style="text-align:right">Limit Table</a>.'
    out = out + '</h3>\n'
#
#--- add the interactive plot here
#
    if (pout == False) or (str(pout) == 'na'):
        out = out + '<h3 style="padding-top:200px;padding-bottom:200px">No Data/No Plot</h3>'
    else:
        out = out +  pout
#
#--- add the rest
#
    out = out + '<ul><li style="font-size:80%">Click the magnifier icon and choose the area to enlarge the area.</li>'
    out = out + '<li style="font-size:80%">Click the cross icon and hold the button to move around the area.</li>'
    out = out + '<li style="font-size:80%">Click the cross icon and then use the roller to zoom in and out.</li>'
    out = out + '<li style="font-size:80%">Click the house icon to go back to the full view.</li>'
    out = out + '<li style="font-size:80%">After enlarging the area with the magnifier,'
    out = out + ' use the cross icon to see the values of each data point.</li></ul>'

    [lout, gname] = get_group_names(msid)
    if lout != '':
        out = out + '<h3>Other msids in this group: ' + gname + '</h3>'
        out = out + lout

    out = out + '<div style="padding-top:30px"></div>'
    out = out + '<hr /><p style="text-align:left; padding-top:10px;padding-bottom:20px">'
    out = out + 'If you have any questions, please contact '
    out = out + '<a href="mailto:tisobe@cfa.harvard.edu">tisobe@cfa.harvard.edu</a>.'
    out = out + '\n\n\n</body>\n</html>\n'
#
#--- write out the html data
#
    name = web_dir + msid + '_plot.html'
    fo = open(name, 'w')
    fo.write(out)
    fo.close()

#----------------------------------------------------------------------------------
#-- create_label_html: creating a list of html links to the distribution plots  ---   
#----------------------------------------------------------------------------------

def create_label_html(indata, msid, unit):
    """
    creating a list of html links to the distribution plots
    """
    [dnum, start, stop, avg, med, std, dmin, dmax, ylow, ytop,  \
                        rlow, rtop, yl_lim, yu_lim, rl_lim, ru_lim] =indata

    hlist = []
    for k in range(0, len(start)):

        atemp = re.split('T', start[k])
        btemp = re.split('T', stop[k])

        line = '<table border=1 cellpadding=2 style="text-align:center;background-color:yellow;">'

        line = line + '<tr><th>Start Time</th>'
        line = line + '<td style="text-align:center;">' + str(atemp[0])  + '</td></tr>'

        line = line + '<tr><th>Stop  Time</th>'
        line = line + '<td style="text-align:center;">' + str(btemp[0])  + '</td></tr>'

        line = line + '<tr><th># of Data </th>'
        line = line + '<td style="text-align:center;">' + str(dnum[k])   + '</td></tr>'

        line = line + '<tr><th>Average   </th>'
        line = line + '<td style="text-align:center;">' + str(avg[k])    + '</td></tr>'

        line = line + '<tr><th>Median    </th>'
        line = line + '<td style="text-align:center;">' + str(med[k])    + '</td></tr>'

        line = line + '<tr><th>Sandard Deviation </th>'
        line = line + '<td style="text-align:center;">' + str(std[k])    + '</td></tr>'

        line = line + '<tr><th>Min       </th>'
        line = line + '<td style="text-align:center;">' + str(dmin[k])   + '</td></tr>'

        line = line + '<tr><th>Max       </th>'
        line = line + '<td style="text-align:center;">' + str(dmax[k])   + '</td></tr>'

        line = line + '<tr><th># of Lower Yellow Violation </th>'
        line = line + '<td style="text-align:center;">' + str(ylow[k])   + '</td></tr>'

        line = line + '<tr><th># of Upper Yellow Violation </th>'
        line = line + '<td style="text-align:center;">' + str(ytop[k])   + '</td></tr>'

        line = line + '<tr><th># of Lower Red Violation    </th>'
        line = line + '<td style="text-align:center;">' + str(rlow[k])   + '</td></tr>'

        line = line + '<tr><th># of Upper Red Violation    </th>'
        line = line + '<td style="text-align:center;">' + str(rtop[k])   + '</td></tr>'

        line = line + '<tr><th>Lower Yellow Limit </th>'
        line = line + '<td style="text-align:center;">' + str(yl_lim[k]) + '</td></tr>'

        line = line + '<tr><th>Upper Yellow Limit </th>'
        line = line + '<td style="text-align:center;">' + str(yu_lim[k]) + '</td></tr>'

        line = line + '<tr><th>Lower Red Limit    </th>'
        line = line + '<td style="text-align:center;">' + str(rl_lim[k]) + '</td></tr>'

        line = line + '<tr><th>Upper Red Limit    </th>'
        line = line + '<td style="text-align:center;">' + str(ru_lim[k]) + '</td></tr>'

        line = line + '</table>'
        line = line + '<div style="padding-bottom:10px;"></div>'

        hlist.append(line)
        
    return hlist

#----------------------------------------------------------------------------------
#-- get_group_names: create a table with links to other msids in the same group  --
#----------------------------------------------------------------------------------

def get_group_names(msid):
    """
    create a table with links to other msids in the same group
    input:  msid    --- msid
    output: line    --- a link list in html table format
    """
#
#--- find which group this msid belongs to and then find all other msids in this group
#
    group = []
    nrow  = 0
    test  = msid + '_plot.html'
    for ent in category_list:
        mc = re.search(test, ent)

        if mc is not None:
            atemp = re.split('::', ent)
            lname = atemp[0].lower()
            gname = '<a href="' + web_address  + 'Htmls/'+ lname + '_main.html">' + lname + '</a>'

            group = re.split(':',  atemp[1])
            break
#
#--- create the table fo these msids with links to the plots
#
    k = 0
    if len(group) > 0:
        line = '<table border=1 cellpadding=3>\n'
        for ent in group:
            if k == 0:
                line = line + '<tr>'
            ctemp = re.split('_plot.html', ent)
            if ctemp[0] == msid:
                continue

            line = line + '<td style="text-align:center"><a href="' + web_address + 'Htmls/' + ent + '">' + ctemp[0] + '</a>\n'
#
#--- 10 entries per row
#
            if k >= 11:
                line = line + '</tr>\n'
                k    = 0
                nrow = 1
            else:
                k += 1

        chk = 0
        if (nrow > 0) and (k > 0):
            for m in range(k, 12):
                line = line + '<td>&#160;</td>\n'
                chk = 1
        else:
            chk = 1

        if chk == 1:
            line = line + '</tr>\n'
            line = line + '</table>\n'

    else:
        gname = ''
        line = ''

    return [line, gname]


#----------------------------------------------------------------------------------
#-- create_limit_table: create a limit table for msid                            --
#----------------------------------------------------------------------------------

def create_limit_table(msid, unit,  xmin, xmax):
    """
    create a limit table for msid
    input:  msid    --- msid
            unit    --- unit
            xmin    --- xmin
            xmax    --- xmax
    output: <web_dir>/Limit_table/<msid>_limit_table.html
    """
#
#--- read limit data
#
    pmsid = msid.replace('_i^',    '')
    pmsid = pmsid.replace('_s^',   '')
    pmsid = pmsid.replace('_off^', '')
    l_list = ecf.set_limit_list(pmsid)

    line = '<!DOCTYPE html>\n'
    line = line + '<html>\n'
    line = line + '<head>\n'
    line = line + '\t<title>' + msid + ' limit table</title>\n'
    line = line + '</head>\n'
    line = line + '<body style="background-color:#FFE4B5; padding-top:20px;background-color:#FAEBD7;'
    line = line + 'font-family:Georgia, "Times New Roman", Times, serif;">\n'
#
#--- except a few, all temperatures are in K
#
    if unit == 'DEGF':
        tline = msid.upper() + ' (K)'
    elif unit == 'DEGC':
        tline = msid.upper() + ' (K)'
    elif unit == '':
        tline = msid.upper()
    else:
        tline = msid.upper() + ' (' + unit + ')'

    line = line + '<h2>' + tline + '</h2>\n'
    line = line + '<table border=1 cellpadding=2>\n'
    line = line + '<tr><th>Start Time</th>\n'
    line = line + '<th>Stop Time</th>\n'
    line = line + '<th style="background-color:yellow">Yellow Lower</th>\n'
    line = line + '<th style="background-color:yellow">Yellow Upper</th>\n'
    line = line + '<th style="background-color:red">Red Lower</th>\n'
    line = line + '<th style="background-color:red">Red Upper</th>\n'
    line = line + '</tr>\n'

    for k in range(0, len(l_list)):
        alist = l_list[k]

        astart = ecf.stime_to_frac_year(float(alist[0]))
        astop  = ecf.stime_to_frac_year(float(alist[1]))
#
#--- there are often the data with <start>=<stop>, drop them
#
        if astart == astop:
            continue

        astart  = '%4.2f' % (round(astart,2))
        astop   = '%4.2f' % (round(astop, 2))

        if k == 0:
            if astart > xmin:
                astart = '---'

        if k == (len(l_list) -1):
            astop = "---"

        yminl   = float(alist[2])
        ymaxl   = float(alist[3])
        rminl   = float(alist[4])
        rmaxl   = float(alist[5])

        line = line + '<tr>\n'
        line = line + '<td style="text-align:center;">' + str(astart) + '</td>\n'
        line = line + '<td style="text-align:center;">' + str(astop)  + '</td>\n'
        line = line + '<td style="text-align:center;">' + str(yminl)  + '</td>\n'
        line = line + '<td style="text-align:center;">' + str(ymaxl)  + '</td>\n'
        line = line + '<td style="text-align:center;">' + str(rminl)  + '</td>\n'
        line = line + '<td style="text-align:center;">' + str(rmaxl)  + '</td>\n'
        line = line + '</tr>\n'

    line = line + '</table>\n'
    line = line + '</body>\n</html>\n'

    file_name = web_dir + 'Limit_table/' + msid + '_limit_table.html'
    fo   = open(file_name, 'w')
    fo.write(line)
    fo.close()

#----------------------------------------------------------------------------------
#-- set_warning_area: set yellow and red violation zones                         --
#----------------------------------------------------------------------------------

def set_warning_area(l_list, xmin, xmax, ymin, ymax):
    """
    set yellow and red violation zones
    input:  l_list  --- a list of lists of [<yellow low>, <yellow top>, <red low>, <red top>]
            xmin    --- xmin
            xmax    --- xmax
            ymin    --- ymin
            ymax    --- ymax
    output: a list of lists:
                    trb_save    
                    rb1_save    --- lower boundary of the bottom red area
                    rb2_save    --- top   boundary of the bottom red area
                    tyb_save    --- extra
                    yb1_save    --- lower boundary of the bottom yellow area
                    yb2_save    --- top   boundary of the bottom yellow area
                    tyt_save    --- extra 
                    yt1_save    --- lower boundary of the top yellow area
                    yt2_save    --- top   boundary of the top yellow area
                    trt_save    --- extra
                    rt1_save    --- lower boundary of the top red area
                    rt2_save    --- top   boundary of the top red area
    """

    l_len = len(l_list)

    trb_save = []
    rb1_save = []
    rb2_save = []
    tyb_save = []
    yb1_save = []
    yb2_save = []

    tyt_save = []
    yt1_save = []
    yt2_save = []
    trt_save = []
    rt1_save = []
    rt2_save = []

    for k in range(0, l_len):
        alist = l_list[k]

        astart = ecf.stime_to_frac_year(float(alist[0]))
        if k == 0:
            if astart > xmin:
                astart = 1998

        astop  = ecf.stime_to_frac_year(float(alist[1]))
        if k == (l_len -1):
            atop = xmax + 2.0

        step = (astop - astart) / 100.0
        trange = []
        for m in range(0, 100):
            val  = astart + step * m 
            trange.append(val)
        trange.append(astop)
#
#--- there are special values which indicate no boundaries
#
        yminl   = float(alist[2])
        rminl   = float(alist[4])
        if yminl in [-99.0, -998.0, -999.0]:
            yminl = ymin - 9.5 * abs(ymin)

        if rminl in [-99.0, -998.0, -999.0]:
            rminl = ymin - 10 * abs(ymin)
            mbot  = rminl - abs(rminl * 0.5)
        else:
            mbot  = rminl - abs(rminl * 0.5)
            if mbot > ymin:
                mbot = ymin - 3.0 * abs(ymin)

        mbrange = ([mbot] * 101)

        ymaxl   = float(alist[3])
        rmaxl   = float(alist[5])
        if ymaxl in [99.0, 998.0, 999.0]:
            ymaxl = ymax + 9.5 * abs(ymax)

        if rmaxl in  [99.0, 998.0, 999.0]:
            rmaxl = ymax + 10 * abs(ymax)
            mtop  = rmaxl + abs(rmaxl * 0.5)
        else:
            mtop  = rmaxl + abs(rmaxl * 0.5)
            if mtop < ymax:
                mtop = ymax + 3.0 * abs(ymax)
        mtrange = ([mtop] * 101)
#
#--- create each period has "101" elements so that it won't mess up the
#--- interactive plots
#
        rbrange = ([rminl] * 101)
        ybrange = ([yminl] * 101)
        ytrange = ([ymaxl] * 101)
        rtrange = ([rmaxl] * 101)

        if rminl != na:
            trb_save += trange
            rb1_save += mbrange
            rb2_save += rbrange
        if yminl != na:
            tyb_save += trange
            yb1_save += rbrange
            yb2_save += ybrange
        if ymaxl != na:
            tyt_save += trange
            yt1_save += ytrange
            yt2_save += rtrange
        if rmaxl != na:
            trt_save += trange
            rt1_save += rtrange
            rt2_save += mtrange

    return [trb_save, rb1_save, rb2_save, tyb_save, yb1_save, yb2_save, tyt_save, \
            yt1_save, yt2_save, trt_save, rt1_save, rt2_save]

#----------------------------------------------------------------------------------
#-- read_data: read the data of msid                                            ---
#----------------------------------------------------------------------------------

def read_data(msid):
    """
    read the data of msid
    input:  msid    --- msid
    output: pdata   --- a list of lists of data
                        xtime  = pdata[0]
                        dnum   = pdata[1]
                        start  = pdata[2]
                        stop   = pdata[3]
                        avg    = pdata[4]
                        med    = pdata[5]
                        std    = pdata[6]
                        dmin   = pdata[7]
                        dmax   = pdata[8]
                        ylow   = pdata[9]
                        ytop   = pdata[10]
                        rlow   = pdata[11]
                        rtop   = pdata[12]
                        yl_lim = pdata[13]
                        yu_lim = pdata[14]
                        rl_lim = pdata[15]
                        ru_lim = pdata[16]
    """

    dfile = data_dir + msid + '_data'
    data  = ecf.read_file_data(dfile)

    if len(data) == 0:
        return na

    xtime  = []
    dnum   = []
    pcolor = []
    start  = []
    stop   = []
    avg    = []
    med    = []
    std    = []
    dmin   = []
    dmax   = []
    ylow   = []
    ytop   = []
    rlow   = []
    rtop   = []
    yl_lim = []
    yu_lim = []
    rl_lim = []
    ru_lim = []

    for ent in data:
        atemp = re.split('\s+', ent)
#
#--- if standard deviation is really large, something wrong with the data; so drop it
#
        tst = float(atemp[5])
        if abs(tst) > 1e6:
            continue

        tstart = float(atemp[0])
        tstop  = float(atemp[1])

        tmid   = 0.5 * (tstart + tstop)
        tmid   = ecf.stime_to_frac_year(tmid)
        xtime.append(tmid)

        start.append(ecf.covertfrom1998sec(tstart))
        stop.append(ecf.covertfrom1998sec(tstop))

        dnum.append(atemp[2])

        avg.append(float(atemp[3]))
        val = float(atemp[4])
        med.append(val)
        std.append(atemp[5])
        dmin.append(float(atemp[6]))
        dmax.append(float(atemp[7]))
        ylow.append(atemp[8])
        ytop.append(atemp[9])
        rlow.append(atemp[10])
        rtop.append(atemp[11])
        yl_lim.append(atemp[12])
        yu_lim.append(atemp[13])
        rl_lim.append(atemp[14])
        ru_lim.append(atemp[15])

        yl = float(atemp[12])
        yu = float(atemp[13])
        rl = float(atemp[14])
        ru = float(atemp[15])
        
        if yl == 'na':
            pcolor.append('blue')
        else:
            if (ru not in [998, 999])     and (val > ru):
                pcolor.append('red')
            elif (rl not in [-999, -998]) and (val < rl):
                pcolor.append('red')
            elif (yu not in  [998, 999])  and (val > yu): 
                pcolor.append('#FFA500')
            elif (yl not in [-999, -998]) and (val < yl):
                pcolor.append('#FFA500')
            else:
                pcolor.append('blue')
#
#--- if the avg is totally flat, the plot wil bust; so change tiny bit at the last entry
#
    test = numpy.std(avg)
    if test == 0:
        alen = len(avg) - 1
        avg[alen] = avg[alen] * 1.0001
        
    return [xtime, dnum,  start, stop, avg, med, std,  \
            dmin, dmax, ylow, ytop, rlow, rtop, yl_lim, yu_lim, rl_lim, ru_lim, pcolor]

#----------------------------------------------------------------------------------
#-- set_y_range: find plotting y range                                          ---
#----------------------------------------------------------------------------------

def set_y_range(pdata, y_min, y_max, msid):
    """
    find plotting y range
    input:  pdata   --- a list of lists of data
                        xtime  = pdata[0]
                        dnum   = pdata[1]
                        start  = pdata[2]
                        stop   = pdata[3]
                        avg    = pdata[4]
                        med    = pdata[5]
                        std    = pdata[6]
                        dmin   = pdata[7]
                        dmax   = pdata[8]
                        ylow   = pdata[9]
                        ytop   = pdata[10]
                        rlow   = pdata[11]
                        rtop   = pdata[12]
                        yl_lim = pdata[13]
                        yu_lim = pdata[14]
                        rl_lim = pdata[15]
                        ru_lim = pdata[16]
                        pcolor = pdata[17]
            y_min   --- a list of lower envelope
            y_max   --- a list of ypper envelope
    output: [ymin, ymax]
    """
#
#--- remove all dummy values
#
    udata = []
    for ent in pdata[5]:
        if ent in [-999, -998,-99, 99, 998, 999]:
            continue
        else:
            udata.append(ent)
#
#--- remove all extreme outlayers before computer med and std
#
    udata.sort()
    lcnt  = len(udata)
    p     = int(0.05 * lcnt)
    test  = udata[p:lcnt-p]
    med   = numpy.mean(numpy.array(test))
    std   = numpy.std(numpy.array(test))

    ymin = med - 3.5 * std
    ymax = med + 3.5 * std

    if ymin == ymax:
        tlist = ecf.set_limit_list(msid)
        ybot  = tlist[-1][4]
        ytop  = tlist[-1][5]

        if (ybot in [-999, -998]) or (ytop in [998, 999]):
            harea = 1.0
        else:
            harea = 0.5 * abs(ytop - ybot)

        ymin = med - harea
        ymax = med + harea
#
#--- check ymin and ymax are reasoble
#
    if ymin < 0.0:
        mcut = 1.05 * med
    else:
        mcut = 0.95 * med
    if ymin > mcut:
        if ymin < 0.0:
            ymin = 1.1 * ymin
        else:
            ymin = 0.9 * ymin

    if ymax < 0.0:
        mcut = 0.95 * med
    else:
        mcut = 1.05 * med

    if ymax < mcut:
        if ymax < 0.0:
            ymax = 0.9 * ymax
        else:
            ymax = 1.1 * ymax
#
#--- adjust ymin/ymax if the envelop is larger than the original ymin/ymax
#
    try:
        out = sorted(y_min)
        test = out[1]
    except:
        test = ymin

    if test < ymin:
        if test > 0:
            ymin = 0.95 * test
        else:
            ymin = 1.05 * test

    try:
        out = sorted(y_max)
        test = out[-2]
    except:
        test = ymax

    if test > ymax:
        if test > 0:
            ymax = 1.05 * test
        else:
            ymax = 0.95 * test

    return [ymin, ymax]

#----------------------------------------------------------------------------------
#-- predict_trend: create moving average of envelope around the average data      -
#----------------------------------------------------------------------------------

def predict_trend(pdata, xmin, xmax):
    """
    create moving average of envelope around the average data
    input:  pdata   --- a list of lists of data.
                        xtime  = pdata[0]
                        dnum   = pdata[1]
                        start  = pdata[2]
                        stop   = pdata[3]
                        avg    = pdata[4]
                        med    = pdata[5]
                        std    = pdata[6]
                        dmin   = pdata[7]
                        dmax   = pdata[8]
                        ylow   = pdata[9]
                        ytop   = pdata[10]
                        rlow   = pdata[11]
                        rtop   = pdata[12]
                        yl_lim = pdata[13]
                        yu_lim = pdata[14]
                        rl_lim = pdata[15]
                        ru_lim = pdata[16]
                        pcolor = pdata[17]
            xmin    --- xmin
            xmax    --- xmax
    output: tlim    --- prediction starting point in time
            tmax    --- prediction ending point in time
            min_a   --- intercept of the bottom prediciton line
            min_b   --- slope of the bottom prediction line
            max_a   --- intercept of the top prediction line
            max-b   --- slope of the top prediction line
            xcent   --- a list of x value for moving average
            y_avg   --- a list of moving average of  center value
            y_min   --- a list of moving averages of y min envelop
            y_max   --- a list of moving averages of y max envelop
    """
#
#--- pdata[0] is time and pdata[5] is med, pdata[6] is std
#
    time = []
    dmin = []
    dmax = []
    temp = []
#
#--- set a few values to find outlayers
#
    emed = numpy.median(pdata[5])
    estd = numpy.std(pdata[5])
    ebot = emed - 3.5 * estd
    etop = emed + 3.5 * estd
    
    efactor = 0.75

    for k in range(len(pdata[5])):

        time.append(pdata[0][k])
#
#--- use factor * (the distance between med to min) as an envelop
#
        bfactor = efactor * abs(pdata[5][k] - pdata[7][k])
        tfactor = efactor * abs(pdata[5][k] - pdata[8][k])
#
#--- if the center value is outside of the limit, replace it with "average" value
#
        if (pdata[5][k] < ebot) or (pdata[5][k] > etop):
            val = emed
        else:
            val = pdata[5][k]

        dmin.append(val - bfactor)
        dmax.append(val + tfactor)

    dlen   = len(time)
    tmax   = time[-1]
    period = 1.0                #---- a year interval
    nterm  = 0                  #---- setting 0 to ignore smooth fitting
    tlim   = tmax - period
#
#--- first find moving average forward, then find moving average backward from the end
#
    try:
        out1  = fma.find_moving_average(pdata[0],  pdata[5], period , nterm)
    except:
        out1  = [[],[]]

    tcnt = len(out1[0])

    try:
        out2  = fma.find_moving_average(time,  dmin,     period , nterm)
        if len(out2[1]) != tcnt:
            elist = create_secondary_bound(out1[1], dmin, loc=0)
            out2  = [[out1[0]],elist]
    except:
        elist = create_secondary_bound(out1[1], dmin, loc=0)
        out2  = [[out1[0]],elist]
    try:
        out3  = fma.find_moving_average(time,  dmax,     period , nterm)
        if len(out3[1]) != tcnt:
            elist = create_secondary_bound(out1[1], dmax, loc=1)
            out3  = [[out1[0]],elist]
    except:
        elist = create_secondary_bound(out1[1], dmax, loc=1)
        out3  = [[out1[0]],elist]

    try:
        out1b = fmab.find_moving_average(pdata[0], pdata[5], period , nterm)
    except:
        out1b = [[],[]]

    tcnt = len(out1b[0])
    try:
        out2b = fmab.find_moving_average(time, dmin,     period , nterm)
        if len(out2b[1]) != tcnt:
            elist = create_secondary_bound(out1b[1], dmin, loc=0)
            outb2 = [[out1b[0]],elist]
    except:
        elist = create_secondary_bound(out1b[1], dmin, loc=0)
        out2b = [[out1b[0]],elist]
    try:
        out3b = fmab.find_moving_average(time, dmax,     period , nterm)
        if len(out3b[1]) != tcnt:
            elist = create_secondary_bound(out1b[1], dmax, loc=1)
            outb3 = [[out1b[0]],elist]
    except:
        elist = create_secondary_bound(out1b[1], dmax, loc=1)
        out3b = [[out1b[0]],elist]

    xcenta = out1[0]
    y_avga = out1[1]
    y_mina = out2[1]
    y_maxa = out3[1]
#
#--- occasionally backward moving average get different numbers of data among
#--- time, min and max envelopes; so check that and fix
#
    tchk1  = len(out1b[0])
    tchk2  = len(out2b[0])
    tchk3  = len(out3b[0])
    amin   = min([tchk1, tchk2, tchk3])
    amax   = max([tchk1, tchk2, tchk3])
    if amin == amax:
        xcentb = out1b[0]
        y_avgb = out1b[1]
        y_minb = out2b[1]
        y_maxb = out3b[1]
    else:
        xcentb = []
        y_avgb = []
        y_minb = []
        y_maxb = []
        for k in range(0, amin):
            m = amin - k - 1
            xcentb.append(out1b[0][m])
            y_avgb.append(out1b[1][m])
            y_minb.append(out2b[1][m])
            y_maxb.append(out3b[1][m])
        xcentb.reverse()
        y_avgb.reverse()
        y_minb.reverse()
        y_maxb.reverse()

#
#--- add the fitting values from the begining to the data fitted from the end
#
    if len(xcentb) > 0:
        xconnect = xcentb[0]
    else:
        xconnect = xmax 

    xcent    = []
    y_avg    = []
    y_min    = []
    y_max    = []
    for k in range(0, len(xcenta)):
        if xcenta[k] >= xconnect:
            break
        else:
            xcent.append(xcenta[k] - 0.5 * period)
            y_avg.append(y_avga[k])
            y_min.append(y_mina[k])
            y_max.append(y_maxa[k])

    if len(xcentb) > 0:
        xcent  += xcentb
        y_avg  += y_avgb
        y_min  += y_minb
        y_max  += y_maxb
#
#--- estimate intercept and slope from the last two data points
#
    [min_a, min_b] = get_int_slope(time, dmin, xcent, y_min)
    [max_a, max_b] = get_int_slope(time, dmax, xcent, y_max)

    return [tlim, tmax, min_a, min_b, max_a, max_b, xcent, y_avg, y_min, y_max]

#----------------------------------------------------------------------------------
#-- create_secondary_bound: create boundray around the data based on med value   --
#----------------------------------------------------------------------------------

def create_secondary_bound(m_list, b_list, loc=0):
    """
    create boundray around the data based on med value
    this is used only when the main moving average boundary failed to be created
    input:  m_list  --- a list of main data
            b_list  --- a list of boundary data (either min or max data list)
            loc:    --- whether is this bottom or top boundary 0: lower or 1: upper
    output: e_list  --- a list of estimated values
    """

    med = numpy.median(numpy.array(b_list))
    sign = 1.0
    if loc == 0:
        sign = -1.0
    e_list = []
    for ent in m_list:
        val = ent + sign * med
        e_list.append(val)

    return e_list

#----------------------------------------------------------------------------------
#-- get_int_slope: estimate a + b * x line  with a robust method               ----
#----------------------------------------------------------------------------------

def get_int_slope(x, y, xl, yl):
    """
    estimate a + b * x line  with a robust method and then compare with a
    simple two point estimate and choose a shallower slope fitting
    input:  x       --- a list of x values
            y       --- a list of y values
            xl      --- a secondary list of x value
            yl      --- a seocndary list of y value
    output: a       --- intercept
            b       --- slope
    """
#
#--- choose the data only in the last one year
#
    bound = ecf.current_time() - 1.0

    xsave = []
    ysave = []

    for k in range(0, len(x)):
        if x[k] < bound:
            continue
        xsave.append(x[k])
        ysave.append(y[k])
#
#--- if there are not enough data, give up the fitting
#
    if len(xsave) < 6:
        return [999, 999]

    try:
#
#--- robust fit
#
        [a,b,err] = rfit.robust_fit(xsave, ysave)
#
#--- two point fit
#
        [al, bl]  = get_int_slope_supl(xl, yl)
#
#--- choose a shallower slope fit
#
        if abs(bl) < abs(b):
            a = al
            b = bl
    except:
        a = 999
        b = 999

    return [a,b]

#----------------------------------------------------------------------------------
#-- get_int_slope: estimate a + b * x line from the last two data points         --
#----------------------------------------------------------------------------------

def get_int_slope_supl(x, y):
    """
    estimate a + b * x line from the last two data points
    input:  x       --- a list of x values
            y       --- a list of y values
    output: icept   --- intercept
            slope   --- slope
    """

    k  = len(x)
    k1 = k -1
    k2 = k -2
    try:
        slope = (y[k1] - y[k2]) / (x[k1] - x[k2])
        icept = y[k1] - slope * x[k1]

        return [icept, slope]
    except:
        return [999,999]


#----------------------------------------------------------------------------------
#-- predict_violation: predict possible limti violations                         --
#----------------------------------------------------------------------------------

def predict_violation(a, b, current, vlimit, side = 1):
    """
    predict possible limti violations
    input:  a       --- intercept of the predicted line
            b       --- slope of the predicted line
            current --- the current value
            vlimit  --- limit value
            side    --- lower (0) or upper (1) limit
    output: rtime   --- estimated violation time. if no violation return 0
    """
    if b == 999:
        return 0

    vlimit = float(vlimit)

    rtime  = 0
    now      = a + b * current
    if side > 0:
        if now > vlimit:
            rtime = current
    else:
        if now < vlimit:
            rtime = current

    if rtime == 0:
#
#--- if the slope is too steep, something is not right; so ignore the future estimation
#
        if  (b == 0) or (b == 999):
            rtime = 0
        else:
            estimate = (vlimit - a) / b
            if estimate > current:
                rtime = estimate
            else:
                rtime = 0

    return rtime

#--------------------------------------------------------------------------------------------------------

from pylab import *
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import matplotlib.lines as lines

if __name__ == '__main__':

    create_html_page()


