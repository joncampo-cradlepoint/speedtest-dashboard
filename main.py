
from speedtest import Speedtest
import time
import cs
from flask import Flask, Markup, render_template
from multiprocessing import Process, Value
import csv
import datetime
import json


app = Flask(__name__)


cp = cs.CSClient()


#set time interval in seconds where 5GSPEED will run
#14400 secs = 4 hours
#21600 secs = 6 hours

interval = 21600




# Set input file name containing list of router URL's in Column 1, username in Column2, passwords in Column 3, and modem firmware in Column 4
speedtest_result_file = 'speedtest_result.csv'

def housekeeping():
    SpeedList = []
    with open(speedtest_result_file, 'r', newline='') as g:
        reader = csv.reader(g)
        #next(reader)
        for row in reader:
            #print (row)
            SpeedList.append(row)

    #Maintain 6 days worth of results
    #Sixdays = (518400 / interval) + 1
    if len(SpeedList) > 25:
        print("For housekeeping to maintain 6 days worth of data - ", len(SpeedList))
        #print(SpeedList)
        del SpeedList[1]

        #print(SpeedList)


        with open(speedtest_result_file, 'w') as writeFile:
            writer = csv.writer(writeFile)
            writer.writerows(SpeedList)


    return

def read_csv():
    SpeedList = []
    labels = []
    values = []
    # Read contents of router list and assign to array variables:  Column 1 = router IP, Column 2 = username, Column 3 = password, Column 4 = modem firmware file
    with open(speedtest_result_file, 'r', newline='') as g:
        reader = csv.reader(g)
        next(reader)
        for row in reader:
            #print (row)
            SpeedList.append(row)

    print(SpeedList)

    #Assign values found in InputRouter.csv file to RouterList variable list
    csv_timestamp = [inner[0] for inner in SpeedList]
    csv_download = [inner[1] for inner in SpeedList]
    csv_upload = [inner[2] for inner in SpeedList]
    csv_link= [inner[3] for inner in SpeedList]


    labels = csv_timestamp
    values = csv_download
    uvalues = csv_upload
    links = csv_link


    return labels, values, uvalues, links

'''
labels = [
    'JAN', 'FEB', 'MAR', 'APR',
    'MAY', 'JUN', 'JUL', 'AUG',
    'SEP', 'OCT', 'NOV', 'DEC'
]

values = [
    23000.67, 1190.89, 1079.75, 1349.19,
    2328.91, 10000.28, 2873.83, 4764.87,
    4349.29, 6458.30, 9907, 20000
]

colors = [
    "#F7464A", "#46BFBD", "#FDB45C", "#FEDCBA",
    "#ABCDEF", "#DDDDDD", "#ABCABC", "#4169E1",
    "#C71585", "#FF4500", "#FEDCBA", "#46BFBD"]
'''

def speedtest():

    print('Ongoing Speedtest...')
    #cp.put('config/system/asset_id', "Ongoing Speedtest. Refresh page after 1 minute for the result")
    servers = []
    s = Speedtest()

    #Find the best ookla speedtest server based from latency and ping
    print("Finding the Best Ookla Speedtest.net Server...")
    server = s.get_best_server()
    print('Found Best Ookla Speedtest.net Server: {}'.format(server['sponsor']))

    p = s.results.ping
    print('Ping: {}ms'.format(p))

    #Perform Download ookla download speedtest
    print("Performing Ookla Speedtest.net Download Test...")
    d = s.download()
    print('Ookla Speedtest.net Download: {:.2f} Kb/s'.format(d / 1000))

    #Perform Upload ookla upload speedtest. Option pre_allocate false prevents memory error
    print("Performing Ookla Speedtest.net Upload Test...")
    u = s.upload(pre_allocate=False)
    print('Ookla Speedtest.net Upload: {:.2f} Kb/s'.format(u / 1000))

    #Access speedtest result dictionary
    res = s.results.dict()

    #share link for ookla test result page
    share = s.results.share()

    t = res['timestamp']

    i = res["client"]["isp"]

    s = server['sponsor']

    #return res["download"], res["upload"], res["ping"],res['timestamp'],server['sponsor'],res["client"]["isp"], share


    print('')
    print('Test Result')
    print('Timestamp GMT: {}H'.format(t))
    print('Client ISP: {}'.format(i))
    print('Ookla Speedtest.net Server: {}'.format(s))
    print('Ping: {}ms'.format(p))
    print('Download Speed: {:.2f} Mb/s'.format(d / 1000 / 1000))
    print('Upload Speed: {:.2f} Mb/s'.format(u / 1000 / 1000))
    print('Ookla Speedtest.net URL Result: {}'.format(share))

    download = '{:.2f}'.format(d / 1000 / 1000)
    upload = '{:.2f}'.format(u / 1000 / 1000)
    text = 'DL:{}Mbps UL:{}Mbps - {}'.format(download, upload, share)
    #cp.put('config/system/asset_id', text)

    #########################for Desktop version, comment below line

    try:
        cp.put('config/system/asset_id', "Speedtest_Monitoring_Dashboard-http://routerip:8000")
    except:
        print('Desktop version')

    print(f'Speedtest Complete! {text}')

    timecurrentDT = datetime.datetime.now()
    timestamp = str(timecurrentDT.strftime("%m%d%Y-%H%M"))
    csvoutputfile = open(speedtest_result_file, 'a', newline='')
    SpeedResults = csv.writer(csvoutputfile)
    SpeedResults.writerow(
        [timestamp + 'H', download, upload, share])




    return

def speedtest_loop(loop_on):
    print('Starting... 5GSPEEDTEST Running every {} seconds'.format(interval))
    while True:
        # cp.put('status/5GSPEED', "1")
        try:
            housekeeping()
        except Exception as e:
            print(e)

        time.sleep(interval)

        try:
            print("Loop on and performing speedtest!")
            speedtest()
        except Exception as e:
            print(e)



@app.route('/')
def speedtest_result():
    labels, values, uvalues, links = read_csv()

    #max_value = int(float(max(values))) + int(100)
    max_value = max([int(float(X)) for X in values]) + int(100)

    line_labels = labels
    line_values = values
    line_uvalues = uvalues
    line_links = links

    return render_template('line_chart.html', title='Speedtest Monitoring Dashboard', max=max_value, labels=line_labels,
                           values=line_values, uvalues=line_uvalues, links=line_links)


@app.route('/stats', methods=['GET'])
def stats():
    labels, values, uvalues, links = read_csv()

    #max_value = int(float(max(values))) + int(100)
    #max_value = max([int(float(X)) for X in values]) + int(100)

    line_labels = labels
    line_values = values
    line_uvalues = uvalues
    line_links = links

    i = 0
    total = len(line_labels)
    print(total)
    speedtest_values = []

    while i < total:
        speedtest_values.append({'timestamp':line_labels[i],'download (Mbps)':line_values[i], 'upload (Mbps)':line_uvalues[i], 'reference':line_links[i]})
        print(speedtest_values)
        i = i + 1

    return json.dumps(speedtest_values)

if __name__ == '__main__':
    try:
        #run speedtest first
        speedtest()
        speedtest_loop_on = Value('b', True)
        p = Process(target=speedtest_loop, args=(speedtest_loop_on,))
        p.start()

        app.run(host="0.0.0.0", port=8000)

        p.join()




    except Exception as e:
        print(e)