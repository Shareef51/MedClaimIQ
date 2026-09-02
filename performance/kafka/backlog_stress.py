#!/usr/bin/env python3
"""Synthetic Kafka backlog recovery model with optional live broker mode kept separate.
This script deliberately measures drain mathematics without pretending a local CI runner is a production broker.
"""
from __future__ import annotations
import argparse, json, math

def simulate(backlog:int, producer_eps:float, consumer_eps:float, max_minutes:int):
    remaining=float(backlog); seconds=0
    while remaining>0 and seconds<max_minutes*60:
        remaining=max(0.0, remaining + producer_eps - consumer_eps); seconds += 1
    return {'initial_backlog':backlog,'producer_eps':producer_eps,'consumer_eps':consumer_eps,'recovered':remaining==0,'recovery_seconds':seconds if remaining==0 else None,'remaining':round(remaining,2)}

def main():
    p=argparse.ArgumentParser(); p.add_argument('--backlog',type=int,default=5000); p.add_argument('--producer-eps',type=float,default=50); p.add_argument('--consumer-eps',type=float,default=150); p.add_argument('--max-minutes',type=int,default=15); a=p.parse_args(); r=simulate(a.backlog,a.producer_eps,a.consumer_eps,a.max_minutes); print(json.dumps(r,indent=2)); raise SystemExit(0 if r['recovered'] else 1)
if __name__=='__main__': main()
