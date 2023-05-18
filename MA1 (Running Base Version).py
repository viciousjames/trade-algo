
# -*- coding: utf-8 -*-
"""
Created on Fri Nov 25 13:54:27 2022

@author: hohei3
"""

import signal
import requests
import time 
from time import sleep
import re

class ApiException(Exception):
    pass

def signal_handler(signum, frame):
    global shutdown
    signal.signal(signal.SIGINT, signal.SIG_DEL)
    shutdown = True

API_KEY = {'X-API-Key': '81G3AZN4'}
shutdown = False

targets = {
    "BPC":{
        "people":0,
        "%chance":0, 
        "estimate":0,
        "last":0
        }
    }

def get_tick(session):
    resp = session.get('http://localhost:9999/v1/case')
    if resp.status_code == 401:
        raise ApiException('Get tick - ERROR')
    case = resp.json()
    return case['tick']


def update_range(targets, news,session):
    
    x = re.findall('[0-9]+', news[0]["body"])

                           
    news_update = {
        'ticker':"BPC",
        'vote': float(x[1]),
        'probability': float(x[2])/100
        }
    print(news_update)
    
    ticker = news_update.get('ticker')
    
    print(ticker)
    
    PNCC = ticker_close(session, "NCC")
    
    n = {
        news_update['ticker']:{
            "vote":news_update['vote'],
            "%chance":str(round(news_update['probability']*100,2))+"%",
            "estimate":round(20*(1-news_update['probability'])+(0.45*PNCC)*news_update['probability'],2),
            "last": ticker_close(session, "BPC")
            }
        }
    
    targets.update(n)

    return targets.update(n)



# this function sends a http help get to fetch news
def check_news(session, targets, news_count):
    resp = session.get('http://localhost:9999/v1/news?since='+str(news_count))
    if resp.status_code == 401:
        raise ApiException('The API Key provided in this Python code must match')
    news = resp.json()
    if len(news)>0:
        print('New estimate available!')
        news_count += 1
        update_range(targets,news,session)
        return news_count
    else:
        print('There is no new estimates!')
        return news_count



def ticker_close(session, ticker):
    payload = {'ticker': ticker, 'limit': 1}
    resp = session.get('http://localhost:9999/v1/securities/history', params=payload)
    if resp.status_code == 401:
        raise ApiException('The API key provided in this Python code must match that in the RIT client (please refer to the API hyperlink in the client toolbar and/or the RIT – User Guide – REST API Documentation.pdf)')
    ticker_history = resp.json()
    if ticker_history:
        return ticker_history[0]['close']
    else:
        raise ApiException('Response error. Unexpected JSON response.')
############
    


def trading_strategy(session, news_count):
    
    
    payloadBPC = {'ticker': "BPC"}
    respBPC = session.get('http://localhost:9999/v1/securities',params=payloadBPC)
    if respBPC.ok: 
        BPC_position = respBPC.json() 
    
    BPCpos = round(int(BPC_position[0]['position']),2)
     
    
    quantity = 5000
    

    # Normal Order if Within range
    def buy_payload(session, to_buy):
        buy_payload = {'ticker': to_buy, 'type': 'MARKET', 'quantity': quantity, 'action': 'BUY'}
        session.post('http://localhost:9999/v1/orders', params=buy_payload)
        session.post('http://localhost:9999/v1/orders', params=buy_payload)
        session.post('http://localhost:9999/v1/orders', params=buy_payload)
        session.post('http://localhost:9999/v1/orders', params=buy_payload)

    def sell_payload(session,to_sell):
        sell_payload = {'ticker': to_sell, 'type': 'MARKET', 'quantity': quantity, 'action': 'SELL'}
        session.post('http://localhost:9999/v1/orders', params=sell_payload)
        session.post('http://localhost:9999/v1/orders', params=sell_payload)
        session.post('http://localhost:9999/v1/orders', params=sell_payload)
        session.post('http://localhost:9999/v1/orders', params=sell_payload)

        
    # Extreme Order if out of range 
    def buy2_payload(session, to_buy):
        buy_payload = {'ticker': to_buy, 'type': 'MARKET', 'quantity': quantity*2, 'action': 'BUY'}
        session.post('http://localhost:9999/v1/orders', params=buy_payload)
        session.post('http://localhost:9999/v1/orders', params=buy_payload)
        session.post('http://localhost:9999/v1/orders', params=buy_payload)
        session.post('http://localhost:9999/v1/orders', params=buy_payload)


    def sell2_payload(session,to_sell):
        sell_payload = {'ticker': to_sell, 'type': 'MARKET', 'quantity': quantity*2, 'action': 'SELL'}
        session.post('http://localhost:9999/v1/orders', params=sell_payload)
        session.post('http://localhost:9999/v1/orders', params=sell_payload)
        session.post('http://localhost:9999/v1/orders', params=sell_payload)
        session.post('http://localhost:9999/v1/orders', params=sell_payload)
    
    
    ##trading Part 
    
    s = session
    
    BPC_last = ticker_close(s, "BPC")
    
    if targets["BPC"]["estimate"] < BPC_last:
        
        sell_payload(session, "BPC")
    
    elif targets["BPC"]["estimate"] > BPC_last:
        
        buy_payload(session, "BPC")
    
 
                

def main():
    global targets
    global update
    global ticker_name
    # creates a session to manage connections and requests to the RIT Client
    with requests.Session() as s:
        # add the API key to the session to authenticate during requests
        s.headers.update(API_KEY)
        # get the current time of the case
        tick = get_tick(s)
        news_count = 1
        
        # while the time is <= 300
        while tick > 1 and tick < 300:
            
            if tick <= 280:
                # calling the check_news function defined above
                news_count = check_news(s,targets, news_count)
                
                print("Current News = " + str(news_count))
                print(targets)
                sleep(0.5)
                
                if tick > 60 and tick <70:
                    
                    trading_strategy(s, news_count)
                
                if tick > 120 and tick < 130:
                    
                    trading_strategy(s, news_count)
                
                if tick > 180 and tick < 190:
                    
                    trading_strategy(s, news_count)
                
                if tick > 240 and tick < 250:
                    
                    trading_strategy(s, news_count)    
                        
            # refresh the case time
            tick = get_tick(s)
            
        # End of simulation
        print('End of Simulation')

# this calls the main() method when you type 'python lt3.py' into the command prompt
if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)
    main()
    
    