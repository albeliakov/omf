''' Powerflow results for one Gridlab instance. '''

import json, os, csv, shutil, math
from os.path import join as pJoin
from functools import reduce
from datetime import timedelta, datetime, tzinfo
from dateutil import parser as dt_parser

# OMF imports
from omf import feeder, weather
from omf.solvers import gridlabd
from omf.models import solarEngineering
from omf.models import __neoMetaModel__
from omf.models.__neoMetaModel__ import *

# Model metadata:
modelName, template = __neoMetaModel__.metadata(__file__)
tooltip = "The cyberStroage model shows the impacts and mitigation options for cyberattacks on energy storage systems."
hidden = False

def work(modelDir, inputDict):
	''' Run the model in its directory.'''
	feederName = [x for x in os.listdir(modelDir) if x.endswith('.omd')][0][:-4]
	inputDict["feederName1"] = feederName
	zipCode = "59001" #TODO get zip code from the PV and Load input file
	
	#Value check for attackVariable
	if inputDict.get("attackVariable", "None") == "None":
		attackAgentType = "None"
	else:
		attackAgentType = inputDict['attackVariable']

	# Value check for train
	if inputDict.get("trainAgent", "") == "True":
		trainAgentValue = True
	else:
		trainAgentValue = False

	# create simLengthValue to represent number of steps in simulation - will be manipulated by number of rows in load solar data csv file
	simLengthValue = 0

	#create startStep to represent which step pyCigar should start on - default = 100
	startStep = 100

	#None check for simulation length
	# if inputDict.get("simLength", "None") == "None":
	# 	simLengthValue = None
	# else:
	# 	simLengthValue = int(simLengthValue)

	#None check for simulation length units
	if inputDict.get("simLengthUnits", "None") == "None":
		simLengthUnitsValue = None
	else:
		simLengthUnitsValue = inputDict["simLengthUnits"]
	#None check for simulation start date
	if inputDict.get("simStartDate", "None") == "None":
		simStartDateTimeValue = None
		simStartDateValue = None
		simStartTimeValue = None
	else:
		simStartDateTimeValue = inputDict["simStartDate"]
		simStartDateValue = simStartDateTimeValue.split('T')[0]
		simStartTimeValue = simStartDateTimeValue.split('T')[1]

	inputDict["climateName"] = weather.zipCodeToClimateName(zipCode)
	shutil.copy(pJoin(__neoMetaModel__._omfDir, "data", "Climate", inputDict["climateName"] + ".tmy2"),
		pJoin(modelDir, "climate.tmy2"))
	
	def convertInputs():
		#create the PyCIGAR_inputs folder to store the input files to run PyCIGAR
		try:
			os.mkdir(pJoin(modelDir,"PyCIGAR_inputs"))
		except FileExistsError:
			print("PyCIGAR_inputs folder already exists!")
			pass
		except:
			print("Error occurred creating PyCIGAR_inputs folder")

		#create misc_inputs.csv file in folder
		with open(pJoin(modelDir,"PyCIGAR_inputs","misc_inputs.csv"),"w") as miscFile:
			#Populate misc_inputs.csv
			# miscFile.write(misc_inputs)
			# for key in misc_dict.keys():
			# 	miscFile.write("%s,%s\n"%(key,misc_dict[key]))
			miscFile.write(inputDict['miscFile'])

		#create ieee37.dss file in folder
		dss_filename = "circuit.dss"
		with open(pJoin(modelDir, "PyCIGAR_inputs", dss_filename),"w") as dssFile:
			dssFile.write(inputDict['dssFile'])

		#create load_solar_data.csv file in folder
		rowCount = 0
		with open(pJoin(modelDir,"PyCIGAR_inputs","load_solar_data.csv"),"w") as loadPVFile:
			loadPVFile.write(inputDict['loadPV'])
			#Open load and PV input file
		try:
			with open(pJoin(modelDir,"PyCIGAR_inputs","load_solar_data.csv"), newline='') as inFile:
				reader = csv.reader(inFile)
				for row in reader:
					rowCount = rowCount+1
			#Check to see if the simulation length matches the load and solar csv
			# if (rowCount-1)*misc_dict["load file timestep"] != simLengthValue:
			# 	errorMessage = "Load and PV Output File does not match simulation length specified by user"
			# 	raise Exception(errorMessage)
			simLengthValue = rowCount-1
		except:
			#TODO change to an appropriate warning message
			errorMessage = "CSV file is incorrect format. Please see valid format definition at <a target='_blank' href='https://github.com/dpinney/omf/wiki/Models-~-demandResponse#walkthrough'>OMF Wiki demandResponse</a>"
			raise Exception(errorMessage)

		#create breakpoints.csv file in folder
		# f1Name = "breakpoints.csv"
		# with open(pJoin(omf.omfDir, "static", "testFiles", "pyCIGAR", f1Name)) as f1:
		# 	breakpoints_inputs = f1.read()
		with open(pJoin(modelDir,"PyCIGAR_inputs","breakpoints.csv"),"w") as breakpointsFile:
			breakpointsFile.write(inputDict['breakpoints'])

		# Open defense agent HDF5(pb?) file if it was uploaded
		with open(pJoin(modelDir,"PyCIGAR_inputs","defenseAgent.pb"),"w") as defenseVariableFile:
			if inputDict['defenseVariable'] == "":
				defenseVariableFile.write("No Defense Agent Variable File Uploaded")
			else:
				defenseVariableFile.write(inputDict['defenseVariable'])

		return simLengthValue

	simLengthValue = convertInputs()

	#simLengthAdjusted accounts for the offset by startStep
	simLengthAdjusted = simLengthValue - startStep
	#hard-coding simLengthAdjusted for testing purposes 
	simLengthAdjusted = 750

	outData = {}
	# Std Err and Std Out
	outData['stderr'] = "This should be stderr"  #rawOut['stderr']
	outData['stdout'] = "This should be stdout"  #rawOut['stdout']
	
	# Create list of timestamps for simulation steps
	outData['timeStamps'] = []
	start_time = dt_parser.isoparse(simStartDateTimeValue)
	for single_datetime in (start_time + timedelta(seconds=n) for n in range(simLengthAdjusted)):
		single_datetime_str = single_datetime.strftime("%Y-%m-%d %H:%M:%S%z") 
		outData['timeStamps'].append(single_datetime_str)

	# Day/Month Aggregation Setup:
	stamps = outData.get('timeStamps',[])
	level = inputDict.get('simLengthUnits','seconds')

	# TODO: Create/populate Climate data without gridlab-d
	outData['climate'] = {}
	outData['allMeterVoltages'] = {}
	outData['allMeterVoltages']['Min'] = [0] * int(simLengthAdjusted)
	outData['allMeterVoltages']['Mean'] = [0] * int(simLengthAdjusted)
	outData['allMeterVoltages']['StdDev'] = [0] * int(simLengthAdjusted)
	outData['allMeterVoltages']['Max'] = [0] * int(simLengthAdjusted)
	# Power Consumption
	outData['Consumption'] = {}
	# Set default value to be 0, avoiding missing value when computing Loads
	outData['Consumption']['Power'] = [0] * int(simLengthAdjusted)
	outData['Consumption']['Losses'] = [0] * int(simLengthAdjusted)
	outData['Consumption']['DG'] = [0] * int(simLengthAdjusted)
	
	outData['swingTimestamps'] = []
	outData['swingTimestamps'] = outData['timeStamps']

	# Aggregate up the timestamps:
	if level=='days':
		outData['timeStamps'] = aggSeries(stamps, stamps, lambda x:x[0][0:10], 'days')
	elif level=='months':
		outData['timeStamps'] = aggSeries(stamps, stamps, lambda x:x[0][0:7], 'months')
		

	def runPyCIGAR():
		#create the pycigarOutput folder to store the output file(s) generated by PyCIGAR
		try:
			os.mkdir(pJoin(modelDir,"pycigarOutput"))
		except FileExistsError:
			print("pycigarOutput folder already exists!")
			pass
		except:
			print("Error occurred creating pycigarOutput folder")

		#import and run pycigar
		import pycigar

		#Set up runType scenarios
		#runType of 2 implies the base scenario - not training a defense agent, nor is there a defense agent entered
		runType = 2
		tempDefenseAgent = None #TODO: change tempDefenseAgent to be !None if defense agent file is input

		# check to see if we are trying to train a defense agent
		if trainAgentValue:	
			#runType of 0 implies the training scenario - runs to train a defense agent and outputs a zip containing defense agent files
			runType = 0 

		#check to see if user entered a defense agent file
		elif tempDefenseAgent != None:
			tempDefenseAgent = modelDir + "/PyCIGAR_inputs/defenseAgent.pb"
			#runType of 1 implies the defense scenario - not training a defense agent, but a defense agent zip was uploaded
			runType = 1 

		# TODO how to factor attackAgentType into pycigar inputs
		# if there is no training selected and no attack variable, run without a defense agent
		pycigar.main(
			modelDir + "/PyCIGAR_inputs/misc_inputs.csv",
			modelDir + "/PyCIGAR_inputs/circuit.dss",
			modelDir + "/PyCIGAR_inputs/load_solar_data.csv",
			modelDir + "/PyCIGAR_inputs/breakpoints.csv",
			runType,
			tempDefenseAgent,
			modelDir + "/pycigarOutput/",
			start=startStep,
			duration=simLengthAdjusted,
			hack_start=250,
			hack_end=None,
			percentage_hack=0.45
		)

		#print("Got through pyCigar!!!")
		

	def convertOutputs():
		#set outData[] values to those from modelDir/pycigarOutput/pycigar_output_specs_.json
		#read in the pycigar-outputed json
		with open(pJoin(modelDir,"pycigarOutput","pycigar_output_specs.json"), 'r') as f:
			pycigarJson = json.load(f)
		
		#convert "allMeterVoltages"
		outData["allMeterVoltages"] = pycigarJson["allMeterVoltages"]
		
		#convert "Consumption"."Power"
		# HACK! Units are actually kW. Needs to be fixed in pyCigar.
		outData["Consumption"]["Power"] = pycigarJson["Consumption"]["Power Substation (W)"]

		#convert "Consumption"."Losses"
		outData["Consumption"]["Losses"] = pycigarJson["Consumption"]["Losses Total (W)"]

		#convert "Consumption"."DG"
		outData["Consumption"]["DG"] = [-1.0 * x for x in pycigarJson["Consumption"]["DG Output (W)"]]

		#convert "powerFactors"
		outData["powerFactors"] = pycigarJson["Substation Power Factor (%)"]	

		#convert "swingVoltage"
		outData["swingVoltage"] = pycigarJson["Substation Top Voltage(V)"]

		#convert "downlineNodeVolts"
		outData["downlineNodeVolts"] = pycigarJson["Substation Bottom Voltage(V)"]

		#convert "minVoltBand"
		outData["minVoltBand"] = pycigarJson["Substation Regulator Minimum Voltage(V)"]

		#convert "maxVoltBand"
		outData["maxVoltBand"] = pycigarJson["Substation Regulator Maximum Voltage(V)"]

		#create lists of circuit object names
		regNameList = []
		capNameList = []
		for key in pycigarJson:
			if key.startswith('Regulator_'):
				regNameList.append(key)
			elif key.startswith('Capacitor_'):
				capNameList.append(key)

		#convert regulator data
		for reg_name in regNameList:
			outData[reg_name] = {}
			regPhaseValue = pycigarJson[reg_name]["RegPhases"]
			if regPhaseValue.find('A') != -1:
				outData[reg_name]["RegTapA"] = pycigarJson[reg_name]["creg1a"]

			if regPhaseValue.find('B') != -1:
				outData[reg_name]["RegTapB"] = pycigarJson[reg_name]["creg1b"]

			if regPhaseValue.find('C') != -1:
				outData[reg_name]["RegTapC"] = pycigarJson[reg_name]["creg1c"]

			outData[reg_name]["RegPhases"] = regPhaseValue

		#convert inverter data
		inverter_output_dict = {} 
		for inv_dict in pycigarJson["Inverter Outputs"]:
			#create a new dictionary to represent the single inverter 
			new_inv_dict = {}
			#get values from pycigar output for given single inverter
			inv_name = inv_dict["Name"]
			inv_volt = inv_dict["Voltage (V)"]
			inv_pow_real = inv_dict["Power Output (W)"]
			inv_pow_imag = inv_dict["Reactive Power Output (VAR)"]
			#populate single inverter dict with pycigar values
			new_inv_dict["Voltage"] = inv_volt
			new_inv_dict["Power_Real"] = inv_pow_real
			new_inv_dict["Power_Imag"] = inv_pow_imag
			#add single inverter dict to dict of all the inverters using the inverter name as the key 
			inverter_output_dict[inv_name] = new_inv_dict
		outData["Inverter_Outputs"] = inverter_output_dict

		#convert capacitor data - Need one on test circuit first!
		for cap_name in capNameList:
			outData[cap_name] = {}
			capPhaseValue = pycigarJson[cap_name]["CapPhases"]
			if capPhaseValue.find('A') != -1:
				outData[cap_name]['Cap1A'] = [0] * int(simLengthValue)
				outData[cap_name]['Cap1A'] = pycigarJson[cap_name]['switchA']

			if capPhaseValue.find('B') != -1:
				outData[cap_name]['Cap1B'] = [0] * int(simLengthValue)
				outData[cap_name]['Cap1B'] = pycigarJson[cap_name]['switchB']

			if capPhaseValue.find('C') != -1:
				outData[cap_name]['Cap1C'] = [0] * int(simLengthValue)
				outData[cap_name]['Cap1C'] = pycigarJson[cap_name]['switchC']
			
			outData[cap_name]["CapPhases"] = capPhaseValue

		outData["stdout"] = pycigarJson["stdout"]

	runPyCIGAR()
	convertOutputs()
	return outData

def avg(inList):
	''' Average a list. Really wish this was built-in. '''
	return sum(inList)/len(inList)

def hdmAgg(series, func, level):
	''' Simple hour/day/month aggregation for Gridlab. '''
	if level in ['days','months']:
		return aggSeries(stamps, series, func, level)
	else:
		return series

def aggSeries(timeStamps, timeSeries, func, level):
	''' Aggregate a list + timeStamps up to the required time level. '''
	# Different substring depending on what level we aggregate to:
	if level=='months': endPos = 7
	elif level=='days': endPos = 10
	combo = list(zip(timeStamps, timeSeries))
	# Group by level:
	groupedCombo = _groupBy(combo, lambda x1,x2: x1[0][0:endPos]==x2[0][0:endPos])
	# Get rid of the timestamps:
	groupedRaw = [[pair[1] for pair in group] for group in groupedCombo]
	return list(map(func, groupedRaw))

def _pyth(x,y):
	''' Compute the third side of a triangle--BUT KEEP SIGNS THE SAME FOR DG. '''
	sign = lambda z:(-1 if z<0 else 1)
	fullSign = sign(sign(x)*x*x + sign(y)*y*y)
	return fullSign*math.sqrt(x*x + y*y)

def _digits(x):
	''' Returns number of digits before the decimal in the float x. '''
	return math.ceil(math.log10(x+1))

def vecPyth(vx,vy):
	''' Pythagorean theorem for pairwise elements from two vectors. '''
	rows = zip(vx,vy)
	return [_pyth(*x) for x in rows]

def vecSum(*args):
	''' Add n vectors. '''
	return list(map(sum,zip(*args)))

def _prod(inList):
	''' Product of all values in a list. '''
	return reduce(lambda x,y:x*y, inList, 1)

def vecProd(*args):
	''' Multiply n vectors. '''
	return list(map(_prod, zip(*args)))

def threePhasePowFac(ra,rb,rc,ia,ib,ic):
	''' Get power factor for a row of threephase volts and amps. Gridlab-specific. '''
	pfRow = lambda row:math.cos(math.atan((row[0]+row[1]+row[2])/(row[3]+row[4]+row[5])))
	rows = zip(ra,rb,rc,ia,ib,ic)
	return list(map(pfRow, rows))

def roundSeries(ser):
	''' Round everything in a vector to 4 sig figs. '''
	return [roundSig(x, 4) for x in ser]

def _groupBy(inL, func):
	''' Take a list and func, and group items in place comparing with func. Make sure the func is an equivalence relation, or your brain will hurt. '''
	if inL == []: return inL
	if len(inL) == 1: return [inL]
	newL = [[inL[0]]]
	for item in inL[1:]:
		if func(item, newL[-1][0]):
			newL[-1].append(item)
		else:
			newL.append([item])
	return newL

def stringToMag(s):
	if 'd' in s:
		return complex(s.replace('d','j')).real
	elif 'j' in s or 'i' in s:
		return abs(complex(s.replace('i','j')))


def new(modelDir):
	''' Create a new instance of this model. Returns true on success, false on failure. '''
	f1Name = "load_solar_data.csv"
	with open(pJoin(omf.omfDir, "static", "testFiles", "pyCIGAR", f1Name)) as f1:
		load_PV = f1.read()

	f2Name = "breakpoints.csv"
	with open(pJoin(omf.omfDir, "static", "testFiles", "pyCIGAR", f2Name)) as f2:
		breakpoints_inputs = f2.read()

	f3Name = "ieee37.dss"
	with open(pJoin(omf.omfDir, "static", "testFiles", "pyCIGAR", f3Name)) as f3:
		dssFile = f3.read()

	f4Name = "misc_inputs.csv"
	with open(pJoin(omf.omfDir, "static", "testFiles", "pyCIGAR", f4Name)) as f4:
		miscFile = f4.read()

	defaultInputs = {
		"simStartDate": "2019-07-01T00:00:00Z",
		"simLengthUnits": "seconds",
		# "feederName1": "ieee37fixed",
		"feederName1": "Olin Barre GH EOL Solar AVolts CapReg",
		"modelType": modelName,
		"zipCode": "59001",
		"loadPV": load_PV,
		"breakpoints": breakpoints_inputs,
		"dssFile": dssFile,
		"miscFile": miscFile,
		"trainAgent": "False",
		"attackVariable": "None",
		"defenseVariable": "None"
	}
	creationCode = __neoMetaModel__.new(modelDir, defaultInputs)
	try:
		shutil.copyfile(pJoin(__neoMetaModel__._omfDir, "static", "publicFeeders", defaultInputs["feederName1"]+'.omd'), pJoin(modelDir, defaultInputs["feederName1"]+'.omd'))
	except:
		return False
	return creationCode

@neoMetaModel_test_setup
def _tests():
	# Location
	modelLoc = pJoin(__neoMetaModel__._omfDir,"data","Model","admin","Automated Testing of " + modelName)
	# Blow away old test results if necessary.
	try:
		shutil.rmtree(modelLoc)
	except:
		# No previous test results.
		pass
	# Create New.
	new(modelLoc)
	# Pre-run.
	# __neoMetaModel__.renderAndShow(modelLoc)
	# Run the model.
	__neoMetaModel__.runForeground(modelLoc)
	# Show the output.
	__neoMetaModel__.renderAndShow(modelLoc)

if __name__ == '__main__':
	_tests()