#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb  7 11:20:08 2024
Changed: 7.11.2025

@author: Fabrizio, (changed by niklas)

This script will run the Experiment 1_A of the NVP_ratCL_05_ Experiments defined in:  https://docs.google.com/document/d/1BmLcY70xOPmVm7B05kRrnfJhQXqwfQyuRvYxLQ4PX_k/edit?tab=t.0 

Duration about 17 minutes

Ready Status: Need to implembent _TIME_BETWEEN_STIMULATIONS properly
"""


#%% Path and Parameters
# Params to be set by UMH
_STIMULATION_ELECTRODE = xy # electrode to stimulate set to a working electrode that can be used for closed loop testing. keep this electrode for all the tests


# Params preset by INI (Niklas), can be changed if required
_TARGET_THRESHOLDS = [10,25,50,75] # target thresholds for the stimulation 

_MAX_CURRENT = 30 # maximum current in uA
_CURRENT_STEP_SIZE = 3 # step size in uA to increase the Current for the closed loop
_AMOUNT_OF_STIMULATIONS = 50 # number of stimulations with each parameter configuration
_TIME_BETWEEN_STIMULATIONS = 5 # time between stimulations in seconds
_FILENAME_BASE = 'NVP_ratCL_05_Exp1_A' # base name for the files


dummy_run = False  # Set to True to run without the hardware
path_save = r'C:\Users\s\Desktop\Closed_Loop_Neuroviper\data\closed_loop\\'
path_proto = 'C:/Users/s/Desktop/Closed_Loop_Neuroviper/protocols/'  # Path to the protocol files



num_opt = _AMOUNT_OF_STIMULATIONS  # number of closed loop runs  
fs = 30000   # sampling frequency
STIM_EL = [_STIMULATION_ELECTRODE]  # Electrodes to stimulate
REC_EL = _STIMULATION_ELECTRODE   # electrode to record from
npoints = fs*3  #number of samples you want to get from the recording
#means_it = 5   #number of times to repeat the stimulation to create an average response, not used anymore


# LFP-RMS calculation parameters
window_size = 0.5  # window size in seconds to calculate the activity over
offset_to_stim = 0.1 # offset in seconds to the stimulation start / stop


# ToDO
# Is the data also recorded in the meantime?
# Remoive / change channel mapping


def runExperiments(Threshold):
    
    #Import Libraries

    # Dummy function when not using the hardware
    if not dummy_run:
        import xipppy as xp
    else:
        class DummyXP:
            def __init__(self):
                pass
            def list_elec(self, type):
                return [1,2,3,4,5,6,7,8,9,10]
            def __getattr__(self, name):
                def method(*args, **kwargs):
                    return None
                return method

        xp = DummyXP()

    from ripple_driver.stim_driver import Ripple_Driver

    import numpy as np
    from random import randint
    import copy
    import random
    from datetime import datetime
    import matplotlib.pyplot as plt
    from scipy import signal
    import time



    """
    Main function for executing the closed-loop stimulation experiment.
    This function performs the following steps:
    1. Sets up the necessary variables and parameters.
    2. Opens the communication with the Ripple device and enables stimulation.
    3. Creates a driver manager and connects to the device.
    4. Starts recording the data.
    5. Loads an example stimulation and modifies its parameters.
    6. Executes the stimulation pattern and records the activity.
    7. Calculates the feedback based on the recorded activity.
    8. Updates the model function.
    9. Saves the metadata.
    10. Stops the recording and closes the communication with the Ripple device.
    Returns:
        None
    """

    today = datetime.now().strftime("%Y_%m_%d")
    dt_string = datetime.now().strftime("%d_%m_%Y_%H_%M_%S")
    file_save = dt_string + _FILENAME_BASE +  f'_threshold_{Threshold}'

    CURRENT = np.repeat(3, len(STIM_EL))  # start value of 3 uA
    offset = [0,0,0,0,0,0,0,0,0,0,0,0,0] # How to use and what is the meaning of this offset? And how is compased for it later on?
    OFFSET = offset[:len(STIM_EL)]  

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
    # RIPPLE.record(path=path_trellis)

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
    OFFSET_value = []
    STIM_CONFIG = []
    RIPPLE._delay(1)



    for rep in range(num_opt):
        
        #create the stimulation pattern
        stim_electrodes = STIM_EL
        stim_current = CURRENT
        off_interleaving = offset[:len(stim_electrodes)]
        
        ELECTRODES.append(stim_electrodes)
        CURRENTS.append(stim_current)
        OFFSET_value.append(off_interleaving)
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

            config['offset'] = off_interleaving[i]
            config['interpulse']= -0.4 + 1000/config['frequency'] -off_interleaving[i]
            # there are more configs parameers that can be changed
            configs.append(config)
        stimulus['configIDs'] = configIDs
        stimulus['configs'] = configs
        stimulus['electrodes'] = electrodes
        protocols['stim'][3]['params'] = stimulus
        STIM_CONFIG.append(copy.deepcopy(stimulus))
        STIM_PATTERNS = RIPPLE.precompile(protocols)  
        
        
        elecs_stim = xp.list_elec('stim')
        
        t1 = time.time()
        ACTIVITY = []

        RIPPLE.shoot(STIM_PATTERNS['stim']) #send the stimulation
        RIPPLE._delay(1.5)          #wait 500ms
        (data, _) = xp.cont_raw(npoints, elecs_stim)    #get the data (last 3*30000 samples)       
        
        if len(data) == number_electrodes*npoints:
            data = np.reshape(np.array(data), (number_electrodes,npoints))     #reshape the data, we have 48 channels so maybe like this ?
        else:
            data = np.reshape(np.array(data), (number_electrodes,npoints-1)) 
        data=data[:number_electrodes,:]
        plt.figure()
        plt.plot(data[REC_EL,:])

        #find artifact (so that I know where the stimulation strted)
        idx_0 = []
        for ch in range(number_electrodes):
            idx_0.append(np.where(data[ch,:]==0)[0]) # find the stimulation start
        common_values = set(idx_0[0])  # find the common values in all the channels
        for idx in idx_0[1:]:   #
            common_values.intersection_update(idx)
        common_values = list(common_values)
        common_values.sort()
        tr = common_values[0]
        plt.plot(tr,0,'x')
        #extract mua (here you will put your data activity calculation)

        stim_duration = config['duration']/1000 # in seconds
        
        plt.plot(tr- offset_to_stim*fs - window_size*fs,0,'xr')
        plt.plot(tr - offset_to_stim*fs,0,'xr')
        plt.plot(tr+stim_duration*fs+offset_to_stim*fs,0,'xg')
        plt.plot(tr+ stim_duration*fs+ offset_to_stim*fs+window_size*fs,0,'xg')
        
        
        # only do for one channel
        dat_before = data[REC_EL,int((tr- offset_to_stim*fs - window_size*fs)):int((tr - offset_to_stim*fs))]
        dat_cond  = data[REC_EL,int((tr+stim_duration*fs+offset_to_stim*fs)):int((tr+ stim_duration*fs+ offset_to_stim*fs+window_size*fs))]
        
        activity = LFP(dat_cond, fs=fs) - LFP(dat_before, fs=fs)
                
            
        RIPPLE._delay(0.5) 

        NEW_Current = calc_feedback_1ch(activity, STIM_EL, CURRENT)
        print(f'Currents: {CURRENT} -> {NEW_Current}')
        CURRENT = NEW_Current
        t2 = time.time()
        print(f' time spent stimulating {t2 - t1}')    
        
        # wait for keybord input to continue
        input('Press Enter to continue')


        #update model function
        # STIM_EL, CURRENT = MODEL(ACTIVITY)


    print('ALMOST FINISH')
    RIPPLE._delay(5)

    METADATA = dict()
    METADATA['ELECTRODES']=ELECTRODES
    METADATA['CURRENTS']=CURRENTS
    METADATA['STIM_CONFIG']=STIM_CONFIG
    METADATA['OFFSET']=OFFSET
    METADATA['REC_EL'] = REC_EL

    np.save(path_save + file_save + '_metadata.npy',METADATA)     

    #END RECORDING
    # RIPPLE.stop(path=path_trellis)file_save = 'trial'


    xp.trial(oper=129,status='stopped', file_name_base=path_trellis)
    xp._close()






def LFP(signal_in, fs=30000):

    # Calculating LFP
    # Remove artifacts
    index = np.where(signal_in < -5000)[0]
    for i in index:
        signal_in[i] = signal_in[i-1] # 
    
    
    #FIlter between 500 and 9000
    cof=np.array([10,200])
    Wn = 2*cof/fs
    Wn[Wn >= 1] = 0.99
    [B, A] = signal.butter(2, Wn, 'bandpass')
    LFP = signal.filtfilt(B,A,signal_in)

    LFP = np.sqrt(np.mean(LFP**2))

    return LFP


def calc_feedback(activity, STIM_EL, CURRENT, threshold, step=_CURRENT_STEP_SIZE, max_current=_MAX_CURRENT):
    # Calculate
    for i, ch in enumerate(STIM_EL):
        if activity[ch] < threshold:
            CURRENT[i] = CURRENT[i] + step
        else:
            CURRENT[i] = CURRENT[i] - step
        if CURRENT[i] > max_current: CURRENT[i] = max_current
        if CURRENT[i] < 0: CURRENT[i] = 0

def calc_feedback_1ch(activity, STIM_EL, current_loc, threshold, step=_CURRENT_STEP_SIZE, max_current=_MAX_CURRENT):
    # Calculate
    if activity < threshold:
        current_loc = current_loc + step
    else:
        current_loc = current_loc - step
    if current_loc[0] > max_current: 
        current_loc = [max_current]*len(current_loc)
    if current_loc[0] < 0: 
        current_loc = [0]*len(current_loc)

    return current_loc
#%% Path and Parameters




if __name__ == '__main__':

    for threshold in _TARGET_THRESHOLDS:  # Run all the thresholds as separate experiments in different files
        runExperiments(threshold)
