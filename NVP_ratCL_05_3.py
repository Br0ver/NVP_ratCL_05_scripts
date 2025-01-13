#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  7 11:20:08 2024
Changed: Sep 3 2024

@author: Fabrizio, (changed by niklas)


This script will run the Experiment 3 of the NVP_ratCL_05_ Experiments defined in:  https://docs.google.com/document/d/1BmLcY70xOPmVm7B05kRrnfJhQXqwfQyuRvYxLQ4PX_k/edit?tab=t.0 


Duration about 100 minutes
Changes:
  - Added the extra electrodes to the stimulation electrodes
  - set random current for extra electrodes

Ready Status: Needs to check for _TIME_BETWEEN_STIMULATIONS to set as short as possible to still get measurements in between approx 600 ms?

"""
import xipppy as xp
from ripple_driver.stim_driver import Ripple_Driver
import numpy as np
from random import randint
import copy
import random
from datetime import datetime
import matplotlib.pyplot as plt
from scipy import signal
import time

#%% Path and Parameters

# Params preset by INI (Niklas), can be changed if required
_CURRENTS_FOR_TRIAL = [5,10,15,20,25,30]
REPETITIONS = 100 # 25
_TIME_BETWEEN_STIMULATIONS = 0.6 # time between stimulations in seconds
_FILENAME_BASE = 'NVP_ratCL_05_Exp3_' # base name for the files
_SEED = 42

# Params to be set by UMH
_STIMULATION_ELECTRODE = None # electrode to stimulate set to a working electrode that can be used for closed loop testing. keep this electrode for all the tests, write as integer e.g. 19
if _STIMULATION_ELECTRODE is None: raise ValueError("Stimulation electrode not set")


path_save = r'C:\Users\s\Desktop\Closed_Loop_Neuroviper\data\\'
file_save = 'trial'
path_proto = 'C:/Users/s/Desktop/Closed_Loop_Neuroviper/protocols/'  # Path to the protocol files

fs = 30000   # sampling frequency
random.seed(_SEED)



def main(CURRENT):
    STIM_EL = [_STIMULATION_ELECTRODE]
    STIM_EL_LIST = []
    for i in range(REPETITIONS*len(CURRENT)):
        STIM_EL_LIST.append(STIM_EL)
        
    CURRENT_LIST = []
    for i in range(len(CURRENT)):
        CURRENT_LIST.append([CURRENT[i]] * len(STIM_EL))
    CURRENT_LIST = CURRENT_LIST * REPETITIONS

    indeces = list(range(len(CURRENT_LIST)))
    random.shuffle(indeces)



    STIM_EL_LIST =[STIM_EL_LIST[i] for i in indeces]
    CURRENT_LIST =[CURRENT_LIST[i] for i in indeces]

  

    METADATA = dict()
    METADATA['stim_el_list']= STIM_EL_LIST
    METADATA['current_list']= CURRENT_LIST

    #%% Import Libraries

    today = datetime.now().strftime("%Y_%m_%d")
    dt_string = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    file_save = dt_string + _FILENAME_BASE  + str(CURRENT[0]) + "uA_"
    

    # open xp communication with ripple and enable stim
    xp._open(use_tcp=True)
    xp.stim_enable_set(True)
    xp.stim_enable()

    elecs = xp.list_elec('stim')
    number_electrodes = len(elecs)
    [xp.signal_set_raw(elec, 1) for elec in elecs]

    # CREATE DRIVER MANAGER AND CONNECT THE DEVICE
    RIPPLE = Ripple_Driver()
    RIPPLE.open_device()

    #START RECORDING
    path_trellis = path_save + file_save + '_trellis'
    operator=xp.add_operator(129)
    xp.trial(oper=129,status='recording', file_name_base=path_trellis)


    # load an example stimulation to change the parameters
    lookup = dict({'stim_A':'example.npy'})
    stim = 'stim_A'
    patterns = list(lookup.values())
    protocols = RIPPLE.load_patterns(patterns, path_proto)
    protocols['stim'] = protocols.pop('example.npy')

    stimulus = copy.deepcopy(protocols['stim'][3]['params'])
    config_example = copy.deepcopy(stimulus['configs'][0])

    ELECTRODES = []
    CURRENTS = []
    STIM_CONFIG = []
    RIPPLE._delay(1)

    for rep in range(len(STIM_EL_LIST)):
        
        #create the stimulation pattern
        stim_electrodes = STIM_EL_LIST[rep]
        stim_current = CURRENT_LIST[rep]
        
        ELECTRODES.append(stim_electrodes)
        CURRENTS.append(stim_current)
        configIDs = []
        configs = []
        electrodes = []
        for i in range(len(stim_electrodes)):
            if stim_electrodes[i]<10:
                electrodes.append('0' + str(stim_electrodes[i]))            
            else:
                electrodes.append(str(stim_electrodes[i]))
            configIDs.append(i)
            config = copy.deepcopy(config_example)
            config['frequency'] = 100
            config['ID'] = i
            config['phase1'] = -stim_current[i]
            config['phase2'] = stim_current[i]
            config['pulses'] = 10

            config['duration'] = np.ceil(config['pulses'] / config['frequency']  * 1000) # milliseconds is related to pulses and frequency

            config['offset'] = 0
            config['interpulse']= -0.4 + 1000/config['frequency'] - 0
            # there are more configs parameers that can be changed
            configs.append(config)
        stimulus['configIDs'] = configIDs
        stimulus['configs'] = configs
        stimulus['electrodes'] = electrodes
        protocols['stim'][3]['params'] = stimulus
        STIM_CONFIG.append(copy.deepcopy(stimulus))
        STIM_PATTERNS = RIPPLE.precompile(protocols)  
            
        RIPPLE.shoot(STIM_PATTERNS['stim']) #send the stimulation
        RIPPLE._delay(_TIME_BETWEEN_STIMULATIONS)          #wait 

    print('ALMOST FINISH')
    RIPPLE._delay(5)

    METADATA['ELECTRODES']=ELECTRODES
    METADATA['CURRENTS']=CURRENTS
    METADATA['STIM_CONFIG']=STIM_CONFIG

    np.save(path_save + file_save + '_metadata.npy',METADATA)     

    #END RECORDING
    # RIPPLE.stop(path=path_trellis)

    xp.trial(oper=129,status='stopped', file_name_base=path_trellis)
    xp._close()


if __name__ == '__main__':

    for current in _CURRENTS_FOR_TRIAL:
        main([current])
        time.sleep(5)  # wait 5 seconds between trials
