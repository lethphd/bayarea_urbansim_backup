import os
import sys
import time
import traceback
import models
import pandas as pd
import orca
import socket
import warnings

warnings.filterwarnings("ignore")

args = sys.argv[1:]

SLACK = MAPS = False
LOGS = True
INTERACT = False
S3 = False
EVERY_NTH_YEAR = 5
CURRENT_COMMIT = os.popen('git rev-parse HEAD').read()

orca.add_injectable("years_per_iter", EVERY_NTH_YEAR)

if len(args) and args[0] == "-i":
    SLACK = MAPS = LOGS = False
    INTERACT = True

if INTERACT:
    import code
    code.interact(local=locals())
    sys.exit()

run_num = orca.get_injectable("run_number")
if LOGS:
    print '***The Standard stream is being written to /logs/sim_out{0}***'\
        .format(run_num)
    sys.stdout = sys.stderr = open("logs/sim_out_%d" % run_num, 'w')

if SLACK:
    from slacker import Slacker
    slack = Slacker('xoxp-7025187590-7026053537-7111663091-9eeeb6')
    host = socket.gethostname()

print "Started", time.ctime()
print "Current Commit : ", CURRENT_COMMIT.rstrip()
print "Current Scenario : ", orca.get_injectable('scenario').rstrip()
in_year, out_year = 2010, 2011

if SLACK:
    slack.chat.post_message(
        '#sim_updates',
        'Starting simulation %d on host %s' % (run_num, host))

try:
    orca.run([
        "neighborhood_vars",            # local accessibility vars
        "regional_vars",                # regional accessibility vars

        "rsh_simulate",                 # residential sales hedonic
        "nrh_simulate",                 # non-residential rent hedonic

        "households_transition",

        "jobs_transition",

        "hlcm_simulate",                 # put these last so they don't get
        "elcm_simulate",                 # displaced by new dev

        "travel_model_output"
    ], iter_vars=range(in_year, out_year+1, EVERY_NTH_YEAR))

except Exception as e:
    print traceback.print_exc()
    if SLACK:
        slack.chat.post_message(
            '#sim_updates',
            'DANG!  Simulation failed for %d on host %s'
            % (run_num, host))
    else:
        raise e
    sys.exit(0)

print "Finished", time.ctime()

if MAPS:
    try:
        os.system('python scripts/explorer.py %d' % run_num)
        os.system('python scripts/compare_to_targets.py %d' % run_num)
        os.system('python scripts/make_pda_result_maps.py %d' % run_num)
    except Exception as e:
        if SLACK:
            slack.chat.post_message(
                '#sim_updates',
                'DANG! Output generation failed for %d on host %s'
                % (run_num, host))
        else:
            raise e
        sys.exit(0)

if S3:
    try:
        os.system(
            'ls runs/run%d_* ' % run_num + 
            '| xargs -I file aws s3 cp file ' +
            's3://bayarea-urbansim-results')
    except Exception as e:
        raise e
    sys.exit(0)

if SLACK:
    slack.chat.post_message(
        '#sim_updates',
        'Completed simulation %d on host %s' % (run_num, host))

    slack.chat.post_message(
        '#sim_updates',
        'UrbanSim explorer is available at ' +
        'http://urbanforecast.com/sim_explorer%d.html' % run_num)

    slack.chat.post_message(
        '#sim_updates',
        'PDA target comparison is available at ' +
        'http://urbanforecast.com/scratchpad/results_%d.html' % run_num)