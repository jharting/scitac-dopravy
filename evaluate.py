import itertools
import os
import re
import math
import pygsheets
import pandas as pd
import argparse

parser = argparse.ArgumentParser(description='Traffic count evaluator')
parser.add_argument('-saf', '--service-account-file', help='Path to the file containing Google API service account token', default='service-account.json')
parser.add_argument('-d', '--document', help='Name of the Google Sheets document to update')
parser.add_argument('-s', '--sheet', help='Index of the sheet in the Google Sheets document to update', type=int, default=0)
parser.add_argument('-w', '--workdir', default="workdir")
parser.add_argument('--interval-start', type=int, default=7, help="Start hour of the monitored interval (inclusive)")
parser.add_argument('--interval-end', type=int, default=17, help="End hour of the monitored interval (exclusive)")
parser.add_argument('-f', '--format', help="Output format ('full' or 'summary')", choices=['summary', 'full'], default="summary")
args = parser.parse_args()

hit_pattern=re.compile('^([\d]{4}-[\d]{2}-[\d]{2})T([\d]{2}):([\d]{2}):[\d]{2}.[\d]+\.(jpg|txt|jpg)$')

def find_all(workdir):
    hits = []

    for _, _, files in sorted(os.walk(workdir, topdown=False)):
        for file in files:
            if re.search(hit_pattern, file):
                hits.append(file)

    return hits

def interval_predicate(hit):
    matched = hit_pattern.match(hit)    
    hour = int(matched.group(2))
    return hour >= args.interval_start and hour < args.interval_end

def filter_interval(hits):
    return [hit for hit in hits if interval_predicate(hit)]

# identifies the corresponding 15-minute bucket for each hit
def grouping_key(key):
    matched = hit_pattern.match(key)
    date = matched.group(1)
    hour = matched.group(2)
    minute = matched.group(3)
    quarter = math.floor(int(minute) / 15) * 15

    result = "%sT%s:%02d" % (date, hour, quarter)
    return result


def next_quarter(time):
    hour, minute = time.split(":")
    quarter = math.floor(int(minute) / 15)
    next_hour = (int(hour) + math.floor((quarter + 1) / 4)) % 24
    next_minute = ((quarter + 1) % 4) * 15
    return "%02d:%02d" % (next_hour, next_minute)

def floating_hour_count(entries, date, start, count):
    if len(entries) < 3:
        return "", ""

    for i in range(3):
        previous = entries[-(i+1)]
        if previous[0] != date or previous[2] != start:
            return "", ""
        count += previous[3]
        start = previous[1]
    
    return count, "=SUM(D%d:D%d)" % (len(entries) - 1, len(entries) + 2)

def process(hits):
    hits = sorted(hits)
    entries = []

    grouped = itertools.groupby(hits, key=grouping_key)

    for k, g in grouped:
        date, time = k.split("T")
        stop = next_quarter(time)
        count = len(list(g))
        floating_count, floating_count_formula = floating_hour_count(entries, date, time, count)

        entries.append([
            date,
            time,
            stop,
            count,
            floating_count,
            floating_count_formula
        ])
    return entries

def summarize(entries):
    results = []

    for k, v in itertools.groupby(entries, key=lambda entry: entry[0]):
        group = list(v)
        daily_max = max(group, key=lambda x: int(x[4]) if x[4] != '' else 0)
        if daily_max[4] == '':
            continue
        
        index = group.index(daily_max)
        results.append([daily_max[0], group[index - 3][1], daily_max[2], daily_max[4]])

    return results

def present(entries):
    for entry in entries:
        print(", ".join(str(i) for i in entry[0:5]))

def present_to_sheets(entries, summarized):
    df = pd.DataFrame()

    date = []
    start = []
    stop = []
    count = []
    floating_hour_count_formula = []
    peak_hour_formula = []

    for e in entries:
        date.append(e[0])
        start.append(e[1])
        stop.append(e[2])
        count.append(e[3])

        if not summarized:
            floating_hour_count_formula.append(e[5])
            peak_hour_formula.append('=IF(INDIRECT("E" & ROW()) = MAXIFS(E$2:E, A$2:A, INDIRECT("A" & ROW())), INDIRECT("E" & ROW()), "")')

    df['date'] = date
    df['start'] = start
    df['stop'] = stop

    if not summarized:
        df['count'] = count
        df['floating hour count'] = floating_hour_count_formula
        df['peak hour'] = peak_hour_formula
    else:
        df['peak hour'] = count
    
    return df

def upload_to_sheets(df):
    gc = pygsheets.authorize(service_file=args.service_account_file)

    sh = gc.open(args.document)

    #select the first sheet 
    wks = sh[args.sheet]
    wks.set_dataframe(df,(1,1))

hits = find_all(args.workdir)
hits = filter_interval(hits)
results = process(hits)

if args.format == 'summary':
    results = summarize(results)
present(results)

if args.document:
    sheet = present_to_sheets(results, args.format == 'summary')
    upload_to_sheets(sheet)