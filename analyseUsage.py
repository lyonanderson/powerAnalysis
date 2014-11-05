import sys
import sqlite3
from datetime import datetime
from datetime import timedelta
import numpy as np
import argparse
from collections import namedtuple

def contiguous_regions(condition):
    d = np.diff(condition)
    idx, = d.nonzero() 

    idx += 1

    if condition[0]:
        idx = np.r_[0, idx]

    if condition[-1]:
        idx = np.r_[idx, condition.size]

    idx.shape = (-1,2)
    return idx


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


def extractSecondsActiveFromResultSet(rows, activeState):
	x = [datetime.fromtimestamp(row[0]) for row in rows]
	y = [row[1] for row in rows]
	condition = np.abs(y) == activeState

	regions = contiguous_regions(condition)
	count = timedelta(0)

	for reg in regions:
		timeOfRow = x[reg[0]];
	
		if (reg[1] < len(x)):
			count += (x[reg[1]] - x[reg[0]])
	return count.total_seconds()

def formatTimeDelta(timedelta):
	hours, remainder = divmod(timedelta.total_seconds, 3600)
	minutes, seconds = divmod(remainder, 60) 
	return  '%d:%02d:%02d' % (hours, minutes, seconds)

def main(argv):
	parser=argparse.ArgumentParser()
	parser.add_argument('inputFile')
	parser.add_argument('-s', "--startDate", help="The Start Date - format YYYY-MM-DD HH:MM", required=False, type=valid_date)
	parser.add_argument('-e', "--endDate", help="The End Date - format YYYY-MM-DD HH:MM", required=False, type=valid_date)
	args=parser.parse_args()

	whereClause = ''

	if args.startDate:
		whereClause = 'timestamp > {startDate} '.format(startDate = args.startDate.strftime('%s'))

	if args.endDate:
		if args.startDate:
			whereClause += ' AND '
		whereClause += ' timestamp < {endDate} '.format(endDate = args.endDate.strftime('%s')) 

	db = sqlite3.connect(argv[0])
	db.row_factory = sqlite3.Row
	cursor = db.cursor()

	cursor.execute('''SELECT timestamp, Active 
						FROM PLDisplayAgent_EventPoint_Display {whereClause} 
						ORDER BY timestamp'''.format(whereClause=('', 'WHERE {0}'.format(whereClause))[len(whereClause) > 0]))

	all_rows = cursor.fetchall()
	displayOnLength =extractSecondsActiveFromResultSet(all_rows, 1)

	cursor.execute('''SELECT  timestamp, state 
						 FROM PLSleepWakeAgent_EventForward_PowerState {whereClause} 
						 ORDER BY timestamp'''.format(whereClause=('', 'WHERE {0}'.format(whereClause))[len(whereClause) > 0]))

	all_rows = cursor.fetchall()
	deviceOnLength =extractSecondsActiveFromResultSet(all_rows, 0)

	(startTimeInData, endTimeInData) = (all_rows[0][0], all_rows[-1][0])

	overallBreakdown = '''<table  class="table table-striped table-bordered display responsive">
									<tbody>
										<tr><td>Display active for {0}</td></tr>
										<tr><td>Device active for {1}</td></tr>
									</tbody>
								</table>
						'''.format(str(timedelta(seconds=displayOnLength)),str(timedelta(seconds=deviceOnLength)))


	# Per Process Timing

	cursor.execute('''SELECT processname, SUM(value) AS TotalTime 
						FROM PLProcessMonitorAgent_EventInterval_ProcessMonitorInterval_Dynamic, PLProcessMonitorAgent_EventInterval_ProcessMonitorInterval 
						WHERE PLProcessMonitorAgent_EventInterval_ProcessMonitorInterval.ID = PLProcessMonitorAgent_EventInterval_ProcessMonitorInterval_Dynamic.FK_ID
							 {whereClause}
					 	GROUP BY processname 
					 	ORDER BY TotalTime DESC'''.format(whereClause=('', 'AND {0}'.format(whereClause))[len(whereClause) > 0]))

	all_rows = cursor.fetchall()
	
	perProcessBreakdownBody = ''
	for row in all_rows:
		perProcessBreakdownBody += '<tr><td>{0}</td><td>{1}</td></tr>\n'.format(row[0], row[1])
	
	perProcesssBreakdown = '''<table id="processBreakdown" class="table table-striped table-condensed">
								<thead>
								<tr>
									<td class="col-md-3">Process Name</td>
									<td>Time (s)</td>
								</tr>
								</thead>
								<tbody>{perProcessBreakdownBody}</tbody>
							</table>'''.format(perProcessBreakdownBody = perProcessBreakdownBody)

	# Energy Usage per process

	whereClauseForEnergy = ''

	if args.startDate:
		whereClauseForEnergy += ' AND (timestamp  > {0} AND {0} < timestamp + timeInterval) '.format(args.startDate.strftime('%s'))

	if args.endDate:
		if args.startDate:
			whereClauseForEnergy += ' OR '
		whereClauseForEnergy += ' (timestamp  > {0} AND {0} < timestamp + timeInterval) '.format(args.endDate.strftime('%s'))


	print

	cursor.execute('''SELECT  BLMAppName As Bundle,
					 	SUM(Airdrop) AS Airdrop, 
					 	SUM(Airplay) AS Airplay, 
						SUM(AirplayMirroring) AS AirplayMirroring,
						SUM(BBCondition) AS BBCondition, 
						SUM(BLMEnergy) AS BLMEnergy, 
						SUM(BLMEnergyAccessory) AS BLMEnergyAccessory,
						SUM(BLMEnergyAssertion) AS BLMEnergyAssertion,
						SUM(BLMEnergyAudio) AS BLMEnergyAudio,
						SUM(BLMEnergyBB) AS BLMEnergyBB,
						SUM(BLMEnergyBluetooth) AS BLMEnergyBluetooth,
						SUM(BLMEnergyCPU) AS BLMEnergyCPU,
						SUM(BLMEnergyDisplay) AS BLMEnergyDisplay,
						SUM(BLMEnergyGPS) AS BLMEnergyGPS,
						SUM(BLMEnergyGPU) AS BLMEnergyGPU,	
						SUM(BLMEnergyPA_accessories) AS BLMEnergyPA_accessories,
						SUM(BLMEnergyPA_apsd) AS BLMEnergyPA_apsd,
						SUM(BLMEnergyPA_assetsd) AS BLMEnergyPA_assetsd,
						SUM(BLMEnergyPA_backboardd) AS BLMEnergyPA_backboardd,
						SUM(BLMEnergyPA_cloudd) AS BLMEnergyPA_cloudd,
						SUM(BLMEnergyPA_commcenter) AS BLMEnergyPA_commcenter,
						SUM(BLMEnergyPA_discoverydBB) AS BLMEnergyPA_discoverydBB,
						SUM(BLMEnergyPA_discoverydWifi) AS BLMEnergyPA_discoverydWifi,
						SUM(BLMEnergyPA_kernel_task) AS BLMEnergyPA_kernel_task,
						SUM(BLMEnergyPA_locationd) AS BLMEnergyPA_locationd, 
						SUM(BLMEnergyPA_mediaserverd) AS BLMEnergyPA_mediaserverd,
						SUM(BLMEnergyPA_notification_display) AS BLMEnergyPA_notification_display,
						SUM(BLMEnergyPA_nsurlsessiond) AS BLMEnergyPA_nsurlsessiond,
						SUM(BLMEnergyPA_syncdefaultd) AS BLMEnergyPA_syncdefaultd,
						SUM(BLMEnergySOC) AS BLMEnergySOC,
						SUM(BLMEnergyTorch) AS BLMEnergyTorch,
						SUM(BLMEnergyWiFi) AS BLMEnergyWiFi,
						SUM(BLMEnergyWiFiLocationScan) AS BLMEnergyWiFiLocationScan,
						SUM(BLMEnergyWiFiPipelineScan) AS BLMEnergyWiFiPipelineScan,
						SUM(BLMEnergy_BackgroundCPU) AS BLMEnergy_BackgroundCPU,
						SUM(BLMEnergy_BackgroundLocation)  BLMEnergy_BackgroundLocation, 
						SUM(background) AS  background
						FROM PLBLMAccountingService_Aggregate_BLMAppEnergyBreakdown
						WHERE timeInterval = '3600' 
						{whereClauseForEnergy}
						GROUP BY Bundle
						ORDER BY BLMEnergy DESC'''.format(whereClauseForEnergy=('', '{0}'.format(whereClauseForEnergy))[len(whereClauseForEnergy) > 0]))

	all_rows = cursor.fetchall()
	

	perProcessEnergyBody = ''
	for row in all_rows:
		perProcessEnergyBody += '<tr>'
		for column in row:
			perProcessEnergyBody += '''<td>{0}</td>'''.format(column).replace('None', '0.0')
		perProcessEnergyBody += '</tr>'

	headingsBody = ''
	for col in cursor.description:
		headingsBody += '<td>{0}</td>\n'.format(col[0])

	perProcesssEnergy = '''
								<table id="energyBreakdown" class="table table-striped table-bordered display responsive">
									<thead><tr>{headingsBody}</tr></thead>
									<tbody>{perProcessEnergyBody}</tbody>
								</table>

							'''.format(headingsBody = headingsBody, perProcessEnergyBody = perProcessEnergyBody)

	# Notifications

	cursor.execute('''SELECT Topic, COUNT(Topic) 
						AS Count FROM PLXPCAgent_EventPoint_Apsd  {whereClause} 
						GROUP BY Topic
						ORDER BY Count DESC'''.format(whereClause=('', 'WHERE {0}'.format(whereClause))[len(whereClause) > 0]))

	all_rows = cursor.fetchall()

	notificationsBody = ''
	for row in all_rows:
		notificationsBody += '<tr><td>{0}</td><td>{1}</td></tr>\n'.format(row[0], row[1])
	
	notificationsBreakdown = '''<table id="notificationBreakdown" class="table table-striped table-condensed">
								<thead>
									<tr>
									<td class="col-md-3">Topic</td>
									<td>Number of Notifications</td>
									</tr>
								</thead>
								<tbody>{notificationsBody}</tbody>
							</table>'''.format(notificationsBody = notificationsBody)


	# Signal Bars
	cursor.execute('''SELECT signalBars, ROUND(CAST(COUNT(*) AS REAL)/total, 2) * 100 AS percent 
				FROM PLBBAgent_EventPoint_TelephonyActivity 
  				CROSS JOIN
				    ( SELECT COUNT(*) AS total 
				      FROM PLBBAgent_EventPoint_TelephonyActivity 
					  WHERE airplaneMode="off" 
					  {whereClause}
				    )
				WHERE airplaneMode="off" {whereClause}
				GROUP BY signalBars'''.format(whereClause=('', 'AND {0}'.format(whereClause))[len(whereClause) > 0]))

	all_rows = cursor.fetchall()

	signalBody = ''
	for row in all_rows:
		signalBody += '<tr><td>{0}</td><td>{1}</td></tr>\n'.format(row[0], row[1])
	
	signalBreakdown = '''<table id="signalBreakdown" class="table table-striped table-condensed">
								<thead>
									<tr>
									<td class="col-md-3">Number of Bars</td>
									<td>%</td>
									</tr>
								</thead>
								<tbody>{signalBody}</tbody>
							</table>'''.format(signalBody = signalBody)


	#locations
	cursor.execute('''SELECT Client, Type, COUNT(Client) AS Count 
						 FROM PLLocationAgent_EventForward_ClientStatus
						 {whereClause}
						 GROUP BY Client ORDER BY Count DESC'''.format(whereClause=('', 'WHERE {0}'.format(whereClause))[len(whereClause) > 0]))

	all_rows = cursor.fetchall()

	locationBody = ''
	for row in all_rows:
		locationBody += '<tr><td>{0}</td><td>{1}</td><td>{2}</td></tr>\n'.format(row[0], row[1], row[2])
	
	locationBreakdown = '''<table id="locationBreakdown" class="table table-striped table-condensed">
								<thead>
									<tr>
									<td class="col-md-3">Client</td>
									<td>Type</td>
									<td>Number of Requests</td>
									</tr>
								</thead>
								<tbody>{locationBody}</tbody>
							</table>'''.format(locationBody = locationBody)


	
	f = open('report.html', 'w')
	report = '''<html>
		<link rel="stylesheet" type="text/css" href="https://netdna.bootstrapcdn.com/bootstrap/3.0.3/css/bootstrap.min.css">
		<link rel="stylesheet" type="text/css" href="https://cdn.datatables.net/plug-ins/380cb78f450/integration/bootstrap/3/dataTables.bootstrap.css">

		<script type="text/javascript" language="javascript" src="https://code.jquery.com/jquery-1.10.2.min.js"></script>
		<script type="text/javascript" language="javascript" src="https://cdn.datatables.net/1.10.3/js/jquery.dataTables.min.js"></script>
		<script type="text/javascript" language="javascript" src="https://cdn.datatables.net/plug-ins/380cb78f450/integration/bootstrap/3/dataTables.bootstrap.js"></script>

		<script type="text/javascript" charset="utf-8">
			$(document).ready(function() {{
				 $('#energyBreakdown').DataTable( {{
        			"responsive": true,
        			"order": [[ 5, "desc" ]]
    			}});
				$('#processBreakdown').DataTable( {{
        			"responsive": true,
        			"order": [[ 1, "desc" ]]
    			}});
				$('#notificationBreakdown').DataTable( {{
        			"responsive": true,
        			"order": [[ 1, "desc" ]]
    			}});
				$('#locationBreakdown').DataTable( {{
        			"responsive": true,
        			"order": [[ 2, "desc" ]]
    			}});
			}});
		</script>

		<body>
			<div class="container">
			<h1>Energy Report - {startDate} to {endDate}<h1>

			<h2>Overall Metrics</h2>
			{overallBreakdown}

			<h2>Process time breakdown</h2>
			{perProcesssBreakdown}

			<h2>Energy Usage</h2>
			{perProcesssEnergy}

			<h2>Notifications</h2>
			{notificationsBreakdown}

			<h2>Core Location</h2>
			{locationBreakdown}

			<h2>Signal Breakdown</h2>
			{signalBreakdown}
			</div>
		<body>
	</html>'''.format(startDate = datetime.fromtimestamp(startTimeInData).strftime("%Y-%m-%d %H:%M"), 
						endDate = datetime.fromtimestamp(endTimeInData).strftime("%Y-%m-%d %H:%M"), 
						overallBreakdown = overallBreakdown,
						perProcesssBreakdown = perProcesssBreakdown,
						perProcesssEnergy = perProcesssEnergy,
						notificationsBreakdown = notificationsBreakdown,
						signalBreakdown=signalBreakdown,
						locationBreakdown = locationBreakdown)
	f.write(report)
	f.close()

	db.close()

if __name__ == "__main__":
   main(sys.argv[1:])
